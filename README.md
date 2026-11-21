# UniTrack - Smart University Management (Flask + PostgreSQL)

## Setup
1. `pip install -r requirements.txt`
2. Create the database and run, in pgAdmin, in this order: `database.sql`, then `more_data.sql` (optional sample data).
3. Copy `.env.example` to `.env` and fill in your DB password / SECRET_KEY.
4. `python app.py` -> open http://127.0.0.1:5000  (the new tables and all login accounts are created automatically on start).

## Logins (one page: /login)
| Role | Username | Starting password |
|------|----------|-------------------|
| Admin | `admin` | `admin123` (or ADMIN_PASSWORD in .env) |
| Student | enrollment number, e.g. `KRM25CSE001` | the enrollment number itself |
| Faculty | university email, e.g. `anita.sharma@unitrack.edu` | `Faculty@123` |
Everyone must set their own password at first login. Admin can reset anyone on **User Accounts**.
Passwords are hashed; new students/faculty get accounts automatically. Staying logged in uses a signed session cookie.

## Admin
Dashboard, list pages with Department/Course filters, search, pagination and CSV export, plus:
Announcements, Timetable (clash detection), Exam Schedule, Leave Requests, Fees (+receipts), Student Queries,
Bulk Attendance, Marks Entry (bulk, auto-grading), Reports (at-risk, toppers, trend by date range, faculty ratings, e-mail warnings),
Import Students (CSV), Promote Semester / Graduate, User Accounts, Activity Log (audit trail + e-mail outbox).

## Faculty portal (/teacher)
Dashboard (today's classes, students below 75%, notices), My Classes + rosters, mark attendance, enter marks,
timetable, anonymous student feedback. Faculty can only touch their own classes.

## Student portal (/student)
Dashboard (attendance, GPA-style stats, rank, exam countdown, today's classes, notices, fee alert), My Courses, Timetable,
Attendance (+ planner), Results (+GPA, print/PDF), Notices, Leave requests, Fees + receipts, Course feedback, Ask Admin, Profile.

## Other
* Dark mode toggle (top bar). Remembered per browser.
* E-mail: set SMTP_* in `.env` to really send; otherwise messages are saved in the outbox (Activity Log page).
* Deploy: `Procfile` (gunicorn) + environment variables from `.env.example` work on Render/Railway/Heroku.
* Not included: CSRF tokens and login rate-limiting (add Flask-WTF / Flask-Limiter before a public launch).
* Files: `app.py` (admin lists), `crud.py`, `admin_tools.py`, `admin_more.py`, `teacher.py`, `student.py`, `auth.py`,
  `util.py`, `bootstrap.py`, `schema_upgrade.sql`, `more_data.sql`, `templates/`, `static/css/style.css`.

## Presentation demo data (optional)

To populate the Admin, Dr. Anita Sharma's Faculty portal, and the student account
`KRM24BBA001` with additional presentation records, open `demo_data.sql` in
pgAdmin's Query Tool while connected to the `unitrack` database and execute it.
The script is designed to be re-runnable and does not reset passwords, drop
objects, or delete existing records. It adds sample announcements, timetable
slots, a paid and pending fee, a pending leave request, an open support ticket,
and faculty feedback. Review the inserted sample records before presenting.
