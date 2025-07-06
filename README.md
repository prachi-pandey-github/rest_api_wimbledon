# 🌟 Wimbledon Finals API

A lightweight Flask-based REST API to fetch historical data on Wimbledon Men's Singles Finals from 2014 to 2024. It supports validation, rate limiting, error handling, CORS, and clean logging.

---

## 📦 Features

* Retrieve detailed information about finals for a specific year.
* List all available years.
* Rate-limited to prevent abuse.
* Well-documented API endpoints.
* Includes health check and metadata in responses.
* Configurable security headers and CORS.
* **NEW**: Separate JSON data file for easy maintenance.
* **NEW**: Simple endpoint for clean responses.

---

## 🚀 Installation

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

---

## ⚙️ Usage

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
curl "http://localhost:5000/wimbledon?year=2021"
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
curl "http://localhost:5000/api/wimbledon?year=2021"
```

Response includes additional metadata:
```json
{
  "year": 2021,
  "champion": "Novak Djokovic",
  "runner_up": "Matteo Berrettini",
  "score": "6-7(4-7), 6-4, 6-4, 6-3",
  "sets": 4,
  "tiebreak": true,
  "metadata": {
    "retrieved_at": "2025-07-06T07:28:22.556136Z",
    "data_source": "Wimbledon Championships Records",
    "api_version": "1.0.0"
  }
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

If exceeded, a 429 error will be returned with a `retry_after` hint.

---

## 🔐 Security & Headers

* CORS enabled (`*` by default)
* Security headers included in every response
* `SECRET_KEY` should be configured via environment variables for production use.

---

## 📄 Environment Variables

| Variable     | Default          | Description                         |
| ------------ | ---------------- | ----------------------------------- |
| `PORT`       | `5000`           | Port to run the server on           |
| `FLASK_ENV`  | `production`     | Set to `development` for debug mode |
| `SECRET_KEY` | Auto-generated   | Flask app secret key                |

---

## 🧪 Testing

Test the API endpoints:

```bash
# Test simple endpoint
curl "http://localhost:5000/wimbledon?year=2021"

# Test detailed endpoint
curl "http://localhost:5000/api/wimbledon?year=2021"

# Test error handling
curl "http://localhost:5000/wimbledon?year=2030"
```

---

## 🚀 Production Deployment

For production deployment:

1. Set environment variables:
   ```bash
   export SECRET_KEY="your-secure-secret-key"
   export FLASK_ENV="production"
   ```

2. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 main:app
   ```

3. Configure a proper storage backend for rate limiting (Redis recommended).

---

