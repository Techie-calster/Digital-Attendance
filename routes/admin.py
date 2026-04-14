from flask import Blueprint, request, jsonify
from models.db import supabase
from postgrest.exceptions import APIError
import os

admin_bp = Blueprint('admin', __name__)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


@admin_bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json

    if data.get("username") == ADMIN_USERNAME and data.get("password") == ADMIN_PASSWORD:
        return {
            "status": "success",
            "message": "Login successful",
            "role": "admin",
            "redirect": "admin-dashboard.html"
        }

    return {"status": "error", "message": "Invalid credentials"}, 401






# ------------------ STUDENT MANAGEMENT ------------------

@admin_bp.route('/admin/students', methods=['GET'])
def get_students():
    response = supabase.table("students").select("*").execute()
    return jsonify(response.data)


@admin_bp.route('/admin/students', methods=['POST'])
def add_student():
    data = request.json

    if not data.get("name") or not data.get("enrollment_no") or not data.get("password"):
        return {"error": "Missing required fields: Name, Enrollment, or Password"}, 400

    try:
        response = supabase.table("students").insert({
            "name": data["name"],
            "enrollment_no": data["enrollment_no"],
            "roll_no": data.get("roll_no"),
            "year": data.get("year"),
            "branch": data.get("branch"),
            "section": data.get("section"),
            "password": data["password"]
        }).execute()

        return {"message": "Student added Successfully", "data": response.data}

    except APIError as e:
        # Code 23505 is the PostgreSQL code for unique_violation (duplicate key)
        if e.code == '23505':
            return {"error": f"Already Exists: The Enrollment No '{data['enrollment_no']}' is already in the database."}, 409
        
        # Catch other database errors
        return {"error": f"Database Error: {e.message}"}, 500

# ------------------ ATTENDANCE MANAGEMENT (FIXER) ------------------

@admin_bp.route('/admin/attendance-view', methods=['GET'])
def admin_get_attendance():
    subject_id = request.args.get('subject_id')
    date = request.args.get('date')
    
    if not subject_id or not date:
        return {"error": "Subject ID and Date are required"}, 400

    # Admin fetches specific records to fix mistakes
    response = supabase.table("attendance") \
        .select("attendance_id, status, student_id, students(name, roll_no)") \
        .eq("subject_id", subject_id) \
        .eq("date", date) \
        .execute()
    
    return jsonify(response.data)

@admin_bp.route('/admin/attendance-update', methods=['POST'])
def admin_update_attendance():
    data = request.json  # List of {attendance_id, status}
    
    for record in data:
        if record.get('attendance_id'):
            supabase.table("attendance") \
                .update({"status": record['status']}) \
                .eq("attendance_id", record['attendance_id']) \
                .execute()
                
    return {"message": "Attendance corrected by Admin"}
# ------------------ FACULTY MANAGEMENT ------------------

@admin_bp.route('/admin/faculty', methods=['GET'])
def get_faculty():
    response = supabase.table("faculty").select("*").execute()
    return jsonify(response.data)


@admin_bp.route('/admin/faculty', methods=['POST'])
def add_faculty():
    data = request.json

    if not data.get("name") or not data.get("employee_id") or not data.get("password"):
        return {"error": "Missing required fields: Name, Employee ID, or Password"}, 400

    try:
        response = supabase.table("faculty").insert({
            "name": data["name"],
            "employee_id": data["employee_id"],
            "department": data.get("department"),
            "password": data["password"]
        }).execute()

        return {"message": "Faculty added Successfully", "data": response.data}

    except APIError as e:
        if e.code == '23505':
            return {"error": f"Already Exists: Employee ID '{data['employee_id']}' is already in the database."}, 409
        
        return {"error": f"Database Error: {e.message}"}, 500

# ------------------ SUBJECT MANAGEMENT ------------------

@admin_bp.route('/admin/subjects', methods=['GET'])
def get_subjects():
    response = supabase.table("subjects").select("*").execute()
    return jsonify(response.data)


@admin_bp.route('/admin/subjects', methods=['POST'])
def add_subject():
    data = request.json

    if not data.get("subject_name") or not data.get("faculty_id"):
        return {"error": "Missing required fields"}, 400

    response = supabase.table("subjects").insert({
        "subject_name": data["subject_name"],
        "faculty_id": data["faculty_id"]
    }).execute()

    return {"message": "Subject added", "data": response.data}

@admin_bp.route('/admin/assign-subject', methods=['POST'])
def assign_subject():
    data = request.json

    # 1. Validation check
    if not data.get("subject_name") or not data.get("faculty_id"):
        return {"error": "Missing required fields: Subject Name or Faculty ID"}, 400

    try:
        # 2. Database Insert
        response = supabase.table("subjects").insert({
            "subject_name": data["subject_name"],
            "faculty_id": data["faculty_id"]
        }).execute()

        return {"message": "Subject added successfully", "data": response.data}

    except APIError as e:
        # Check for Foreign Key violation (Code 23503)
        # Occurs if the faculty_id provided does not exist in the Faculty table
        if e.code == '23503':
            return {"error": f"Invalid Faculty: ID {data['faculty_id']} does not exist."}, 400
        
        # Check for Duplicate Name if you've set subject_name to UNIQUE (Code 23505)
        if e.code == '23505':
            return {"error": f"Already Exists: '{data['subject_name']}' is already registered."}, 409

        return {"error": f"Database Error: {e.message}"}, 500
@admin_bp.route('/admin/student-subjects/<int:student_id>', methods=['GET'])
def get_student_subjects(student_id):
    response = supabase.table("student_subject") \
        .select("subject_id, subjects(*)") \
        .eq("student_id", student_id) \
        .execute()

    return jsonify(response.data)

