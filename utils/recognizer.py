import face_recognition
import sqlite3
import numpy as np
from datetime import datetime
import cv2

DB = 'db.sqlite3'

def load_known_faces():
    known_encodings, ids, names = [], [], []
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT person_id, name, encoding FROM users")
        for pid, name, enc_blob in cur.fetchall():
            enc = np.frombuffer(enc_blob, dtype=np.float64)
            ids.append(pid)
            names.append(name)
            known_encodings.append(enc)
    return known_encodings, ids, names

def get_last_status(person_id, date):
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT status FROM logs 
            WHERE person_id=? AND DATE(timestamp)=? 
            ORDER BY timestamp DESC LIMIT 1
        """, (person_id, date))
        result = cur.fetchone()
        return result[0] if result else None
def detect_faces_from_frame(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    small = cv2.resize(rgb, (0, 0), fx=0.5, fy=0.5)

    locations = face_recognition.face_locations(small)
    encodings = face_recognition.face_encodings(small, locations)

    known_encodings, ids, names = load_known_faces()
    results = []

    for enc in encodings:
        matches = face_recognition.compare_faces(known_encodings, enc)
        if True in matches:
            idx = matches.index(True)
            pid = ids[idx]
            name = names[idx]
            ts = datetime.now()
            date_str = ts.date().isoformat()
            

            # ✅ Reusing the same logic from image upload
            last_status = get_last_status(pid, date_str)
            status = 'exit' if last_status == 'entry' else 'entry'

            results.append({
                'id': pid,
                'name': name,
                'timestamp': ts.isoformat(),
                'status': status
            })

            print(f"Matched: {name} ({pid}) - Status: {status}")

    return results

def detect_faces(image_path):
    img = face_recognition.load_image_file(image_path)
    small_img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
    face_locations = face_recognition.face_locations(small_img, model="hog")  # or cnn if GPU
    encodings = face_recognition.face_encodings(small_img, face_locations)

    known_encodings, ids, names = load_known_faces()
    results = []

    for enc in encodings:
        matches = face_recognition.compare_faces(known_encodings, enc)
        if True in matches:
            idx = matches.index(True)
            pid = ids[idx]
            name = names[idx]
            ts = datetime.now()
            date_str = ts.date().isoformat()

            last_status = get_last_status(pid, date_str)
            status = 'exit' if last_status == 'entry' else 'entry'

            results.append({
                'id': pid,
                'name': name,
                'timestamp': ts.isoformat(),
                'status': status
            })
 return results