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
from datetime import date
from decimal import Decimal
from functools import wraps
from flask import Blueprint, render_template, request, redirect, session, flash
from psycopg2.extras import RealDictCursor
from db import get_db_connection

student = Blueprint("student", __name__, url_prefix="/student")
MIN_ATTENDANCE = 75


from util import run, page, section, row, act, field, form, grid, write, fmt_date, fmt_time  # shared helpers


@student.errorhandler(ConnectionError)
def db_down(error):
    return str(error), 500


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "student_id" not in session:
            return redirect("/login")
        me = run("""SELECT s.*, d.department_name, sem.semester_number, sem.academic_year
                    FROM student s
                    JOIN department d ON d.department_id = s.department_id
                    JOIN semester sem ON sem.semester_id = s.semester_id
                    WHERE s.student_id = %s""", (session["student_id"],), one=True)
        if me is None:                      # student deleted by admin meanwhile
            session.clear()
            return redirect("/login")
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
@student.route("/login")
def login():
    return redirect("/login")


@student.route("/logout")
def logout():
    return redirect("/logout")


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

    notices = run("""SELECT title, body, created_at FROM announcement
                     WHERE audience IN ('All', 'Students') AND (department_id IS NULL OR department_id = %s)
                     ORDER BY created_at DESC LIMIT 4""", (me["department_id"],))
    today_classes = run("""SELECT t.start_time, t.end_time, c.course_name, t.room, f.faculty_name
                           FROM enrollment en
                           JOIN timetable t ON t.offering_id = en.offering_id
                           JOIN course_offering o ON o.offering_id = en.offering_id
                           JOIN course c ON c.course_id = o.course_id
                           JOIN faculty f ON f.faculty_id = o.faculty_id
                           WHERE en.student_id = %s AND en.enrollment_status = 'Enrolled' AND t.day_of_week = %s
                           ORDER BY t.start_time""", (sid, date.today().isoweekday()))
    fees_due = run("SELECT COALESCE(SUM(amount), 0) AS due, COUNT(*) AS n FROM fee WHERE student_id = %s AND status = 'Pending'",
                   (sid,), one=True)

    pct = summary.get("attendance_pct")
    return render_template(
        "student/dashboard.html", me=me, active="dashboard", s=summary, rank=rank,
        att_level=att_level(pct) if pct is not None else "", low_attendance=pct is not None and pct < MIN_ATTENDANCE,
        att_labels=[a[0] for a in att_chart], att_values=[a[1] for a in att_chart],
        perf_labels=[p["course_code"] for p in perf], perf_values=[p["pct"] for p in perf],
        recent=recent, upcoming=upcoming, min_att=MIN_ATTENDANCE,
        notices=notices, today_classes=today_classes, fees_due=fees_due, today=date.today())


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


# =================================================== v4: timetable, notices, leave, fees ...
def spage(me, active, heading, sections, sub="", **ctx):
    return page("student/base.html", heading, sections, sub, me=me, active=active, **ctx)


@student.route("/timetable")
@login_required
def timetable(me):
    rows = run("""SELECT t.day_of_week, t.start_time, t.end_time, c.course_code || ' · ' || c.course_name AS title,
                         f.faculty_name || ' · Room ' || t.room AS sub
                  FROM enrollment en
                  JOIN course_offering o ON o.offering_id = en.offering_id
                  JOIN timetable t ON t.offering_id = o.offering_id
                  JOIN course c ON c.course_id = o.course_id
                  JOIN faculty f ON f.faculty_id = o.faculty_id
                  WHERE en.student_id = %s AND en.enrollment_status = 'Enrolled'
                  ORDER BY t.day_of_week, t.start_time""", (me["student_id"],))
    return spage(me, "timetable", "Timetable", [section(grid=grid(rows))], "Your weekly class schedule")


@student.route("/notices")
@login_required
def notices(me):
    rows = run("""SELECT title, body, audience, created_at FROM announcement
                  WHERE audience IN ('All', 'Students') AND (department_id IS NULL OR department_id = %s)
                  ORDER BY created_at DESC LIMIT 50""", (me["department_id"],))
    return spage(me, "notices", "Notices", [section(
        notes=[dict(title=n["title"], meta=fmt_date(n["created_at"]), text=n["body"]) for n in rows],
        empty="No notices right now.")], "Announcements from the university")


@student.route("/leave")
@login_required
def leave(me):
    rows = run("SELECT * FROM leave_request WHERE student_id = %s ORDER BY created_at DESC", (me["student_id"],))
    return spage(me, "leave", "Leave", [
        section("Apply for leave", form=form([
            field("from_date", "From", "date", value=date.today().isoformat()),
            field("to_date", "To", "date", value=date.today().isoformat()),
            field("reason", "Reason", "textarea")], "/student/leave/apply", "Submit request")),
        section("My requests", columns=["From", "To", "Reason", "Status", "Admin note"],
                rows=[row([fmt_date(r["from_date"]), fmt_date(r["to_date"]), r["reason"], r["status"], r["admin_note"]]) for r in rows],
                empty="You haven't applied for leave."),
    ], "Request time off; the admin will approve or reject")


@student.route("/leave/apply", methods=["POST"])
@login_required
def leave_apply(me):
    f = request.form
    write("INSERT INTO leave_request (student_id, from_date, to_date, reason) VALUES (%s, %s, %s, %s)",
          (me["student_id"], f.get("from_date"), f.get("to_date"), f.get("reason", "").strip()), "Leave request submitted.")
    return redirect("/student/leave")


@student.route("/fees")
@login_required
def fees(me):
    rows = run("SELECT * FROM fee WHERE student_id = %s ORDER BY due_date DESC, fee_id DESC", (me["student_id"],))
    due = sum(r["amount"] for r in rows if r["status"] == "Pending")
    paid = sum(r["amount"] for r in rows if r["status"] == "Paid")
    return spage(me, "fees", "Fees", [section(
        columns=["Fee", "Amount", "Due date", "Status", "Paid on", "Receipt no."],
        rows=[row([r["title"], f"₹{r['amount']:,.0f}", fmt_date(r["due_date"]), r["status"], fmt_date(r["paid_on"]), r["receipt_no"]],
                  *([act("Receipt", f"/student/fees/{r['fee_id']}/receipt", get=True)] if r["status"] == "Paid" else []))
              for r in rows], empty="No fees have been raised for you.")],
        "Your fee status and receipts",
        stats=[dict(label="Pending", value=f"₹{due:,.0f}", sub="Pay at the accounts office", icon="wallet", cls="warn" if due else "ok"),
               dict(label="Paid so far", value=f"₹{paid:,.0f}", sub="Receipts available below", icon="check")])


@student.route("/fees/<int:fee_id>/receipt")
@login_required
def receipt(me, fee_id):
    fee = run("SELECT * FROM fee WHERE fee_id = %s AND student_id = %s AND status = 'Paid'",
              (fee_id, me["student_id"]), one=True)
    if fee is None:
        return redirect("/student/fees")
    return render_template("student/receipt.html", me=me, fee=fee)


@student.route("/feedback")
@login_required
def feedback(me):
    open_courses = run("""SELECT en.enrollment_id, c.course_code || ' · ' || c.course_name || ' (' || f.faculty_name || ')' AS label
                          FROM enrollment en
                          JOIN course_offering o ON o.offering_id = en.offering_id
                          JOIN course c ON c.course_id = o.course_id
                          JOIN faculty f ON f.faculty_id = o.faculty_id
                          WHERE en.student_id = %s AND en.enrollment_status <> 'Dropped'
                            AND NOT EXISTS (SELECT 1 FROM feedback fb WHERE fb.enrollment_id = en.enrollment_id)""",
                       (me["student_id"],))
    given = run("""SELECT c.course_code, c.course_name, fb.rating, fb.comment, fb.created_at
                   FROM feedback fb JOIN enrollment en ON en.enrollment_id = fb.enrollment_id
                   JOIN course_offering o ON o.offering_id = en.offering_id
                   JOIN course c ON c.course_id = o.course_id
                   WHERE en.student_id = %s ORDER BY fb.created_at DESC""", (me["student_id"],))
    sections = []
    if open_courses:
        sections.append(section("Rate a course", "Your name is never shown to faculty.", form=form([
            field("enrollment_id", "Course", "select", options=[(o["enrollment_id"], o["label"]) for o in open_courses]),
            field("rating", "Rating", "select", options=[(5, "5 - Excellent"), (4, "4 - Good"), (3, "3 - Okay"), (2, "2 - Poor"), (1, "1 - Very poor")]),
            field("comment", "Comment (optional)", "textarea", False)], "/student/feedback/add", "Submit feedback")))
    sections.append(section("My feedback", columns=["Course", "Rating", "Comment", "Date"],
                            rows=[row([f"{g['course_code']} · {g['course_name']}", "⭐" * g["rating"], g["comment"], fmt_date(g["created_at"])]) for g in given],
                            empty="No feedback given yet."))
    return spage(me, "feedback", "Course Feedback", sections, "Help improve teaching quality")


@student.route("/feedback/add", methods=["POST"])
@login_required
def feedback_add(me):
    f = request.form
    write("""INSERT INTO feedback (enrollment_id, rating, comment)
             SELECT en.enrollment_id, %s, %s FROM enrollment en
             WHERE en.enrollment_id = %s AND en.student_id = %s AND en.enrollment_status <> 'Dropped'""",
          (f.get("rating"), f.get("comment", "").strip() or None, f.get("enrollment_id"), me["student_id"]), "Thanks for your feedback!")
    return redirect("/student/feedback")


@student.route("/support")
@login_required
def support(me):
    rows = run("SELECT * FROM support_ticket WHERE student_id = %s ORDER BY created_at DESC", (me["student_id"],))
    return spage(me, "support", "Ask Admin", [
        section("Send a query or complaint", form=form([
            field("subject", "Subject"), field("message", "Message", "textarea")], "/student/support/add", "Send")),
        section("My queries", columns=["Date", "Subject", "Message", "Status", "Reply"],
                rows=[row([fmt_date(r["created_at"]), r["subject"], r["message"], r["status"], r["reply"]]) for r in rows],
                empty="No queries yet."),
    ], "Questions, complaints and requests")


@student.route("/support/add", methods=["POST"])
@login_required
def support_add(me):
    f = request.form
    write("INSERT INTO support_ticket (student_id, subject, message) VALUES (%s, %s, %s)",
          (me["student_id"], f.get("subject", "").strip(), f.get("message", "").strip()), "Sent! The admin will reply here.")
    return redirect("/student/support")
