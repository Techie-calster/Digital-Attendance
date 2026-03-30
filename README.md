
# Digital Attendance System

A full-stack web application designed to manage student attendance, calculate internal marks, and provide smart insights like skip prediction.


## Project Overview

This project helps students and faculty track attendance in a digital way.

- Students can view their **attendance percentage**
- System automatically calculates **internal marks**
- It also tells **how many classes a student can safely skip**
- Faculty can mark attendance using a simple interface


## Key Features

### Student Dashboard
- View overall attendance
- Subject-wise attendance breakdown
- Internal marks calculation based on attendance
- Skip prediction (how many classes can be skipped)
- View detailed subject info in popup (modal)


### Faculty Dashboard
- Select class (branch, year, section)
- Generate attendance sheet
- Mark students as present/absent


### Login System
- Separate login for:
  - Students
  - Faculty
- Data stored using backend API


## How It Works

### Login
- User selects role (student/faculty)
- Enters ID and password
- Backend verifies from database


### Student Flow
- Student logs in
- Dashboard loads data using APIs
- Attendance is calculated from database
- Marks are calculated using percentage
- Skip logic is applied based on 67% rule


### Attendance Logic

- Attendance % = (Present / Total) × 100

- Marks Calculation:
  - < 67% → 0 marks
  - 67–70 → 1.2 marks
  - 70–75 → 2.4 marks
  - 75–80 → 3.6 marks
  - 80–85 → 4.8 marks
  - > 85% → 6 marks


### Skip Logic

System calculates how many lectures can be skipped while maintaining 67% attendance.


### Backend (Flask API)

Handles:
- Login authentication
- Student data fetching
- Attendance calculation
- Subject-wise data


### Database (PostgreSQL - Supabase)

Tables used:
- Students
- Faculty
- Subjects
- Student_Subject
- Attendance
- Marks


## Tech Stack

### Frontend
- HTML
- Tailwind CSS
- JavaScript

### Backend
- Python (Flask)

### Database
- Supabase (PostgreSQL)

## How to Run
   1. Start backend:python app.py
   2. Open frontend:login.html
   3. Login using student or faculty credentials
