# 🌟 Wimbledon Finals API

A lightweight Flask-based REST API to fetch historical data on Wimbledon Men's Singles Finals from 2014 to 2023. It supports validation, rate limiting, error handling, CORS, and clean logging.

---

## 📦 Features

* Retrieve detailed information about finals for a specific year.
* List all available years.
* Rate-limited to prevent abuse.
* Well-documented API endpoints.
* Includes health check and metadata in responses.
* Configurable security headers and CORS.

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
python app.py
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

### 🗓️ Get Finals for a Specific Year

**GET** `/api/wimbledon?year=YYYY`

Query Parameters:

* `year` (required): Year from 2014 to 2023.

Example:

```bash
curl "http://localhost:5000/api/wimbledon?year=2021"
```

---

### 📆 List All Available Years

**GET** `/api/wimbledon/years`

Returns a sorted list of years for which data is available.

---

## 📈 Rate Limiting

* Global: `200/day`, `50/hour`
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
| `SECRET_KEY` | `dev-secret-key` | Flask app secret key                |

---

