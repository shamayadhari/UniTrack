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
