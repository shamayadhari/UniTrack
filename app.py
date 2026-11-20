

import os
from flask import Flask, render_template
from db import get_db_connection
from crud import crud
from student import student

app = Flask(__name__)
# needed for flash() messages; set SECRET_KEY in the environment for real use
app.secret_key = os.environ.get("SECRET_KEY", "unitrack-dev-key")
app.register_blueprint(crud)      # Create / Update / Delete routes (see crud.py)
app.register_blueprint(student)   # Student portal under /student (see student.py)



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



#STUDENT PAGE
@app.route("/students")
def students():
    query = """
        SELECT
            s.student_id,
            s.enrollment_number,
            s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
            d.department_name,
            sem.semester_number,
            s.status
        FROM student s
        JOIN department d
            ON s.department_id = d.department_id
        JOIN semester sem
            ON s.semester_id = sem.semester_id
        ORDER BY s.student_id;
    """

    columns = [
        "Student ID",
        "Enrollment No.",
        "Name",
        "Department",
        "Semester",
        "Status"
    ]

    return show_table("Students", query, columns, "students")


# FACULTY PAGE
@app.route("/faculty")
def faculty():
    return show_table(
        "Faculty",
        """
        SELECT f.faculty_id, f.faculty_name, f.email,
               f.designation, d.department_name
        FROM faculty f
        JOIN department d ON f.department_id = d.department_id
        ORDER BY f.faculty_id
        """,
        ["ID", "Faculty Name", "Email", "Designation", "Department"],
        "faculty"
    )


# COURSES PAGE
@app.route("/courses")
def courses():
    return show_table(
        "Courses",
        """
        SELECT c.course_id, c.course_code, c.course_name,
               c.credits, d.department_name
        FROM course c
        JOIN department d ON c.department_id = d.department_id
        ORDER BY c.course_id
        """,
        ["ID", "Course Code", "Course Name", "Credits", "Department"],
        "courses"
    )


# ENROLLMENTS PAGE
@app.route("/enrollments")
def enrollments():
    return show_table(
        "Enrollments",
        """
        SELECT en.enrollment_id,
               s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
               c.course_code, c.course_name, o.section,
               en.enrollment_date, en.enrollment_status
        FROM enrollment en
        JOIN student s ON en.student_id = s.student_id
        JOIN course_offering o ON en.offering_id = o.offering_id
        JOIN course c ON o.course_id = c.course_id
        ORDER BY en.enrollment_id
        """,
        ["ID", "Student", "Course Code", "Course", "Section", "Enrolled On", "Status"],
        "enrollments"
    )


# ATTENDANCE PAGE
@app.route("/attendance")
def attendance():
    return show_table(
        "Attendance",
        """
        SELECT a.attendance_id, s.first_name || ' ' ||
               COALESCE(s.last_name, '') AS student_name,
               c.course_name, a.attendance_date,
               a.attendance_status
        FROM attendance a
        JOIN enrollment en ON a.enrollment_id = en.enrollment_id
        JOIN student s ON en.student_id = s.student_id
        JOIN course_offering o ON en.offering_id = o.offering_id
        JOIN course c ON o.course_id = c.course_id
        ORDER BY a.attendance_date DESC, a.attendance_id
        """,
        ["ID", "Student", "Course", "Date", "Status"],
        "attendance"
    )


# RESULTS PAGE
@app.route("/results")
def results():
    return show_table(
        "Results",
        """
        SELECT r.result_id,
               s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
               c.course_name, ex.exam_name,
               r.marks_obtained, ex.maximum_marks,
               r.grade, r.result_status
        FROM results r
        JOIN enrollment en ON r.enrollment_id = en.enrollment_id
        JOIN student s ON en.student_id = s.student_id
        JOIN examination ex ON r.exam_id = ex.exam_id
        JOIN course_offering o ON ex.offering_id = o.offering_id
        JOIN course c ON o.course_id = c.course_id
        ORDER BY r.result_id
        """,
        ["ID", "Student", "Course", "Exam", "Marks", "Maximum", "Grade", "Status"],
        "results"
    )


# COMMON FUNCTION FOR ALL FOUR PAGES
def show_table(title, query, columns, slug=None):
    connection = get_db_connection()

    if connection is None:
        return "Database connection failed!"

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        records = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template(
            "data_table.html",
            title=title,
            slug=slug,
            columns=columns,
            records=records
        )

    except Exception as error:
        connection.close()
        return f"Error loading {title}: {error}"


if __name__ == "__main__":
    app.run(debug=True)
