from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import os
import secrets
from datetime import datetime
import logging
import json
import redis
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
 
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['JSON_SORT_KEYS'] = False

# Redis configuration
def get_redis_connection():
    """Create Redis connection with fallback configuration"""
    redis_url = os.environ.get('REDIS_URL')
    
    if redis_url:
        # Parse Redis URL (useful for production environments like Heroku)
        url = urlparse(redis_url)
        return redis.Redis(
            host=url.hostname,
            port=url.port,
            password=url.password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
    else:
        # Local Redis configuration
        return redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', 6379)),
            password=os.environ.get('REDIS_PASSWORD'),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )

# Initialize Redis connection
try:
    redis_client = get_redis_connection()
    redis_client.ping()  # Test connection
    logger.info("Redis connection established successfully")
    REDIS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Falling back to in-memory operations.")
    redis_client = None
    REDIS_AVAILABLE = False

# CORS configuration
CORS(app, origins=['*'])  # In production, specify allowed origins

# Rate limiting with Redis backend
if REDIS_AVAILABLE:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=f"redis://{redis_client.connection_pool.connection_kwargs.get('host', 'localhost')}:{redis_client.connection_pool.connection_kwargs.get('port', 6379)}"
    )
else:
    # Fallback to memory-based rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
limiter.init_app(app)

# Load Wimbledon data from JSON file
with open('wimbledon_data.json', 'r', encoding='utf-8') as f:
    WIMBLEDON_DATA = {int(k): v for k, v in json.load(f).items()}

# Cache configuration
CACHE_TTL = {
    'wimbledon_data': 3600,  # 1 hour for individual year data
    'available_years': 7200,  # 2 hours for years list
    'health_check': 60       # 1 minute for health check
}

# Redis helper functions
def get_cache_key(prefix, *args):
    """Generate cache key with prefix and arguments"""
    return f"{prefix}:{'_'.join(map(str, args))}"

def get_from_cache(key):
    """Get data from Redis cache with fallback"""
    if not REDIS_AVAILABLE:
        return None
    
    try:
        cached_data = redis_client.get(key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Cache read error for key {key}: {e}")
    
    return None

def set_cache(key, data, ttl=3600):
    """Set data in Redis cache with fallback"""
    if not REDIS_AVAILABLE:
        return False
    
    try:
        redis_client.setex(key, ttl, json.dumps(data))
        return True
    except Exception as e:
        logger.warning(f"Cache write error for key {key}: {e}")
        return False

def invalidate_cache_pattern(pattern):
    """Invalidate cache keys matching pattern"""
    if not REDIS_AVAILABLE:
        return
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching pattern: {pattern}")
    except Exception as e:
        logger.warning(f"Cache invalidation error for pattern {pattern}: {e}")

# Cache decorator
def cache_response(cache_key_prefix, ttl=3600):
    """Decorator to cache API responses"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = get_cache_key(cache_key_prefix, *args, 
                                    *[v for v in kwargs.values()],
                                    *[request.args.get(k, '') for k in sorted(request.args.keys())])
            
            # Try to get from cache
            cached_response = get_from_cache(cache_key)
            if cached_response:
                logger.info(f"Cache hit for key: {cache_key}")
                # Add cache indicator to response
                if isinstance(cached_response, dict):
                    cached_response['cache_info'] = {
                        'cached': True,
                        'cache_key': cache_key,
                        'served_at': datetime.utcnow().isoformat() + 'Z'
                    }
                return jsonify(cached_response)
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            
            # Cache successful responses
            if isinstance(result, tuple):
                response_data, status_code = result
                if status_code == 200 and hasattr(response_data, 'get_json'):
                    json_data = response_data.get_json()
                    if json_data:
                        set_cache(cache_key, json_data, ttl)
                        logger.info(f"Cached response for key: {cache_key}")
            
            return result
            
        return decorated_function
    return decorator

# Error classes
class ValidationError(Exception):
    def __init__(self, message, code, status_code=400):
        self.message = message
        self.code = code
        self.status_code = status_code

# Validation decorator
def validate_year(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            year_param = request.args.get('year')
            
            if not year_param:
                raise ValidationError(
                    'Year parameter is required',
                    'MISSING_YEAR_PARAMETER'
                )
            
            try:
                year = int(year_param)
            except ValueError:
                raise ValidationError(
                    'Year must be a valid number',
                    'INVALID_YEAR_FORMAT'
                )
            
            if year < 1877:
                raise ValidationError(
                    'Wimbledon tournament started in 1877',
                    'YEAR_TOO_EARLY'
                )
            
            if year > datetime.now().year:
                raise ValidationError(
                    'Cannot request data for future years',
                    'YEAR_IN_FUTURE'
                )
            
            return f(year, *args, **kwargs)
            
        except ValidationError as e:
            return jsonify({
                'error': e.message,
                'code': e.code,
                'message': e.message
            }), e.status_code
            
    return decorated_function

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'code': 'NOT_FOUND',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': [
            'GET /health',
            'GET /api/docs',
            'GET /wimbledon?year=YYYY',
            'GET /api/wimbledon?year=YYYY',
            'GET /api/wimbledon/years'
        ]
    }), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'error': 'Rate limit exceeded',
        'code': 'RATE_LIMIT_EXCEEDED',
        'message': 'Too many requests. Please try again later.',
        'retry_after': str(e.retry_after)
    }), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Internal server error: {error}')
    return jsonify({
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR',
        'message': 'An unexpected error occurred while processing your request'
    }), 500

@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({
        'error': e.message,
        'code': e.code,
        'message': e.message
    }), e.status_code

# Routes
@app.route('/health', methods=['GET'])
@cache_response('health', CACHE_TTL['health_check'])
def health_check():
    """Health check endpoint for monitoring"""
    redis_status = 'connected'
    redis_info = {}
    
    if REDIS_AVAILABLE:
        try:
            redis_client.ping()
            redis_info = {
                'connected': True,
                'version': redis_client.info().get('redis_version', 'unknown'),
                'memory_usage': redis_client.info().get('used_memory_human', 'unknown'),
                'connected_clients': redis_client.info().get('connected_clients', 0)
            }
        except Exception as e:
            redis_status = 'error'
            redis_info = {'connected': False, 'error': str(e)}
    else:
        redis_status = 'unavailable'
        redis_info = {'connected': False, 'reason': 'Redis not configured'}
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': '1.0.0',
        'service': 'wimbledon-api',
        'redis': {
            'status': redis_status,
            'details': redis_info
        },
        'cache': {
            'enabled': REDIS_AVAILABLE,
            'ttl_config': CACHE_TTL
        }
    })

@app.route('/api/docs', methods=['GET'])
def api_documentation():
    """API documentation endpoint"""
    return jsonify({
        'title': 'Wimbledon Finals API',
        'version': '1.0.0',
        'description': 'Get information about Wimbledon men\'s singles finals by year',
        'base_url': request.url_root.rstrip('/'),
        'endpoints': [
            {
                'method': 'GET',
                'path': '/api/wimbledon',
                'description': 'Get Wimbledon final information for a specific year',
                'parameters': [
                    {
                        'name': 'year',
                        'type': 'integer',
                        'required': True,
                        'description': 'Year of the tournament (1877-present)'
                    }
                ],
                'example': f"{request.url_root.rstrip('/')}/api/wimbledon?year=2021"
            },
            {
                'method': 'GET',
                'path': '/api/wimbledon/years',
                'description': 'Get list of available years',
                'parameters': [],
                'example': f"{request.url_root.rstrip('/')}/api/wimbledon/years"
            },
            {
                'method': 'GET',
                'path': '/api/cache/stats',
                'description': 'Get cache statistics and Redis information',
                'parameters': [],
                'example': f"{request.url_root.rstrip('/')}/api/cache/stats"
            },
            {
                'method': 'POST',
                'path': '/api/cache/clear',
                'description': 'Clear all cached data (admin endpoint)',
                'parameters': [],
                'example': f"{request.url_root.rstrip('/')}/api/cache/clear"
            }
        ],
        'response_format': {
            'year': 'integer',
            'champion': 'string',
            'runner_up': 'string',
            'score': 'string',
            'sets': 'integer',
            'tiebreak': 'boolean',
            'metadata': {
                'retrieved_at': 'ISO 8601 timestamp',
                'data_source': 'string'
            }
        },
        'rate_limits': {
            'per_hour': 50,
            'per_day': 200
        }
    })

@app.route('/wimbledon', methods=['GET'])
@limiter.limit("30 per minute")
@validate_year
@cache_response('wimbledon_simple', CACHE_TTL['wimbledon_data'])
def get_wimbledon_final_simple(year):
    """Get Wimbledon final information for a specific year (simple endpoint)"""
    try:
        logger.info(f'Request for year {year} from {request.remote_addr} (simple endpoint)')
        
        final_data = WIMBLEDON_DATA.get(year)
        
        if not final_data:
            return jsonify({
                'error': 'Data not found',
                'code': 'YEAR_NOT_FOUND',
                'message': f'No data available for year {year}',
                'year': year
            }), 404
        
        # Return simple response matching the example format
        response = {
            'year': year,
            'champion': final_data['champion'],
            'runner_up': final_data['runner_up'],
            'score': final_data['score'],
            'sets': final_data['sets'],
            'tiebreak': final_data['tiebreak']
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f'Error processing request for year {year}: {str(e)}')
        return jsonify({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred while processing your request'
        }), 500

@app.route('/api/wimbledon', methods=['GET'])
@limiter.limit("30 per minute")
@validate_year
@cache_response('wimbledon_api', CACHE_TTL['wimbledon_data'])
def get_wimbledon_final(year):
    """Get Wimbledon final information for a specific year"""
    try:
        logger.info(f'Request for year {year} from {request.remote_addr}')
        
        final_data = WIMBLEDON_DATA.get(year)
        
        if not final_data:
            return jsonify({
                'error': 'Data not found',
                'code': 'YEAR_NOT_FOUND',
                'message': f'No data available for year {year}',
                'year': year,
                'available_years_endpoint': f"{request.url_root.rstrip('/')}/api/wimbledon/years"
            }), 404
        
        # Construct response
        response = {
            'year': year,
            **final_data,
            'metadata': {
                'retrieved_at': datetime.utcnow().isoformat() + 'Z',
                'data_source': 'Wimbledon Championships Records',
                'api_version': '1.0.0'
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f'Error processing request for year {year}: {str(e)}')
        return jsonify({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred while processing your request'
        }), 500

@app.route('/api/wimbledon/years', methods=['GET'])
@limiter.limit("10 per minute")
@cache_response('available_years', CACHE_TTL['available_years'])
def get_available_years():
    """Get list of available years"""
    try:
        available_years = sorted(WIMBLEDON_DATA.keys(), reverse=True)
        
        return jsonify({
            'available_years': available_years,
            'total_years': len(available_years),
            'range': {
                'earliest': min(available_years),
                'latest': max(available_years)
            },
            'metadata': {
                'retrieved_at': datetime.utcnow().isoformat() + 'Z',
                'total_tournaments': len([y for y in available_years if WIMBLEDON_DATA[y]['champion'] != 'Tournament Cancelled'])
            }
        })
        
    except Exception as e:
        logger.error(f'Error getting available years: {str(e)}')
        return jsonify({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred while processing your request'
        }), 500

@app.route('/api/cache/clear', methods=['POST'])
@limiter.limit("5 per minute")
def clear_cache():
    """Clear all cached data (admin endpoint)"""
    try:
        if not REDIS_AVAILABLE:
            return jsonify({
                'error': 'Cache not available',
                'code': 'CACHE_UNAVAILABLE',
                'message': 'Redis is not configured or unavailable'
            }), 503
        
        # Clear all cache keys with our prefixes
        patterns = ['wimbledon_simple:*', 'wimbledon_api:*', 'available_years:*', 'health:*']
        total_cleared = 0
        
        for pattern in patterns:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                total_cleared += len(keys)
        
        logger.info(f"Cache cleared: {total_cleared} keys removed")
        
        return jsonify({
            'success': True,
            'message': f'Cache cleared successfully. {total_cleared} keys removed.',
            'cleared_at': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f'Error clearing cache: {str(e)}')
        return jsonify({
            'error': 'Cache clear failed',
            'code': 'CACHE_CLEAR_ERROR',
            'message': 'An error occurred while clearing the cache'
        }), 500

@app.route('/api/cache/stats', methods=['GET'])
@limiter.limit("10 per minute")
def cache_stats():
    """Get cache statistics"""
    try:
        if not REDIS_AVAILABLE:
            return jsonify({
                'cache_enabled': False,
                'redis_available': False,
                'message': 'Redis is not configured or unavailable'
            })
        
        # Get Redis info
        info = redis_client.info()
        
        # Count cache keys by prefix
        cache_counts = {}
        for prefix in ['wimbledon_simple', 'wimbledon_api', 'available_years', 'health']:
            keys = redis_client.keys(f"{prefix}:*")
            cache_counts[prefix] = len(keys)
        
        return jsonify({
            'cache_enabled': True,
            'redis_available': True,
            'redis_info': {
                'version': info.get('redis_version'),
                'memory_usage': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_keys': info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': round((info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0))) * 100, 2)
            },
            'cache_counts': cache_counts,
            'total_cached_items': sum(cache_counts.values()),
            'ttl_configuration': CACHE_TTL,
            'retrieved_at': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f'Error getting cache stats: {str(e)}')
        return jsonify({
            'error': 'Cache stats unavailable',
            'code': 'CACHE_STATS_ERROR',
            'message': 'An error occurred while retrieving cache statistics'
        }), 500

# Add security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"Starting Wimbledon API server on port {port}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"API documentation: http://localhost:{port}/api/docs")
    print(f"Example usage: http://localhost:{port}/api/wimbledon?year=2021")
    
    app.run(host='0.0.0.0', port=port, debug=debug)