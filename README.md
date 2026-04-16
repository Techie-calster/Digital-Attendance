# Digital Attendance (Real-Time Attendance Monitoring System)

A role-based web application for managing student attendance, viewing subject-wise attendance summaries, marking attendance for classes, and maintaining student/faculty/admin records.

## Overview

This project provides three separate user experiences:

- **Student Portal** – view attendance percentage, subject-wise summary, eligibility status, required classes to reach the next threshold, and attendance history.
- **Faculty Portal** – view assigned subjects and mark attendance for students in a class session.
- **Admin Portal** – manage students, faculty, subjects, student-subject assignment, and correct attendance records when a mistake is found.

The application uses a Flask backend with a Supabase/PostgreSQL database and HTML/CSS/JavaScript-based frontends.

## Key Features

- Role-based login for **Student**, **Faculty**, and **Administrator**
- Student dashboard with:
  - overall attendance summary
  - subject-wise attendance summary
  - attendance history for each subject
  - eligibility / shortage information
- Faculty dashboard with:
  - assigned subject listing
  - attendance marking for a class session
  - attendance overview and analytics
- Admin dashboard with:
  - add/view students
  - add/view faculty
  - add/view subjects
  - assign students to subjects
  - attendance correction panel
- Predefined attendance thresholds used by the system logic
- Responsive UI built with modern HTML and Tailwind CSS

## Technologies Used

- **Backend:** Python, Flask, Flask-CORS
- **Database:** Supabase / PostgreSQL
- **Frontend:** HTML, CSS, JavaScript, Tailwind CSS
- **Libraries:** Supabase client, python-dotenv, requests, and related dependencies listed in `requirements.txt`

## Project Structure

```text
.
├── app.py
├── admin.py
├── db.py
├── DATABASE.sql
├── login.html
├── admin-login.html
├── ram_landing.html
├── student-dashboard.html
├── faculty-dashboard.html
├── admin-dashboard.html
├── requirements.txt
└── README.md
```

## Database Schema

The database script includes tables for:

- `students`
- `faculty`
- `subjects`
- `student_subject`
- `attendance`
- `marks`

Use `DATABASE.sql` to create the schema in your PostgreSQL/Supabase database.

## System Requirements

- Python 3.10 or later
- A PostgreSQL / Supabase database
- Modern web browser
- Internet access for CDN assets used by the HTML pages

## Installation and Setup

### 1) Clone or copy the project
Place the project files in a local folder.

### 2) Create and activate a virtual environment
```bash
python -m venv venv
```

Activate it:

**Windows**
```bash
venv\Scripts\activate
```

**macOS / Linux**
```bash
source venv/bin/activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Configure environment variables
Create a `.env` file in the project folder and add the required values used by your project:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password
```

### 5) Set up the database
Import `DATABASE.sql` into your PostgreSQL/Supabase database and make sure all tables are created successfully.

### 6) Run the Flask backend
```bash
python app.py
```

By default, the backend runs on:

```text
http://0.0.0.0:5000
```

### 7) Open the frontend pages
Open the HTML files in a browser or serve them using a local static server / Live Server extension.

Recommended entry pages:
- `ram_landing.html`
- `login.html`
- `admin-login.html`

## User Roles and Access

### Student
Students can log in and view:
- attendance percentage
- subject-wise attendance summary
- attendance history
- eligibility status and required classes to reach the next threshold

### Faculty
Faculty members can:
- log in with employee credentials
- view assigned subjects
- mark attendance for a class session
- submit attendance records for the selected subject/date

### Administrator
Administrators can:
- log in to the admin console
- manage students, faculty, and subjects
- assign students to subjects
- review and correct attendance records if required

## Notes on Current Functionality

- Attendance thresholds are used by the system logic, but they are **not editable from the admin interface** in the current version.
- Report download / export functionality is **not implemented** in the current version.
- Administrative attendance correction is available through the admin attendance fixer panel.

## Default Routes and Pages

### Backend API
- `GET /` – API health message
- `POST /api/login` – student/faculty login
- `POST /api/admin/login` – admin login
- `GET /api/student/<enrollment_no>` – fetch student profile
- `GET /api/attendance/<student_id>` – overall attendance
- `GET /api/subject-attendance/<student_id>` – subject-wise attendance summary
- `GET /api/attendance-history/<student_id>/<subject_id>` – attendance history
- `POST /api/mark-attendance` – submit attendance records

### Admin API
- `GET /api/admin/students`
- `POST /api/admin/students`
- `GET /api/admin/faculty`
- `POST /api/admin/faculty`
- `GET /api/admin/subjects`
- `POST /api/admin/subjects`
- `POST /api/assign-subject`
- `GET /api/admin/attendance-view`
- `POST /api/admin/attendance-update`

## How the System Works

1. The user logs in according to their role.
2. The backend validates credentials.
3. The correct dashboard opens based on the selected role.
4. Students view attendance details.
5. Faculty mark attendance for a subject and session date.
6. Admins manage records and correct attendance if a mistake is found.
7. Attendance percentages and eligibility values are calculated automatically by the system.

## Limitations

- No PDF/Excel export feature
- No direct report download feature
- Attendance thresholds are fixed in the current version
- No mobile app version is provided

## Troubleshooting

### Invalid credentials
Check the username/password and the selected role.

### Database connection issue
Verify Supabase credentials, database access, and table names.

### Attendance not showing correctly
Confirm that the student is assigned to the subject and that attendance data exists for that subject.

### Admin correction panel not loading
Make sure the subject ID and date are entered correctly.

## Future Enhancements

- Dynamic attendance threshold configuration
- Export attendance reports to PDF/CSV
- More advanced analytics and charts
- Mobile app support
- Improved security with hashed passwords and session handling

## Author

Prepared as an academic project for attendance monitoring and management.

## License

This project is intended for educational use.
