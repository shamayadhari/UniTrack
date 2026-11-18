"""
UniTrack - CRUD (Create, Read, Update, Delete) for the web app.

Every entity is described once in the ENTITIES dictionary below (table name,
primary key, form fields).  Three generic routes then give each entity:
    /<entity>/add            -> CREATE  (INSERT)
    /<entity>/<id>/edit      -> UPDATE
    /<entity>/<id>/delete    -> DELETE
READ is the list page that already exists in app.py (/students, /faculty ...).

All values go to PostgreSQL as query parameters (%s), so user input can never
change the SQL itself (no SQL injection).  Table and column names come only
from the dictionary below, never from the browser.
"""
from flask import Blueprint, render_template, request, redirect, flash, abort
from db import get_db_connection

crud = Blueprint("crud", __name__)

# ---------- dropdown queries: each returns (value, label) ----------
DEPARTMENTS = """SELECT department_id, department_name
                 FROM department ORDER BY department_name"""

SEMESTERS = """SELECT semester_id,
                      'Semester ' || semester_number || ' (' || academic_year || ')'
               FROM semester ORDER BY academic_year, semester_number"""

ACTIVE_STUDENTS = """SELECT student_id,
                            enrollment_number || ' - ' || first_name || ' ' || COALESCE(last_name, '')
                     FROM student WHERE status = 'Active' ORDER BY enrollment_number"""

OFFERINGS = """SELECT o.offering_id,
                      c.course_code || ' - ' || c.course_name ||
                      ' (Sec ' || o.section || ', Sem ' || sem.semester_number || ')'
               FROM course_offering o
               JOIN course c     ON c.course_id = o.course_id
               JOIN semester sem ON sem.semester_id = o.semester_id
               ORDER BY c.course_code, o.section"""

ENROLMENTS = """SELECT en.enrollment_id,
                       s.first_name || ' ' || COALESCE(s.last_name, '') || ' - ' ||
                       c.course_code || ' (Sec ' || o.section || ')'
                FROM enrollment en
                JOIN student s         ON s.student_id  = en.student_id
                JOIN course_offering o ON o.offering_id = en.offering_id
                JOIN course c          ON c.course_id   = o.course_id
                WHERE en.enrollment_status <> 'Dropped'
                ORDER BY 2"""

EXAMS = """SELECT ex.exam_id,
                  ex.exam_name || ' - ' || c.course_code ||
                  ' (Sec ' || o.section || ', max ' || ex.maximum_marks || ')'
           FROM examination ex
           JOIN course_offering o ON o.offering_id = ex.offering_id
           JOIN course c          ON c.course_id   = o.course_id
           ORDER BY c.course_code, ex.exam_name"""


def field(name, label, kind="text", required=False, options=None, mode="both", step=None):
    """mode: 'both' = add + edit form, 'add' = only when creating, 'edit' = only when editing."""
    return dict(name=name, label=label, type=kind, required=required,
                options=options, mode=mode, step=step)


ENTITIES = {
    "students": dict(
        title="Student", table="student", pk="student_id", fields=[
            field("enrollment_number", "Enrollment Number", required=True),
            field("first_name", "First Name", required=True),
            field("last_name", "Last Name"),
            field("email", "Email", "email"),
            field("phone", "Phone"),
            field("gender", "Gender", "select", options=["Male", "Female", "Other"]),
            field("date_of_birth", "Date of Birth", "date"),
            field("admission_date", "Admission Date", "date"),
            field("department_id", "Department", "select", True, DEPARTMENTS),
            field("semester_id", "Current Semester", "select", True, SEMESTERS),
            field("status", "Status", "select", True, ["Active", "Inactive", "Graduated"]),
        ]),
    "faculty": dict(
        title="Faculty", table="faculty", pk="faculty_id", fields=[
            field("faculty_name", "Faculty Name", required=True),
            field("email", "Email", "email"),
            field("phone", "Phone"),
            field("designation", "Designation", "select", options=[
                "Professor", "Associate Professor", "Assistant Professor", "Lecturer"]),
            field("department_id", "Department", "select", True, DEPARTMENTS),
        ]),
    "courses": dict(
        title="Course", table="course", pk="course_id", fields=[
            field("course_code", "Course Code", required=True),
            field("course_name", "Course Name", required=True),
            field("credits", "Credits (1-6)", "number", True),
            field("department_id", "Department", "select", True, DEPARTMENTS),
        ]),
    "enrollments": dict(
        title="Enrollment", table="enrollment", pk="enrollment_id",
        # New enrolments go through the stored procedure sp_enroll_student, so the
        # database itself checks: active student, free seat, no duplicate.
        insert_proc="sp_enroll_student", proc_args=["student_id", "offering_id"],
        fields=[
            field("student_id", "Student", "select", True, ACTIVE_STUDENTS, mode="add"),
            field("offering_id", "Course Offering", "select", True, OFFERINGS, mode="add"),
            field("enrollment_status", "Status", "select", True,
                  ["Enrolled", "Completed", "Dropped"], mode="edit"),
        ]),
    "attendance": dict(
        title="Attendance", table="attendance", pk="attendance_id", fields=[
            field("enrollment_id", "Student - Course", "select", True, ENROLMENTS),
            field("attendance_date", "Date", "date", True),
            field("attendance_status", "Status", "select", True, ["Present", "Absent", "Late"]),
        ]),
    "results": dict(
        title="Result", table="results", pk="result_id", fields=[
            field("exam_id", "Examination", "select", True, EXAMS),
            field("enrollment_id", "Student - Course", "select", True, ENROLMENTS),
            # grade and result_status are filled in automatically by trigger trg_validate_result
            field("marks_obtained", "Marks Obtained", "number", True, step="0.5"),
        ]),
}


# ---------------------------------------------------------------- helpers
def get_entity(slug):
    entity = ENTITIES.get(slug)
    if entity is None:
        abort(404)
    return entity


def fields_for(entity, mode):
    return [f for f in entity["fields"] if f["mode"] in ("both", mode)]


def load_options(cursor, fields):
    """Fill every dropdown: {field_name: [(value, label), ...]}"""
    options = {}
    for f in fields:
        if f["type"] != "select":
            continue
        if isinstance(f["options"], list):
            options[f["name"]] = [(v, v) for v in f["options"]]
        else:
            cursor.execute(f["options"])
            options[f["name"]] = [(str(v), label) for v, label in cursor.fetchall()]
    return options


def friendly_error(error):
    """Turn a PostgreSQL error into one readable line (trigger / constraint messages)."""
    diag = getattr(error, "diag", None)
    message = getattr(diag, "message_primary", None) or str(error).splitlines()[0]
    detail = getattr(diag, "message_detail", None)
    return f"{message} - {detail}" if detail else message


def clean(value):
    value = (value or "").strip()
    return value if value != "" else None


def render_form(entity, slug, mode, values, options, record_id=None):
    return render_template(
        "form.html", entity=entity, slug=slug, mode=mode, record_id=record_id,
        fields=fields_for(entity, mode), values=values, options=options)


# ----------------------------------------------------------------- CREATE
@crud.route("/<slug>/add", methods=["GET", "POST"])
def add(slug):
    entity = get_entity(slug)
    fields = fields_for(entity, "add")
    connection = get_db_connection()
    if connection is None:
        return "Database connection failed!"
    cursor = connection.cursor()
    try:
        if request.method == "POST":
            values = {f["name"]: clean(request.form.get(f["name"])) for f in fields}
            try:
                if entity.get("insert_proc"):
                    args = [int(values[name]) for name in entity["proc_args"]]
                    marks = ", ".join(["%s"] * len(args))
                    cursor.execute(f"CALL {entity['insert_proc']}({marks})", args)
                else:
                    # blank optional fields are left out so column DEFAULTs still apply
                    given = {k: v for k, v in values.items() if v is not None}
                    columns = ", ".join(given)
                    marks = ", ".join(["%s"] * len(given))
                    cursor.execute(
                        f"INSERT INTO {entity['table']} ({columns}) VALUES ({marks})",
                        list(given.values()))
                connection.commit()
                flash(f"{entity['title']} added successfully.", "success")
                return redirect("/" + slug)
            except Exception as error:          # constraint, trigger or procedure rejected it
                connection.rollback()
                flash(friendly_error(error), "error")
                return render_form(entity, slug, "add", values, load_options(cursor, fields))
        return render_form(entity, slug, "add", {}, load_options(cursor, fields))
    finally:
        cursor.close()
        connection.close()


# ----------------------------------------------------------------- UPDATE
@crud.route("/<slug>/<int:record_id>/edit", methods=["GET", "POST"])
def edit(slug, record_id):
    entity = get_entity(slug)
    fields = fields_for(entity, "edit")
    connection = get_db_connection()
    if connection is None:
        return "Database connection failed!"
    cursor = connection.cursor()
    try:
        if request.method == "POST":
            values = {f["name"]: clean(request.form.get(f["name"])) for f in fields}
            try:
                assignments = ", ".join(f"{name} = %s" for name in values)
                cursor.execute(
                    f"UPDATE {entity['table']} SET {assignments} WHERE {entity['pk']} = %s",
                    list(values.values()) + [record_id])
                connection.commit()
                flash(f"{entity['title']} updated successfully.", "success")
                return redirect("/" + slug)
            except Exception as error:
                connection.rollback()
                flash(friendly_error(error), "error")
                return render_form(entity, slug, "edit", values,
                                   load_options(cursor, fields), record_id)

        columns = ", ".join(f["name"] for f in fields)
        cursor.execute(f"SELECT {columns} FROM {entity['table']} WHERE {entity['pk']} = %s",
                       (record_id,))
        row = cursor.fetchone()
        if row is None:
            abort(404)
        values = {f["name"]: ("" if v is None else str(v)) for f, v in zip(fields, row)}
        return render_form(entity, slug, "edit", values, load_options(cursor, fields), record_id)
    finally:
        cursor.close()
        connection.close()


# ----------------------------------------------------------------- DELETE
@crud.route("/<slug>/<int:record_id>/delete", methods=["POST"])
def delete(slug, record_id):
    entity = get_entity(slug)
    connection = get_db_connection()
    if connection is None:
        return "Database connection failed!"
    cursor = connection.cursor()
    try:
        cursor.execute(f"DELETE FROM {entity['table']} WHERE {entity['pk']} = %s", (record_id,))
        connection.commit()
        if cursor.rowcount == 0:
            flash(f"{entity['title']} not found (already deleted?).", "error")
        else:
            flash(f"{entity['title']} deleted.", "success")
    except Exception as error:      # e.g. ON DELETE RESTRICT: still referenced elsewhere
        connection.rollback()
        flash("Could not delete: " + friendly_error(error), "error")
    finally:
        cursor.close()
        connection.close()
    return redirect("/" + slug)
