from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import os
import secrets
from datetime import datetime
import logging
import redis
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['JSON_SORT_KEYS'] = False
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Environment configuration
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
DATABASE_URL = os.environ.get('DATABASE_URL', None)
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')

# CORS configuration
if FLASK_ENV == 'production':
    CORS(app, origins=ALLOWED_ORIGINS)
else:
    CORS(app, origins=['*'])  # Allow all origins in development

# Redis connection for rate limiting
try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()  # Test connection
    logger.info("Redis connection successful")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Using in-memory storage for rate limiting.")
    redis_client = None

# Rate limiting configuration
if redis_client:
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=REDIS_URL
    )
else:
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

# Wimbledon men's singles finals data
# In production, this would be stored in a database
WIMBLEDON_DATA = {
    2023: {
        "champion": "Novak Djokovic",
        "runner_up": "Carlos Alcaraz",
        "score": "1–6, 7–6(6–8), 6–1, 3–6, 6–4",
        "sets": 5,
        "tiebreak": True
    },
    2022: {
        "champion": "Novak Djokovic",
        "runner_up": "Nick Kyrgios",
        "score": "4–6, 6–3, 6–4, 7–6(7–3)",
        "sets": 4,
        "tiebreak": True
    },
    2021: {
        "champion": "Novak Djokovic",
        "runner_up": "Matteo Berrettini",
        "score": "6–7(4–7), 6–4, 6–4, 6–3",
        "sets": 4,
        "tiebreak": True
    },
    2020: {
        "champion": "Tournament Cancelled",
        "runner_up": None,
        "score": None,
        "sets": None,
        "tiebreak": None,
        "note": "Cancelled due to COVID-19 pandemic"
    },
    2019: {
        "champion": "Novak Djokovic",
        "runner_up": "Roger Federer",
        "score": "7–6(7–5), 1–6, 7–6(7–4), 4–6, 13–12(7–3)",
        "sets": 5,
        "tiebreak": True
    },
    2018: {
        "champion": "Novak Djokovic",
        "runner_up": "Kevin Anderson",
        "score": "6–2, 6–2, 7–6(7–3)",
        "sets": 3,
        "tiebreak": True
    },
    2017: {
        "champion": "Roger Federer",
        "runner_up": "Marin Čilić",
        "score": "6–3, 6–1, 6–4",
        "sets": 3,
        "tiebreak": False
    },
    2016: {
        "champion": "Andy Murray",
        "runner_up": "Milos Raonic",
        "score": "6–4, 7–6(7–3), 7–6(7–2)",
        "sets": 3,
        "tiebreak": True
    },
    2015: {
        "champion": "Novak Djokovic",
        "runner_up": "Roger Federer",
        "score": "7–6(7–1), 6–7(10–12), 6–4, 6–3",
        "sets": 4,
        "tiebreak": True
    },
    2014: {
        "champion": "Novak Djokovic",
        "runner_up": "Roger Federer",
        "score": "6–7(7–9), 6–4, 7–6(7–4), 5–7, 6–4",
        "sets": 5,
        "tiebreak": True
    },
    2013: {
        "champion": "Andy Murray",
        "runner_up": "Novak Djokovic",
        "score": "6–4, 7–5, 6–4",
        "sets": 3,
        "tiebreak": False
    },
    2012: {
        "champion": "Roger Federer",
        "runner_up": "Andy Murray",
        "score": "4–6, 7–5, 6–3, 6–4",
        "sets": 4,
        "tiebreak": False
    },
    2011: {
        "champion": "Novak Djokovic",
        "runner_up": "Rafael Nadal",
        "score": "6–4, 6–1, 1–6, 6–3",
        "sets": 4,
        "tiebreak": False
    },
    2010: {
        "champion": "Rafael Nadal",
        "runner_up": "Tomáš Berdych",
        "score": "6–3, 7–5, 6–4",
        "sets": 3,
        "tiebreak": False
    }
}

# Error classes
class ValidationError(Exception):
    def __init__(self, message, code, status_code=400):
        self.message = message
        self.code = code
        self.status_code = status_code

# Health check functions
def check_redis_health():
    """Check Redis connection health"""
    try:
        if redis_client:
            redis_client.ping()
            return True
        return False
    except Exception:
        return False

def check_database_health():
    """Check database connection health"""
    # In production, implement actual database health check
    # For now, return True as we're using in-memory data
    return True

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
            'GET /ready',
            'GET /api/docs',
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
def health_check():
    """Basic health check endpoint for load balancer"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': '1.0.0',
        'service': 'wimbledon-api'
    })

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Detailed readiness check for Kubernetes"""
    redis_healthy = check_redis_health()
    database_healthy = check_database_health()
    
    overall_status = 'ready' if redis_healthy and database_healthy else 'not ready'
    status_code = 200 if overall_status == 'ready' else 503
    
    return jsonify({
        'status': overall_status,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': '1.0.0',
        'service': 'wimbledon-api',
        'environment': FLASK_ENV,
        'checks': {
            'redis': 'healthy' if redis_healthy else 'unhealthy',
            'database': 'healthy' if database_healthy else 'unhealthy'
        }
    }), status_code

@app.route('/api/docs', methods=['GET'])
def api_documentation():
    """API documentation endpoint"""
    return jsonify({
        'title': 'Wimbledon Finals API',
        'version': '1.0.0',
        'description': 'Get information about Wimbledon men\'s singles finals by year',
        'base_url': request.url_root.rstrip('/'),
        'environment': FLASK_ENV,
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
            'per_minute': 30,
            'per_hour': 50,
            'per_day': 200
        }
    })

@app.route('/api/wimbledon', methods=['GET'])
@limiter.limit("30 per minute")
@validate_year
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
                'total_tournaments': len([y for y in available_years if WIMBLEDON_DATA[y]['champion'] != 'Tournament Cancelled']),
                'cancelled_tournaments': len([y for y in available_years if WIMBLEDON_DATA[y]['champion'] == 'Tournament Cancelled'])
            }
        })
        
    except Exception as e:
        logger.error(f'Error getting available years: {str(e)}')
        return jsonify({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred while processing your request'
        }), 500

@app.route('/api/wimbledon/stats', methods=['GET'])
@limiter.limit("10 per minute")
def get_wimbledon_stats():
    """Get Wimbledon statistics"""
    try:
        # Calculate statistics
        valid_tournaments = [data for data in WIMBLEDON_DATA.values() if data['champion'] != 'Tournament Cancelled']
        
        champion_counts = {}
        for tournament in valid_tournaments:
            champion = tournament['champion']
            champion_counts[champion] = champion_counts.get(champion, 0) + 1
        
        # Sort by wins
        top_champions = sorted(champion_counts.items(), key=lambda x: x[1], reverse=True)
        
        return jsonify({
            'total_tournaments': len(valid_tournaments),
            'cancelled_tournaments': len(WIMBLEDON_DATA) - len(valid_tournaments),
            'year_range': {
                'earliest': min(WIMBLEDON_DATA.keys()),
                'latest': max(WIMBLEDON_DATA.keys())
            },
            'most_successful_champions': top_champions[:10],
            'statistics': {
                'tournaments_with_tiebreak': len([t for t in valid_tournaments if t.get('tiebreak', False)]),
                'five_set_matches': len([t for t in valid_tournaments if t.get('sets') == 5]),
                'straight_set_victories': len([t for t in valid_tournaments if t.get('sets') == 3])
            },
            'metadata': {
                'retrieved_at': datetime.utcnow().isoformat() + 'Z',
                'data_source': 'Wimbledon Championships Records',
                'api_version': '1.0.0'
            }
        })
        
    except Exception as e:
        logger.error(f'Error getting statistics: {str(e)}')
        return jsonify({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred while processing your request'
        }), 500

# Add security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Only add HSTS in production with HTTPS
    if FLASK_ENV == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

# Request logging middleware
@app.before_request
def log_request_info():
    """Log request information"""
    logger.info(f'{request.method} {request.url} - {request.remote_addr}')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = FLASK_ENV == 'development'
    
    # Log startup information
    logger.info(f"Starting Wimbledon API server")
    logger.info(f"Environment: {FLASK_ENV}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Redis connected: {redis_client is not None}")
    
    print(f"Starting Wimbledon API server on port {port}")
    print(f"Environment: {FLASK_ENV}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"Readiness check: http://localhost:{port}/ready")
    print(f"API documentation: http://localhost:{port}/api/docs")
    print(f"Example usage: http://localhost:{port}/api/wimbledon?year=2021")
    
    # In production, use a proper WSGI server like Gunicorn
    if FLASK_ENV == 'production':
        print("WARNING: Running with Flask's built-in server in production is not recommended.")
        print("Use a production WSGI server like Gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 main:app")
    
    app.run(host='0.0.0.0', port=port, debug=debug)