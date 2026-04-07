from collections import defaultdict
from datetime import date
from math import ceil

from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

try:
    from routes.admin import admin_bp
except Exception:
    admin_bp = None

app = Flask(__name__)
if admin_bp is not None:
    app.register_blueprint(admin_bp, url_prefix="/api")
CORS(app)

@app.route('/')
def home():
    return {"message": "API is running 🚀"}

# 🔐 Supabase config
SUPABASE_URL = "https://afxkkvygukkoxfjgqyur.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFmeGtrdnlndWtrb3hmamdxeXVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ3ODQ0MjUsImV4cCI6MjA5MDM2MDQyNX0.wg7Ob6vpFwRYaurexbIXgBcvd1z_Id5r-bRWfHBKeYc"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ELIGIBILITY_THRESHOLD = 67
WARNING_THRESHOLD = 75
HIGH_THRESHOLD = 85


def success_response(data=None, **extra):
    payload = {"status": "success"}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload)


def error_response(message, status_code=400):
    return jsonify({"status": "error", "message": message}), status_code


def safe_data(result):
    if result is None:
        return []
    return getattr(result, "data", None) or []


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
    return max(0, ceil(numerator / denominator))


def attendance_zone(percentage):
    if percentage < ELIGIBILITY_THRESHOLD:
        return "danger"
    if percentage < WARNING_THRESHOLD:
        return "watch"
    if percentage < HIGH_THRESHOLD:
        return "stable"
    return "high"


def eligibility_label(percentage):
    if percentage >= HIGH_THRESHOLD:
        return "Excellent"
    if percentage >= WARNING_THRESHOLD:
        return "Strong"
    if percentage >= ELIGIBILITY_THRESHOLD:
        return "Eligible"
    return "Shortage"


def get_faculty_record(employee_id):
    faculty_result = (
        supabase.table("faculty")
        .select("*")
        .eq("employee_id", employee_id)
        .maybe_single()
        .execute()
    )
    if faculty_result is None:
        return None
    return getattr(faculty_result, "data", None)


def get_subjects_for_faculty(faculty_id):
    subject_result = (
        supabase.table("subjects")
        .select("subject_id, subject_name, faculty_id")
        .eq("faculty_id", faculty_id)
        .execute()
    )
    return safe_data(subject_result)


def get_subject_student_rows(subject_id):
    return safe_data(
        supabase.table("student_subject")
        .select("student_id, students!inner(name, roll_no, branch, year, section)")
        .eq("subject_id", subject_id)
        .execute()
    )


def get_subject_attendance_rows(subject_id):
    return safe_data(
        supabase.table("attendance")
        .select("attendance_id, student_id, subject_id, status, date")
        .eq("subject_id", subject_id)
        .order("date")
        .execute()
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
                "eligibility": eligibility_label(percentage),
                "zone": attendance_zone(percentage),
                "required_for_67": required_classes_for_threshold(
                    present_classes, total_classes, ELIGIBILITY_THRESHOLD
                ),
                "required_for_75": required_classes_for_threshold(
                    present_classes, total_classes, WARNING_THRESHOLD
                ),
                "required_for_85": required_classes_for_threshold(
                    present_classes, total_classes, HIGH_THRESHOLD
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
    roster = build_subject_roster(subject["subject_id"])
    percentages = [row["percentage"] for row in roster]
    average_percentage = round(sum(percentages) / len(percentages), 2) if percentages else 0
    shortage_count = sum(1 for row in roster if row["percentage"] < ELIGIBILITY_THRESHOLD)
    strong_count = sum(1 for row in roster if row["percentage"] >= HIGH_THRESHOLD)

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
    faculty = get_faculty_record(employee_id)
    if not faculty:
        return []

    subjects = get_subjects_for_faculty(faculty["faculty_id"])
    if not subjects:
        return []

    subject_ids = [subject["subject_id"] for subject in subjects]
    subject_name_by_id = {subject["subject_id"]: subject["subject_name"] for subject in subjects}

    student_subject_rows = safe_data(
        supabase.table("student_subject")
        .select("student_id, subject_id, students!inner(name, roll_no)")
        .in_("subject_id", subject_ids)
        .execute()
    )
    attendance_rows = safe_data(
        supabase.table("attendance")
        .select("student_id, subject_id, status")
        .in_("subject_id", subject_ids)
        .execute()
    )

    attendance_by_student = defaultdict(list)
    for record in attendance_rows:
        attendance_by_student[str(record["student_id"])].append(record)

    student_map = {}
    for row in student_subject_rows:
        student_id = row["student_id"]
        key = str(student_id)
        student = row.get("students")
        if not isinstance(student, dict):
            continue
        if key not in student_map:
            student_map[key] = {
                "student_id": student_id,
                "name": student["name"],
                "roll_no": student["roll_no"],
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
                "eligibility": eligibility_label(percentage),
                "zone": attendance_zone(percentage),
                "required_for_67": required_classes_for_threshold(
                    present_classes, total_classes, ELIGIBILITY_THRESHOLD
                ),
                "required_for_75": required_classes_for_threshold(
                    present_classes, total_classes, WARNING_THRESHOLD
                ),
                "required_for_85": required_classes_for_threshold(
                    present_classes, total_classes, HIGH_THRESHOLD
                ),
                "subject_count": len(student["subject_ids"]),
                "subject_names": subject_names,
            }
        )

    return overview


# -------------------------
# 🔐 LOGIN (CLEANED & VALIDATED)
# -------------------------
@app.route("/api/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    login_id = payload.get("login_id")
    password = payload.get("password")
    role = payload.get("role")

    if not login_id or not password or not role:
        return error_response("Missing login_id, password, or role")

    try:
        if role == "student":
            result = (
                supabase.table("students")
                .select("name, enrollment_no")
                .eq("enrollment_no", login_id)
                .eq("password", password)
                .maybe_single()
                .execute()
            )
            if result.data:
                return jsonify(
                    {
                        "status": "success",
                        "name": result.data["name"],
                        "role": "student",
                        "enrollment_no": result.data["enrollment_no"],
                        "redirect": "student-dashboard.html",
                    }
                )

        if role == "faculty":
            result = (
                supabase.table("faculty")
                .select("name, employee_id")
                .eq("employee_id", login_id)
                .eq("password", password)
                .maybe_single()
                .execute()
            )
            if result.data:
                return jsonify(
                    {
                        "status": "success",
                        "name": result.data["name"],
                        "role": "faculty",
                        "employee_id": result.data["employee_id"],
                        "redirect": "faculty-dashboard.html",
                    }
                )

        return error_response("Invalid credentials", 401)
    except Exception as exc:
        return error_response(str(exc), 500)

@app.route("/api/student/<enrollment_no>")
def get_student(enrollment_no):
    try:
        result = (
            supabase.table("students")
            .select("student_id, name, enrollment_no, roll_no, year, branch")
            .eq("enrollment_no", enrollment_no)
            .maybe_single()
            .execute()
        )
        student = result.data
        if not student:
            return error_response("Student not found", 404)

        response = {"status": "success", "data": student}
        response.update(student)
        return jsonify(response)
    except Exception as exc:
        return error_response(str(exc), 500)
# -------------------------
# 📊 ATTENDANCE (FIXED TABLE NAMES)
# -------------------------
@app.route("/api/attendance/<student_id>")
def get_attendance(student_id):
    try:
        records = safe_data(
            supabase.table("attendance").select("*").eq("student_id", student_id).execute()
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
    except Exception as exc:
        return error_response(str(exc), 500)
# /subjectATTENDANCE
@app.route("/api/subject-attendance/<student_id>")
def subject_attendance(student_id):
    try:
        records = safe_data(
            supabase.table("attendance")
            .select("subject_id, status")
            .eq("student_id", student_id)
            .execute()
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
            summary["percentage"] = calculate_percentage(
                summary["present"], summary["total"]
            )

        return jsonify(result)
    except Exception as exc:
        return error_response(str(exc), 500)

# -------------------------
# 🧑‍🏫 MARK ATTENDANCE (VALIDATED)
# -------------------------
@app.route("/api/mark-attendance", methods=["POST"])
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
                    "student_id": student_id,
                    "subject_id": subject_id,
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
        target_date = normalized_rows[0]["date"]
        target_student_ids = [row["student_id"] for row in normalized_rows]
        existing_rows = safe_data(
            supabase.table("attendance")
            .select("attendance_id, student_id, status")
            .eq("subject_id", target_subject_id)
            .eq("date", target_date)
            .in_("student_id", target_student_ids)
            .execute()
        )
        existing_map = {
            str(record["student_id"]): record
            for record in existing_rows
            if record.get("student_id") is not None
        }

        rows_to_insert = []
        rows_to_update = []
        unchanged_count = 0
        for row in normalized_rows:
            existing = existing_map.get(str(row["student_id"]))
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
            supabase.table("attendance").insert(rows_to_insert).execute()
        for row in rows_to_update:
            (
                supabase.table("attendance")
                .update({"status": row["status"]})
                .eq("attendance_id", row["attendance_id"])
                .execute()
            )

        inserted_count = len(rows_to_insert)
        updated_count = len(rows_to_update)
        change_parts = []
        if inserted_count:
            change_parts.append(f"added {inserted_count}")
        if updated_count:
            change_parts.append(f"updated {updated_count}")
        if unchanged_count:
            change_parts.append(f"left {unchanged_count} unchanged")
        if change_parts:
            message = "Attendance saved: " + ", ".join(change_parts) + "."
        else:
            message = "No attendance changes were saved."

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

@app.route("/api/student-subjects/<student_id>")
def get_student_subjects(student_id):
    try:
        data = (
            supabase.table("student_subject")
            .select("subject_id, subjects(subject_name, faculty(name))")
            .eq("student_id", student_id)
            .execute()
        )
        return jsonify(data.data)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.route("/api/faculty/<employee_id>")
def get_faculty(employee_id):
    try:
        faculty = get_faculty_record(employee_id)
        if not faculty:
            return error_response("Faculty not found", 404)

        response = {"status": "success", "data": faculty}
        response.update(faculty)
        return jsonify(response)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.route("/api/faculty-subjects/<employee_id>")
def faculty_subjects(employee_id):
    try:
        faculty = get_faculty_record(employee_id)
        if not faculty:
            return success_response([])

        subjects = get_subjects_for_faculty(faculty["faculty_id"])
        summaries = [build_subject_summary(subject) for subject in subjects]
        summaries.sort(key=lambda item: item["subject_name"])
        return success_response(summaries)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.route("/api/faculty-stats/<employee_id>")
def faculty_stats(employee_id):
    try:
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
        average_attendance = (
            round(sum(percentages) / len(percentages), 2) if percentages else 0
        )

        data = {
            "active_subjects": len(subjects),
            "tracked_students": len(overview),
            "students_below_67": sum(
                1 for student in overview if student["percentage"] < ELIGIBILITY_THRESHOLD
            ),
            "students_between_67_75": sum(
                1
                for student in overview
                if ELIGIBILITY_THRESHOLD <= student["percentage"] < WARNING_THRESHOLD
            ),
            "students_above_85": sum(
                1 for student in overview if student["percentage"] >= HIGH_THRESHOLD
            ),
            "students_above_88": sum(
                1 for student in overview if student["percentage"] >= 88
            ),
            "average_attendance": average_attendance,
        }
        return success_response(data)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.route("/api/subject-cohorts/<subject_id>")
def subject_cohorts(subject_id):
    try:
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
    except Exception as exc:
        return error_response(str(exc), 500)


@app.route("/api/subject-students/<subject_id>/<branch>/<year>/<section>")
def get_filtered_students(subject_id, branch, year, section):
    try:
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

        percentages = [row["percentage"] for row in filtered_rows]
        meta = {
            "student_count": len(filtered_rows),
            "average_percentage": round(sum(percentages) / len(percentages), 2)
            if percentages
            else 0,
            "shortage_count": sum(
                1 for row in filtered_rows if row["percentage"] < ELIGIBILITY_THRESHOLD
            ),
            "strong_count": sum(
                1 for row in filtered_rows if row["percentage"] >= HIGH_THRESHOLD
            ),
            "branch": branch,
            "year": int(year),
            "section": section,
            "session_date": session_date,
            "recorded_for_session": sum(
                1 for row in filtered_rows if row.get("session_recorded")
            ),
        }
        return success_response(filtered_rows, meta=meta)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.route("/api/subject-session-history/<subject_id>/<branch>/<year>/<section>")
def subject_session_history(subject_id, branch, year, section):
    try:
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
            present_count = sum(
                1 for status in status_by_student.values() if status == "Present"
            )
            absent_count = sum(
                1 for status in status_by_student.values() if status == "Absent"
            )
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
    except Exception as exc:
        return error_response(str(exc), 500)


@app.route("/api/faculty-zone-students/<employee_id>/<zone>")
def faculty_zone_students(employee_id, zone):
    try:
        overview = build_faculty_student_overview(employee_id)
        zone_key = zone.lower()
        if zone_key == "top":
            zone_key = "high"

        if zone_key == "danger":
            filtered = [
                student for student in overview if student["percentage"] < ELIGIBILITY_THRESHOLD
            ]
            filtered.sort(key=lambda item: (item["percentage"], item["roll_no"]))
        elif zone_key == "watch":
            filtered = [
                student
                for student in overview
                if ELIGIBILITY_THRESHOLD <= student["percentage"] < WARNING_THRESHOLD
            ]
            filtered.sort(key=lambda item: (item["percentage"], item["roll_no"]))
        elif zone_key == "high":
            filtered = [student for student in overview if student["percentage"] >= HIGH_THRESHOLD]
            filtered.sort(key=lambda item: (-item["percentage"], item["roll_no"]))
        else:
            return success_response([])

        return success_response(filtered, zone=zone_key)
    except Exception as exc:
        return error_response(str(exc), 500)
# -------------------------
# 🚀 RUN
# -------------------------
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
