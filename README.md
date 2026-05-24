# Breathe ESG

Enterprise carbon emissions data ingestion, normalization, and review platform.

## What It Does

Breathe ESG ingests messy real-world emissions data from three source types:

| Source | Scope | Input Format | Key Challenge |
|--------|-------|--------------|---------------|
| **SAP Fuel & Procurement** | Scope 1 | ME2M CSV export (German locale) | Semicolons, comma decimals, plant codes, material groups |
| **Utility Electricity** | Scope 2 | Portal CSV (Green Button-style) | Non-calendar billing periods, meter multipliers, estimated reads |
| **Corporate Travel** | Scope 3, Cat. 6 | TMC report CSV (Concur-style) | IATA code → distance calculation, cabin class factors, hotel nights |

It normalizes units, calculates CO₂e using versioned emission factors, flags anomalies, and provides a review dashboard where analysts can approve, reject, and lock records before audit submission.

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend

```bash
cd breathe-esg/backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed reference data (emission factors, airports, plant codes, demo user)
python manage.py seed_data

# Start server
python manage.py runserver
```

### Frontend

```bash
cd breathe-esg/frontend

# Install dependencies
npm install

# Start dev server (proxies API to localhost:8000)
npm run dev
```

### Demo Credentials

```
Username: analyst
Password: breathe2024
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                 React SPA (Vite)                      │
│  Dashboard │ Upload │ Review Queue │ Detail Panel      │
└──────────────────────┬───────────────────────────────┘
                       │ REST API (JWT Auth)
┌──────────────────────┴───────────────────────────────┐
│                Django REST Framework                   │
│                                                        │
│  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌────────┐ │
│  │  core   │  │ ingestion │  │emissions │  │ review │ │
│  │ (auth)  │  │ (parsers) │  │(records) │  │(audit) │ │
│  └────┬────┘  └─────┬─────┘  └────┬─────┘  └───┬────┘ │
│       │             │             │             │      │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐ │
│  │              SQLite / PostgreSQL                   │ │
│  └───────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

## Sample Data

Three sample CSV files are included in `backend/sample_data/`:

- **sap_fuel_export.csv** — 25 rows, semicolon-delimited, German headers/numbers
- **utility_electricity.csv** — 18 rows, 3 meters, non-calendar billing periods
- **travel_report.csv** — 26 rows, flights/hotels/cars/taxis across 11 trips

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login/` | JWT login |
| POST | `/api/auth/register/` | Create tenant + user |
| POST | `/api/auth/token/refresh/` | Refresh JWT |
| GET | `/api/dashboard/summary/` | Scope totals, review counts |
| POST | `/api/ingestion/upload/` | Upload CSV (multipart) |
| GET | `/api/ingestion/history/` | List uploads |
| GET | `/api/emissions/records/` | Filtered emission records |
| GET | `/api/emissions/records/{id}/` | Record detail + audit trail |
| POST | `/api/review/approve/` | Bulk approve |
| POST | `/api/review/reject/` | Bulk reject |
| POST | `/api/review/lock/` | Lock for audit |

## Documentation

- [MODEL.md](MODEL.md) — Data model with design rationale
- [DECISIONS.md](DECISIONS.md) — Architecture decisions and alternatives considered
- [TRADEOFFS.md](TRADEOFFS.md) — Honest tradeoffs and what we traded away
- [SOURCES.md](SOURCES.md) — Emission factor databases and technical references
