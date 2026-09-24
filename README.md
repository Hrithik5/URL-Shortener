# 🔗 URL Shortener

A simple, scalable URL shortener built with **FastAPI, Redis, SQLite, and Apache ZooKeeper**.

The system converts long URLs into short URLs, stores the mapping, caches frequently accessed URLs, tracks clicks, and provides a Streamlit dashboard for testing and monitoring.

## 🏗️ Architecture

![URL Shortener Architecture](URL_Shortener_Architecture.png)

### How It Works

When a user wants to shorten a URL:

```text
Long URL
   │
   ▼
FastAPI
   │
   │ Request unique ID
   ▼
ZooKeeper
   │
   │ Unique ID
   ▼
Base62 Encoding
   │
   │ Short Code
   ▼
SQLite + Redis
   │
   │ Store short code → long URL
   ▼
Short URL
```

### URL Creation Flow

1. The user sends a long URL to the `/shorten` endpoint.
2. FastAPI requests a unique ID from ZooKeeper.
3. ZooKeeper generates the next unique ID.
4. The ID is converted into a short code using **Base62 encoding**.
5. The short code is mapped to the original long URL.
6. The mapping is stored in SQLite.
7. The mapping is also cached in Redis for faster future lookups.
8. The API returns the generated short URL.

For example:

```text
Long URL
https://example.com/a/very/long/url

        ↓

ZooKeeper
Unique ID → 532986463

        ↓

Base62

Short Code → jshgaghwlfg2ywkjfqr

        ↓

Short URL

https://short.ly/jshgaghwlfg2ywkjfqr
```

### URL Redirect Flow

When someone opens the short URL:

```text
Short URL
    │
    ▼
FastAPI
    │
    ▼
Redis
    │
    ├── Cache Hit ──────► Original URL
    │
    └── Cache Miss
             │
             ▼
          SQLite
             │
             ▼
        Original URL
             │
             ▼
        Redirect User
```

Redis is checked first because it is faster than querying the database.

If the URL is not found in Redis, the application retrieves it from SQLite and can cache it for future requests.

---

## ✨ Features

* **URL Shortening** — Converts long URLs into short URLs.
* **Distributed ID Generation** — Uses ZooKeeper to generate unique IDs when multiple application instances create URLs concurrently.
* **Base62 Encoding** — Converts numeric IDs into compact short codes.
* **Redis Caching** — Speeds up frequently accessed URL lookups.
* **Database Persistence** — Stores URL mappings in SQLite.
* **Redis Fallback** — If Redis is unavailable, the application can fetch URLs directly from SQLite.
* **Click Tracking** — Tracks how many times each short URL is accessed.
* **URL Expiration** — Supports optional URL expiry times.
* **Analytics** — Provides URL-level statistics and system metrics.
* **Streamlit Dashboard** — Provides an interactive UI for creating URLs, testing redirects, viewing analytics, and monitoring system components.
* **Docker Support** — Runs Redis and ZooKeeper using Docker Compose.

---

## 🛠️ Tech Stack

| Component     | Technology          | Purpose                              |
| ------------- | ------------------- | ------------------------------------ |
| API           | FastAPI             | Handles URL shortening and redirects |
| Language      | Python 3.12         | Application development              |
| Database      | SQLite + SQLAlchemy | Stores URL mappings and metadata     |
| Cache         | Redis               | Fast URL lookups                     |
| Coordination  | Apache ZooKeeper    | Generates unique IDs                 |
| Encoding      | Base62              | Converts IDs into short codes        |
| Dashboard     | Streamlit           | Testing and monitoring UI            |
| Data / Charts | Pandas, Altair      | Dashboard analytics                  |
| Containers    | Docker Compose      | Runs Redis and ZooKeeper             |

---

## 🚀 Quick Start

### 1. Start Redis and ZooKeeper

Make sure Docker is running, then:

```bash
docker compose up -d
```

This starts the required backing services.

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Using a virtual environment is recommended:

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Start the FastAPI server

```bash
uvicorn app:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

### 4. Start the Streamlit dashboard

Open another terminal:

```bash
streamlit run ui.py
```

Then open:

```text
http://localhost:8501
```

---

## 📡 API Endpoints

| Method | Endpoint        | Description                                             |
| ------ | --------------- | ------------------------------------------------------- |
| `POST` | `/shorten`      | Creates a short URL                                     |
| `GET`  | `/{code}`       | Redirects to the original URL and records the click     |
| `GET`  | `/stats/{code}` | Returns statistics for a short URL                      |
| `GET`  | `/health`       | Checks the health of the database, Redis, and ZooKeeper |
| `GET`  | `/system/stats` | Returns system-level metrics                            |
| `GET`  | `/system/data`  | Returns stored Redis and ZooKeeper data                 |

### Example: Create a Short URL

**Request**

```http
POST /shorten
```

```json
{
  "original_url": "https://example.com/a/very/long/url",
  "expiry_hours": 24
}
```

**Response**

```json
{
  "short_url": "http://localhost:8000/jshgaghwlfg2ywkjfqr"
}
```

### Example: Redirect

Open:

```text
http://localhost:8000/jshgaghwlfg2ywkjfqr
```

The API looks up the short code and redirects the user to the original URL.

---

## 🔑 Why ZooKeeper?

When the application runs with multiple FastAPI instances, multiple users can create URLs at the same time.

For example:

```text
Server 1 ──┐
Server 2 ──┼──► ZooKeeper
Server 3 ──┘
```

ZooKeeper coordinates the ID counter so that concurrent requests receive different IDs:

```text
Request 1 → 501
Request 2 → 502
Request 3 → 503
```

These IDs are then converted to short codes using Base62.

> ZooKeeper is used for **ID coordination**. It does not store the original URLs.

---

## ⚡ Why Redis?

Redis provides a fast way to retrieve frequently accessed URLs.

Without Redis:

```text
Short URL
   ↓
SQLite
   ↓
Original URL
```

With Redis:

```text
Short URL
   ↓
Redis
   ↓
Original URL
```

If Redis does not contain the URL, the application falls back to SQLite.

This follows a **cache-aside pattern**.

---

## 📊 Dashboard

The Streamlit dashboard allows you to:

* Create short URLs
* Test URL redirects
* View click counts
* View URL metadata
* Check Redis status
* Check ZooKeeper status
* View system metrics
* Inspect stored data

Run it with:

```bash
streamlit run ui.py
```

---

## 📁 Project Structure

```text
URL-Shortener/
│
├── app.py                 # FastAPI application
├── ui.py                  # Streamlit dashboard
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Redis + ZooKeeper
├── URL_Shortener_Architecture.png
├── README.md
└── LICENSE
```

---

## 🧠 Architecture Summary

The system has four main responsibilities:

```text
FastAPI
   │
   ├── API & URL handling
   │
   ▼
ZooKeeper
   │
   └── Unique ID generation
   │
   ▼
Base62
   │
   └── Short code generation
   │
   ├───────────────┐
   ▼               ▼
SQLite           Redis
   │               │
   │ Persistence   │ Fast lookup
   └───────────────┘
```

**In short:**

* **FastAPI** handles requests.
* **ZooKeeper** generates unique IDs.
* **Base62** converts IDs into short codes.
* **SQLite** stores the URL mapping.
* **Redis** provides fast lookups.
* **Streamlit** provides a testing and monitoring dashboard.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
