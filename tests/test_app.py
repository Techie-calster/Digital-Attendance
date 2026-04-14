import unittest

from app import app
from models.db import reset_database


class DigitalAttendanceTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.client = app.test_client()

    def login_student(self):
        response = self.client.post(
            "/api/login",
            json={"role": "student", "login_id": "ENR001", "password": "rahul123"},
        )
        self.assertEqual(response.status_code, 200)

    def login_faculty(self):
        response = self.client.post(
            "/api/login",
            json={"role": "faculty", "login_id": "EMP001", "password": "amit123"},
        )
        self.assertEqual(response.status_code, 200)

    def login_admin(self):
        response = self.client.post(
            "/api/admin/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_routes_require_authentication(self):
        response = self.client.get("/api/admin/students")
        self.assertEqual(response.status_code, 401)

    def test_student_can_view_own_dashboard_but_not_other_student(self):
        self.login_student()

        own_record = self.client.get("/api/student/ENR001")
        self.assertEqual(own_record.status_code, 200)
        self.assertEqual(own_record.get_json()["name"], "Rahul Sharma")

        other_record = self.client.get("/api/student/ENR002")
        self.assertEqual(other_record.status_code, 403)

    def test_admin_can_update_rules(self):
        self.login_admin()

        update_response = self.client.put(
            "/api/admin/rules",
            json={
                "eligibility_threshold": 68,
                "warning_threshold": 76,
                "high_threshold": 86,
            },
        )
        self.assertEqual(update_response.status_code, 200)

        rules_response = self.client.get("/api/admin/rules")
        self.assertEqual(rules_response.status_code, 200)
        self.assertEqual(
            rules_response.get_json()["data"],
            {
                "eligibility_threshold": 68,
                "warning_threshold": 76,
                "high_threshold": 86,
            },
        )

    def test_faculty_can_mark_attendance_for_assigned_subject(self):
        self.login_faculty()

        roster_response = self.client.get("/api/subject-students/1/CSE/1/A?session_date=2026-03-05")
        self.assertEqual(roster_response.status_code, 200)
        roster = roster_response.get_json()["data"]
        self.assertTrue(roster)

        attendance_payload = [
            {
                "student_id": row["student_id"],
                "subject_id": 1,
                "date": "2026-03-05",
                "status": "Present",
            }
            for row in roster
        ]
        mark_response = self.client.post("/api/mark-attendance", json=attendance_payload)
        self.assertEqual(mark_response.status_code, 200)
        mark_data = mark_response.get_json()["data"]
        self.assertEqual(mark_data["inserted_count"], len(roster))

        history_response = self.client.get("/api/subject-session-history/1/CSE/1/A")
        self.assertEqual(history_response.status_code, 200)
        history = history_response.get_json()["data"]
        self.assertEqual(history[0]["date"], "2026-03-05")


if __name__ == "__main__":
    unittest.main()
