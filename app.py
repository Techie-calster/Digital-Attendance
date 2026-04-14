from collections import defaultdict
from datetime import date
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

from models.db import check_password, get_rules, query_all, query_one, run_transaction
from routes.admin import admin_bp

BASE_DIR = Path(__file__).resolve().parent
KNOWN_PAGES = {
    "login.html",
    "student-dashboard.html",
    "faculty-dashboard.html",
    "admin-login.html",
    "admin-dashboard.html",
    "ram_landing.html",
}

app = Flask(__name__)
app.secret_key = "digital-attendance-dev-secret"
app.register_blueprint(admin_bp, url_prefix="/api")
CORS(app, supports_credentials=True)


def success_response(data=None, **extra):
    payload = {"status": "success"}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload)


def error_response(message, status_code=400):
    return jsonify({"status": "error", "message": message}), status_code


def thresholds():
    return get_rules()


def calculate_percentage(present_count, total_count):
    if total_count <= 0:
        return 0.0
    return round((present_count / total_count) * 100, 2)


def required_classes_for_threshold(present_count, total_count, threshold_percent):
    if total_count <= 0:
        return 0

    threshold = threshold_percent / 100
    current_ratio = present_count / total_count
    if current_ratio >= threshold:
        return 0

    numerator = (threshold * total_count) - present_count
    denominator = 1 - threshold
    return max(0, int(-(-numerator // denominator)))


def attendance_zone(percentage, rules=None):
    current_rules = rules or thresholds()
    if percentage < current_rules["eligibility_threshold"]:
        return "danger"
    if percentage < current_rules["warning_threshold"]:
        return "watch"
    if percentage < current_rules["high_threshold"]:
        return "stable"
    return "high"


def eligibility_label(percentage, rules=None):
    current_rules = rules or thresholds()
    if percentage >= current_rules["high_threshold"]:
        return "Excellent"
    if percentage >= current_rules["warning_threshold"]:
        return "Strong"
    if percentage >= current_rules["eligibility_threshold"]:
        return "Eligible"
    return "Shortage"


def get_student_by_enrollment(enrollment_no):
    return query_one(
        """
        SELECT student_id, name, enrollment_no, roll_no, year, branch, section, password_hash
        FROM students
        WHERE enrollment_no = ?
        """,
        (enrollment_no,),
    )


def get_student_by_id(student_id):
    return query_one(
        """
        SELECT student_id, name, enrollment_no, roll_no, year, branch, section
        FROM students
        WHERE student_id = ?
        """,
        (student_id,),
    )


def get_faculty_record(employee_id):
    return query_one(
        """
        SELECT faculty_id, name, employee_id, department, password_hash
        FROM faculty
        WHERE employee_id = ?
        """,
        (employee_id,),
    )


def get_subjects_for_faculty(faculty_id):
    return query_all(
        """
        SELECT subject_id, subject_name, faculty_id
        FROM subjects
        WHERE faculty_id = ?
        ORDER BY subject_name
        """,
        (faculty_id,),
    )


def get_subject_student_rows(subject_id):
    rows = query_all(
        """
        SELECT ss.student_id, s.name, s.roll_no, s.branch, s.year, s.section
        FROM student_subject AS ss
        INNER JOIN students AS s ON s.student_id = ss.student_id
        WHERE ss.subject_id = ?
        ORDER BY s.roll_no, s.name
        """,
        (subject_id,),
    )
    return [
        {
            "student_id": row["student_id"],
            "students": {
                "name": row["name"],
                "roll_no": row["roll_no"],
                "branch": row["branch"],
                "year": row["year"],
                "section": row["section"],
            },
        }
        for row in rows
    ]


def get_subject_attendance_rows(subject_id):
    return query_all(
        """
        SELECT attendance_id, student_id, subject_id, status, date
        FROM attendance
        WHERE subject_id = ?
        ORDER BY date, attendance_id
        """,
        (subject_id,),
    )


def row_matches_cohort(row, branch, year, section):
    try:
        return (
            str(row["branch"]).upper() == str(branch).upper()
            and int(row["year"]) == int(year)
            and str(row["section"]).upper() == str(section).upper()
        )
    except (KeyError, TypeError, ValueError):
        return False


def filter_roster_by_cohort(roster, branch, year, section):
    return [row for row in roster if row_matches_cohort(row, branch, year, section)]


def build_subject_roster(
    subject_id,
    session_date=None,
    exclude_session_date=False,
    student_subject_rows=None,
    attendance_rows=None,
):
    current_rules = thresholds()
    if student_subject_rows is None:
        student_subject_rows = get_subject_student_rows(subject_id)
    if attendance_rows is None:
        attendance_rows = get_subject_attendance_rows(subject_id)

    attendance_by_student = defaultdict(list)
    for record in attendance_rows:
        attendance_by_student[str(record["student_id"])].append(record)

    roster = []
    for row in student_subject_rows:
        student = row.get("students")
        if not isinstance(student, dict):
            continue
        student_id = row["student_id"]
        key = str(student_id)
        all_records = attendance_by_student[key]
        session_records = []
        if session_date:
            session_records = [
                record for record in all_records if record.get("date") == session_date
            ]
        records = [
            record
            for record in all_records
            if not (exclude_session_date and session_date and record.get("date") == session_date)
        ]
        total_classes = len(records)
        present_classes = sum(1 for record in records if record["status"] == "Present")
        percentage = calculate_percentage(present_classes, total_classes)
        latest_record = records[-1] if records else None

        roster.append(
            {
                "student_id": student_id,
                "name": student["name"],
                "roll_no": student["roll_no"],
                "branch": student["branch"],
                "year": student["year"],
                "section": student["section"],
                "previous_attendance": f"{present_classes}/{total_classes}",
                "present_classes": present_classes,
                "total_classes": total_classes,
                "percentage": percentage,
                "eligibility": eligibility_label(percentage, current_rules),
                "zone": attendance_zone(percentage, current_rules),
                "required_for_67": required_classes_for_threshold(
                    present_classes,
                    total_classes,
                    current_rules["eligibility_threshold"],
                ),
                "required_for_75": required_classes_for_threshold(
                    present_classes,
                    total_classes,
                    current_rules["warning_threshold"],
                ),
                "required_for_85": required_classes_for_threshold(
                    present_classes,
                    total_classes,
                    current_rules["high_threshold"],
                ),
                "last_status": latest_record["status"] if latest_record else None,
                "last_attendance_date": latest_record["date"] if latest_record else None,
                "session_status": session_records[-1]["status"] if session_records else None,
                "session_recorded": bool(session_records),
            }
        )

    roster.sort(key=lambda item: (item["percentage"], item["roll_no"], item["name"]))
    return roster


def build_subject_summary(subject):
    current_rules = thresholds()
    roster = build_subject_roster(subject["subject_id"])
    percentages = [row["percentage"] for row in roster]
    average_percentage = round(sum(percentages) / len(percentages), 2) if percentages else 0
    shortage_count = sum(
        1 for row in roster if row["percentage"] < current_rules["eligibility_threshold"]
    )
    strong_count = sum(
        1 for row in roster if row["percentage"] >= current_rules["high_threshold"]
    )

    cohorts = []
    cohort_map = defaultdict(int)
    for row in roster:
        cohort_key = (row["branch"], row["year"], row["section"])
        cohort_map[cohort_key] += 1

    for (branch, year, section), student_count in sorted(cohort_map.items()):
        cohorts.append(
            {
                "branch": branch,
                "year": year,
                "section": section,
                "student_count": student_count,
            }
        )

    last_attendance_date = None
    dated_rows = [row["last_attendance_date"] for row in roster if row["last_attendance_date"]]
    if dated_rows:
        last_attendance_date = max(dated_rows)

    return {
        "subject_id": subject["subject_id"],
        "subject_name": subject["subject_name"],
        "student_count": len(roster),
        "cohort_count": len(cohorts),
        "average_percentage": average_percentage,
        "shortage_count": shortage_count,
        "strong_count": strong_count,
        "last_attendance_date": last_attendance_date,
        "cohorts": cohorts,
    }


def build_faculty_student_overview(employee_id):
    current_rules = thresholds()
    faculty = get_faculty_record(employee_id)
    if not faculty:
        return []

    subjects = get_subjects_for_faculty(faculty["faculty_id"])
    if not subjects:
        return []

    subject_ids = [subject["subject_id"] for subject in subjects]
    placeholders = ",".join("?" for _ in subject_ids)
    subject_name_by_id = {subject["subject_id"]: subject["subject_name"] for subject in subjects}

    student_subject_rows = query_all(
        f"""
        SELECT ss.student_id, ss.subject_id, s.name, s.roll_no
        FROM student_subject AS ss
        INNER JOIN students AS s ON s.student_id = ss.student_id
        WHERE ss.subject_id IN ({placeholders})
        ORDER BY s.roll_no, s.name
        """,
        subject_ids,
    )
    attendance_rows = query_all(
        f"""
        SELECT student_id, subject_id, status
        FROM attendance
        WHERE subject_id IN ({placeholders})
        """,
        subject_ids,
    )

    attendance_by_student = defaultdict(list)
    for record in attendance_rows:
        attendance_by_student[str(record["student_id"])].append(record)

    student_map = {}
    for row in student_subject_rows:
        student_id = row["student_id"]
        key = str(student_id)
        if key not in student_map:
            student_map[key] = {
                "student_id": student_id,
                "name": row["name"],
                "roll_no": row["roll_no"],
                "subject_ids": set(),
            }
        student_map[key]["subject_ids"].add(row["subject_id"])

    overview = []
    for key, student in student_map.items():
        records = [
            record
            for record in attendance_by_student[key]
            if record["subject_id"] in student["subject_ids"]
        ]
        total_classes = len(records)
        present_classes = sum(1 for record in records if record["status"] == "Present")
        percentage = calculate_percentage(present_classes, total_classes)
        subject_names = [
            subject_name_by_id[subject_id] for subject_id in sorted(student["subject_ids"])
        ]
        overview.append(
            {
                "student_id": student["student_id"],
                "name": student["name"],
                "roll_no": student["roll_no"],
                "percentage": percentage,
                "eligibility": eligibility_label(percentage, current_rules),
                "zone": attendance_zone(percentage, current_rules),
                "required_for_67": required_classes_for_threshold(
                    present_classes,
                    total_classes,
                    current_rules["eligibility_threshold"],
                ),
                "required_for_75": required_classes_for_threshold(
                    present_classes,
                    total_classes,
                    current_rules["warning_threshold"],
                ),
                "required_for_85": required_classes_for_threshold(
                    present_classes,
                    total_classes,
                    current_rules["high_threshold"],
                ),
                "subject_count": len(student["subject_ids"]),
                "subject_names": subject_names,
            }
        )

    return overview


def clear_and_set_session(role, login_id, user_id, display_name):
    session.clear()
    session["role"] = role
    session["login_id"] = login_id
    session["user_id"] = user_id
    session["display_name"] = display_name


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                return error_response("Authentication required", 401)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def ensure_student_access(enrollment_no=None, student_id=None):
    role = session.get("role")
    if role == "admin":
        return None
    if role != "student":
        return error_response("Student authentication required", 401)
    if enrollment_no is not None and session.get("login_id") != enrollment_no:
        return error_response("You can only access your own student record.", 403)
    if student_id is not None and str(session.get("user_id")) != str(student_id):
        return error_response("You can only access your own student record.", 403)
    return None


def ensure_faculty_access(employee_id=None, subject_id=None):
    role = session.get("role")
    if role == "admin":
        return None
    if role != "faculty":
        return error_response("Faculty authentication required", 401)
    if employee_id is not None and session.get("login_id") != employee_id:
        return error_response("You can only access your own faculty record.", 403)
    if subject_id is not None:
        assigned_subject = query_one(
            """
            SELECT s.subject_id
            FROM subjects AS s
            INNER JOIN faculty AS f ON f.faculty_id = s.faculty_id
            WHERE f.employee_id = ? AND s.subject_id = ?
            """,
            (session.get("login_id"), subject_id),
        )
        if not assigned_subject:
            return error_response(
                "This subject is not assigned to the logged-in faculty member.",
                403,
            )
    return None


@app.route("/api/health")
def health():
    return success_response({"message": "API is running"})


@app.route("/api/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    login_id = str(payload.get("login_id", "")).strip()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "")).strip().lower()

    if not login_id or not password or role not in {"student", "faculty"}:
        return error_response("Valid login_id, password, and role are required.")

    if role == "student":
        student = get_student_by_enrollment(login_id)
        if not student or not check_password(password, student.get("password_hash")):
            return error_response("Invalid credentials", 401)
        clear_and_set_session("student", student["enrollment_no"], student["student_id"], student["name"])
        return success_response(
            {
                "name": student["name"],
                "role": "student",
                "student_id": student["student_id"],
                "enrollment_no": student["enrollment_no"],
                "redirect": "student-dashboard.html",
            },
            message="Login successful.",
        )

    faculty = get_faculty_record(login_id)
    if not faculty or not check_password(password, faculty.get("password_hash")):
        return error_response("Invalid credentials", 401)
    clear_and_set_session("faculty", faculty["employee_id"], faculty["faculty_id"], faculty["name"])
    return success_response(
        {
            "name": faculty["name"],
            "role": "faculty",
            "faculty_id": faculty["faculty_id"],
            "employee_id": faculty["employee_id"],
            "redirect": "faculty-dashboard.html",
        },
        message="Login successful.",
    )


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return success_response(message="Logged out successfully.")


@app.route("/api/session")
def get_session_state():
    if not session.get("role"):
        return success_response({"authenticated": False})
    return success_response(
        {
            "authenticated": True,
            "role": session.get("role"),
            "login_id": session.get("login_id"),
            "user_id": session.get("user_id"),
            "display_name": session.get("display_name"),
        }
    )


@app.route("/api/rules")
def rules():
    return success_response(get_rules())


@app.route("/api/student/<enrollment_no>")
def get_student(enrollment_no):
    access_error = ensure_student_access(enrollment_no=enrollment_no)
    if access_error:
        return access_error

    student = query_one(
        """
        SELECT student_id, name, enrollment_no, roll_no, year, branch, section
        FROM students
        WHERE enrollment_no = ?
        """,
        (enrollment_no,),
    )
    if not student:
        return error_response("Student not found", 404)

    response = {"status": "success", "data": student}
    response.update(student)
    return jsonify(response)


@app.route("/api/attendance/<student_id>")
def get_attendance(student_id):
    access_error = ensure_student_access(student_id=student_id)
    if access_error:
        return access_error

    records = query_all(
        """
        SELECT status
        FROM attendance
        WHERE student_id = ?
        """,
        (student_id,),
    )
    total_classes = len(records)
    present_classes = sum(1 for record in records if record["status"] == "Present")

    return jsonify(
        {
            "percentage": calculate_percentage(present_classes, total_classes),
            "total_classes": total_classes,
            "present": present_classes,
        }
    )


@app.route("/api/subject-attendance/<student_id>")
def subject_attendance(student_id):
    access_error = ensure_student_access(student_id=student_id)
    if access_error:
        return access_error

    records = query_all(
        """
        SELECT subject_id, status
        FROM attendance
        WHERE student_id = ?
        """,
        (student_id,),
    )

    result = {}
    for record in records:
        subject_id = record["subject_id"]
        if subject_id not in result:
            result[subject_id] = {"present": 0, "total": 0}
        result[subject_id]["total"] += 1
        if record["status"] == "Present":
            result[subject_id]["present"] += 1

    for subject_id, summary in result.items():
        summary["percentage"] = calculate_percentage(summary["present"], summary["total"])

    return jsonify(result)


@app.route("/api/student-subjects/<student_id>")
def get_student_subjects(student_id):
    access_error = ensure_student_access(student_id=student_id)
    if access_error:
        return access_error

    rows = query_all(
        """
        SELECT
            ss.subject_id,
            s.subject_name,
            f.name AS faculty_name,
            COALESCE(m.marks, 0) AS marks
        FROM student_subject AS ss
        INNER JOIN subjects AS s ON s.subject_id = ss.subject_id
        LEFT JOIN faculty AS f ON f.faculty_id = s.faculty_id
        LEFT JOIN marks AS m ON m.student_id = ss.student_id AND m.subject_id = ss.subject_id
        WHERE ss.student_id = ?
        ORDER BY s.subject_name
        """,
        (student_id,),
    )
    payload = [
        {
            "subject_id": row["subject_id"],
            "subjects": {
                "subject_name": row["subject_name"],
                "faculty": {"name": row["faculty_name"]} if row["faculty_name"] else None,
            },
            "marks": row["marks"],
        }
        for row in rows
    ]
    return jsonify(payload)


@app.route("/api/student-subject-history/<student_id>/<subject_id>")
def student_subject_history(student_id, subject_id):
    access_error = ensure_student_access(student_id=student_id)
    if access_error:
        return access_error

    history = query_all(
        """
        SELECT date, status
        FROM attendance
        WHERE student_id = ? AND subject_id = ?
        ORDER BY date DESC, attendance_id DESC
        """,
        (student_id, subject_id),
    )
    return success_response(history)


@app.route("/api/faculty/<employee_id>")
def get_faculty(employee_id):
    access_error = ensure_faculty_access(employee_id=employee_id)
    if access_error:
        return access_error

    faculty = get_faculty_record(employee_id)
    if not faculty:
        return error_response("Faculty not found", 404)

    faculty.pop("password_hash", None)
    response = {"status": "success", "data": faculty}
    response.update(faculty)
    return jsonify(response)


@app.route("/api/faculty-subjects/<employee_id>")
def faculty_subjects(employee_id):
    access_error = ensure_faculty_access(employee_id=employee_id)
    if access_error:
        return access_error

    faculty = get_faculty_record(employee_id)
    if not faculty:
        return success_response([])

    subjects = get_subjects_for_faculty(faculty["faculty_id"])
    summaries = [build_subject_summary(subject) for subject in subjects]
    summaries.sort(key=lambda item: item["subject_name"])
    return success_response(summaries)


@app.route("/api/faculty-stats/<employee_id>")
def faculty_stats(employee_id):
    access_error = ensure_faculty_access(employee_id=employee_id)
    if access_error:
        return access_error

    current_rules = thresholds()
    faculty = get_faculty_record(employee_id)
    if not faculty:
        return success_response(
            {
                "active_subjects": 0,
                "tracked_students": 0,
                "students_below_67": 0,
                "students_between_67_75": 0,
                "students_above_85": 0,
                "students_above_88": 0,
                "average_attendance": 0,
            }
        )

    subjects = get_subjects_for_faculty(faculty["faculty_id"])
    overview = build_faculty_student_overview(employee_id)
    percentages = [student["percentage"] for student in overview]
    average_attendance = round(sum(percentages) / len(percentages), 2) if percentages else 0

    data = {
        "active_subjects": len(subjects),
        "tracked_students": len(overview),
        "students_below_67": sum(
            1
            for student in overview
            if student["percentage"] < current_rules["eligibility_threshold"]
        ),
        "students_between_67_75": sum(
            1
            for student in overview
            if current_rules["eligibility_threshold"]
            <= student["percentage"]
            < current_rules["warning_threshold"]
        ),
        "students_above_85": sum(
            1
            for student in overview
            if student["percentage"] >= current_rules["high_threshold"]
        ),
        "students_above_88": sum(1 for student in overview if student["percentage"] >= 88),
        "average_attendance": average_attendance,
    }
    return success_response(data)


@app.route("/api/subject-cohorts/<subject_id>")
def subject_cohorts(subject_id):
    access_error = ensure_faculty_access(subject_id=subject_id)
    if access_error:
        return access_error

    roster = build_subject_roster(subject_id)
    cohort_map = defaultdict(int)
    for row in roster:
        cohort_key = (row["branch"], row["year"], row["section"])
        cohort_map[cohort_key] += 1

    cohorts = []
    for (branch, year, section), student_count in sorted(cohort_map.items()):
        cohorts.append(
            {
                "branch": branch,
                "year": year,
                "section": section,
                "student_count": student_count,
            }
        )

    return success_response(cohorts)


@app.route("/api/subject-students/<subject_id>/<branch>/<year>/<section>")
def get_filtered_students(subject_id, branch, year, section):
    access_error = ensure_faculty_access(subject_id=subject_id)
    if access_error:
        return access_error

    session_date = request.args.get("session_date")
    if session_date:
        try:
            date.fromisoformat(session_date)
        except ValueError:
            return error_response("Attendance date must be in YYYY-MM-DD format")

    roster = build_subject_roster(
        subject_id,
        session_date=session_date,
        exclude_session_date=bool(session_date),
    )
    filtered_rows = filter_roster_by_cohort(roster, branch, year, section)

    current_rules = thresholds()
    percentages = [row["percentage"] for row in filtered_rows]
    meta = {
        "student_count": len(filtered_rows),
        "average_percentage": round(sum(percentages) / len(percentages), 2) if percentages else 0,
        "shortage_count": sum(
            1
            for row in filtered_rows
            if row["percentage"] < current_rules["eligibility_threshold"]
        ),
        "strong_count": sum(
            1
            for row in filtered_rows
            if row["percentage"] >= current_rules["high_threshold"]
        ),
        "branch": branch,
        "year": int(year),
        "section": section,
        "session_date": session_date,
        "recorded_for_session": sum(1 for row in filtered_rows if row.get("session_recorded")),
    }
    return success_response(filtered_rows, meta=meta)


@app.route("/api/subject-session-history/<subject_id>/<branch>/<year>/<section>")
def subject_session_history(subject_id, branch, year, section):
    access_error = ensure_faculty_access(subject_id=subject_id)
    if access_error:
        return access_error

    student_subject_rows = get_subject_student_rows(subject_id)
    attendance_rows = get_subject_attendance_rows(subject_id)
    roster = build_subject_roster(
        subject_id,
        student_subject_rows=student_subject_rows,
        attendance_rows=attendance_rows,
    )
    filtered_rows = filter_roster_by_cohort(roster, branch, year, section)
    expected_students = len(filtered_rows)
    if not expected_students:
        return success_response(
            [],
            meta={
                "expected_students": 0,
                "branch": branch,
                "year": int(year),
                "section": section,
            },
        )

    allowed_student_ids = {str(row["student_id"]) for row in filtered_rows}
    sessions = defaultdict(dict)
    for record in attendance_rows:
        student_key = str(record.get("student_id"))
        session_key = record.get("date")
        status = record.get("status")
        if student_key not in allowed_student_ids or not session_key:
            continue
        sessions[session_key][student_key] = status

    history = []
    for session_key in sorted(sessions.keys(), reverse=True):
        status_by_student = sessions[session_key]
        recorded_count = len(status_by_student)
        present_count = sum(1 for status in status_by_student.values() if status == "Present")
        absent_count = sum(1 for status in status_by_student.values() if status == "Absent")
        missing_count = max(0, expected_students - recorded_count)
        history.append(
            {
                "date": session_key,
                "present_count": present_count,
                "absent_count": absent_count,
                "recorded_count": recorded_count,
                "expected_count": expected_students,
                "missing_count": missing_count,
                "completion_label": "Complete"
                if recorded_count == expected_students
                else "Partial",
            }
        )

    return success_response(
        history,
        meta={
            "expected_students": expected_students,
            "branch": branch,
            "year": int(year),
            "section": section,
        },
    )


@app.route("/api/faculty-zone-students/<employee_id>/<zone>")
def faculty_zone_students(employee_id, zone):
    access_error = ensure_faculty_access(employee_id=employee_id)
    if access_error:
        return access_error

    current_rules = thresholds()
    overview = build_faculty_student_overview(employee_id)
    zone_key = zone.lower()
    if zone_key == "top":
        zone_key = "high"

    if zone_key == "danger":
        filtered = [
            student
            for student in overview
            if student["percentage"] < current_rules["eligibility_threshold"]
        ]
        filtered.sort(key=lambda item: (item["percentage"], item["roll_no"]))
    elif zone_key == "watch":
        filtered = [
            student
            for student in overview
            if current_rules["eligibility_threshold"]
            <= student["percentage"]
            < current_rules["warning_threshold"]
        ]
        filtered.sort(key=lambda item: (item["percentage"], item["roll_no"]))
    elif zone_key == "high":
        filtered = [
            student
            for student in overview
            if student["percentage"] >= current_rules["high_threshold"]
        ]
        filtered.sort(key=lambda item: (-item["percentage"], item["roll_no"]))
    else:
        return success_response([])

    return success_response(filtered, zone=zone_key)


@app.route("/api/mark-attendance", methods=["POST"])
@role_required("faculty", "admin")
def submit_attendance():
    payload = request.get_json(silent=True)
    if not isinstance(payload, list) or not payload:
        return error_response("No attendance data provided")

    try:
        normalized_rows = []
        seen_rows = set()
        subject_ids = set()
        session_dates = set()

        for entry in payload:
            if not isinstance(entry, dict):
                return error_response("Attendance payload must contain objects only")

            student_id = entry.get("student_id")
            subject_id = entry.get("subject_id")
            session_date = entry.get("date")
            status = str(entry.get("status", "")).strip().capitalize()

            if not student_id or not subject_id or not session_date or not status:
                return error_response(
                    "Each attendance row needs student_id, subject_id, date, and status"
                )

            if status not in {"Present", "Absent"}:
                return error_response("Attendance status must be Present or Absent")

            try:
                date.fromisoformat(session_date)
            except ValueError:
                return error_response("Attendance date must be in YYYY-MM-DD format")

            unique_key = (str(student_id), str(subject_id), session_date)
            if unique_key in seen_rows:
                return error_response("Duplicate attendance rows found in the request")

            seen_rows.add(unique_key)
            subject_ids.add(str(subject_id))
            session_dates.add(session_date)
            normalized_rows.append(
                {
                    "student_id": int(student_id),
                    "subject_id": int(subject_id),
                    "date": session_date,
                    "status": status,
                }
            )

        if len(subject_ids) != 1:
            return error_response("Attendance submission must target exactly one subject")
        if len(session_dates) != 1:
            return error_response(
                "Attendance submission must target exactly one class session date"
            )

        target_subject_id = normalized_rows[0]["subject_id"]
        access_error = ensure_faculty_access(subject_id=target_subject_id)
        if access_error:
            return access_error

        target_student_ids = [row["student_id"] for row in normalized_rows]
        placeholders = ",".join("?" for _ in target_student_ids)
        assigned_students = query_all(
            f"""
            SELECT student_id
            FROM student_subject
            WHERE subject_id = ? AND student_id IN ({placeholders})
            """,
            [target_subject_id] + target_student_ids,
        )
        assigned_student_ids = {row["student_id"] for row in assigned_students}
        if assigned_student_ids != set(target_student_ids):
            return error_response(
                "Attendance can only be recorded for students assigned to the selected subject."
            )

        def commit_rows(connection):
            existing_rows = connection.execute(
                f"""
                SELECT attendance_id, student_id, status
                FROM attendance
                WHERE subject_id = ? AND date = ? AND student_id IN ({placeholders})
                """,
                [target_subject_id, normalized_rows[0]["date"]] + target_student_ids,
            ).fetchall()
            existing_map = {int(row["student_id"]): dict(row) for row in existing_rows}

            rows_to_insert = []
            rows_to_update = []
            unchanged_count = 0
            for row in normalized_rows:
                existing = existing_map.get(int(row["student_id"]))
                if not existing:
                    rows_to_insert.append(row)
                    continue
                if existing.get("status") == row["status"]:
                    unchanged_count += 1
                    continue
                rows_to_update.append(
                    {
                        "attendance_id": existing["attendance_id"],
                        "status": row["status"],
                    }
                )

            if rows_to_insert:
                connection.executemany(
                    """
                    INSERT INTO attendance (student_id, subject_id, date, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            row["student_id"],
                            row["subject_id"],
                            row["date"],
                            row["status"],
                        )
                        for row in rows_to_insert
                    ],
                )

            for row in rows_to_update:
                connection.execute(
                    """
                    UPDATE attendance
                    SET status = ?
                    WHERE attendance_id = ?
                    """,
                    (row["status"], row["attendance_id"]),
                )

            return {
                "inserted_count": len(rows_to_insert),
                "updated_count": len(rows_to_update),
                "unchanged_count": unchanged_count,
            }

        result = run_transaction(commit_rows)
        inserted_count = result["inserted_count"]
        updated_count = result["updated_count"]
        unchanged_count = result["unchanged_count"]
        change_parts = []
        if inserted_count:
            change_parts.append(f"added {inserted_count}")
        if updated_count:
            change_parts.append(f"updated {updated_count}")
        if unchanged_count:
            change_parts.append(f"left {unchanged_count} unchanged")
        message = (
            "Attendance saved: " + ", ".join(change_parts) + "."
            if change_parts
            else "No attendance changes were saved."
        )

        return success_response(
            {
                "inserted_count": inserted_count,
                "updated_count": updated_count,
                "unchanged_count": unchanged_count,
                "date": next(iter(session_dates)),
            },
            message=message,
        )
    except Exception as exc:
        return error_response(str(exc), 500)


@app.route("/")
def landing_page():
    return send_from_directory(BASE_DIR, "ram_landing.html")


@app.route("/login.html")
@app.route("/student-dashboard.html")
@app.route("/faculty-dashboard.html")
@app.route("/admin-login.html")
@app.route("/admin-dashboard.html")
@app.route("/ram_landing.html")
def serve_known_pages():
    page_name = request.path.lstrip("/")
    return send_from_directory(BASE_DIR, page_name)


@app.route("/Digital-Attendance/<path:filename>")
def serve_legacy_workspace_file(filename):
    if filename in KNOWN_PAGES:
        return send_from_directory(BASE_DIR, filename)
    return serve_workspace_file(filename)


@app.route("/<path:filename>")
def serve_workspace_file(filename):
    if filename.startswith("api/"):
        return error_response("Not found", 404)

    target = BASE_DIR / filename
    allowed_suffixes = {".html", ".js", ".css", ".png", ".jpg", ".jpeg", ".pdf"}
    if not target.is_file() or target.suffix.lower() not in allowed_suffixes:
        return error_response("Not found", 404)
    return send_from_directory(BASE_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
