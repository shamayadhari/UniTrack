"""
UniTrack - more admin pages. Every page is built from the generic templates/panel.html.
    /announcements  /timetable  /exams  /leaves  /fees  /tickets
    /import/students  /promote  /users  /activity
"""
import csv
import io
import re
from datetime import date
from flask import Blueprint, request, redirect, flash, session, Response
from werkzeug.security import generate_password_hash
from crud import friendly_error
from db import get_db_connection
from util import (run, write, admin_page, section, form, field, row, act, DAYS,
                  fmt_date, fmt_time)
import bootstrap

more = Blueprint("more", __name__)


def dept_options():
    return [(d["department_id"], d["department_name"])
            for d in run("SELECT department_id, department_name FROM department ORDER BY department_name")]


def offering_options():
    return [(o["offering_id"], o["label"]) for o in run("""
        SELECT o.offering_id,
               c.course_code || ' ' || o.section || ' - ' || c.course_name ||
               ' (Sem ' || sem.semester_number || ', ' || f.faculty_name || ')' AS label
        FROM course_offering o
        JOIN course c ON c.course_id = o.course_id
        JOIN semester sem ON sem.semester_id = o.semester_id
        JOIN faculty f ON f.faculty_id = o.faculty_id
        ORDER BY c.course_code, o.section""")]


def money(x):
    return f"₹{x:,.0f}"


# ------------------------------------------------------------- announcements
@more.route("/announcements")
def announcements():
    rows = run("""SELECT a.announcement_id, a.title, a.body, a.audience,
                         COALESCE(d.department_name, 'All departments') AS dept, a.posted_by, a.created_at
                  FROM announcement a LEFT JOIN department d ON d.department_id = a.department_id
                  ORDER BY a.created_at DESC LIMIT 100""")
    return admin_page("Announcements", [
        section("Post a notice", "Students and faculty see it on their dashboards.", form=form([
            field("title", "Title"),
            field("audience", "Audience", "select", options=[("All", "Everyone"), ("Students", "Students only"), ("Faculty", "Faculty only")], value="All", blank="Everyone"),
            field("department", "Department", "select", required=False, options=dept_options(), blank="All departments"),
            field("body", "Message", "textarea"),
        ], "/announcements/add", "Post notice")),
        section("Posted notices", columns=["ID", "Title", "Audience", "Department", "Posted by", "Date", "Message"],
                rows=[row([r["announcement_id"], r["title"], r["audience"], r["dept"], r["posted_by"],
                           fmt_date(r["created_at"]), r["body"]],
                          act("Delete", f"/announcements/{r['announcement_id']}/delete", "btn-danger", "Delete this notice?"))
                      for r in rows], empty="No notices yet."),
    ], "Broadcast news to students and faculty", slug="announcements")


@more.route("/announcements/add", methods=["POST"])
def announcement_add():
    f = request.form
    write("""INSERT INTO announcement (title, body, audience, department_id, posted_by)
             VALUES (%s, %s, %s, %s, %s)""",
          (f.get("title", "").strip(), f.get("body", "").strip(), f.get("audience") or "All",
           f.get("department") or None, session.get("username")), "Notice posted.")
    return redirect("/announcements")


@more.route("/announcements/<int:aid>/delete", methods=["POST"])
def announcement_delete(aid):
    write("DELETE FROM announcement WHERE announcement_id = %s", (aid,), "Notice deleted.")
    return redirect("/announcements")


# ----------------------------------------------------------------- timetable
@more.route("/timetable")
def timetable_admin():
    fac, crs = request.args.get("faculty", type=int), request.args.get("course", type=int)
    where, params = [], []
    if fac:
        where.append("o.faculty_id = %s"); params.append(fac)
    if crs:
        where.append("o.course_id = %s"); params.append(crs)
    rows = run(f"""SELECT t.slot_id, t.day_of_week, t.start_time, t.end_time, c.course_code, c.course_name,
                          o.section, f.faculty_name, t.room
                   FROM timetable t
                   JOIN course_offering o ON o.offering_id = t.offering_id
                   JOIN course c ON c.course_id = o.course_id
                   JOIN faculty f ON f.faculty_id = o.faculty_id
                   {"WHERE " + " AND ".join(where) if where else ""}
                   ORDER BY t.day_of_week, t.start_time""", params)
    faculty = [(r["faculty_id"], r["faculty_name"]) for r in run("SELECT faculty_id, faculty_name FROM faculty ORDER BY faculty_name")]
    courses = [(r["course_id"], f"{r['course_code']} · {r['course_name']}") for r in run("SELECT course_id, course_code, course_name FROM course ORDER BY course_code")]
    return admin_page("Timetable", [
        section("Add a class slot", "Clashes (same teacher or same room at overlapping times) are blocked.", form=form([
            field("offering_id", "Course offering", "select", options=offering_options()),
            field("day", "Day", "select", options=list(DAYS.items())),
            field("start", "Start time", "time"), field("end", "End time", "time"),
            field("room", "Room", placeholder="e.g. A-101"),
        ], "/timetable/add", "Add slot")),
        section("Weekly slots", form=form([
            field("faculty", "Faculty", "select", False, faculty, fac or "", "All faculty"),
            field("course", "Course", "select", False, courses, crs or "", "All courses"),
        ], "/timetable", "Filter", "get"),
            columns=["ID", "Day", "Time", "Course", "Section", "Faculty", "Room"],
            rows=[row([r["slot_id"], DAYS[r["day_of_week"]], f"{fmt_time(r['start_time'])}–{fmt_time(r['end_time'])}",
                       f"{r['course_code']} · {r['course_name']}", r["section"], r["faculty_name"], r["room"]],
                      act("Delete", f"/timetable/{r['slot_id']}/delete", "btn-danger", "Delete this slot?"))
                  for r in rows], empty="No slots yet."),
    ], "Weekly class schedule", slug="timetable")


@more.route("/timetable/add", methods=["POST"])
def timetable_add():
    f = request.form
    args = (f.get("offering_id"), f.get("day"), f.get("start"), f.get("end"), f.get("room", "").strip())
    clash = run("""SELECT 1 FROM timetable t JOIN course_offering o ON o.offering_id = t.offering_id
                   WHERE t.day_of_week = %s AND t.start_time < %s::time AND %s::time < t.end_time
                     AND (o.faculty_id = (SELECT faculty_id FROM course_offering WHERE offering_id = %s)
                          OR LOWER(t.room) = LOWER(%s)) LIMIT 1""",
                (args[1], args[3], args[2], args[0], args[4]), one=True)
    if clash:
        flash("Clash: that teacher or room is already booked at an overlapping time.", "error")
    else:
        write("""INSERT INTO timetable (offering_id, day_of_week, start_time, end_time, room)
                 VALUES (%s, %s, %s, %s, %s)""", args, "Slot added.")
    return redirect("/timetable")


@more.route("/timetable/<int:sid>/delete", methods=["POST"])
def timetable_delete(sid):
    write("DELETE FROM timetable WHERE slot_id = %s", (sid,), "Slot deleted.")
    return redirect("/timetable")


# --------------------------------------------------------------------- exams
@more.route("/exams")
def exams():
    crs = request.args.get("course", type=int)
    rows = run(f"""SELECT ex.exam_id, c.course_code, c.course_name, o.section, ex.exam_name, ex.exam_date,
                          ex.maximum_marks, (SELECT COUNT(*) FROM results r WHERE r.exam_id = ex.exam_id) AS graded
                   FROM examination ex
                   JOIN course_offering o ON o.offering_id = ex.offering_id
                   JOIN course c ON c.course_id = o.course_id
                   {"WHERE o.course_id = %s" if crs else ""}
                   ORDER BY ex.exam_date NULLS LAST, ex.exam_id""", (crs,) if crs else ())
    courses = [(r["course_id"], f"{r['course_code']} · {r['course_name']}") for r in run("SELECT course_id, course_code, course_name FROM course ORDER BY course_code")]
    return admin_page("Exam Schedule", [
        section("Schedule an exam", "Students see upcoming exams (with a countdown) on their dashboard.", form=form([
            field("offering_id", "Course offering", "select", options=offering_options()),
            field("exam_name", "Exam name", placeholder="e.g. End-Term Exam"),
            field("exam_date", "Date", "date"),
            field("maximum_marks", "Maximum marks", "number", min=1, value=50),
        ], "/exams/add", "Schedule exam")),
        section("All exams", form=form([field("course", "Course", "select", False, courses, crs or "", "All courses")],
                                       "/exams", "Filter", "get"),
                columns=["ID", "Course", "Section", "Exam", "Date", "Max marks", "Results entered"],
                rows=[row([r["exam_id"], f"{r['course_code']} · {r['course_name']}", r["section"], r["exam_name"],
                           fmt_date(r["exam_date"]), int(r["maximum_marks"]), r["graded"]],
                          act("Enter marks", f"/marks/bulk?exam_id={r['exam_id']}", get=True),
                          act("Delete", f"/exams/{r['exam_id']}/delete", "btn-danger",
                              "Delete this exam and its results?"))
                      for r in rows], empty="No exams scheduled."),
    ], "Plan exams and track marks entry", slug="exams")


@more.route("/exams/add", methods=["POST"])
def exam_add():
    f = request.form
    write("""INSERT INTO examination (offering_id, exam_name, exam_date, maximum_marks)
             VALUES (%s, %s, %s, %s)""",
          (f.get("offering_id"), f.get("exam_name", "").strip(), f.get("exam_date"), f.get("maximum_marks")),
          "Exam scheduled.")
    return redirect("/exams")


@more.route("/exams/<int:eid>/delete", methods=["POST"])
def exam_delete(eid):
    write("DELETE FROM examination WHERE exam_id = %s", (eid,), "Exam deleted.")
    return redirect("/exams")


# -------------------------------------------------------------------- leaves
@more.route("/leaves")
def leaves():
    rows = run("""SELECT l.leave_id, s.enrollment_number,
                         s.first_name || ' ' || COALESCE(s.last_name, '') AS name,
                         l.from_date, l.to_date, l.reason, l.status, l.admin_note
                  FROM leave_request l JOIN student s ON s.student_id = l.student_id
                  ORDER BY (l.status = 'Pending') DESC, l.created_at DESC LIMIT 200""")
    note = [{"name": "note", "placeholder": "Note (optional)"}]
    return admin_page("Leave Requests", [section(
        columns=["ID", "Enrollment No.", "Student", "From", "To", "Reason", "Status", "Admin note"],
        rows=[row([r["leave_id"], r["enrollment_number"], r["name"], fmt_date(r["from_date"]), fmt_date(r["to_date"]),
                   r["reason"], r["status"], r["admin_note"]],
                  *([act("Approve", f"/leaves/{r['leave_id']}/approved", "btn-light", fields=note),
                     act("Reject", f"/leaves/{r['leave_id']}/rejected", "btn-danger", fields=note)]
                    if r["status"] == "Pending" else []))
              for r in rows], empty="No leave requests.")],
        "Approve or reject student leave", slug="leaves")


@more.route("/leaves/<int:lid>/<decision>", methods=["POST"])
def leave_decide(lid, decision):
    if decision in ("approved", "rejected"):
        write("""UPDATE leave_request SET status = %s, admin_note = %s
                 WHERE leave_id = %s AND status = 'Pending'""",
              (decision.title(), request.form.get("note", "").strip() or None, lid), f"Leave {decision}.")
    return redirect("/leaves")


# --------------------------------------------------------------------- fees
@more.route("/fees")
def fees():
    status = request.args.get("status")
    rows = run(f"""SELECT f.fee_id, s.enrollment_number,
                          s.first_name || ' ' || COALESCE(s.last_name, '') AS name,
                          f.title, f.amount, f.due_date, f.status, f.paid_on, f.receipt_no
                   FROM fee f JOIN student s ON s.student_id = f.student_id
                   {"WHERE f.status = %s" if status in ("Pending", "Paid") else ""}
                   ORDER BY f.due_date DESC, f.fee_id DESC LIMIT 300""", (status,) if status in ("Pending", "Paid") else ())
    tot = run("""SELECT COALESCE(SUM(amount) FILTER (WHERE status = 'Paid'), 0) AS paid,
                        COALESCE(SUM(amount) FILTER (WHERE status = 'Pending'), 0) AS pending FROM fee""", one=True)
    return admin_page("Fees", [
        section("Create fee", "Leave 'Enrollment number' empty to bill every active student (optionally one department).", form=form([
            field("title", "Fee title", placeholder="e.g. Semester 3 tuition"),
            field("amount", "Amount (₹)", "number", step=0.01, min=1),
            field("due_date", "Due date", "date", value=date.today().isoformat()),
            field("department", "Department", "select", False, dept_options(), blank="All departments"),
            field("enrollment_number", "Enrollment number (one student)", required=False),
        ], "/fees/add", "Create fee")),
        section(f"Collected {money(tot['paid'])} · Pending {money(tot['pending'])}",
                form=form([field("status", "Status", "select", False, [("Pending", "Pending"), ("Paid", "Paid")], status or "", "All")],
                          "/fees", "Filter", "get"),
                columns=["ID", "Enrollment No.", "Student", "Fee", "Amount", "Due", "Status", "Paid on", "Receipt"],
                rows=[row([r["fee_id"], r["enrollment_number"], r["name"], r["title"], money(r["amount"]),
                           fmt_date(r["due_date"]), r["status"], fmt_date(r["paid_on"]), r["receipt_no"]],
                          *([act("Mark paid", f"/fees/{r['fee_id']}/pay", "btn-light", "Mark this fee as paid?")]
                            if r["status"] == "Pending" else []))
                      for r in rows], empty="No fees yet."),
    ], "Billing and collection", slug="fees")


@more.route("/fees/add", methods=["POST"])
def fee_add():
    f = request.form
    dept, enr = f.get("department") or None, (f.get("enrollment_number") or "").strip() or None
    count = write("""INSERT INTO fee (student_id, title, amount, due_date)
                     SELECT s.student_id, %s, %s, %s FROM student s
                     WHERE s.status = 'Active'
                       AND (%s::int IS NULL OR s.department_id = %s)
                       AND (%s::text IS NULL OR LOWER(s.enrollment_number) = LOWER(%s))""",
                  (f.get("title", "").strip(), f.get("amount"), f.get("due_date"), dept, dept, enr, enr), None)
    if count:
        flash(f"Fee created for {count} student{'s' if count != 1 else ''}.", "success")
    elif count == 0:
        flash("No matching active students - nothing was created.", "error")
    return redirect("/fees")


@more.route("/fees/<int:fid>/pay", methods=["POST"])
def fee_pay(fid):
    write("""UPDATE fee SET status = 'Paid', paid_on = CURRENT_DATE,
                    receipt_no = 'RCPT-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || LPAD(fee_id::text, 5, '0')
             WHERE fee_id = %s AND status = 'Pending'""", (fid,), "Marked as paid; receipt generated.")
    return redirect("/fees")


# ------------------------------------------------------------------- tickets
@more.route("/tickets")
def tickets():
    rows = run("""SELECT t.ticket_id, s.enrollment_number,
                         s.first_name || ' ' || COALESCE(s.last_name, '') AS name,
                         t.subject, t.message, t.status, t.reply, t.created_at
                  FROM support_ticket t JOIN student s ON s.student_id = t.student_id
                  ORDER BY (t.status = 'Open') DESC, t.created_at DESC LIMIT 200""")
    return admin_page("Student Queries", [section(
        columns=["ID", "Enrollment No.", "Student", "Subject", "Message", "Status", "Reply"],
        rows=[row([r["ticket_id"], r["enrollment_number"], r["name"], r["subject"], r["message"], r["status"], r["reply"]],
                  *([act("Reply", f"/tickets/{r['ticket_id']}/reply", "btn-light",
                         fields=[{"name": "reply", "placeholder": "Type your reply"}])]
                    if r["status"] == "Open" else []))
              for r in rows], empty="No queries from students.")],
        "Reply to questions and complaints", slug="tickets")


@more.route("/tickets/<int:tid>/reply", methods=["POST"])
def ticket_reply(tid):
    reply = request.form.get("reply", "").strip()
    if reply:
        write("""UPDATE support_ticket SET reply = %s, status = 'Resolved', replied_at = NOW()
                 WHERE ticket_id = %s""", (reply, tid), "Reply sent; ticket resolved.")
    else:
        flash("Type a reply first.", "error")
    return redirect("/tickets")


# -------------------------------------------------------------- import students
SAMPLE_CSV = ("enrollment_number,first_name,last_name,email,phone,gender,date_of_birth,department_code,semester\n"
              "KRM26CSE001,Arnav,Kulkarni,arnav.kulkarni@student.unitrack.edu,9876501001,Male,2007-01-15,CSE,3\n"
              "KRM26ECE001,Sana,Qureshi,sana.qureshi@student.unitrack.edu,9876501002,Female,2006-11-02,ECE,3\n")


@more.route("/import/students", methods=["GET", "POST"])
def import_students():
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename.lower().endswith(".csv"):
            flash("Please choose a .csv file.", "error")
            return redirect("/import/students")
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed!"
        added = skipped = 0
        problems = []
        try:
            cur = conn.cursor()
            text = io.StringIO(upload.stream.read().decode("utf-8-sig"))
            for n, r in enumerate(csv.DictReader(text), start=2):
                r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
                cur.execute("SAVEPOINT one_row")
                try:
                    cur.execute("""INSERT INTO student (enrollment_number, first_name, last_name, email, phone,
                                                        gender, date_of_birth, department_id, semester_id)
                                   SELECT %s, %s, %s, %s, %s, %s, %s, d.department_id, sem.semester_id
                                   FROM department d JOIN semester sem ON sem.semester_number = %s::int
                                   WHERE d.department_code = %s
                                   ORDER BY sem.academic_year DESC LIMIT 1
                                   ON CONFLICT (enrollment_number) DO NOTHING""",
                                (r.get("enrollment_number"), r.get("first_name"), r.get("last_name") or None,
                                 r.get("email") or None, r.get("phone") or None, r.get("gender") or None,
                                 r.get("date_of_birth") or None, r.get("semester"), r.get("department_code")))
                    added, skipped = added + cur.rowcount, skipped + (1 - cur.rowcount)
                except Exception as error:
                    cur.execute("ROLLBACK TO SAVEPOINT one_row")
                    skipped += 1
                    if len(problems) < 5:
                        problems.append(f"row {n}: {friendly_error(error)}")
            conn.commit()
        except Exception as error:
            conn.rollback()
            flash(f"Could not read the file: {friendly_error(error)}", "error")
            return redirect("/import/students")
        finally:
            conn.close()
        bootstrap.ensure_users()
        flash(f"Imported {added} students; skipped {skipped} (duplicates, unknown department/semester or invalid data).",
              "success" if added else "error")
        for p in problems:
            flash(p, "error")
        return redirect("/import/students")
    return admin_page("Import Students", [
        section("Upload a CSV", "Columns: enrollment_number, first_name, last_name, email, phone, gender, date_of_birth, "
                "department_code (CSE/ECE/ME/BBA), semester (number). Existing enrollment numbers are skipped. "
                "Each new student also gets a login (starting password = enrollment number).",
                form=form([field("file", "CSV file", "file", accept=".csv")], "/import/students", "Import", enctype="multipart/form-data"),
                html='<p style="margin-top:16px"><a class="btn btn-light btn-small" href="/import/students/sample.csv">⬇ Download sample CSV</a></p>')],
        "Add many students at once", slug="import")


@more.route("/import/students/sample.csv")
def import_sample():
    return Response(SAMPLE_CSV, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=students_sample.csv"})


# ------------------------------------------------------------------- promote
@more.route("/promote", methods=["GET", "POST"])
def promote():
    if request.method == "POST":
        f = request.form
        dept = f.get("department") or None
        from_id, action = f.get("from_semester", type=int), f.get("action")
        if action == "graduate":
            write("""UPDATE student SET status = 'Graduated'
                     WHERE semester_id = %s AND status = 'Active'
                       AND (%s::int IS NULL OR department_id = %s)""", (from_id, dept, dept),
                  "Students marked as Graduated.")
            return redirect("/promote")
        number, year = f.get("to_number", type=int), (f.get("to_year") or "").strip()
        if not number or not 1 <= number <= 8 or not re.fullmatch(r"\d{4}-\d{2}", year):
            flash("Enter a semester number (1-8) and an academic year like 2027-28.", "error")
            return redirect("/promote")
        y = int(year[:4])
        start, end = ((date(y, 7, 27), date(y, 12, 18)) if number % 2 else (date(y + 1, 1, 12), date(y + 1, 5, 20)))
        write("""INSERT INTO semester (semester_number, academic_year, start_date, end_date)
                 VALUES (%s, %s, %s, %s) ON CONFLICT (semester_number, academic_year) DO NOTHING""",
              (number, year, start, end), None)
        count = write("""UPDATE student SET semester_id = (SELECT semester_id FROM semester
                                                            WHERE semester_number = %s AND academic_year = %s)
                         WHERE semester_id = %s AND status = 'Active'
                           AND (%s::int IS NULL OR department_id = %s)""",
                      (number, year, from_id, dept, dept), None)
        if count is not None:
            flash(f"{count} students promoted to Semester {number} ({year}). "
                  f"Remember to create their new enrollments / offerings.", "success")
        return redirect("/promote")
    semesters = [(s["semester_id"], f"Semester {s['semester_number']} ({s['academic_year']}) - {s['n']} active students")
                 for s in run("""SELECT sem.semester_id, sem.semester_number, sem.academic_year,
                                        COUNT(s.student_id) FILTER (WHERE s.status = 'Active') AS n
                                 FROM semester sem LEFT JOIN student s ON s.semester_id = sem.semester_id
                                 GROUP BY sem.semester_id ORDER BY sem.academic_year, sem.semester_number""")]
    base = [field("from_semester", "From semester", "select", options=semesters),
            field("department", "Department", "select", False, dept_options(), blank="All departments")]
    return admin_page("Promote Semester", [
        section("Move students up", "All ACTIVE students of the chosen semester (and department) move to the new semester. "
                "The semester is created automatically if it doesn't exist.",
                form=form(base + [field("to_number", "To semester number", "number", min=1, value=4),
                                  field("to_year", "Academic year", placeholder="2027-28", value="2027-28"),
                                  field("action", "Action", "select", options=[("promote", "Promote")], value="promote", blank="Promote")],
                          "/promote", "Promote students")),
        section("Graduate students", "Final-year students: mark everyone in a semester as Graduated.",
                form=form(base + [field("action", "Action", "select", options=[("graduate", "Mark as Graduated")], value="graduate", blank="Mark as Graduated")],
                          "/promote", "Graduate students")),
    ], "End-of-term operations", slug="promote")


# --------------------------------------------------------------------- users
@more.route("/users")
def users():
    rows = run("""SELECT u.user_id, u.username, u.role,
                         COALESCE(s.first_name || ' ' || COALESCE(s.last_name, ''), f.faculty_name, 'Administrator') AS name,
                         u.must_change, u.last_login
                  FROM app_user u
                  LEFT JOIN student s ON s.student_id = u.student_id
                  LEFT JOIN faculty f ON f.faculty_id = u.faculty_id
                  ORDER BY u.role, u.username""")
    return admin_page("User Accounts", [section(
        "Accounts are created automatically for every student and faculty member",
        "Reset puts the account back on its starting password (students: enrollment number, faculty: Faculty@123) and forces a change at next login.",
        columns=["Username", "Role", "Name", "Must change password", "Last login"],
        rows=[row([r["username"], r["role"].title(), r["name"], "Yes" if r["must_change"] else "No",
                   r["last_login"].strftime("%d %b %Y %H:%M") if r["last_login"] else "never"],
                  act("Reset password", f"/users/{r['user_id']}/reset", "btn-light", "Reset this password?"))
              for r in rows])], "Logins and password resets", slug="users")


@more.route("/users/<int:uid>/reset", methods=["POST"])
def user_reset(uid):
    u = run("SELECT username, role FROM app_user WHERE user_id = %s", (uid,), one=True)
    if u:
        write("UPDATE app_user SET password_hash = %s, must_change = TRUE WHERE user_id = %s",
              (generate_password_hash(bootstrap.default_password(u["role"], u["username"]), method=bootstrap.QUICK), uid),
              f"{u['username']} is back on the starting password.")
    return redirect("/users")


# ------------------------------------------------------------------ activity
@more.route("/activity")
def activity():
    log = run("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 200")
    mails = run("SELECT * FROM email_outbox ORDER BY created_at DESC LIMIT 50")
    return admin_page("Activity Log", [
        section("Who did what", "Every change made by admin, faculty and students (last 200).",
                columns=["When", "Who", "Role", "Action"],
                rows=[row([l["created_at"].strftime("%d %b %H:%M"), l["actor"], l["role"], l["action"]]) for l in log],
                empty="Nothing logged yet."),
        section("E-mail outbox", "Messages UniTrack tried to send (Status = Sent only when SMTP is configured).",
                columns=["When", "To", "Subject", "Status"],
                rows=[row([m["created_at"].strftime("%d %b %H:%M"), m["to_email"], m["subject"],
                           "Sent" if m["sent"] else "Queued"]) for m in mails],
                empty="No e-mails yet."),
    ], "Audit trail", slug="activity")
