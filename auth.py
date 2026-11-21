"""Login for all three roles, password change, route guard and audit trail."""
import re
from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from util import run, execute, log_activity
import bootstrap

auth = Blueprint("auth", __name__)
HOME = {"admin": "/", "student": "/student/", "faculty": "/teacher/"}
OPEN_PATHS = ("/login", "/logout", "/student/login", "/student/logout", "/static")
AREAS = (("/student", "student"), ("/teacher", "faculty"))      # everything else = admin


def _find(username):
    return run("SELECT * FROM app_user WHERE LOWER(username) = LOWER(%s)", (username,), one=True)


def init_auth(app):
    @app.before_request
    def guard():
        path = request.path
        if path.startswith(OPEN_PATHS):
            return
        role = session.get("role")
        if not role:
            return redirect("/login" + ("?next=" + path if request.method == "GET" and path != "/" else ""))
        if path.startswith("/account/"):
            return
        if session.get("must_change"):
            return redirect("/account/password")
        needed = next((r for prefix, r in AREAS if path == prefix or path.startswith(prefix + "/")), "admin")
        if role != needed:
            flash("That page isn't available for your account.", "error")
            return redirect(HOME[role])

    @app.after_request
    def audit(response):
        """Every successful POST by a logged-in user lands in the activity log."""
        try:
            if request.method == "POST" and response.status_code in (301, 302, 303) \
                    and session.get("role") and not request.path.startswith(OPEN_PATHS):
                parts = request.path.strip("/").split("/")
                if len(parts) == 2 and parts[1] == "add":
                    action = f"Added new record in {parts[0]}"
                elif len(parts) == 3 and parts[2] in ("edit", "delete"):
                    action = f"{parts[2].title()}d {parts[0]} #{parts[1]}".replace("Editd", "Edited")
                else:
                    action = "POST " + request.path
                log_activity(action)
                if request.path in ("/students/add", "/faculty/add"):
                    bootstrap.ensure_users()          # new person -> new login account
        except Exception as error:
            print("audit failed:", error)
        return response


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = _find(username)
        if user is None:                       # maybe a brand-new student/faculty
            bootstrap.ensure_users()
            user = _find(username)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["user_id"], role=user["role"], username=user["username"],
                           student_id=user["student_id"], faculty_id=user["faculty_id"],
                           must_change=user["must_change"])
            execute("UPDATE app_user SET last_login = NOW() WHERE user_id = %s", (user["user_id"],))
            if user["must_change"]:
                flash("Welcome! Please set your own password to continue.", "warn")
            nxt = request.form.get("next", "")
            safe = nxt.startswith("/") and not nxt.startswith("//") and not nxt.startswith("/login")
            return redirect(nxt if safe else HOME[user["role"]])
        flash("Wrong username or password.", "error")
    elif session.get("role"):
        return redirect(HOME[session["role"]])
    return render_template("login.html", next=request.args.get("next", request.form.get("next", "")))


@auth.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect("/login")


@auth.route("/account/password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        current, new, again = (request.form.get(k, "") for k in ("current", "new", "again"))
        user = run("SELECT password_hash FROM app_user WHERE user_id = %s", (session["user_id"],), one=True)
        if not user or not check_password_hash(user["password_hash"], current):
            flash("Current password is wrong.", "error")
        elif len(new) < 8 or not re.search(r"\d", new) or not re.search(r"[A-Za-z]", new):
            flash("New password needs 8+ characters with letters and a number.", "error")
        elif new != again:
            flash("The two new passwords don't match.", "error")
        elif new == current:
            flash("Choose a password different from the current one.", "error")
        else:
            execute("UPDATE app_user SET password_hash = %s, must_change = FALSE WHERE user_id = %s",
                    (generate_password_hash(new), session["user_id"]))
            session["must_change"] = False
            log_activity("Changed own password")
            flash("Password updated.", "success")
            return redirect(HOME[session["role"]])
    return render_template("change_password.html", forced=session.get("must_change"), home=HOME[session["role"]])
