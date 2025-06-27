from flask import Flask, render_template, request, redirect,flash,Response, url_for
import sqlite3
import os
from datetime import datetime
from utils.recognizer import detect_faces
import face_recognition
from datetime import datetime, timedelta
from utils.analysis import analyze_attendance
import csv
from io import StringIO
import cv2
import time
import numpy as np
app = Flask(__name__)

DB = 'db.sqlite3'
app.secret_key = 'shhhh'
PI_CAM_SERVER = 'http://192.168.137.217:5000'
latest_frame = None  # To store the latest frame from Pi

from utils.recognizer import detect_faces_from_frame
last_detected_time = {}  # To avoid duplicate logs
@app.route('/upload_feed', methods=['POST'])
def upload_feed():
    global latest_frame
    file = request.files['frame']
    img = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(img, cv2.IMREAD_COLOR)

    # 🔥 Fix color: Convert RGB to BGR if needed
   # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


    latest_frame = cv2.resize(frame, (640, 480))
    return 'OK'

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
import requests

@app.route('/rotate', methods=['GET'])
def rotate_from_laptop():
    angle = request.args.get('angle', 90)
    try:
        r = requests.get(f"{PI_CAM_SERVER}/rotate_servo", params={"angle": angle}, timeout=2)
        flash(f"✅ Pi says: {r.text}", "success")
    except Exception as e:
        flash(f"❌ Failed to contact Pi: {e}", "error")
    return redirect('/')

def gen_frames():
    global latest_frame
    while True:
        if latest_frame is not None:
            now = datetime.now()

            # Detect faces every 2 seconds
            if int(now.timestamp()) % 2 == 0:
                data = detect_faces_from_frame(latest_frame)

                with sqlite3.connect(DB) as con:
                    cur = con.cursor()
                    for person in data:
                        pid = person['id']
                        if pid != 'Unknown':
                            # Skip if last detection was under 30s ago
                            last_time = last_detected_time.get(pid)
                            if not last_time or (now - last_time).total_seconds() > 30:
                                print(f"Inserting log for {person['name']} at {now.isoformat()} - {person['status']}")
                                cur.execute("INSERT INTO logs (person_id, name, timestamp, status) VALUES (?, ?, ?, ?)",
                                            (pid, person['name'], now.isoformat(), person['status']))
                                con.commit()
                                last_detected_time[pid] = now

            _, buffer = cv2.imencode('.jpg', latest_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        time.sleep(0.1)


# Init DB (Run once)
def init_db():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id TEXT UNIQUE,
                name TEXT,
                role TEXT,
                encoding BLOB
            )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT,
            name TEXT,
            timestamp TEXT,
            status TEXT
        )''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS punctuality_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id TEXT,
                name TEXT,
                date TEXT,
                late INTEGER,
                early_exit INTEGER,
                long_breaks INTEGER
            )
            ''')        
        cur.execute('''CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT,
            class_start TEXT,
            class_end TEXT,
            FOREIGN KEY (person_id) REFERENCES users(person_id)
        )''')
        con.commit()
@app.route('/')
def index():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10")
        logs = cur.fetchall()
    return render_template('index.html', logs=logs)


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    if file:
        img_path = 'temp.jpg'
        file.save(img_path)

        data = detect_faces(img_path)

        if not data:
            flash("No known face detected. Upload a valid frame.", "error")
            return redirect('/')

        # insert only known faces
        with sqlite3.connect(DB) as con:
            cur = con.cursor()
            for person in data:
                if person['id'] != 'Unknown':
                    cur.execute("INSERT INTO logs (person_id, name, timestamp, status) VALUES (?, ?, ?, ?)",
                                (person['id'], person['name'], person['timestamp'], person['status']))
            con.commit()

    return redirect('/dashboard')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        person_id = request.form['person_id']
        name = request.form['name']
        role = request.form['role']
        image = request.files['image']

        img_path = 'temp_reg.jpg'
        image.save(img_path)
        img = face_recognition.load_image_file(img_path)
        encodings = face_recognition.face_encodings(img)

        if len(encodings) > 0:
            enc_blob = encodings[0].tobytes()
            with sqlite3.connect(DB) as con:
                cur = con.cursor()
                cur.execute("INSERT INTO users (person_id, name, role, encoding) VALUES (?, ?, ?, ?)",
                            (person_id, name, role, enc_blob))
                con.commit()
            return redirect('/')
        else:
            return "No face detected in the image. Try again."

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM logs ORDER BY timestamp DESC")
        rows = cur.fetchall()
    return render_template('dashboard.html', logs=rows)
from datetime import datetime, timedelta





@app.route('/punctuality', methods=['GET', 'POST'])
def punctuality():
    selected_range = request.form.get("range") if request.method == 'POST' else "daily"

    all_data = analyze_attendance()
    filtered = []

    today = datetime.now().date()

    for item in all_data:
        report_date = datetime.fromisoformat(item['date']).date()

        if selected_range == "daily":
            if report_date == today:
                filtered.append(item)

        elif selected_range == "weekly":
            if (today - report_date).days <= 7:
                filtered.append(item)

        elif selected_range == "monthly":
            if report_date.month == today.month and report_date.year == today.year:
                filtered.append(item)

    return render_template("punctuality.html", report=filtered, selected=selected_range)

@app.route('/download_report')
def download_report():
    from utils.analysis import analyze_attendance
    range_type = request.args.get('range', 'daily')
    data = analyze_attendance()

    today = datetime.now().date()
    filtered = []

    for item in data:
        d = datetime.fromisoformat(item['date']).date()
        if (range_type == "daily" and d == today) or \
           (range_type == "weekly" and (today - d).days <= 7) or \
           (range_type == "monthly" and d.month == today.month and d.year == today.year):
            filtered.append(item)

    si = StringIO()
    cw = csv.DictWriter(si, fieldnames=filtered[0].keys())
    cw.writeheader()
    cw.writerows(filtered)
    output = si.getvalue()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=punctuality_{range_type}.csv"}
    )

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        start = request.form['class_start']
        end = request.form['class_end']

        with sqlite3.connect(DB) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM schedule")  # Clear previous
            cur.execute("INSERT INTO schedule (class_start, class_end) VALUES (?, ?)", (start, end))
            con.commit()

        flash("Class schedule updated successfully.", "success")
        return redirect('/schedule')

    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT class_start, class_end FROM schedule LIMIT 1")
        row = cur.fetchone()
        class_start, class_end = row if row else ("", "")

    return render_template('schedule.html', class_start=class_start, class_end=class_end)
@app.route('/assign_schedule', methods=['GET', 'POST'])
def assign_schedule():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()

        if request.method == 'POST':
            person_id = request.form['person_id']
            class_start = request.form['class_start']
            class_end = request.form['class_end']

            # delete old
            cur.execute("DELETE FROM schedule WHERE person_id = ?", (person_id,))
            # insert new
            cur.execute("INSERT INTO schedule (person_id, class_start, class_end) VALUES (?, ?, ?)",
                        (person_id, class_start, class_end))
            con.commit()
            flash("Schedule assigned successfully!", "success")
            return redirect('/assign_schedule')

        # Fetch users and their schedules
        cur.execute("SELECT person_id, name FROM users")
        users = cur.fetchall()

        cur.execute("SELECT person_id, class_start, class_end FROM schedule")
        schedule_data = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

    return render_template('assign_schedule.html', users=users, schedule_data=schedule_data)
@app.route('/monitor')
def monitor():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10")
        recent_logs = cur.fetchall()
    return render_template('monitor.html', logs=recent_logs)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000,debug=True)