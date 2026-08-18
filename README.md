# ⚖️ eCourts Autonomous Legal Case Tracker & WhatsApp Dispatcher

An enterprise-grade, autonomous legal management and case tracking system built for advocates and law practices to monitor Indian court cases (Supreme Court, High Courts, District Courts), manage daily courtroom hearing schedules, predict hearing dates, and automatically dispatch hearing updates to clients via WhatsApp.

---

![eCourts Case Tracker Dashboard Preview](assets/dashboard_preview.png)

---

## 🌟 Key Features

- **🔍 Dual Engine Architecture:**
  - **API-First Engine:** High-speed integration with official eCourts Partner API (`https://webapi.ecourtsindia.com`).
  - **Autonomous Self-Correcting Agent (LangGraph):** Playwright + EasyOCR visual loop that navigates portal CAPTCHAs and auto-retries on failure.
- **🛡️ Fail-Safe Credit-Guard & Local SQLite Chamber Vault:**
  - Zero-credit consumption mode with local caching and offline chamber enrollment.
  - Smart predictive polling (sleeps far-away hearings, only checks near dates).
- **📋 Daily Cause List & Hearing Board:**
  - Court-complex grouped daily hearing board with item numbers, courtroom allocation, and presiding judges.
  - A4 Printable Court Docket and Advocate Case Dossier generators.
- **💬 Automated WhatsApp Dispatcher:**
  - Official Meta WhatsApp Business Cloud API integration.
  - One-click dispatch via WhatsApp Web and WhatsApp Mobile deep links.
- **🤖 JARVIS Agentic Legal AI Co-Pilot:**
  - Morning legal briefing analyzing urgent warrants, injunctions, and courtroom strategies.
  - Interactive natural language queries over the active case portfolio.
- **📊 Prospective Client Leads Management:**
  - Integrated intake funnel for client consultations and matter registrations.

---

## 🏗️ Architecture

```
                       [ ⚖️ Client / Advocate Web UI ]
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
       [ 🚀 eCourts Partner API ]              [ 🤖 LangGraph Vision Agent ]
        (High-speed JSON endpoint)             (Playwright + EasyOCR Loop)
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                        [ 💾 SQLite Database Vault ]
                      (Predictive Polling & Change Tracker)
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
   [ 📲 Meta WhatsApp Cloud API ]              [ 🤖 JARVIS AI Co-Pilot ]
    (Official Client Notifications)             (Morning Strategy Briefing)
```

---

## 📂 Project Structure

```
ecourts-case-tracker/
├── app/                              # Core application package
│   ├── __init__.py                   # App factory (create_app) & lifecycle management
│   ├── config.py                     # Centralized environment configuration
│   ├── api/                          # Modular API Blueprints
│   │   ├── __init__.py               # Blueprint registration
│   │   ├── cases.py                  # Case management & CNR queries (/api/cases, /api/check-case)
│   │   ├── cause_list.py             # Cause list & export routes (/api/cause-list)
│   │   ├── whatsapp.py               # WhatsApp dispatch routes (/api/whatsapp/*)
│   │   ├── ai.py                     # AI Briefing & Copilot query routes (/api/ai-*)
│   │   ├── scheduler.py              # Background sync / scheduler evaluation routes
│   │   ├── leads.py                  # Prospective client inquiries (/api/leads)
│   │   ├── settings.py               # Advocate & API settings (/api/advocate-settings)
│   │   └── health.py                 # Health checks & keep-alive (/healthz, /api/health)
│   ├── services/                     # Business logic & external domain integrations
│   │   ├── __init__.py
│   │   ├── ecourts_service.py        # eCourts Partner API client & circuit breaker
│   │   ├── whatsapp_service.py       # Meta WhatsApp Cloud API integration
│   │   ├── sync_service.py           # Predictive polling worker & scheduler engine
│   │   ├── ai_service.py             # JARVIS Agentic Legal AI reasoning engine
│   │   └── vision_agent.py           # LangGraph + Playwright OCR fallback loop
│   ├── db/                           # SQLite database access layer
│   │   ├── __init__.py
│   │   ├── database.py               # Connection pool with WAL mode & migrations
│   │   ├── repository.py             # CRUD methods for cases, logs, leads, cache
│   │   └── seed_data.py              # Sample court hearings & IST synchronizer
│   └── templates/                    # Jinja2 HTML templates for reports
│       ├── cause_list_print.html     # A4 Printable Daily Court Hearing Board docket
│       └── case_dossier.html         # A4 Printable Advocate Case Brief Dossier
├── static/                           # Web Dashboard Frontend
│   ├── index.html                    # Single-Page Application interface
│   ├── style.css                     # Responsive styling & design tokens
│   ├── app.js                        # Frontend interactive application logic
│   └── logo.jpg                      # Court / firm emblem asset
├── tests/                            # Automated test suite (Pytest)
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures & isolated DB setup
│   ├── test_api_routes.py            # API endpoint integration tests
│   ├── test_database.py              # Repository & migration unit tests
│   ├── test_services.py              # eCourts, WhatsApp & AI service tests
│   └── test_scheduler.py             # Predictive polling & credit shield tests
├── scripts/                          # Utility & CLI tools
│   ├── case_tracker.py               # CLI runner for terminal case lookup
│   ├── run_vision_agent.py           # CLI runner for LangGraph Vision Agent
│   ├── update_dates.py               # Date synchronization helper
│   └── capture_readme_shot.py        # Automated screenshot generator
├── data/                             # Persistent SQLite storage directory
│   └── cases.db                      # Local database file (git-ignored)
├── run.py                            # Local development entrypoint (`python run.py`)
├── wsgi.py                           # Production WSGI entrypoint (`gunicorn wsgi:app`)
├── server.py                         # Backward-compatible entrypoint shim
├── Procfile                          # Cloud deployment configuration (Render / Heroku)
├── requirements.txt                  # Production dependencies
├── requirements-dev.txt              # Developer & testing dependencies
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore rules
└── README.md                         # Project documentation
```

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/Mukil630/ecourts-case-tracker.git
cd ecourts-case-tracker
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and add your credentials:
```bash
cp .env.example .env
```
```env
ECOURTS_API_KEY=eci_live_your_api_key_here
```
*(Get ₹200 free API trial credits at [webapi.ecourtsindia.com](https://webapi.ecourtsindia.com))*

---

## 🖥️ Running Locally

### 🌐 Option A: Start the Development Server
```bash
python run.py
```
Open your browser at: `http://127.0.0.1:5000`

### 💻 Option B: Run CLI Case Tracker
```bash
python scripts/case_tracker.py DLND020047882015 --name "Client Name" --phone "+919876543210"
```

### 🤖 Option C: Run Autonomous LangGraph Agent Loop
```bash
python scripts/run_vision_agent.py DLND020047882015
```

### 🧪 Option D: Run Test Suite
```bash
python -m pytest tests -v
```

---

## 🌐 Live Cloud Deployment

The platform is configured for instant 24/7 cloud deployment on **Render**:
* **Live Web App:** [https://ecourts-case-tracker.onrender.com](https://ecourts-case-tracker.onrender.com)
* **Health Check & Keep-Alive:** [https://ecourts-case-tracker.onrender.com/healthz](https://ecourts-case-tracker.onrender.com/healthz)

---

## 📜 License
MIT License. Developed by **Mukil**.
