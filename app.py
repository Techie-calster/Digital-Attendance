from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return {"message": "API is running 🚀"}

# 🔐 Supabase config
SUPABASE_URL = "https://afxkkvygukkoxfjgqyur.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFmeGtrdnlndWtrb3hmamdxeXVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ3ODQ0MjUsImV4cCI6MjA5MDM2MDQyNX0.wg7Ob6vpFwRYaurexbIXgBcvd1z_Id5r-bRWfHBKeYc"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------
# 🔐 LOGIN (FIXED ✅)
# -------------------------

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    login_id = data.get('login_id')
    password = data.get('password')
    role = data.get('role')

    try:
        # ✅ STUDENT LOGIN
        if role == "student":
            print("LOGIN INPUT:", login_id, password, role)
            result = supabase.table("students") \
                .select("name, enrollment_no") \
                .eq("enrollment_no", login_id) \
                .eq("password", password) \
                .maybe_single().execute()
            print("DB RESULT:", result.data)

            if result.data:
                return jsonify({
                    "status": "success",
                    "name": result.data["name"],
                    "role": "student",
                    "enrollment_no": result.data["enrollment_no"],  # ✅ ADD THIS
                    "redirect": "student-dashboard.html"
                })
    

        # ✅ FACULTY LOGIN
        elif role == "faculty":
            result = supabase.table("faculty") \
                .select("name, employee_id") \
                .eq("employee_id", login_id) \
                .eq("password", password) \
                .maybe_single().execute()

            if result.data:
                return jsonify({
                    "status": "success",
                    "name": result.data["name"],
                    "role": "faculty",
                    "redirect": "faculty-dashboard.html"
                })

        return jsonify({
            "status": "error",
            "message": "Invalid credentials"
        }), 401

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"status": "error"}), 500

@app.route('/api/student/<enrollment_no>')
def get_student(enrollment_no):
    try:
        result = supabase.table("students") \
            .select("student_id, name, enrollment_no, roll_no") \
            .eq("enrollment_no", enrollment_no) \
            .maybe_single().execute()

        return jsonify(result.data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# -------------------------
# 📊 ATTENDANCE (FIXED TABLE NAMES)
# -------------------------
@app.route('/api/attendance/<student_id>')
def get_attendance(student_id):
    try:
        data = supabase.table("attendance") \
            .select("*") \
            .eq("student_id", student_id).execute()

        records = data.data

        total = len(records)
        present = sum(1 for r in records if r['status'] == "Present")

        percentage = (present / total * 100) if total > 0 else 0

        return jsonify({
            "percentage": round(percentage, 2),
            "total_classes": total,
            "present": present
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# /subjectATTENDANCE
@app.route('/api/subject-attendance/<student_id>')
def subject_attendance(student_id):
    try:
        data = supabase.table("attendance") \
            .select("subject_id, status") \
            .eq("student_id", student_id).execute()

        records = data.data or []   

        result = {}

        for r in records:
            sid = r['subject_id']

            if sid not in result:
                result[sid] = {"present": 0, "total": 0}

            result[sid]["total"] += 1

            if r["status"] == "Present":
                result[sid]["present"] += 1

        for sid in result:
            p = result[sid]["present"]
            t = result[sid]["total"]
            result[sid]["percentage"] = round((p/t)*100, 2) if t > 0 else 0

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------
# 🧑‍🏫 MARK ATTENDANCE (FIXED TABLE NAME)
# -------------------------
@app.route('/api/mark-attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json()

    try:
        supabase.table("attendance").insert(data).execute()
        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/student-subjects/<student_id>')
def get_student_subjects(student_id):
    try:
        data = supabase.table("student_subject") \
           .select("subject_id, subjects(subject_name, faculty(name))") \
            .eq("student_id", student_id).execute()

        return jsonify(data.data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# -------------------------
# 🚀 RUN
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)