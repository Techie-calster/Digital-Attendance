import sqlite3

from flask import Blueprint, jsonify, request, session

from models.db import (
    check_password,
    execute_write,
    get_rules,
    make_password_hash,
    query_all,
    query_one,
    update_rules,
)

admin_bp = Blueprint("admin", __name__)


def success_response(data=None, **extra):
    payload = {"status": "success"}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload)


def error_response(message, status_code=400):
    return jsonify({"status": "error", "message": message}), status_code


def _validate_rules(eligibility, warning, high):
    if not all(isinstance(value, int) for value in (eligibility, warning, high)):
        return "Attendance thresholds must be integers."
    if not (0 < eligibility <= warning <= high <= 100):
        return "Thresholds must satisfy 0 < eligibility <= warning <= high <= 100."
    return None


@admin_bp.before_request
def require_admin_session():
    if request.method == "OPTIONS":
        return None
    if request.endpoint == "admin.admin_login":
        return None
    if session.get("role") != "admin":
        return error_response("Admin authentication required", 401)
    return None


@admin_bp.route("/admin/login", methods=["POST"])
def admin_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    if not username or not password:
        return error_response("Username and password are required.")

    admin = query_one(
        """
        SELECT admin_id, username, display_name, password_hash
        FROM admin_users
        WHERE username = ?
        """,
        (username,),
    )
    if not admin or not check_password(password, admin.get("password_hash")):
        return error_response("Invalid credentials", 401)

    session.clear()
    session["role"] = "admin"
    session["login_id"] = admin["username"]
    session["user_id"] = admin["admin_id"]
    session["display_name"] = admin["display_name"]

    return success_response(
        {
            "username": admin["username"],
            "display_name": admin["display_name"],
            "role": "admin",
            "redirect": "admin-dashboard.html",
        },
        message="Login successful.",
    )


@admin_bp.route("/admin/dashboard-summary", methods=["GET"])
def dashboard_summary():
    students = query_one("SELECT COUNT(*) AS count FROM students") or {"count": 0}
    faculty = query_one("SELECT COUNT(*) AS count FROM faculty") or {"count": 0}
    subjects = query_one("SELECT COUNT(*) AS count FROM subjects") or {"count": 0}
    assignments = query_one("SELECT COUNT(*) AS count FROM student_subject") or {"count": 0}
    return success_response(
        {
            "students": students["count"],
            "faculty": faculty["count"],
            "subjects": subjects["count"],
            "assignments": assignments["count"],
        }
    )


@admin_bp.route("/admin/students", methods=["GET"])
def get_students():
    students = query_all(
        """
        SELECT student_id, name, enrollment_no, roll_no, year, branch, section
        FROM students
        ORDER BY branch, year, section, roll_no, name
        """
    )
    return success_response(students)


@admin_bp.route("/admin/students", methods=["POST"])
def add_student():
    payload = request.get_json(silent=True) or {}
    required_fields = ["name", "enrollment_no", "roll_no", "year", "branch", "section", "password"]
    missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    try:
        student_id = execute_write(
            """
            INSERT INTO students (name, enrollment_no, roll_no, year, branch, section, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(payload["name"]).strip(),
                str(payload["enrollment_no"]).strip(),
                str(payload["roll_no"]).strip(),
                int(payload["year"]),
                str(payload["branch"]).strip().upper(),
                str(payload["section"]).strip().upper(),
                make_password_hash(str(payload["password"])),
            ),
        )
    except ValueError:
        return error_response("Year must be a number.")
    except sqlite3.IntegrityError:
        return error_response("Enrollment number already exists.", 409)

    student = query_one(
        """
        SELECT student_id, name, enrollment_no, roll_no, year, branch, section
        FROM students
        WHERE student_id = ?
        """,
        (student_id,),
    )
    return success_response(student, message="Student added successfully.")


@admin_bp.route("/admin/faculty", methods=["GET"])
def get_faculty():
    faculty = query_all(
        """
        SELECT faculty_id, name, employee_id, department
        FROM faculty
        ORDER BY department, name
        """
    )
    return success_response(faculty)


@admin_bp.route("/admin/faculty", methods=["POST"])
def add_faculty():
    payload = request.get_json(silent=True) or {}
    required_fields = ["name", "employee_id", "department", "password"]
    missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    try:
        faculty_id = execute_write(
            """
            INSERT INTO faculty (name, employee_id, department, password_hash)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(payload["name"]).strip(),
                str(payload["employee_id"]).strip(),
                str(payload["department"]).strip(),
                make_password_hash(str(payload["password"])),
            ),
        )
    except sqlite3.IntegrityError:
        return error_response("Employee ID already exists.", 409)

    faculty_member = query_one(
        """
        SELECT faculty_id, name, employee_id, department
        FROM faculty
        WHERE faculty_id = ?
        """,
        (faculty_id,),
    )
    return success_response(faculty_member, message="Faculty member added successfully.")


@admin_bp.route("/admin/subjects", methods=["GET"])
def get_subjects():
    subjects = query_all(
        """
        SELECT s.subject_id, s.subject_name, s.faculty_id, f.name AS faculty_name
        FROM subjects AS s
        LEFT JOIN faculty AS f ON f.faculty_id = s.faculty_id
        ORDER BY s.subject_name
        """
    )
    return success_response(subjects)


@admin_bp.route("/admin/subjects", methods=["POST"])
def add_subject():
    payload = request.get_json(silent=True) or {}
    subject_name = str(payload.get("subject_name", "")).strip()
    faculty_id = payload.get("faculty_id")

    if not subject_name or faculty_id in (None, ""):
        return error_response("subject_name and faculty_id are required.")

    try:
        faculty_id = int(faculty_id)
        subject_id = execute_write(
            """
            INSERT INTO subjects (subject_name, faculty_id)
            VALUES (?, ?)
            """,
            (subject_name, faculty_id),
        )
    except ValueError:
        return error_response("faculty_id must be numeric.")
    except sqlite3.IntegrityError:
        return error_response("Subject could not be created with the provided faculty.", 409)

    subject = query_one(
        """
        SELECT s.subject_id, s.subject_name, s.faculty_id, f.name AS faculty_name
        FROM subjects AS s
        LEFT JOIN faculty AS f ON f.faculty_id = s.faculty_id
        WHERE s.subject_id = ?
        """,
        (subject_id,),
    )
    return success_response(subject, message="Subject added successfully.")


@admin_bp.route("/admin/assign-subject", methods=["POST"])
def assign_subject():
    payload = request.get_json(silent=True) or {}
    student_id = payload.get("student_id")
    subject_id = payload.get("subject_id")

    if student_id in (None, "") or subject_id in (None, ""):
        return error_response("student_id and subject_id are required.")

    try:
        execute_write(
            """
            INSERT INTO student_subject (student_id, subject_id)
            VALUES (?, ?)
            """,
            (int(student_id), int(subject_id)),
        )
    except ValueError:
        return error_response("student_id and subject_id must be numeric.")
    except sqlite3.IntegrityError:
        return error_response("This student is already assigned to the selected subject.", 409)

    return success_response(message="Subject assigned successfully.")


@admin_bp.route("/admin/student-subjects/<int:student_id>", methods=["GET"])
def get_student_subjects(student_id):
    subjects = query_all(
        """
        SELECT s.subject_id, s.subject_name, s.faculty_id, f.name AS faculty_name
        FROM student_subject AS ss
        INNER JOIN subjects AS s ON s.subject_id = ss.subject_id
        LEFT JOIN faculty AS f ON f.faculty_id = s.faculty_id
        WHERE ss.student_id = ?
        ORDER BY s.subject_name
        """,
        (student_id,),
    )
    return success_response(subjects)


@admin_bp.route("/admin/rules", methods=["GET"])
def admin_rules():
    return success_response(get_rules())


@admin_bp.route("/admin/rules", methods=["PUT"])
def save_rules():
    payload = request.get_json(silent=True) or {}
    try:
        eligibility = int(payload.get("eligibility_threshold"))
        warning = int(payload.get("warning_threshold"))
        high = int(payload.get("high_threshold"))
    except (TypeError, ValueError):
        return error_response("All thresholds are required and must be numeric.")

    validation_error = _validate_rules(eligibility, warning, high)
    if validation_error:
        return error_response(validation_error)

    update_rules(eligibility, warning, high)
    return success_response(get_rules(), message="Attendance rules updated successfully.")
