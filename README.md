# ⚖️ eCourts Autonomous Legal Case Tracker & Practice Management Suite

[![Live Cloud App](https://img.shields.io/badge/Render-Live%20Deploy-success?style=for-the-badge&logo=render)](https://ecourts-case-tracker.onrender.com)
[![Tests Passing](https://img.shields.io/badge/Pytest-29%2F29%20Passed-brightgreen?style=for-the-badge&logo=pytest)](https://github.com/Mukil630/ecourts-case-tracker)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/License-MIT-amber?style=for-the-badge)](LICENSE)

An enterprise-grade, autonomous legal practice management and case tracking system purpose-built for **Advocate R. Anbaiya & Associates** (*Karur Bar Association*) to monitor Indian court proceedings, manage daily courtroom hearing schedules, automate client notices safely, and run AI-assisted chamber briefings.

---

![eCourts Case Tracker Live Dashboard Preview](assets/dashboard_preview.png)

---

## 🌐 Live Demonstrations

* 🚀 **Live Cloud Web App:** [https://ecourts-case-tracker.onrender.com](https://ecourts-case-tracker.onrender.com)
* ⚡ **Health Check & Auto-Sync Engine:** [https://ecourts-case-tracker.onrender.com/healthz](https://ecourts-case-tracker.onrender.com/healthz)
* 💻 **Local Development Server:** `http://127.0.0.1:5000`

---

## 🌟 Core Chamber Capabilities

### 1. 🏛️ Daily Court Hearing Board & Real-Time Cause List
* **Grouped Court Complex Docket:** Automatically groups active cases across Karur Court Complexes (*Principal District Court, Principal Sub Court, Mahila Court, Principal District Munsif Court, Fast Track Court, CJM Court*).
* **Item-Wise Allocation:** Real-time visibility into Court Hall numbers, Presiding Judges, Case Numbers, and Item Numbers.
* **🌙 Evening Advance Docket:** Pre-compiles tomorrow's full courtroom board and advance schedule every evening.
* **📅 Upcoming Pipeline (7–14 Days):** Advance client notice pipeline and strategic hearing roadmap.
* **🔄 Adjournment & Re-Scheduling Audit:** Instant logging of court date alterations with 1-click WhatsApp date alerts.

### 2. 📲 100% Ban-Safe Sequential WhatsApp Dispatcher
* **0% Ban Risk Guarantee:** Uses the official `https://wa.me/` standard protocol with zero illegal DOM injections or scraper bot drivers.
* **Guided Fast-Send Queue:** Re-uses a single dedicated browser window to dispatch personalized bilingual legal notices to 11–30+ clients in under 20 seconds.
* **Official Meta WhatsApp Cloud API Support:** 1-click background multi-dispatch via Meta Verified Business templates.

### 3. 🛡️ 100% Zero-Credit Chamber Vault & Live eCourts Sync
* **Predictive Polling:** Only queries eCourts India API when hearing dates approach, saving 100% of API credits during inactive trial phases.
* **Chamber SQLite Vault:** High-concurrency database with Write-Ahead Logging (`WAL` mode) preserving client files, case logs, and orders offline.

### 4. 🤖 JARVIS Agentic Legal AI Co-Pilot
* **Morning Chamber Briefing:** Autonomous summary of daily priorities, urgent warrants, injunction applications, and trial evidence matters.
* **Interactive Legal Assistant:** Natural language query engine indexing active case portfolios, past orders, and client contacts.

### 5. 🖨️ Professional A4 Printable Dockets & Dossiers
* **A4 Printable Daily Cause List:** High-resolution formatted court docket with official firm crest, bar verification, and case details.
* **Client Case Dossiers:** Printable 1-page case dossiers with complete hearing histories and advocate notes.

---

## 🏗️ System Architecture

```
                                 ┌──────────────────────────────────────────────┐
                                 │         ADVOCATE WEB & MOBILE DASHBOARD      │
                                 │     Single-Page Application (HTML5/CSS3/JS)  │
                                 └──────────────────────┬───────────────────────┘
                                                        │
                      ┌─────────────────────────────────┼─────────────────────────────────┐
                      │                                 │                                 │
                      ▼                                 ▼                                 ▼
         ┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
         │   eCourts API Client    │       │   Chamber SQLite Vault  │       │  Safe WhatsApp Queue    │
         │  • Zero-Credit Caching  │       │  • WAL High-Concurrency │       │  • Single-Tab Dispatch  │
         │  • Partner API Sync     │       │  • Change Audit History │       │  • 0% Ban Risk Protocol │
         └────────────┬────────────┘       └────────────┬────────────┘       └────────────┬────────────┘
                      │                                 │                                 │
                      └─────────────────────────────────┼─────────────────────────────────┘
                                                        │
                                                        ▼
                                       ┌──────────────────────────────────┐
                                       │     JARVIS Legal AI Assistant    │
                                       │   • Morning Docket Analysis      │
                                       │   • Strategy & Briefing Engine   │
                                       └──────────────────────────────────┘
```

---

## 📂 Repository Structure

```
ecourts-case-tracker/
├── app/                              # Core application package
│   ├── __init__.py                   # App factory & lifecycle management
│   ├── config.py                     # Centralized environment configuration
│   ├── api/                          # Modular API Blueprints
│   │   ├── cases.py                  # Case management & CNR queries (/api/cases, /api/case/<cnr>)
│   │   ├── cause_list.py             # Cause list & export routes (/api/cause-list)
│   │   ├── whatsapp.py               # WhatsApp dispatch routes (/api/whatsapp/*)
│   │   ├── ai.py                     # AI Briefing & Copilot query routes (/api/ai-*)
│   │   ├── scheduler.py              # Background sync / scheduler evaluation routes
│   │   ├── leads.py                  # Prospective client inquiries (/api/leads)
│   │   ├── settings.py               # Advocate & API settings (/api/advocate-settings)
│   │   └── health.py                 # Health checks & keep-alive (/healthz, /api/health)
│   ├── services/                     # Business logic & external domain integrations
│   │   ├── ecourts_service.py        # eCourts Partner API client & circuit breaker
│   │   ├── whatsapp_service.py       # Meta WhatsApp Cloud API integration
│   │   ├── sync_service.py           # Predictive polling worker & scheduler engine
│   │   ├── ai_service.py             # JARVIS Agentic Legal AI reasoning engine
│   │   └── vision_agent.py           # LangGraph + Playwright OCR fallback loop
│   ├── db/                           # SQLite database access layer
│   │   ├── database.py               # Connection pool with WAL mode & migrations
│   │   ├── repository.py             # CRUD methods for cases, logs, leads, cache
│   │   └── seed_data.py              # Authentic Karur Bar chamber cases & IST synchronizer
│   └── templates/                    # Jinja2 HTML templates for reports
│       ├── cause_list_print.html     # A4 Printable Daily Court Hearing Board docket
│       └── case_dossier.html         # A4 Printable Advocate Case Brief Dossier
├── static/                           # Web Dashboard Frontend
│   ├── index.html                    # Single-Page Application interface
│   ├── style.css                     # Responsive styling & luxury gold tokens
│   ├── app.js                        # Frontend interactive application logic
│   ├── loading_video.mp4             # High-resolution startup intro animation
│   └── logo.png                      # Official gold heraldic law firm emblem
├── tests/                            # Automated test suite (Pytest - 29/29 Passing)
│   ├── test_api_routes.py            # API endpoint integration tests
│   ├── test_database.py              # Repository & migration unit tests
│   ├── test_services.py              # eCourts, WhatsApp & AI service tests
│   └── test_telegram.py              # Telegram configuration tests
├── run.py                            # Local development entrypoint
├── wsgi.py                           # Production WSGI entrypoint (Gunicorn)
├── Procfile                          # Cloud deployment configuration (Render)
├── requirements.txt                  # Production dependencies
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

### 3. Start Local Server
```bash
python run.py
```
Open your browser at **`http://127.0.0.1:5000`**

### 4. Run Automated Test Suite
```bash
python -m pytest tests -v
```
*(All 29 integration and unit tests will run and pass).*

---

## 📜 License & Credits

Developed with ❤️ by **Mukil** for **Advocate R. Anbaiya & Associates, Advocates & Legal Consultants, Karur**.
Released under the **MIT License**.

