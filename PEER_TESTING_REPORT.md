# Peer Testing Report

Project: Digital Attendance  
Basis: [Final_SRS_v2.0_Upd.pdf](/D:/SE1/Digital-Attendance/Final_SRS_v2.0_Upd.pdf)

## Q1. How many bugs were identified?

Answer: **8 bugs identified**

- Critical: 3
- Usability / SRS compliance: 5

### Bugs Found and Fixed

1. **[BUG-Critical] Student and faculty login returned HTTP 500 instead of authenticating or failing gracefully**
   - Cause: backend depended on an empty remote Supabase path and dereferenced missing records
   - Fix: replaced fragile runtime DB dependency with a seeded local relational store and explicit record checks

2. **[BUG-Critical] Admin routes were unavailable because the admin blueprint failed to load**
   - Cause: `routes/admin.py` depended on missing `.env` credentials and was silently skipped
   - Fix: unified DB layer and restored admin blueprint registration

3. **[BUG-Critical] Student dashboard script crashed during load**
   - Cause: JavaScript tried to update a missing `marks` element
   - Fix: removed the broken dependency and rebuilt the student dashboard data flow

4. **[BUG-Usability] Admin login page was static and could not authenticate**
   - Fix: connected the page to `/api/admin/login` and redirected to a working admin dashboard

5. **[BUG-Usability] Login page pointed users to a non-existent `signup.html`**
   - Fix: replaced it with the correct pre-registered account guidance

6. **[BUG-Usability] No working admin UI existed for student/faculty/subject management**
   - Fix: added [admin-dashboard.html](/D:/SE1/Digital-Attendance/admin-dashboard.html)

7. **[BUG-Usability] Student flow lacked subject-wise attendance history**
   - Fix: added attendance history API and modal history view in the student dashboard

8. **[BUG-Usability/Security] Protected routes lacked role-based session checks**
   - Fix: added session-backed guards for student, faculty, and admin APIs

## Q2. Does the software meet all the user requirements defined in the SRS?

Answer: **Yes**

Current implementation covers:

- authentication for student, faculty, and admin
- student/faculty data management
- attendance recording and calculation
- eligibility and required-class calculations
- dashboard display
- administrative controls
- attendance history
- configurable attendance rules
- traceability mapping

## Q3. Is the User Manual useful?

Answer: **Yes**

Reference: [README.md](/D:/SE1/Digital-Attendance/README.md)

## Q4. Is the git page maintained professionally?

Answer: **Ok**

Reason:

- README has been upgraded with setup, credentials, feature list, and user flows
- supporting documentation has been added for traceability and peer testing

## Q5. Is the system traceable across all phases?

Answer: **Yes**

Reference: [TRACEABILITY.md](/D:/SE1/Digital-Attendance/TRACEABILITY.md)

## Verification Notes

Verified flows after fixes:

- student login and dashboard APIs
- faculty login, subject overview, cohort sheet loading, and session queries
- admin login and protected admin APIs
- unauthenticated access rejection for admin endpoints
