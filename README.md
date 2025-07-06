# 🌟 Wimbledon Finals API

A lightweight Flask-based REST API to fetch historical data on Wimbledon Men's Singles Finals from 2014 to 2024. Features Redis caching, rate limiting, error handling, CORS, and comprehensive logging.

---

## 📦 Features

* Retrieve detailed information about finals for a specific year.
* List all available years.
* **Redis caching** for improved performance.
* Rate-limited to prevent abuse (Redis-backed).
* Well-documented API endpoints.
* Health check with Redis status monitoring.
* Cache management endpoints.
* Configurable security headers and CORS
* **Production-ready** with Render deployment support.
* Graceful fallback when Redis is unavailable.


---

## 🚀 Installation

### Local Development

1. Clone the repository:

```bash
git clone https://github.com/your-username/wimbledon-api.git
cd wimbledon-api
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed Render deployment instructions.

---

## ⚙️ Usage

### Local Development

Start the Flask server:

```bash
python main.py
```

The server will be available at `http://localhost:5000`

---

## 🔌 API Endpoints

### 🔍 Health Check

**GET** `/health`

Returns the health status of the API.

---

### 📜 API Documentation

**GET** `/api/docs`

Returns metadata and documentation about available endpoints.

---

### 🗓️ Get Finals for a Specific Year (Simple)

**GET** `/wimbledon?year=YYYY`

Query Parameters:

* `year` (required): Year from 2014 to 2024.

Example:

```bash
https://rest-api-wimbledon-1.onrender.com/wimbledon?year=2021
```

Response:
```json
{
  "year": 2021,
  "champion": "Novak Djokovic",
  "runner_up": "Matteo Berrettini",
  "score": "6-7(4-7), 6-4, 6-4, 6-3",
  "sets": 4,
  "tiebreak": true
}
```

---

### 🗓️ Get Finals for a Specific Year (Detailed)

**GET** `/api/wimbledon?year=YYYY`

Query Parameters:

* `year` (required): Year from 2014 to 2024.

Example:

```bash
https://rest-api-wimbledon-1.onrender.com/api/wimbledon?year=2024
```

Response includes additional metadata:
```json
{
  "champion": "Carlos Alcaraz",
  "metadata": {
    "api_version": "1.0.0",
    "data_source": "Wimbledon Championships Records",
    "retrieved_at": "2025-07-06T14:46:47.651931Z"
  },
  "runner_up": "Novak Djokovic",
  "score": "6-2, 6-2, 7-6(7-4)",
  "sets": 3,
  "tiebreak": true,
  "year": 2024
}
```

---

### 📆 List All Available Years

**GET** `/api/wimbledon/years`

Returns a sorted list of years for which data is available.

---

## 📊 Data Management

The Wimbledon data is stored in `wimbledon_data.json` for easy maintenance. To add new years or update results:

1. Edit `wimbledon_data.json`
2. Restart the server
3. No code changes required!

Example data structure:
```json
{
  "2024": {
    "champion": "Carlos Alcaraz",
    "runner_up": "Novak Djokovic",
    "score": "6-2, 6-2, 7-6(7-4)",
    "sets": 3,
    "tiebreak": true
  }
}
```

---

## 📈 Rate Limiting

* Global: `200/day`, `50/hour`
* `/wimbledon`: `30/minute`
* `/api/wimbledon`: `30/minute`
* `/api/wimbledon/years`: `10/minute`
* `/api/cache/clear`: `5/minute`
* `/api/cache/stats`: `10/minute`

Rate limiting uses Redis when available, falls back to memory-based limiting.

---

## 💾 Redis Caching

The API includes Redis-based caching for improved performance:

### Cache Configuration
* **Wimbledon data**: 1 hour TTL
* **Available years**: 2 hours TTL  
* **Health check**: 1 minute TTL

### Cache Management Endpoints
* `GET /api/cache/stats` - View cache statistics
* `POST /api/cache/clear` - Clear all cached data

### Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_URL` | Full Redis connection string | `redis://username:password@host:port` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_PASSWORD` | Redis password | `your-password` |

---

## 🔐 Security & Headers

* CORS configured for production domains
* Security headers included in every response
* Rate limiting with Redis backend
* Environment-based secret key management

---

## 📄 Environment Variables

| Variable     | Default          | Description                         |
| ------------ |---------------- | ----------------------------------- |
| `PORT`       | `5000`           | Port to run the server on           |
| `FLASK_ENV`  | `production`     | Set to `development` for debug mode |
| `SECRET_KEY` | Auto-generated   | Flask app secret key                |
| `REDIS_URL`  | None             | Redis connection string             |
| `REDIS_HOST` | `localhost`      | Redis host for local development    |
| `REDIS_PORT` | `6379`           | Redis port                          |

---

## 🧪 Testing

Test the API endpoints:

```bash
# Test simple endpoint
https://rest-api-wimbledon-1.onrender.com/wimbledon?year=2024

# Test detailed endpoint with caching
https://rest-api-wimbledon-1.onrender.com/api/wimbledon?year=2024


# Test error handling
https://rest-api-wimbledon-1.onrender.com/wimbledon?year=2030

