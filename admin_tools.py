"""
UniTrack - extra admin tools.
    /attendance/bulk   mark attendance for a whole class in one go (upsert)
    /reports           at-risk students, toppers and course performance
"""
from datetime import date
from flask import Blueprint, render_template, request, redirect, flash
from db import get_db_connection
from crud import friendly_error
from student import run          # small helper: SELECT -> list of dicts

tools = Blueprint("tools", __name__)
MIN_ATTENDANCE = 75


@tools.route("/attendance/bulk", methods=["GET", "POST"])
def bulk_attendance():
    if request.method == "POST":
        offering_id = request.form.get("offering_id", type=int)
        day = request.form.get("date", "")
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed!"
        try:
            cur, saved = conn.cursor(), 0
            for key, status in request.form.items():
                if key.startswith("status_") and status in ("Present", "Absent", "Late"):
                    # the enrollment must belong to the chosen offering; re-saving a date updates it
                    cur.execute("""INSERT INTO attendance (enrollment_id, attendance_date, attendance_status)
                                   SELECT en.enrollment_id, %s, %s FROM enrollment en
                                   WHERE en.enrollment_id = %s AND en.offering_id = %s
                                   ON CONFLICT (enrollment_id, attendance_date)
                                   DO UPDATE SET attendance_status = EXCLUDED.attendance_status""",
                                (day, status, int(key[7:]), offering_id))
                    saved += cur.rowcount
            conn.commit()
            flash(f"Attendance saved for {saved} students.", "success")
        except Exception as error:
            conn.rollback()
            flash(friendly_error(error), "error")
        finally:
            conn.close()
        return redirect(f"/attendance/bulk?offering_id={offering_id}&date={day}")

    offerings = run("""SELECT o.offering_id,
                              c.course_code || ' - ' || c.course_name || ' (Sec ' || o.section ||
                              ', Sem ' || sem.semester_number || ')' AS label
                       FROM course_offering o
                       JOIN course c ON c.course_id = o.course_id
                       JOIN semester sem ON sem.semester_id = o.semester_id
                       ORDER BY c.course_code, o.section""")
    offering_id = request.args.get("offering_id", type=int)
    try:
        day = date.fromisoformat(request.args.get("date", "")).isoformat()
    except ValueError:
        day = date.today().isoformat()
    students = []
    if offering_id:
        students = run("""SELECT en.enrollment_id, s.enrollment_number,
                                 s.first_name || ' ' || COALESCE(s.last_name, '') AS name,
                                 a.attendance_status AS current
                          FROM enrollment en
                          JOIN student s ON s.student_id = en.student_id
                          LEFT JOIN attendance a ON a.enrollment_id = en.enrollment_id
                                                AND a.attendance_date = %s
                          WHERE en.offering_id = %s AND en.enrollment_status = 'Enrolled'
                          ORDER BY s.enrollment_number""", (day, offering_id))
    return render_template("bulk_attendance.html", slug="attendance", offerings=offerings,
                           offering_id=offering_id, day=day, students=students)


@tools.route("/reports")
def reports():
    people = run("SELECT * FROM student_academic_view WHERE status = 'Active'")
    at_risk = []
    for p in people:
        why = []
        if p["attendance_pct"] is not None and p["attendance_pct"] < MIN_ATTENDANCE:
            why.append(f"Attendance {p['attendance_pct']}%")
        if p["failed_exams"]:
            why.append(f"{p['failed_exams']} failed exam{'s' if p['failed_exams'] > 1 else ''}")
        if why:
            p["reasons"] = why
            at_risk.append(p)
    at_risk.sort(key=lambda p: (p["attendance_pct"] is None, p["attendance_pct"] or 0))

    toppers = sorted((p for p in people if p["avg_percentage"] is not None),
                     key=lambda p: -p["avg_percentage"])[:5]
    courses = run("SELECT * FROM course_performance_view ORDER BY course_code, section")
    for c in courses:
        graded = c["passes"] + c["fails"]
        c["pass_rate"] = round(100 * c["passes"] / graded, 1) if graded else None
    rates = [p["attendance_pct"] for p in people if p["attendance_pct"] is not None]
    passes, fails = sum(c["passes"] for c in courses), sum(c["fails"] for c in courses)
    return render_template(
        "reports.html", slug="reports", at_risk=at_risk, toppers=toppers, courses=courses,
        avg_att=round(sum(rates) / len(rates), 1) if rates else None,
        pass_rate=round(100 * passes / (passes + fails), 1) if passes + fails else None,
        min_att=MIN_ATTENDANCE)
