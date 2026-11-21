"""Small shared helpers: DB access, flash-on-write, activity log, e-mail, and the
tiny builders (field / form / section / row / act) used by templates/panel.html."""
import os
import smtplib
from decimal import Decimal
from email.message import EmailMessage
from flask import session, flash, render_template
from psycopg2.extras import RealDictCursor
from db import get_db_connection
from crud import friendly_error

DAYS = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday"}


def _conn():
    conn = get_db_connection()
    if conn is None:
        raise ConnectionError("Database connection failed!")
    return conn


def run(sql, params=(), one=False):
    """SELECT -> list of dicts (or one dict / None). Decimals become floats."""
    conn = _conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        rows = [{k: float(v) if isinstance(v, Decimal) else v for k, v in r.items()}
                for r in cur.fetchall()]
        cur.close()
    finally:
        conn.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, params=()):
    """INSERT/UPDATE/DELETE with commit. Returns rowcount; errors propagate."""
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        count = cur.rowcount
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def write(sql, params=(), ok="Saved."):
    """Run a write and flash the result. Returns rowcount, or None if it failed."""
    try:
        count = execute(sql, params)
    except Exception as error:
        flash(friendly_error(error), "error")
        return None
    if ok:
        flash(ok, "success")
    return count


def log_activity(action, details=""):
    try:
        execute("INSERT INTO activity_log (actor, role, action, details) VALUES (%s, %s, %s, %s)",
                (session.get("username", "?"), session.get("role", "?"), action[:200], details[:300]))
    except Exception as error:
        print("activity log failed:", error)


def send_mail(to, subject, body):
    """Send through SMTP when SMTP_HOST is configured; always keep a copy in email_outbox."""
    sent, host = False, os.environ.get("SMTP_HOST")
    if host:
        try:
            msg = EmailMessage()
            msg["From"] = os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "unitrack@localhost"))
            msg["To"], msg["Subject"] = to, subject
            msg.set_content(body)
            with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587)), timeout=15) as server:
                server.starttls()
                if os.environ.get("SMTP_USER"):
                    server.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
                server.send_message(msg)
            sent = True
        except Exception as error:
            print("SMTP failed:", error)
    execute("INSERT INTO email_outbox (to_email, subject, body, sent) VALUES (%s, %s, %s, %s)",
            (to, subject, body, sent))
    return sent


# ----------------------------------------------------- builders for panel.html
def field(name, label, type="text", required=True, options=None, value="", placeholder="", blank=None, **extra):
    return dict(name=name, label=label, type=type, required=required, options=options or [],
                value=value, placeholder=placeholder, blank=blank, **extra)


def form(fields, action=None, submit="Save", method="post", enctype=None):
    return dict(fields=fields, action=action, submit=submit, method=method, enctype=enctype)


def act(label, url, cls="btn-light", confirm=None, fields=(), get=False):
    return dict(label=label, url=url, cls=cls, confirm=confirm, fields=list(fields), is_link=get)


def row(cells, *actions):
    return {"cells": list(cells), "actions": list(actions)}


def section(title=None, sub=None, form=None, columns=None, rows=None, **extra):
    rows = rows or []
    return dict(title=title, sub=sub, form=form, columns=columns, rows=rows,
                has_actions=any(r["actions"] for r in rows),
                empty=extra.pop("empty", "Nothing here yet."), **extra)


def page(layout, heading, sections, sub="", **ctx):
    return render_template("panel.html", layout=layout, heading=heading, sub=sub,
                           sections=sections, **ctx)


def admin_page(heading, sections, sub="", slug=None, **ctx):
    return page("base.html", heading, sections, sub, slug=slug, **ctx)


def fmt_date(value, pattern="%d %b %Y"):
    return value.strftime(pattern) if value else "-"


def fmt_time(value):
    return value.strftime("%H:%M") if value else "-"


def grid(rows):
    """rows need day_of_week, start_time, end_time, title, sub -> [(day name, [slot, ...]), ...]"""
    days = {d: [] for d in DAYS}
    for r in rows:
        days[r["day_of_week"]].append(dict(time=f"{fmt_time(r['start_time'])}–{fmt_time(r['end_time'])}",
                                           title=r["title"], sub=r["sub"]))
    return [(DAYS[d], days[d]) for d in DAYS]
