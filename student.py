"""
UniTrack - Student portal.

Routes (all read-only, every query is limited to the logged-in student):
    /student/login        sign in with enrollment number + registered email
    /student/             dashboard (attendance, scores, rank, upcoming exams)
    /student/courses      my enrolled courses
    /student/attendance   per-course attendance + recent log
    /student/results      exam results grouped by course
    /student/profile      personal details

NOTE: the database has no password column, so sign-in checks the enrollment
number AND the email stored for that student. Fine for a college project demo;
add a hashed password column before any real deployment.
"""
from decimal import Decimal
from functools import wraps
from flask import Blueprint, render_template, request, redirect, session, flash
from psycopg2.extras import RealDictCursor
from db import get_db_connection

student = Blueprint("student", __name__, url_prefix="/student")
MIN_ATTENDANCE = 75


def run(sql, params=(), one=False):
    """Run a SELECT with parameters; returns list of dicts (or one dict / None)."""
    conn = get_db_connection()
    if conn is None:
        raise ConnectionError("Database connection failed!")
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        rows = [{k: float(v) if isinstance(v, Decimal) else v for k, v in r.items()}
                for r in cur.fetchall()]
        cur.close()
    finally:
        conn.close()
    return (rows[0] if rows else None) if one else rows


@student.errorhandler(ConnectionError)
def db_down(error):
    return str(error), 500


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "student_id" not in session:
            return redirect("/student/login")
        me = run("""SELECT s.*, d.department_name, sem.semester_number, sem.academic_year
                    FROM student s
                    JOIN department d ON d.department_id = s.department_id
                    JOIN semester sem ON sem.semester_id = s.semester_id
                    WHERE s.student_id = %s""", (session["student_id"],), one=True)
        if me is None:                      # student deleted by admin meanwhile
            session.clear()
            return redirect("/student/login")
        return view(me, *args, **kwargs)
    return wrapper


def att_level(pct):
    return "ok" if pct >= MIN_ATTENDANCE else "warn" if pct >= 60 else "bad"


def planner(attended, total):
    """How many classes to attend (or can be skipped) to stay at the minimum."""
    if not total:
        return "-"
    if attended * 100 >= MIN_ATTENDANCE * total:
        skip = int(attended * 100 / MIN_ATTENDANCE - total)
        return f"Can skip {skip} class{'es' if skip != 1 else ''}" if skip else "Don't miss the next class"
    need = -(-(MIN_ATTENDANCE * total - 100 * attended) // (100 - MIN_ATTENDANCE))
    return f"Attend next {need} class{'es' if need != 1 else ''}"


def grade_point(pct):
    """Same cut-offs as the grading trigger: A+ >=90 ... D >=40, else F."""
    for cut, pts in ((90, 10), (80, 9), (70, 8), (60, 7), (50, 6), (40, 5)):
        if pct >= cut:
            return pts
    return 0


# ------------------------------------------------------------ login / logout
@student.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        enr = request.form.get("enrollment_number", "").strip()
        email = request.form.get("email", "").strip()
        row = run("""SELECT student_id FROM student
                     WHERE LOWER(enrollment_number) = LOWER(%s) AND LOWER(email) = LOWER(%s)""",
                  (enr, email), one=True)
        if row:
            session["student_id"] = row["student_id"]
            return redirect("/student/")
        flash("Enrollment number and email don't match any student.", "error")
    return render_template("student/login.html")


@student.route("/logout")
def logout():
    session.pop("student_id", None)
    flash("You have been signed out.", "success")
    return redirect("/student/login")


# ---------------------------------------------------------------- dashboard
@student.route("/")
@login_required
def dashboard(me):
    sid = me["student_id"]
    summary = run("SELECT * FROM student_academic_view WHERE student_id = %s", (sid,), one=True) or {}

    rank = run("""SELECT rnk, total FROM (
                    SELECT student_id,
                           RANK() OVER (PARTITION BY department_id, semester_number
                                        ORDER BY avg_percentage DESC) AS rnk,
                           COUNT(*) OVER (PARTITION BY department_id, semester_number) AS total
                    FROM student_academic_view WHERE avg_percentage IS NOT NULL) t
                  WHERE student_id = %s""", (sid,), one=True)

    att = run("""SELECT c.course_code,
                        COUNT(a.attendance_id) AS total,
                        COUNT(a.attendance_id) FILTER (WHERE a.attendance_status IN ('Present','Late')) AS attended
                 FROM enrollment en
                 JOIN course_offering o ON o.offering_id = en.offering_id
                 JOIN course c ON c.course_id = o.course_id
                 LEFT JOIN attendance a ON a.enrollment_id = en.enrollment_id
                 WHERE en.student_id = %s AND en.enrollment_status <> 'Dropped'
                 GROUP BY en.enrollment_id, c.course_code ORDER BY c.course_code""", (sid,))
    att_chart = [(r["course_code"], round(100 * r["attended"] / r["total"], 1) if r["total"] else 0) for r in att]

    perf = run("""SELECT c.course_code, ROUND(AVG(r.marks_obtained * 100 / ex.maximum_marks), 1) AS pct
                  FROM results r
                  JOIN enrollment en ON en.enrollment_id = r.enrollment_id
                  JOIN examination ex ON ex.exam_id = r.exam_id
                  JOIN course_offering o ON o.offering_id = ex.offering_id
                  JOIN course c ON c.course_id = o.course_id
                  WHERE en.student_id = %s GROUP BY c.course_code ORDER BY c.course_code""", (sid,))

    recent = run("""SELECT c.course_name, ex.exam_name, r.marks_obtained, ex.maximum_marks, r.grade, r.result_status
                    FROM results r
                    JOIN enrollment en ON en.enrollment_id = r.enrollment_id
                    JOIN examination ex ON ex.exam_id = r.exam_id
                    JOIN course_offering o ON o.offering_id = ex.offering_id
                    JOIN course c ON c.course_id = o.course_id
                    WHERE en.student_id = %s
                    ORDER BY ex.exam_date DESC NULLS LAST, r.result_id DESC LIMIT 5""", (sid,))

    upcoming = run("""SELECT c.course_name, ex.exam_name, ex.exam_date, ex.maximum_marks
                      FROM enrollment en
                      JOIN examination ex ON ex.offering_id = en.offering_id
                      JOIN course_offering o ON o.offering_id = en.offering_id
                      JOIN course c ON c.course_id = o.course_id
                      WHERE en.student_id = %s AND en.enrollment_status = 'Enrolled'
                        AND ex.exam_date >= CURRENT_DATE
                      ORDER BY ex.exam_date LIMIT 5""", (sid,))

    pct = summary.get("attendance_pct")
    return render_template(
        "student/dashboard.html", me=me, active="dashboard", s=summary, rank=rank,
        att_level=att_level(pct) if pct is not None else "", low_attendance=pct is not None and pct < MIN_ATTENDANCE,
        att_labels=[a[0] for a in att_chart], att_values=[a[1] for a in att_chart],
        perf_labels=[p["course_code"] for p in perf], perf_values=[p["pct"] for p in perf],
        recent=recent, upcoming=upcoming, min_att=MIN_ATTENDANCE)


# ------------------------------------------------------------------ courses
@student.route("/courses")
@login_required
def courses(me):
    rows = run("""SELECT c.course_code, c.course_name, c.credits, o.section, f.faculty_name,
                         sem.semester_number, en.enrollment_status
                  FROM enrollment en
                  JOIN course_offering o ON o.offering_id = en.offering_id
                  JOIN course c ON c.course_id = o.course_id
                  JOIN faculty f ON f.faculty_id = o.faculty_id
                  JOIN semester sem ON sem.semester_id = o.semester_id
                  WHERE en.student_id = %s
                  ORDER BY sem.semester_number DESC, c.course_code""", (me["student_id"],))
    return render_template("student/courses.html", me=me, active="courses", courses=rows,
                           credits=sum(r["credits"] for r in rows if r["enrollment_status"] != "Dropped"))


# --------------------------------------------------------------- attendance
@student.route("/attendance")
@login_required
def attendance(me):
    sid = me["student_id"]
    rows = run("""SELECT c.course_code, c.course_name,
                         COUNT(a.attendance_id) AS total,
                         COUNT(a.attendance_id) FILTER (WHERE a.attendance_status = 'Present') AS present,
                         COUNT(a.attendance_id) FILTER (WHERE a.attendance_status = 'Late')    AS late,
                         COUNT(a.attendance_id) FILTER (WHERE a.attendance_status = 'Absent')  AS absent
                  FROM enrollment en
                  JOIN course_offering o ON o.offering_id = en.offering_id
                  JOIN course c ON c.course_id = o.course_id
                  LEFT JOIN attendance a ON a.enrollment_id = en.enrollment_id
                  WHERE en.student_id = %s AND en.enrollment_status <> 'Dropped'
                  GROUP BY en.enrollment_id, c.course_code, c.course_name
                  ORDER BY c.course_code""", (sid,))
    for r in rows:
        r["pct"] = round(100 * (r["present"] + r["late"]) / r["total"], 1) if r["total"] else 0
        r["level"] = att_level(r["pct"])
        r["note"] = planner(r["present"] + r["late"], r["total"])
    log = run("""SELECT a.attendance_date, c.course_name, a.attendance_status
                 FROM attendance a
                 JOIN enrollment en ON en.enrollment_id = a.enrollment_id
                 JOIN course_offering o ON o.offering_id = en.offering_id
                 JOIN course c ON c.course_id = o.course_id
                 WHERE en.student_id = %s
                 ORDER BY a.attendance_date DESC LIMIT 15""", (sid,))
    low = [r for r in rows if r["total"] and r["pct"] < MIN_ATTENDANCE]
    return render_template("student/attendance.html", me=me, active="attendance",
                           rows=rows, log=log, low=low, min_att=MIN_ATTENDANCE)


# ------------------------------------------------------------------ results
@student.route("/results")
@login_required
def results(me):
    rows = run("""SELECT c.course_code, c.course_name, c.credits, ex.exam_name, ex.exam_date,
                         r.marks_obtained, ex.maximum_marks, r.grade, r.result_status,
                         ROUND(r.marks_obtained * 100 / ex.maximum_marks, 1) AS pct
                  FROM results r
                  JOIN enrollment en ON en.enrollment_id = r.enrollment_id
                  JOIN examination ex ON ex.exam_id = r.exam_id
                  JOIN course_offering o ON o.offering_id = ex.offering_id
                  JOIN course c ON c.course_id = o.course_id
                  WHERE en.student_id = %s
                  ORDER BY c.course_code, ex.exam_date NULLS LAST""", (me["student_id"],))
    grouped = {}
    for r in rows:
        grouped.setdefault((r["course_code"], r["course_name"]), []).append(r)
    summary = {k: dict(avg=round(sum(e["pct"] for e in v) / len(v), 1), credits=v[0]["credits"]) for k, v in grouped.items()}
    for s in summary.values():
        s["gp"] = grade_point(s["avg"])
    credit_sum = sum(s["credits"] for s in summary.values())
    gpa = round(sum(s["gp"] * s["credits"] for s in summary.values()) / credit_sum, 2) if credit_sum else None
    passed = sum(1 for r in rows if r["result_status"] == "Pass")
    return render_template("student/results.html", me=me, active="results", grouped=grouped,
                           summary=summary, gpa=gpa, total=len(rows), passed=passed, failed=len(rows) - passed,
                           avg=round(sum(r["pct"] for r in rows) / len(rows), 1) if rows else None)


# ------------------------------------------------------------------ profile
@student.route("/profile")
@login_required
def profile(me):
    return render_template("student/profile.html", me=me, active="profile")
