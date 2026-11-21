

import os
import csv, io
try:                                   # read settings from a .env file when python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from flask import Flask, render_template, request, Response
from db import get_db_connection
from crud import crud
from student import student
from admin_tools import tools
from admin_more import more
from teacher import teacher
from auth import auth, init_auth
import bootstrap

app = Flask(__name__)
# needed for flash() messages; set SECRET_KEY in the environment for real use
app.secret_key = os.environ.get("SECRET_KEY", "unitrack-dev-key")
app.register_blueprint(crud)      # Create / Update / Delete routes (see crud.py)
app.register_blueprint(tools)     # Bulk attendance + reports (see admin_tools.py)
app.register_blueprint(more)      # Announcements, timetable, exams, fees ... (see admin_more.py)
app.register_blueprint(student)   # Student portal under /student (see student.py)
app.register_blueprint(teacher)   # Faculty portal under /teacher (see teacher.py)
app.register_blueprint(auth)      # Login, logout, change password (see auth.py)
init_auth(app)                    # login guard + audit trail


@app.errorhandler(ConnectionError)
def database_down(error):
    return str(error), 500


try:                              # create the v4 tables + login accounts (safe to repeat)
    bootstrap.apply_schema()
    bootstrap.ensure_users()
except Exception as error:
    print("Setup step skipped:", error)



@app.route("/")
def dashboard():
    connection = get_db_connection()

    if connection is None:
        return "Database connection failed!"

    try:
        cursor = connection.cursor()

        # 1. Dashboard statistics
        cursor.execute("SELECT COUNT(*) FROM student;")
        total_students = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM faculty;")
        total_faculty = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM course;")
        total_courses = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM enrollment
            WHERE enrollment_status <> 'Dropped';
        """)
        active_enrollments = cursor.fetchone()[0]

        # 2. Students by Department
        cursor.execute("""
            SELECT d.department_name, COUNT(s.student_id)
            FROM department d
            LEFT JOIN student s
                ON d.department_id = s.department_id
            GROUP BY d.department_name
            ORDER BY d.department_name;
        """)
        department_data = cursor.fetchall()

        # 3. Attendance Overview
        cursor.execute("""
            SELECT attendance_status, COUNT(*)
            FROM attendance
            GROUP BY attendance_status
            ORDER BY attendance_status;
        """)
        attendance_data = cursor.fetchall()

        # 4. Average Course Performance (percentage)
        cursor.execute("""
            SELECT
                c.course_name,
                ROUND(
                    AVG(
                        (r.marks_obtained::numeric /
                        NULLIF(ex.maximum_marks, 0)) * 100
                    ), 2
                )
            FROM results r
            JOIN examination ex
                ON r.exam_id = ex.exam_id
            JOIN course_offering co
                ON ex.offering_id = co.offering_id
            JOIN course c
                ON co.course_id = c.course_id
            GROUP BY c.course_name
            ORDER BY c.course_name;
        """)
        performance_data = cursor.fetchall()

        cursor.close()
        connection.close()
        stats = {
          "total_students": total_students,
          "total_faculty": total_faculty,
          "total_courses": total_courses,
          "active_enrollments": active_enrollments
        }
        return render_template(
            "dashboard.html",
            stats=stats,

            # Statistics
            total_students=total_students,
            total_faculty=total_faculty,
            total_courses=total_courses,
            active_enrollments=active_enrollments,

            # Chart data
            department_labels=[row[0] for row in department_data],
            department_values=[row[1] for row in department_data],

            attendance_labels=[row[0] for row in attendance_data],
            attendance_values=[row[1] for row in attendance_data],

            performance_labels=[row[0] for row in performance_data],
            performance_values=[
                float(row[1]) if row[1] is not None else 0
                for row in performance_data
            ]
        )

    except Exception as error:
        connection.close()
        return f"Dashboard Error: {error}"



# ----------------------------------------------------------------------
# LIST PAGES  (Students, Faculty, Courses, Enrollments, Attendance, Results)
# Every page can be narrowed with ?dept=<department_id> and/or ?course=<course_id>.
# The "/*WHERE*/" marker in each query is replaced by those conditions; the ids
# always travel as query parameters (%s), never inside the SQL text.
# ----------------------------------------------------------------------
def filtered(query, dept_sql, course_sql):
    conditions, params = [], []
    dept = request.args.get("dept", type=int)
    course = request.args.get("course", type=int)
    if dept:
        conditions.append(f"{dept_sql} = %s")
        params.append(dept)
    if course:
        conditions.append(course_sql)
        params.append(course)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return query.replace("/*WHERE*/", where), params


# STUDENT PAGE
@app.route("/students")
def students():
    query, params = filtered("""
        SELECT s.student_id, s.enrollment_number,
               s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
               s.email, d.department_name, sem.semester_number,
               (SELECT string_agg(c2.course_code, ', ' ORDER BY c2.course_code)
                  FROM enrollment e2
                  JOIN course_offering o2 ON o2.offering_id = e2.offering_id
                  JOIN course c2 ON c2.course_id = o2.course_id
                 WHERE e2.student_id = s.student_id
                   AND e2.enrollment_status <> 'Dropped') AS courses,
               s.status
        FROM student s
        JOIN department d ON s.department_id = d.department_id
        JOIN semester sem ON s.semester_id = sem.semester_id
        /*WHERE*/
        ORDER BY s.student_id
    """, "s.department_id",
        """EXISTS (SELECT 1 FROM enrollment ef
                   JOIN course_offering ofr ON ofr.offering_id = ef.offering_id
                  WHERE ef.student_id = s.student_id AND ofr.course_id = %s
                    AND ef.enrollment_status <> 'Dropped')""")
    columns = ["Student ID", "Enrollment No.", "Name", "Email", "Department",
               "Semester", "Courses", "Status"]
    return show_table("Students", query, columns, "students", params)


# FACULTY PAGE
@app.route("/faculty")
def faculty():
    query, params = filtered("""
        SELECT f.faculty_id, f.faculty_name, f.email, f.designation, d.department_name,
               (SELECT string_agg(DISTINCT c2.course_code, ', ' ORDER BY c2.course_code)
                  FROM course_offering o2
                  JOIN course c2 ON c2.course_id = o2.course_id
                 WHERE o2.faculty_id = f.faculty_id) AS courses
        FROM faculty f
        JOIN department d ON f.department_id = d.department_id
        /*WHERE*/
        ORDER BY f.faculty_id
    """, "f.department_id",
        """EXISTS (SELECT 1 FROM course_offering ofr
                  WHERE ofr.faculty_id = f.faculty_id AND ofr.course_id = %s)""")
    return show_table("Faculty", query,
                      ["ID", "Faculty Name", "Email", "Designation", "Department", "Teaches"],
                      "faculty", params)


# COURSES PAGE
@app.route("/courses")
def courses():
    query, params = filtered("""
        SELECT c.course_id, c.course_code, c.course_name, c.credits, d.department_name,
               (SELECT COUNT(*) FROM enrollment e
                  JOIN course_offering o ON o.offering_id = e.offering_id
                 WHERE o.course_id = c.course_id
                   AND e.enrollment_status <> 'Dropped') AS students,
               (SELECT COUNT(DISTINCT o.faculty_id) FROM course_offering o
                 WHERE o.course_id = c.course_id) AS faculty
        FROM course c
        JOIN department d ON c.department_id = d.department_id
        /*WHERE*/
        ORDER BY c.course_id
    """, "c.department_id", "c.course_id = %s")
    return show_table("Courses", query,
                      ["ID", "Course Code", "Course Name", "Credits", "Department",
                       "Students", "Faculty"], "courses", params)


# ENROLLMENTS PAGE
@app.route("/enrollments")
def enrollments():
    query, params = filtered("""
        SELECT en.enrollment_id,
               s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
               c.course_code, c.course_name, o.section,
               en.enrollment_date, en.enrollment_status
        FROM enrollment en
        JOIN student s ON en.student_id = s.student_id
        JOIN course_offering o ON en.offering_id = o.offering_id
        JOIN course c ON o.course_id = c.course_id
        /*WHERE*/
        ORDER BY en.enrollment_id
    """, "c.department_id", "o.course_id = %s")
    return show_table("Enrollments", query,
                      ["ID", "Student", "Course Code", "Course", "Section",
                       "Enrolled On", "Status"], "enrollments", params)


# ATTENDANCE PAGE
@app.route("/attendance")
def attendance():
    query, params = filtered("""
        SELECT a.attendance_id,
               s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
               c.course_name, a.attendance_date, a.attendance_status
        FROM attendance a
        JOIN enrollment en ON a.enrollment_id = en.enrollment_id
        JOIN student s ON en.student_id = s.student_id
        JOIN course_offering o ON en.offering_id = o.offering_id
        JOIN course c ON o.course_id = c.course_id
        /*WHERE*/
        ORDER BY a.attendance_date DESC, a.attendance_id
    """, "c.department_id", "o.course_id = %s")
    return show_table("Attendance", query,
                      ["ID", "Student", "Course", "Date", "Status"], "attendance", params)


# RESULTS PAGE
@app.route("/results")
def results():
    query, params = filtered("""
        SELECT r.result_id,
               s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
               c.course_name, ex.exam_name,
               r.marks_obtained, ex.maximum_marks, r.grade, r.result_status
        FROM results r
        JOIN enrollment en ON r.enrollment_id = en.enrollment_id
        JOIN student s ON en.student_id = s.student_id
        JOIN examination ex ON r.exam_id = ex.exam_id
        JOIN course_offering o ON ex.offering_id = o.offering_id
        JOIN course c ON o.course_id = c.course_id
        /*WHERE*/
        ORDER BY r.result_id
    """, "c.department_id", "o.course_id = %s")
    return show_table("Results", query,
                      ["ID", "Student", "Course", "Exam", "Marks", "Maximum", "Grade", "Status"],
                      "results", params)


PER_PAGE = 25


# COMMON FUNCTION FOR ALL LIST PAGES
def show_table(title, query, columns, slug=None, params=()):
    connection = get_db_connection()

    if connection is None:
        return "Database connection failed!"

    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        records = cursor.fetchall()

        q = (request.args.get("q") or "").strip().lower()      # server-side search over every column
        if q:
            records = [r for r in records if q in " ".join(str(v) for v in r if v is not None).lower()]

        # data for the Department / Course filter bar
        cursor.execute("SELECT department_id, department_name FROM department ORDER BY department_name")
        departments = cursor.fetchall()
        cursor.execute("""SELECT course_id, course_code, course_name, department_id
                          FROM course ORDER BY course_code""")
        course_list = cursor.fetchall()

        cursor.close()
        connection.close()

        sel_dept = request.args.get("dept", type=int)
        sel_course = request.args.get("course", type=int)
        scope = [c[2] for c in course_list if c[0] == sel_course] or \
                [d[1] for d in departments if d[0] == sel_dept]

        if request.args.get("export") == "csv":     # ?export=csv -> download the (filtered) table
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(columns)
            writer.writerows(records)
            return Response(buf.getvalue(), mimetype="text/csv", headers={
                "Content-Disposition": f"attachment; filename={slug or title.lower()}.csv"})

        total = len(records)                                  # pagination (CSV above keeps every row)
        pages = max(-(-total // PER_PAGE), 1)
        page = min(max(request.args.get("page", 1, type=int), 1), pages)
        shown = records[(page - 1) * PER_PAGE: page * PER_PAGE]

        return render_template(
            "data_table.html",
            title=title,
            slug=slug,
            columns=columns,
            records=shown, total=total, page=page, pages=pages, per_page=PER_PAGE, q=q,
            departments=departments,
            course_list=course_list,
            sel_dept=sel_dept,
            sel_course=sel_course,
            scope=scope[0] if scope else None
        )

    except Exception as error:
        connection.close()
        return f"Error loading {title}: {error}"


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
