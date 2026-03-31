from flask import Blueprint, request, jsonify
from models.db import supabase
import os

admin_bp = Blueprint('admin', __name__)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


@admin_bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json

    if data.get("username") == ADMIN_USERNAME and data.get("password") == ADMIN_PASSWORD:
        return {
            "message": "Login successful",
            "role": "admin"
        }

    return {"error": "Invalid credentials"}, 401






# ------------------ STUDENT MANAGEMENT ------------------

@admin_bp.route('/admin/students', methods=['GET'])
def get_students():
    response = supabase.table("students").select("*").execute()
    return jsonify(response.data)


@admin_bp.route('/admin/students', methods=['POST'])
def add_student():
    data = request.json

    if not data.get("name") or not data.get("enrollment_no"):
        return {"error": "Missing required fields"}, 400

    response = supabase.table("students").insert({
        "name": data["name"],
        "enrollment_no": data["enrollment_no"],
        "roll_no": data.get("roll_no"),
        "year": data.get("year"),
        "branch": data.get("branch"),
        "section": data.get("section")
    }).execute()

    return {"message": "Student added", "data": response.data}


# ------------------ FACULTY MANAGEMENT ------------------

@admin_bp.route('/admin/faculty', methods=['GET'])
def get_faculty():
    response = supabase.table("faculty").select("*").execute()
    return jsonify(response.data)


@admin_bp.route('/admin/faculty', methods=['POST'])
def add_faculty():
    data = request.json

    if not data.get("name") or not data.get("employee_id"):
        return {"error": "Missing required fields"}, 400

    response = supabase.table("faculty").insert({
        "name": data["name"],
        "employee_id": data["employee_id"],
        "department": data.get("department")
    }).execute()

    return {"message": "Faculty added", "data": response.data}


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

    if not data.get("student_id") or not data.get("subject_id"):
        return {"error": "Missing fields"}, 400

    response = supabase.table("student_subject").insert({
        "student_id": data["student_id"],
        "subject_id": data["subject_id"]
    }).execute()

    return {"message": "Subject assigned", "data": response.data}

@admin_bp.route('/admin/student-subjects/<int:student_id>', methods=['GET'])
def get_student_subjects(student_id):
    response = supabase.table("student_subject") \
        .select("subject_id, subjects(*)") \
        .eq("student_id", student_id) \
        .execute()

    return jsonify(response.data)

