from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# Replace with your actual Supabase details
URL = "Subabase URL here"
KEY = "Supabase Key here"
URL = "Subabase URL here"
KEY = "Supabase Key here"
URL = "Subabase URL here" 
KEY = "Supabase Key here"
# URL = "" ---- paste URL here-----
# KEY = "" ----- paste key here-----
supabase: Client = create_client(URL, KEY)

# @app.route('/api/login', methods=['POST'])
# def login():
#     data = request.json
#     login_id = data.get('login_id')
#     password = data.get('password')
#     role_type = data.get('role')

#     try:
#         if role_type == 'student':
#             # Check if Enrollment No AND Password match in the Student table
#             result = supabase.table("Student").select("S_name") \
#                 .eq("S_enrollment_no", login_id) \
#                 .eq("S_password", password) \
#                 .maybe_single().execute()
            
#             if result.data:
#                 return jsonify({
#                     "status": "success",
#                     "redirect": "student-dashboard.html",
#                     "role": "student",
#                     "name": result.data['S_name']
#                 })

#         else: # Faculty
#             # Check if Email AND Password match in the Faculty table
#             result = supabase.table("Faculty").select("F_name") \
#                 .eq("F_email", login_id) \
#                 .eq("F_password", password) \
#                 .maybe_single().execute()
            
#             if result.data:
#                 return jsonify({
#                     "status": "success",
#                     "redirect": "faculty-dashboard.html",
#                     "role": "faculty",
#                     "name": result.data['F_name']
#                 })

#         # If no match was found in the selected table
#         return jsonify({"status": "error", "message": "Invalid ID/Email or Password"}), 401

#     except Exception as e:
#         return jsonify({"status": "error", "message": "Connection error"}), 500
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    login_id = data.get('login_id')
    password = data.get('password')
    role_type = data.get('role')

    try:
        if role_type == 'student':
            # Changed table to "student" and columns to lowercase
            result = supabase.table("student").select("s_name") \
                .eq("s_enrollment_no", login_id) \
                .eq("s_password", password) \
                .maybe_single().execute()
            
            if result.data:
                return jsonify({
                    "status": "success",
                    "redirect": "student-dashboard.html",
                    "role": "student",
                    "name": result.data['s_name'] # Note: lowercase key
                })

        else: # Faculty
            # Changed table to "faculty" and columns to lowercase
            result = supabase.table("faculty").select("f_name") \
                .eq("f_email", login_id) \
                .eq("f_password", password) \
                .maybe_single().execute()
            
            if result.data:
                return jsonify({
                    "status": "success",
                    "redirect": "faculty-dashboard.html",
                    "role": "faculty",
                    "name": result.data['f_name'] # Note: lowercase key
                })

        return jsonify({"status": "error", "message": "Invalid ID/Email or Password"}), 401

    except Exception as e:
        print(f"Error: {e}") # This will print the exact issue to your terminal
        return jsonify({"status": "error", "message": "Connection error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)