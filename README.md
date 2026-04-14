# Digital Attendance

Digital Attendance is a web-based attendance management system for students, faculty, and administrators. The project now runs as a self-contained Flask application with a local seeded relational database, so the full demo works without depending on an external Supabase instance.

## Features

- Student login, attendance overview, subject-wise attendance, marks display, and attendance history
- Faculty login, subject dashboard, structured attendance sheet, session history, and attendance updates
- Admin login, student/faculty/subject management, subject assignment, and configurable attendance thresholds
- Session-based role checks on protected APIs
- Seeded demo data for peer testing and walkthroughs

## Run Locally

1. Install dependencies:

```bash
pip install flask flask-cors werkzeug
```

2. Start the application:

```bash
python app.py
```

3. Open the app in a browser:

```text
http://127.0.0.1:5000/
```

The first run creates `digital_attendance.db` automatically and seeds demo data.

## Demo Credentials

Use any seeded user from the database. A few ready-to-use examples:

- Student: `ENR001` / `rahul123`
- Student: `ENR003` / `priya123`
- Faculty: `EMP001` / `amit123`
- Faculty: `EMP002` / `neha123`
- Admin: `admin` / `Admin@123`

## User Manual

### Student Flow

1. Open [login.html](/D:/SE1/Digital-Attendance/login.html).
2. Select `Student`.
3. Sign in with an enrollment number and password.
4. View:
   - overall attendance percentage
   - present vs total classes
   - subject-wise attendance
   - subject marks
   - attendance history from the subject modal

### Faculty Flow

1. Open [login.html](/D:/SE1/Digital-Attendance/login.html).
2. Select `Faculty Member`.
3. Sign in with an employee ID and password.
4. On the faculty dashboard:
   - review assigned subjects
   - pick a subject and cohort
   - choose a session date
   - mark attendance in the structured sheet
   - save or update attendance
   - inspect saved session history

### Admin Flow

1. Open [admin-login.html](/D:/SE1/Digital-Attendance/admin-login.html).
2. Sign in with admin credentials.
3. On [admin-dashboard.html](/D:/SE1/Digital-Attendance/admin-dashboard.html), you can:
   - create students
   - create faculty members
   - create subjects
   - assign subjects to students
   - update attendance thresholds

## Project Structure

- [app.py](/D:/SE1/Digital-Attendance/app.py): Flask app, authentication, student routes, faculty routes, attendance logic, static page serving
- [routes/admin.py](/D:/SE1/Digital-Attendance/routes/admin.py): admin authentication and admin management APIs
- [models/db.py](/D:/SE1/Digital-Attendance/models/db.py): local relational database setup, seeding, password hashing, shared DB helpers
- [student-dashboard.html](/D:/SE1/Digital-Attendance/student-dashboard.html): student UI
- [faculty-dashboard.html](/D:/SE1/Digital-Attendance/faculty-dashboard.html): faculty UI
- [admin-dashboard.html](/D:/SE1/Digital-Attendance/admin-dashboard.html): admin UI
- [DATABASE.sql](/D:/SE1/Digital-Attendance/DATABASE.sql): original schema reference from the project
- [Final_SRS_v2.0_Upd.pdf](/D:/SE1/Digital-Attendance/Final_SRS_v2.0_Upd.pdf): SRS used for the audit

## Notes

- The application now uses a local SQLite database for reliable demo/testing behavior.
- Passwords are stored as hashes in the local runtime database.
- Attendance rules are editable from the admin dashboard and reflected by the student and faculty flows.

## Supporting Docs

- [TRACEABILITY.md](/D:/SE1/Digital-Attendance/TRACEABILITY.md)
- [PEER_TESTING_REPORT.md](/D:/SE1/Digital-Attendance/PEER_TESTING_REPORT.md)
