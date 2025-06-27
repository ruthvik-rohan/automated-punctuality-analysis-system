import sqlite3
from datetime import datetime, timedelta

DB = 'db.sqlite3'

def analyze_attendance():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()

        # Get logs
        cur.execute("SELECT person_id, name, timestamp, status FROM logs ORDER BY timestamp")
        logs = cur.fetchall()

        # Get schedule for each person
        cur.execute("SELECT person_id, class_start, class_end FROM schedule")
        schedules = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

    attendance_data = {}

    for pid, name, ts, status in logs:
        date = ts.split("T")[0]
        key = (pid, date)
        if key not in attendance_data:
            attendance_data[key] = {
                'name': name,
                'entries': [],
                'exits': [],
            }

        dt = datetime.fromisoformat(ts)
        if status == 'entry':
            attendance_data[key]['entries'].append(dt)
        else:
            attendance_data[key]['exits'].append(dt)

    report = []

    for (pid, date), record in attendance_data.items():
        entries = sorted(record['entries'])
        exits = sorted(record['exits'])

        start_time = entries[0] if entries else None
        end_time = exits[-1] if exits else None

        schedule_start, schedule_end = schedules.get(pid, (None, None))
        if schedule_start:
            class_start = datetime.fromisoformat(schedule_start)
            class_end = datetime.fromisoformat(schedule_end)
        else:
            class_start = class_end = None

        late = start_time > class_start + timedelta(minutes=5) if class_start and start_time else False
        early_exit = end_time < class_end - timedelta(minutes=5) if class_end and end_time else False

        long_breaks = 0
        if len(entries) > 1:
            for i in range(1, len(entries)):
                gap = (entries[i] - exits[i - 1]).total_seconds()
                if gap > 600:  # 10 mins
                    long_breaks += 1

        report.append({
            'person_id': pid,
            'name': record['name'],
            'date': date,
            'late': late,
            'early_exit': early_exit,
            'long_breaks': long_breaks,
            'entries': len(entries),
            'exits': len(exits)
        })
return report