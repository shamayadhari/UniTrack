"""
UniTrack - Faculty portal (/teacher/...). Faculty only ever see and change THEIR OWN classes:
    dashboard, my classes + rosters, mark attendance, enter marks, timetable, student feedback.
"""
from datetime import date
from functools import wraps
from flask import Blueprint, session, redirect, flash
from util import run, page, section, row, act, grid, fmt_date, fmt_time
from admin_tools import attendance_view, marks_view, MIN_ATTENDANCE

teacher = Blueprint("teacher", __name__, url_prefix="/teacher")


@teacher.errorhandler(ConnectionError)
def db_down(error):
    return str(error), 500


def faculty_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        me = run("""SELECT f.*, d.department_name FROM faculty f
                    JOIN department d ON d.department_id = f.department_id
                    WHERE f.faculty_id = %s""", (session.get("faculty_id"),), one=True)
        if me is None:
            session.clear()
            return redirect("/login")
        return view(me, *args, **kwargs)
    return wrapper


def tpage(me, active, heading, sections, sub="", **ctx):
    return page("teacher/base.html", heading, sections, sub, me=me, active=active, **ctx)


def pct(v):
    return f"{v}%" if v is not None else "-"


@teacher.route("/")
@faculty_required
def dashboard(me):
    fid = me["faculty_id"]
    n_classes = run("SELECT COUNT(*) AS n FROM course_offering WHERE faculty_id = %s", (fid,), one=True)["n"]
    n_students = run("""SELECT COUNT(DISTINCT en.student_id) AS n FROM enrollment en
                        JOIN course_offering o ON o.offering_id = en.offering_id
                        WHERE o.faculty_id = %s AND en.enrollment_status <> 'Dropped'""", (fid,), one=True)["n"]
    rating = run("""SELECT ROUND(AVG(fb.rating), 1) AS avg, COUNT(*) AS n FROM feedback fb
                    JOIN enrollment en ON en.enrollment_id = fb.enrollment_id
                    JOIN course_offering o ON o.offering_id = en.offering_id
                    WHERE o.faculty_id = %s""", (fid,), one=True)
    today = run("""SELECT t.start_time, t.end_time, c.course_code, c.course_name, o.section, t.room
                   FROM timetable t JOIN course_offering o ON o.offering_id = t.offering_id
                   JOIN course c ON c.course_id = o.course_id
                   WHERE o.faculty_id = %s AND t.day_of_week = %s ORDER BY t.start_time""",
                (fid, date.today().isoweekday()))
    low = run("""SELECT * FROM (
                   SELECT s.enrollment_number, s.first_name || ' ' || COALESCE(s.last_name, '') AS name, c.course_code,
                          ROUND(100.0 * COUNT(a.attendance_id) FILTER (WHERE a.attendance_status IN ('Present','Late'))
                                / NULLIF(COUNT(a.attendance_id), 0), 1) AS pct
                   FROM enrollment en
                   JOIN student s ON s.student_id = en.student_id
                   JOIN course_offering o ON o.offering_id = en.offering_id
                   JOIN course c ON c.course_id = o.course_id
                   LEFT JOIN attendance a ON a.enrollment_id = en.enrollment_id
                   WHERE o.faculty_id = %s AND en.enrollment_status = 'Enrolled'
                   GROUP BY en.enrollment_id, s.enrollment_number, s.first_name, s.last_name, c.course_code) t
                 WHERE pct < %s ORDER BY pct LIMIT 10""", (fid, MIN_ATTENDANCE))
    notices = run("""SELECT title, body, created_at FROM announcement
                     WHERE audience IN ('All', 'Faculty') AND (department_id IS NULL OR department_id = %s)
                     ORDER BY created_at DESC LIMIT 4""", (me["department_id"],))
    return tpage(me, "dashboard", "Dashboard", [
        section("Today's classes", date.today().strftime("%A, %d %b"), columns=["Time", "Course", "Section", "Room"],
                rows=[row([f"{fmt_time(t['start_time'])}–{fmt_time(t['end_time'])}", f"{t['course_code']} · {t['course_name']}",
                           t["section"], t["room"]]) for t in today], empty="No classes scheduled today."),
        section("Students needing attention", f"Below {MIN_ATTENDANCE}% attendance in your classes",
                columns=["Enrollment No.", "Student", "Course", "Attendance"],
                rows=[row([l["enrollment_number"], l["name"], l["course_code"], pct(l["pct"])]) for l in low],
                empty="🎉 Everyone in your classes is above the minimum."),
        section("Notices", notes=[dict(title=n["title"], meta=fmt_date(n["created_at"]), text=n["body"]) for n in notices],
                empty="No notices."),
    ], stats=[
        dict(label="My classes", value=n_classes, sub="Course sections", icon="book"),
        dict(label="My students", value=n_students, sub="Across all classes", icon="cap"),
        dict(label="Classes today", value=len(today), sub=date.today().strftime("%A"), icon="clock"),
        dict(label="Student rating", value=(f"{rating['avg']}/5" if rating["avg"] else "–"),
             sub=f"{rating['n']} responses", icon="star", cls="ok" if rating["avg"] and rating["avg"] >= 4 else ""),
    ], welcome=dict(title=f"Hello, {me['faculty_name']} 👋", text="Here's your teaching overview.",
                    chips=[me["department_name"], me["designation"]]))


@teacher.route("/classes")
@faculty_required
def classes(me):
    rows = run("""SELECT o.offering_id, c.course_code, c.course_name, o.section, sem.semester_number,
                         (SELECT COUNT(*) FROM enrollment e WHERE e.offering_id = o.offering_id
                             AND e.enrollment_status <> 'Dropped') AS students,
                         (SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE a.attendance_status IN ('Present','Late'))
                                       / NULLIF(COUNT(*), 0), 1)
                            FROM attendance a JOIN enrollment e ON e.enrollment_id = a.enrollment_id
                           WHERE e.offering_id = o.offering_id) AS att,
                         (SELECT ROUND(AVG(r.marks_obtained * 100 / ex.maximum_marks), 1)
                            FROM results r JOIN examination ex ON ex.exam_id = r.exam_id
                           WHERE ex.offering_id = o.offering_id) AS score
                  FROM course_offering o
                  JOIN course c ON c.course_id = o.course_id
                  JOIN semester sem ON sem.semester_id = o.semester_id
                  WHERE o.faculty_id = %s ORDER BY c.course_code, o.section""", (me["faculty_id"],))
    return tpage(me, "classes", "My Classes", [section(
        columns=["Course", "Section", "Semester", "Students", "Avg attendance", "Avg score"],
        rows=[row([f"{r['course_code']} · {r['course_name']}", r["section"], r["semester_number"], r["students"],
                   pct(r["att"]), pct(r["score"])],
                  act("Roster", f"/teacher/class/{r['offering_id']}", get=True),
                  act("Attendance", f"/teacher/attendance?offering_id={r['offering_id']}", get=True))
              for r in rows], empty="You aren't assigned to any course yet.")], "Every section you teach")


@teacher.route("/class/<int:offering_id>")
@faculty_required
def roster(me, offering_id):
    info = run("""SELECT c.course_code, c.course_name, o.section FROM course_offering o
                  JOIN course c ON c.course_id = o.course_id
                  WHERE o.offering_id = %s AND o.faculty_id = %s""", (offering_id, me["faculty_id"]), one=True)
    if info is None:
        flash("That class isn't yours.", "error")
        return redirect("/teacher/classes")
    rows = run("""SELECT s.enrollment_number, s.first_name || ' ' || COALESCE(s.last_name, '') AS name, en.enrollment_status,
                         (SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE a.attendance_status IN ('Present','Late'))
                                       / NULLIF(COUNT(*), 0), 1) FROM attendance a WHERE a.enrollment_id = en.enrollment_id) AS att,
                         (SELECT ROUND(AVG(r.marks_obtained * 100 / ex.maximum_marks), 1)
                            FROM results r JOIN examination ex ON ex.exam_id = r.exam_id
                           WHERE r.enrollment_id = en.enrollment_id) AS score
                  FROM enrollment en JOIN student s ON s.student_id = en.student_id
                  WHERE en.offering_id = %s ORDER BY s.enrollment_number""", (offering_id,))
    return tpage(me, "classes", f"{info['course_code']} · Section {info['section']}", [section(
        info["course_name"], columns=["Enrollment No.", "Student", "Attendance", "Avg score", "Status"],
        rows=[row([r["enrollment_number"], r["name"], pct(r["att"]), pct(r["score"]), r["enrollment_status"]]) for r in rows],
        empty="No students enrolled.")], "Class roster")


@teacher.route("/attendance", methods=["GET", "POST"])
@faculty_required
def attendance(me):
    return attendance_view(faculty_id=me["faculty_id"], layout="teacher/base.html",
                           back="/teacher/classes", me=me, active="attendance")


@teacher.route("/marks", methods=["GET", "POST"])
@faculty_required
def marks(me):
    return marks_view(faculty_id=me["faculty_id"], layout="teacher/base.html",
                      back="/teacher/classes", me=me, active="marks")


@teacher.route("/timetable")
@faculty_required
def timetable(me):
    rows = run("""SELECT t.day_of_week, t.start_time, t.end_time,
                         c.course_code || ' · ' || c.course_name AS title, 'Sec ' || o.section || ' · Room ' || t.room AS sub
                  FROM timetable t JOIN course_offering o ON o.offering_id = t.offering_id
                  JOIN course c ON c.course_id = o.course_id
                  WHERE o.faculty_id = %s ORDER BY t.day_of_week, t.start_time""", (me["faculty_id"],))
    return tpage(me, "timetable", "My Timetable", [section(grid=grid(rows))], "Your weekly schedule")


@teacher.route("/feedback")
@faculty_required
def feedback(me):
    base = """FROM feedback fb
              JOIN enrollment en ON en.enrollment_id = fb.enrollment_id
              JOIN course_offering o ON o.offering_id = en.offering_id
              JOIN course c ON c.course_id = o.course_id
              WHERE o.faculty_id = %s"""
    avg = run(f"""SELECT c.course_code, o.section, ROUND(AVG(fb.rating), 1) AS avg, COUNT(*) AS n {base}
                  GROUP BY c.course_code, o.section ORDER BY c.course_code""", (me["faculty_id"],))
    comments = run(f"""SELECT c.course_code, fb.rating, fb.comment, fb.created_at {base}
                       AND fb.comment IS NOT NULL AND fb.comment <> '' ORDER BY fb.created_at DESC LIMIT 30""", (me["faculty_id"],))
    return tpage(me, "feedback", "Student Feedback", [
        section("Ratings by class", columns=["Course", "Section", "Average rating", "Responses"],
                rows=[row([r["course_code"], r["section"], f"{r['avg']} / 5", r["n"]]) for r in avg], empty="No feedback yet."),
        section("Comments", "Anonymous - students' names are never shown.",
                notes=[dict(title=f"{c['course_code']} · {'⭐' * c['rating']}", meta=fmt_date(c["created_at"]), text=c["comment"])
                       for c in comments], empty="No comments yet."),
    ], "What students say about your classes")
