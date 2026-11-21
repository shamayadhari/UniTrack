"""
UniTrack - admin tools shared with the faculty portal.
    /attendance/bulk   mark attendance for a whole class in one go (upsert)
    /marks/bulk        enter / correct marks for a whole class (upsert)
    /reports           at-risk students, toppers, course performance, trend, feedback
    /reports/warn      e-mail every student below the attendance minimum
The two *_view functions take faculty_id so teachers can reuse them for THEIR classes only.
"""
from datetime import date
from flask import Blueprint, render_template, request, redirect, flash, abort
from db import get_db_connection
from crud import friendly_error
from util import run, send_mail

tools = Blueprint("tools", __name__)
MIN_ATTENDANCE = 75


def valid_day(text, fallback=None):
    try:
        return date.fromisoformat(text or "")
    except ValueError:
        return fallback


# ------------------------------------------------------------------ attendance
def attendance_view(faculty_id=None, layout="base.html", back="/attendance", **ctx):
    if request.method == "POST":
        offering_id = request.form.get("offering_id", type=int)
        day = valid_day(request.form.get("date"), date.today()).isoformat()
        if faculty_id and not run("SELECT 1 FROM course_offering WHERE offering_id = %s AND faculty_id = %s",
                                  (offering_id, faculty_id), one=True):
            abort(403)
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
        return redirect(f"{request.path}?offering_id={offering_id}&date={day}")

    offerings = run(f"""SELECT o.offering_id,
                               c.course_code || ' - ' || c.course_name || ' (Sec ' || o.section ||
                               ', Sem ' || sem.semester_number || ')' AS label
                        FROM course_offering o
                        JOIN course c ON c.course_id = o.course_id
                        JOIN semester sem ON sem.semester_id = o.semester_id
                        {"WHERE o.faculty_id = %s" if faculty_id else ""}
                        ORDER BY c.course_code, o.section""", (faculty_id,) if faculty_id else ())
    offering_id = request.args.get("offering_id", type=int)
    if offering_id and offering_id not in [o["offering_id"] for o in offerings]:
        abort(403 if faculty_id else 404)
    day = valid_day(request.args.get("date"), date.today()).isoformat()
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
    return render_template("bulk_attendance.html", layout=layout, back=back, offerings=offerings,
                           offering_id=offering_id, day=day, students=students, **ctx)


@tools.route("/attendance/bulk", methods=["GET", "POST"])
def bulk_attendance():
    return attendance_view(slug="attendance")


# ----------------------------------------------------------------------- marks
def marks_view(faculty_id=None, layout="base.html", back="/results", **ctx):
    exams = run(f"""SELECT ex.exam_id, ex.offering_id, ex.maximum_marks,
                           c.course_code || ' ' || o.section || ' - ' || ex.exam_name ||
                           ' (max ' || ex.maximum_marks::int || ')' AS label
                    FROM examination ex
                    JOIN course_offering o ON o.offering_id = ex.offering_id
                    JOIN course c ON c.course_id = o.course_id
                    {"WHERE o.faculty_id = %s" if faculty_id else ""}
                    ORDER BY c.course_code, o.section, ex.exam_date""", (faculty_id,) if faculty_id else ())
    by_id = {e["exam_id"]: e for e in exams}

    if request.method == "POST":
        exam_id = request.form.get("exam_id", type=int)
        exam = by_id.get(exam_id)
        if exam is None:
            abort(403)
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed!"
        try:
            cur, saved = conn.cursor(), 0
            for key, value in request.form.items():
                if key.startswith("marks_") and value.strip() != "":
                    cur.execute("""INSERT INTO results (exam_id, enrollment_id, marks_obtained)
                                   SELECT %s, en.enrollment_id, %s FROM enrollment en
                                   WHERE en.enrollment_id = %s AND en.offering_id = %s
                                   ON CONFLICT (exam_id, enrollment_id)
                                   DO UPDATE SET marks_obtained = EXCLUDED.marks_obtained""",
                                (exam_id, float(value), int(key[6:]), exam["offering_id"]))
                    saved += cur.rowcount
            conn.commit()
            flash(f"Marks saved for {saved} students (grades were filled in automatically).", "success")
        except Exception as error:               # e.g. marks above the maximum -> trigger message
            conn.rollback()
            flash(friendly_error(error), "error")
        finally:
            conn.close()
        return redirect(f"{request.path}?exam_id={exam_id}")

    exam_id = request.args.get("exam_id", type=int)
    exam, students = by_id.get(exam_id), []
    if exam_id and exam is None:
        abort(403 if faculty_id else 404)
    if exam:
        students = run("""SELECT en.enrollment_id, s.enrollment_number,
                                 s.first_name || ' ' || COALESCE(s.last_name, '') AS name,
                                 r.marks_obtained, r.grade
                          FROM enrollment en
                          JOIN student s ON s.student_id = en.student_id
                          LEFT JOIN results r ON r.enrollment_id = en.enrollment_id AND r.exam_id = %s
                          WHERE en.offering_id = %s AND en.enrollment_status <> 'Dropped'
                          ORDER BY s.enrollment_number""", (exam_id, exam["offering_id"]))
    return render_template("marks_entry.html", layout=layout, back=back, exams=exams,
                           exam=exam, students=students, **ctx)


@tools.route("/marks/bulk", methods=["GET", "POST"])
def bulk_marks():
    return marks_view(slug="marks")


# --------------------------------------------------------------------- reports
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

    # attendance trend for a chosen date range (defaults to everything recorded)
    bounds = run("SELECT MIN(attendance_date) AS lo, MAX(attendance_date) AS hi FROM attendance", one=True)
    lo = valid_day(request.args.get("from"), bounds["lo"])
    hi = valid_day(request.args.get("to"), bounds["hi"])
    trend = run("""SELECT attendance_date,
                          ROUND(100.0 * COUNT(*) FILTER (WHERE attendance_status IN ('Present','Late')) / COUNT(*), 1) AS pct
                   FROM attendance WHERE attendance_date BETWEEN %s AND %s
                   GROUP BY attendance_date ORDER BY attendance_date""", (lo, hi)) if lo and hi else []

    ratings = run("""SELECT f.faculty_name, c.course_code, o.section,
                            ROUND(AVG(fb.rating), 1) AS avg_rating, COUNT(*) AS votes
                     FROM feedback fb
                     JOIN enrollment en ON en.enrollment_id = fb.enrollment_id
                     JOIN course_offering o ON o.offering_id = en.offering_id
                     JOIN course c ON c.course_id = o.course_id
                     JOIN faculty f ON f.faculty_id = o.faculty_id
                     GROUP BY f.faculty_name, c.course_code, o.section
                     ORDER BY avg_rating DESC""")
    return render_template(
        "reports.html", slug="reports", at_risk=at_risk, toppers=toppers, courses=courses,
        avg_att=round(sum(rates) / len(rates), 1) if rates else None,
        pass_rate=round(100 * passes / (passes + fails), 1) if passes + fails else None,
        min_att=MIN_ATTENDANCE, ratings=ratings,
        trend_labels=[t["attendance_date"].strftime("%d %b") for t in trend],
        trend_values=[t["pct"] for t in trend],
        lo=lo.isoformat() if lo else "", hi=hi.isoformat() if hi else "")


@tools.route("/reports/warn", methods=["POST"])
def warn_students():
    rows = run("""SELECT v.student_name, s.email, v.attendance_pct
                  FROM student_academic_view v JOIN student s ON s.student_id = v.student_id
                  WHERE v.status = 'Active' AND v.attendance_pct < %s AND s.email IS NOT NULL""",
               (MIN_ATTENDANCE,))
    sent = sum(send_mail(
        r["email"], "UniTrack: low attendance warning",
        f"Hi {r['student_name']},\n\nYour overall attendance is {r['attendance_pct']}%, below the required "
        f"{MIN_ATTENDANCE}%. Please attend your upcoming classes or contact your department.\n\n- UniTrack")
        for r in rows)
    flash(f"{len(rows)} warning e-mails prepared: {sent} sent, {len(rows) - sent} saved in the outbox "
          f"(set SMTP_* in .env to really send them).", "success")
    return redirect("/reports")
