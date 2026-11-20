# UniTrack - Smart University Management and Academic Analytics System

## Run
1. Create database `unitrack`, run `database.sql`, then `additional.sql` (rankings) and optionally `crud.sql`.
2. `pip install flask psycopg2-binary`
3. Set your password (either edit `config.py` or set env vars DB_PASSWORD, DB_USER, DB_HOST, DB_PORT, DB_NAME).
4. `python app.py` -> http://127.0.0.1:5000

## CRUD (new)
| Entity | Add | Edit | Delete |
|---|---|---|---|
| Students, Faculty, Courses, Attendance, Results | /<entity>/add | /<entity>/<id>/edit | Delete button in list |
| Enrollments | /enrollments/add (uses `sp_enroll_student`) | status only | Delete button |

* `crud.py` - one config dictionary + 3 generic routes (create / update / delete). Reading = the list pages in `app.py`.
* All values are sent as query parameters (no SQL injection). Database errors (UNIQUE, CHECK, FOREIGN KEY, the
  result-validation trigger, the enrolment procedure) are shown as friendly messages.
* `crud.sql` - the same INSERT / SELECT / UPDATE / DELETE statements per table, for the viva.
* Fixed: dashboard cards were blank because template keys did not match `app.py`.

## Student portal (new)
Open http://127.0.0.1:5000/student/login and sign in with a student's **enrollment number + registered email** (both from the `student` table).
Pages: Dashboard, My Courses, Attendance, Results, Profile. Everything is read-only and limited to the logged-in student. See `student.py`.
The admin sidebar has an "Open Student Portal" link, and the student sidebar links back to the admin dashboard.
UI: all pages share `templates/base.html` + one stylesheet (`static/css/style.css`), same purple palette.

## New features
**Admin:** `/attendance/bulk` (mark a whole class, re-saving a date updates it), `/reports` (at-risk students, toppers, course pass rates),
CSV download on every list page (`?export=csv`), Email column on Students.
**Student:** attendance planner (classes to attend / can skip to stay at 75%), credit-weighted GPA on 10-point scale
(from each course's average %, same cut-offs as the grading trigger), Print / Save-as-PDF on Results.
