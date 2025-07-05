from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'thisisasecretkey')
app.config['JSON_SORT_KEYS'] = False

# CORS configuration
CORS(app, origins=['*'])  # In production, specify allowed origins

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
limiter.init_app(app)

# Wimbledon men's singles finals data
WIMBLEDON_DATA = {
    2023: {
        "champion": "Novak Djokovic",
        "runner_up": "Carlos Alcaraz",
        "score": "1-6, 7-6(6-8), 6-1, 3-6, 6-4",
        "sets": 5,
        "tiebreak": True
    },
    2022: {
        "champion": "Novak Djokovic",
        "runner_up": "Nick Kyrgios",
        "score": "4-6, 6-3, 6-4, 7-6(7-3)",
        "sets": 4,
        "tiebreak": True
    },
    2021: {
        "champion": "Novak Djokovic",
        "runner_up": "Matteo Berrettini",
        "score": "6-7(4-7), 6-4, 6-4, 6-3",
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
        "score": "7-6(7-5), 1-6, 7-6(7-4), 4-6, 13-12(7-3)",
        "sets": 5,
        "tiebreak": True
    },
    2018: {
        "champion": "Novak Djokovic",
        "runner_up": "Kevin Anderson",
        "score": "6-2, 6-2, 7-6(7-3)",
        "sets": 3,
        "tiebreak": True
    },
    2017: {
        "champion": "Roger Federer",
        "runner_up": "Marin Čilić",
        "score": "6-3, 6-1, 6-4",
        "sets": 3,
        "tiebreak": False
    },
    2016: {
        "champion": "Andy Murray",
        "runner_up": "Milos Raonic",
        "score": "6-4, 7-6(7-3), 7-6(7-2)",
        "sets": 3,
        "tiebreak": True
    },
    2015: {
        "champion": "Novak Djokovic",
        "runner_up": "Roger Federer",
        "score": "7-6(7-1), 6-7(10-12), 6-4, 6-3",
        "sets": 4,
        "tiebreak": True
    },
    2014: {
        "champion": "Novak Djokovic",
        "runner_up": "Roger Federer",
        "score": "6-7(7-9), 6-4, 7-6(7-4), 5-7, 6-4",
        "sets": 5,
        "tiebreak": True
    }
}

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
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': '1.0.0',
        'service': 'wimbledon-api'
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