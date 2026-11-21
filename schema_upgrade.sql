/* UniTrack v4 - new tables. Applied automatically at app start (idempotent),
   or run by hand in pgAdmin after database.sql. */

CREATE TABLE IF NOT EXISTS app_user (
    user_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username       VARCHAR(100) NOT NULL UNIQUE,
    password_hash  VARCHAR(300) NOT NULL,
    role           VARCHAR(10)  NOT NULL CHECK (role IN ('admin', 'student', 'faculty')),
    student_id     INTEGER UNIQUE REFERENCES student (student_id) ON DELETE CASCADE,
    faculty_id     INTEGER UNIQUE REFERENCES faculty (faculty_id) ON DELETE CASCADE,
    must_change    BOOLEAN NOT NULL DEFAULT TRUE,
    last_login     TIMESTAMP,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS announcement (
    announcement_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title           VARCHAR(150) NOT NULL,
    body            TEXT NOT NULL,
    audience        VARCHAR(10) NOT NULL DEFAULT 'All' CHECK (audience IN ('All', 'Students', 'Faculty')),
    department_id   INTEGER REFERENCES department (department_id) ON DELETE SET NULL,
    posted_by       VARCHAR(100),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS timetable (
    slot_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    offering_id  INTEGER NOT NULL REFERENCES course_offering (offering_id) ON DELETE CASCADE,
    day_of_week  INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 6),   -- 1 = Monday
    start_time   TIME NOT NULL,
    end_time     TIME NOT NULL,
    room         VARCHAR(30) NOT NULL,
    CONSTRAINT chk_slot_time CHECK (end_time > start_time),
    CONSTRAINT uq_slot UNIQUE (offering_id, day_of_week, start_time)
);

CREATE TABLE IF NOT EXISTS leave_request (
    leave_id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES student (student_id) ON DELETE CASCADE,
    from_date   DATE NOT NULL,
    to_date     DATE NOT NULL,
    reason      TEXT NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    admin_note  TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_leave_dates CHECK (to_date >= from_date)
);

CREATE TABLE IF NOT EXISTS fee (
    fee_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES student (student_id) ON DELETE CASCADE,
    title       VARCHAR(100) NOT NULL,
    amount      NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    due_date    DATE NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Paid')),
    paid_on     DATE,
    receipt_no  VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_id  INTEGER NOT NULL UNIQUE REFERENCES enrollment (enrollment_id) ON DELETE CASCADE,
    rating         INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment        TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS support_ticket (
    ticket_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES student (student_id) ON DELETE CASCADE,
    subject     VARCHAR(150) NOT NULL,
    message     TEXT NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'Open' CHECK (status IN ('Open', 'Resolved')),
    reply       TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    replied_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity_log (
    log_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor       VARCHAR(100),
    role        VARCHAR(10),
    action      VARCHAR(200) NOT NULL,
    details     VARCHAR(300),
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_outbox (
    email_id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    to_email    VARCHAR(150) NOT NULL,
    subject     VARCHAR(200) NOT NULL,
    body        TEXT NOT NULL,
    sent        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
