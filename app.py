from flask import Flask, render_template, request, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__)
DB = Path(__file__).with_name("fairride.db")

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS bookings(
          id INTEGER PRIMARY KEY AUTOINCREMENT, pickup TEXT, destination TEXT,
          ride_type TEXT, original_fare REAL, current_fare REAL, status TEXT,
          driver TEXT, created_at TEXT, cancelled_by TEXT, reason TEXT,
          lock_until TEXT, rebook_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS reports(
          id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, category TEXT,
          details TEXT, status TEXT DEFAULT 'Received', created_at TEXT);
        CREATE TABLE IF NOT EXISTS usage_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, event_type TEXT,
          event_value TEXT, duration_seconds REAL, created_at TEXT);
        """)
init_db()

def stamp(): return datetime.now().isoformat(timespec="seconds")

@app.route("/")
def index(): return render_template("index.html")

@app.get("/api/stats")
def stats():
    with connect() as c:
        q=lambda table: c.execute(f"SELECT COUNT(*) n FROM {table}").fetchone()["n"]
        return jsonify(bookings=q("bookings"), protected=c.execute(
            "SELECT COUNT(*) n FROM bookings WHERE lock_until IS NOT NULL").fetchone()["n"],
            reports=q("reports"), events=q("usage_events"))

@app.post("/api/book")
def book():
    d=request.get_json(force=True)
    pickup=(d.get("pickup") or "").strip(); dest=(d.get("destination") or "").strip()
    if not pickup or not dest: return jsonify(error="Enter pickup and destination."),400
    fares={"FairGo":180,"FairAuto":120,"FairMoto":90,"FairPlus":260}
    fare=fares.get(d.get("ride_type"),180)
    with connect() as c:
        cur=c.execute("""INSERT INTO bookings(pickup,destination,ride_type,original_fare,current_fare,status,driver,created_at)
        VALUES(?,?,?,?,?,?,?,?)""",(pickup,dest,d.get("ride_type","FairGo"),fare,fare,"Driver assigned","Aarav",stamp()))
        bid=cur.lastrowid
    return jsonify(id=bid,pickup=pickup,destination=dest,fare=fare,driver="Aarav",status="Driver assigned")

@app.post("/api/cancel-driver")
def cancel_driver():
    bid=request.get_json(force=True).get("booking_id")
    with connect() as c:
        r=c.execute("SELECT * FROM bookings WHERE id=?",(bid,)).fetchone()
        if not r:return jsonify(error="Booking not found."),404
        until=datetime.now()+timedelta(minutes=10)
        c.execute("""UPDATE bookings SET status='Driver cancelled',cancelled_by='Driver',
        reason='Driver cancelled after accepting',lock_until=? WHERE id=?""",(until.isoformat(timespec="seconds"),bid))
    return jsonify(original_fare=r["original_fare"],lock_until=until.isoformat(timespec="seconds"))

@app.post("/api/rebook")
def rebook():
    bid=request.get_json(force=True).get("booking_id")
    with connect() as c:
        r=c.execute("SELECT * FROM bookings WHERE id=?",(bid,)).fetchone()
        if not r:return jsonify(error="Booking not found."),404
        if r["cancelled_by"]!="Driver" or not r["lock_until"]:
            return jsonify(error="Fare Lock requires a driver-initiated cancellation."),400
        if datetime.fromisoformat(r["lock_until"])<datetime.now():
            return jsonify(error="The 10-minute Fare Lock has expired."),400
        quote=round(r["original_fare"]*1.22,2)
        fare=min(r["original_fare"],quote)
        c.execute("UPDATE bookings SET current_fare=?,status='Replacement ride assigned',driver='Meera',rebook_count=rebook_count+1 WHERE id=?",(fare,bid))
    return jsonify(payable_fare=fare,quote=quote,savings=round(quote-fare,2),driver="Meera")

@app.post("/api/report")
def report():
    d=request.get_json(force=True); category=(d.get("category") or "").strip()
    if not category:return jsonify(error="Choose a report category."),400
    with connect() as c:
        cur=c.execute("INSERT INTO reports(booking_id,category,details,created_at) VALUES(?,?,?,?)",
                      (d.get("booking_id"),category,d.get("details",""),stamp()))
    return jsonify(id=cur.lastrowid,status="Received")

@app.post("/api/event")
def event():
    d=request.get_json(force=True)
    with connect() as c:
        c.execute("INSERT INTO usage_events(session_id,event_type,event_value,duration_seconds,created_at) VALUES(?,?,?,?,?)",
                  (d.get("session_id","demo"),d.get("event_type","interaction"),str(d.get("event_value",""))[:300],d.get("duration_seconds"),stamp()))
    return jsonify(ok=True)

if __name__=="__main__":
    app.run(debug=True)
