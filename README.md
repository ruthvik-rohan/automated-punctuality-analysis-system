# Automated Punctuality Analysis System

This project is a real-time punctuality tracking system designed for students and faculty. It uses an IoT Wi-Fi camera to capture images as individuals enter a classroom and automatically logs their attendance based on the time of entry. The system also provides analytics on punctuality patterns.

## Features

- Real-time face detection and recognition using images from a Wi-Fi camera.
- Automatic classification of individuals as "on time" or "late" based on predefined time rules.
- Punctuality tracking on a daily, weekly, and monthly basis.
- Flask-based web dashboard for viewing attendance records.
- Option to download attendance and punctuality data in CSV format.
- SQLite used as the local database for storing attendance records.

## Technologies Used

- HTML, Tailwind CSS for frontend
- Python (Flask) for backend
- OpenCV and Dlib for face recognition
- SQLite for database
- IoT Wi-Fi Camera for real-time image capture

## Project Structure
Automated_Punctuality_Analysis_System/
  ├─ templates/       # HTML templates for dashboard
  ├─ utils/           # Python utilities for face recognition
  ├─ server.py        # Main backend server using Flask
  ├─ db.sqlite3       # SQLite database file
  ├─ README.md        # Project documentation


## How It Works

1. The IoT camera captures an image when someone enters the room.
2. The image is sent to the backend server.
3. The server processes the image to identify the person and record the timestamp.
4. The system determines if the person is late or on time.
5. The data is displayed on the dashboard and stored in the database.

## Note

This project requires an IoT Wi-Fi camera to send live images to the backend. Without this hardware, the system cannot perform real-time attendance tracking.

## Author

Ruthvik Rohan  
GitHub: [ruthvik-rohan](https://github.com/ruthvik-rohan)

