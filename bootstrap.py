"""Runs at app start: creates the v4 tables and makes sure every admin / student /
faculty member has a login account. Safe to run repeatedly."""
import os
from werkzeug.security import generate_password_hash
from db import get_db_connection

ADMIN_DEFAULT = os.environ.get("ADMIN_PASSWORD", "admin123")
FACULTY_DEFAULT = os.environ.get("FACULTY_DEFAULT_PASSWORD", "Faculty@123")
QUICK = "pbkdf2:sha256:50000"        # initial passwords are forced to change at first login


def default_password(role, username):
    return {"admin": ADMIN_DEFAULT, "student": username}.get(role, FACULTY_DEFAULT)


def apply_schema():
    conn = get_db_connection()
    if conn is None:
        return
    try:
        path = os.path.join(os.path.dirname(__file__), "schema_upgrade.sql")
        with open(path, encoding="utf-8") as f:
            cur = conn.cursor()
            cur.execute(f.read())
        conn.commit()
    finally:
        conn.close()


def ensure_users():
    """Create missing accounts. Username = 'admin' / enrollment number / faculty email."""
    conn = get_db_connection()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM app_user WHERE role = 'admin'")
        if cur.fetchone() is None:
            cur.execute("""INSERT INTO app_user (username, password_hash, role) VALUES ('admin', %s, 'admin')
                           ON CONFLICT (username) DO NOTHING""",
                        (generate_password_hash(ADMIN_DEFAULT, method=QUICK),))
        cur.execute("""SELECT student_id, enrollment_number FROM student s
                       WHERE NOT EXISTS (SELECT 1 FROM app_user u WHERE u.student_id = s.student_id)""")
        for sid, enr in cur.fetchall():
            cur.execute("""INSERT INTO app_user (username, password_hash, role, student_id)
                           VALUES (%s, %s, 'student', %s) ON CONFLICT (username) DO NOTHING""",
                        (enr, generate_password_hash(enr, method=QUICK), sid))
        cur.execute("""SELECT faculty_id, email FROM faculty f
                       WHERE email IS NOT NULL
                         AND NOT EXISTS (SELECT 1 FROM app_user u WHERE u.faculty_id = f.faculty_id)""")
        faculty_hash = generate_password_hash(FACULTY_DEFAULT, method=QUICK)
        for fid, email in cur.fetchall():
            cur.execute("""INSERT INTO app_user (username, password_hash, role, faculty_id)
                           VALUES (%s, %s, 'faculty', %s) ON CONFLICT (username) DO NOTHING""",
                        (email, faculty_hash, fid))
        conn.commit()
    finally:
        conn.close()
