FairRide backend
=================

Files:
- app.py: Flask backend and REST API
- requirements.txt: Python dependencies (includes Gunicorn for Render deployment)

Local setup:
1. Install Python 3.10 or newer.
2. In this folder, run: python -m venv venv
3. Activate the environment:
   Windows: venv\Scripts\activate
   macOS/Linux: source venv/bin/activate
4. Install dependencies: pip install -r requirements.txt
5. Run locally: python app.py

The backend expects the frontend templates/index.html and static/ files
from the full FairRide project to be present beside app.py in the usual
Flask folder structure. It creates fairride.db automatically.

Render start command:
gunicorn app:app --bind 0.0.0.0:$PORT

API endpoints:
GET  /                  Serves the frontend page
GET  /api/stats         Returns demo usage counts
POST /api/book          Creates a demo booking
POST /api/cancel-driver Simulates a driver cancellation and starts a 10-minute lock
POST /api/rebook        Rebooks at the protected original fare, if lock is active
POST /api/report        Saves a fairness report
POST /api/event         Logs a usage event

This is an academic simulation only. It is not connected to Uber, live drivers,
GPS, live fares, or payment systems. SQLite data may not persist on ephemeral
hosting storage.
