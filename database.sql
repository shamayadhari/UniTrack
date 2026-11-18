/* =====================================================================
   UniTrack - Smart University Management and Academic Analytics System
   File     : database.sql
   Database : PostgreSQL 12+ (tested on PostgreSQL 16)
   Tool     : pgAdmin 4 (Query Tool) or psql

   HOW TO RUN (pgAdmin)
   1. Right-click Databases > Create > Database...  name it:  unitrack
   2. Right-click the new "unitrack" database > Query Tool
   3. Open this file (folder icon) and press F5 (Execute).
   The script can be re-run any number of times: it drops and rebuilds
   everything.  (If you use psql instead:  psql -U postgres -c "CREATE DATABASE unitrack;"
   then  psql -U postgres -d unitrack -f database.sql )

   CONTENTS
   Part 1  DDL      - tables, constraints, indexes
   Part 2  Trigger  - result validation (must exist BEFORE results are inserted)
   Part 3  DML      - sample data, UPDATE and DELETE examples
   Part 4  Queries  - SELECT, aggregates, joins, subqueries, set operations
   Part 5  Advanced - views, window functions, CTEs, index demo
   Part 6  TCL      - transactions and savepoints
   Part 7  DCL      - roles, GRANT, REVOKE
   Part 8  Stored procedure for enrolment
   ===================================================================== */


/* =====================================================================
   PART 1 : DDL  (Data Definition Language)
   ===================================================================== */

-- Clean slate so the script can be re-run safely.
DROP VIEW      IF EXISTS student_academic_view, course_performance_view CASCADE;
DROP TABLE     IF EXISTS results, attendance, examination, enrollment,
                         course_offering, student, faculty, course,
                         semester, department CASCADE;
DROP PROCEDURE IF EXISTS sp_enroll_student(INTEGER, INTEGER);
DROP FUNCTION  IF EXISTS fn_validate_result() CASCADE;

-- ---------------------------------------------------------------------
-- Table 1 : department
-- ---------------------------------------------------------------------
CREATE TABLE department (
    department_id    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name  VARCHAR(100) NOT NULL UNIQUE,
    department_code  VARCHAR(10)  UNIQUE,
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table 5 : semester  (created before student because student references it)
-- A "semester" row is one running term, e.g. Semester 3 of 2026-27.
-- ---------------------------------------------------------------------
CREATE TABLE semester (
    semester_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    semester_number  INTEGER     NOT NULL CHECK (semester_number BETWEEN 1 AND 8),
    academic_year    VARCHAR(9)  NOT NULL,              -- e.g. '2026-27'
    start_date       DATE        NOT NULL,
    end_date         DATE        NOT NULL,
    CONSTRAINT chk_semester_dates  CHECK (end_date > start_date),
    CONSTRAINT uq_semester_term    UNIQUE (semester_number, academic_year)
);

-- ---------------------------------------------------------------------
-- Table 2 : student
-- ---------------------------------------------------------------------
CREATE TABLE student (
    student_id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_number  VARCHAR(20)  NOT NULL UNIQUE,
    first_name         VARCHAR(50)  NOT NULL,
    last_name          VARCHAR(50),
    email              VARCHAR(100) UNIQUE,
    phone              VARCHAR(15),
    gender             VARCHAR(10),
    date_of_birth      DATE,
    admission_date     DATE         DEFAULT CURRENT_DATE,
    department_id      INTEGER      NOT NULL,
    semester_id        INTEGER      NOT NULL,
    status             VARCHAR(10)  NOT NULL DEFAULT 'Active',
    CONSTRAINT fk_student_department FOREIGN KEY (department_id)
        REFERENCES department (department_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_student_semester FOREIGN KEY (semester_id)
        REFERENCES semester (semester_id)     ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_student_gender CHECK (gender IN ('Male', 'Female', 'Other')),
    CONSTRAINT chk_student_status CHECK (status IN ('Active', 'Inactive', 'Graduated')),
    CONSTRAINT chk_student_email  CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_student_dob    CHECK (date_of_birth < admission_date)
);

-- ---------------------------------------------------------------------
-- Table 3 : faculty
-- ---------------------------------------------------------------------
CREATE TABLE faculty (
    faculty_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    faculty_name   VARCHAR(100) NOT NULL,
    email          VARCHAR(100) UNIQUE,
    phone          VARCHAR(15),
    designation    VARCHAR(50),
    department_id  INTEGER      NOT NULL,
    CONSTRAINT fk_faculty_department FOREIGN KEY (department_id)
        REFERENCES department (department_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_faculty_designation CHECK
        (designation IN ('Professor', 'Associate Professor', 'Assistant Professor', 'Lecturer'))
);

-- ---------------------------------------------------------------------
-- Table 4 : course
-- ---------------------------------------------------------------------
CREATE TABLE course (
    course_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    course_code    VARCHAR(10)  NOT NULL UNIQUE,
    course_name    VARCHAR(100) NOT NULL,
    credits        INTEGER      NOT NULL DEFAULT 3 CHECK (credits BETWEEN 1 AND 6),
    department_id  INTEGER      NOT NULL,
    CONSTRAINT fk_course_department FOREIGN KEY (department_id)
        REFERENCES department (department_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- ---------------------------------------------------------------------
-- Table 6 : course_offering  (a course taught by a faculty in a semester)
-- ---------------------------------------------------------------------
CREATE TABLE course_offering (
    offering_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    course_id    INTEGER     NOT NULL,
    faculty_id   INTEGER     NOT NULL,
    semester_id  INTEGER     NOT NULL,
    section      VARCHAR(5)  NOT NULL DEFAULT 'A',
    capacity     INTEGER     NOT NULL DEFAULT 60 CHECK (capacity > 0),
    CONSTRAINT fk_offering_course FOREIGN KEY (course_id)
        REFERENCES course (course_id)     ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_offering_faculty FOREIGN KEY (faculty_id)
        REFERENCES faculty (faculty_id)   ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_offering_semester FOREIGN KEY (semester_id)
        REFERENCES semester (semester_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_offering UNIQUE (course_id, semester_id, section)
);

-- ---------------------------------------------------------------------
-- Table 7 : enrollment  (student <-> course_offering, many-to-many)
-- ---------------------------------------------------------------------
CREATE TABLE enrollment (
    enrollment_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id         INTEGER     NOT NULL,
    offering_id        INTEGER     NOT NULL,
    enrollment_date    DATE        NOT NULL DEFAULT CURRENT_DATE,
    enrollment_status  VARCHAR(10) NOT NULL DEFAULT 'Enrolled',
    CONSTRAINT fk_enrollment_student FOREIGN KEY (student_id)
        REFERENCES student (student_id)           ON DELETE CASCADE  ON UPDATE CASCADE,
    CONSTRAINT fk_enrollment_offering FOREIGN KEY (offering_id)
        REFERENCES course_offering (offering_id)  ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_enrollment UNIQUE (student_id, offering_id),   -- no duplicate enrolment
    CONSTRAINT chk_enrollment_status CHECK (enrollment_status IN ('Enrolled', 'Completed', 'Dropped'))
);

-- ---------------------------------------------------------------------
-- Table 8 : attendance
-- ---------------------------------------------------------------------
CREATE TABLE attendance (
    attendance_id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_id      INTEGER     NOT NULL,
    attendance_date    DATE        NOT NULL,
    attendance_status  VARCHAR(10) NOT NULL,
    CONSTRAINT fk_attendance_enrollment FOREIGN KEY (enrollment_id)
        REFERENCES enrollment (enrollment_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_attendance UNIQUE (enrollment_id, attendance_date),  -- one entry per day
    CONSTRAINT chk_attendance_status CHECK (attendance_status IN ('Present', 'Absent', 'Late'))
);

-- ---------------------------------------------------------------------
-- Table 9 : examination
-- ---------------------------------------------------------------------
CREATE TABLE examination (
    exam_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    offering_id    INTEGER       NOT NULL,
    exam_name      VARCHAR(50)   NOT NULL,
    exam_date      DATE,
    maximum_marks  NUMERIC(6,2)  NOT NULL CHECK (maximum_marks > 0),
    CONSTRAINT fk_exam_offering FOREIGN KEY (offering_id)
        REFERENCES course_offering (offering_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_exam UNIQUE (offering_id, exam_name)
);

-- ---------------------------------------------------------------------
-- Table 10 : results
-- grade and result_status are filled automatically by the trigger in Part 2.
-- ---------------------------------------------------------------------
CREATE TABLE results (
    result_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    exam_id         INTEGER       NOT NULL,
    enrollment_id   INTEGER       NOT NULL,
    marks_obtained  NUMERIC(6,2)  NOT NULL CHECK (marks_obtained >= 0),
    grade           VARCHAR(2),
    result_status   VARCHAR(10),
    CONSTRAINT fk_results_exam FOREIGN KEY (exam_id)
        REFERENCES examination (exam_id)      ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_results_enrollment FOREIGN KEY (enrollment_id)
        REFERENCES enrollment (enrollment_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_results UNIQUE (exam_id, enrollment_id),       -- no duplicate result
    CONSTRAINT chk_results_status CHECK (result_status IN ('Pass', 'Fail'))
);

-- ---------------------------------------------------------------------
-- Indexes (speed up searches and joins on foreign keys)
-- NOTE: PostgreSQL already builds an index for every PRIMARY KEY / UNIQUE
-- constraint. The three indexes marked (*) duplicate those on purpose so you
-- can show them in your viva and in EXPLAIN output (Part 5).
-- ---------------------------------------------------------------------
CREATE INDEX idx_student_enrollment_number ON student (enrollment_number);   -- (*)
CREATE INDEX idx_course_code               ON course (course_code);          -- (*)
CREATE INDEX idx_enrollment_student_id     ON enrollment (student_id);       -- (*)
CREATE INDEX idx_enrollment_offering_id    ON enrollment (offering_id);
CREATE INDEX idx_student_department_id     ON student (department_id);
CREATE INDEX idx_student_semester_id       ON student (semester_id);
CREATE INDEX idx_attendance_enrollment_id  ON attendance (enrollment_id);
CREATE INDEX idx_results_enrollment_id     ON results (enrollment_id);
CREATE INDEX idx_offering_faculty_id       ON course_offering (faculty_id);


/* =====================================================================
   PART 2 : TRIGGER  - validates and auto-grades every result
   Why it is here: sample results in Part 3 are inserted through this trigger.
   A CHECK constraint cannot compare marks_obtained with maximum_marks because
   they live in different tables, so a trigger is the correct tool.
   ===================================================================== */

CREATE OR REPLACE FUNCTION fn_validate_result()
RETURNS TRIGGER AS $$
DECLARE
    v_max_marks     NUMERIC;
    v_exam_offering INTEGER;
    v_enrol_offering INTEGER;
    v_percent       NUMERIC;
BEGIN
    SELECT maximum_marks, offering_id INTO v_max_marks, v_exam_offering
    FROM examination WHERE exam_id = NEW.exam_id;

    SELECT offering_id INTO v_enrol_offering
    FROM enrollment WHERE enrollment_id = NEW.enrollment_id;

    -- Rule 1: marks cannot exceed the exam's maximum marks
    IF NEW.marks_obtained > v_max_marks THEN
        RAISE EXCEPTION 'Marks obtained (%) cannot exceed maximum marks (%)',
            NEW.marks_obtained, v_max_marks;
    END IF;

    -- Rule 2: the student must be enrolled in the course offering the exam belongs to
    IF v_exam_offering <> v_enrol_offering THEN
        RAISE EXCEPTION 'Enrollment % is not enrolled in the offering of exam %',
            NEW.enrollment_id, NEW.exam_id;
    END IF;

    -- Rule 3: derive grade and pass/fail from the percentage (pass mark = 40%)
    v_percent := NEW.marks_obtained * 100 / v_max_marks;
    NEW.grade := CASE
        WHEN v_percent >= 90 THEN 'A+'
        WHEN v_percent >= 80 THEN 'A'
        WHEN v_percent >= 70 THEN 'B+'
        WHEN v_percent >= 60 THEN 'B'
        WHEN v_percent >= 50 THEN 'C'
        WHEN v_percent >= 40 THEN 'D'
        ELSE 'F' END;
    NEW.result_status := CASE WHEN v_percent >= 40 THEN 'Pass' ELSE 'Fail' END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_result
BEFORE INSERT OR UPDATE ON results
FOR EACH ROW EXECUTE FUNCTION fn_validate_result();


/* =====================================================================
   PART 3 : DML  (Data Manipulation Language) - sample data
   Rows are inserted in dependency order so every foreign key is valid.
   Identity columns start at 1 on a fresh database, so the ids below are
   predictable and the data is relationally consistent.
   ===================================================================== */

-- 4 departments (ids 1-4)
INSERT INTO department (department_name, department_code) VALUES
 ('Computer Science and Engineering',   'CSE'),
 ('Electronics and Communication',      'ECE'),
 ('Mechanical Engineering',             'ME'),
 ('Business Administration',            'BBA');

-- 2 semesters (ids 1-2): odd-semester term 2026-27 for two different years of study
INSERT INTO semester (semester_number, academic_year, start_date, end_date) VALUES
 (3, '2026-27', '2026-07-27', '2026-12-18'),
 (5, '2026-27', '2026-07-27', '2026-12-18');

-- 8 faculty members (ids 1-8)
INSERT INTO faculty (faculty_name, email, phone, designation, department_id) VALUES
 ('Dr. Anita Sharma',   'anita.sharma@unitrack.edu',   '9810011001', 'Professor',           1),
 ('Prof. Rajesh Verma', 'rajesh.verma@unitrack.edu',   '9810011002', 'Associate Professor', 1),
 ('Dr. Neha Gupta',     'neha.gupta@unitrack.edu',     '9810011003', 'Assistant Professor', 1),
 ('Dr. Sanjay Mehta',   'sanjay.mehta@unitrack.edu',   '9810011004', 'Professor',           2),
 ('Prof. Kavita Rao',   'kavita.rao@unitrack.edu',     '9810011005', 'Assistant Professor', 2),
 ('Dr. Vikram Singh',   'vikram.singh@unitrack.edu',   '9810011006', 'Associate Professor', 3),
 ('Dr. Pooja Malhotra', 'pooja.malhotra@unitrack.edu', '9810011007', 'Professor',           4),
 ('Prof. Arjun Kapoor', 'arjun.kapoor@unitrack.edu',   '9810011008', 'Assistant Professor', 4);

-- 11 courses (ids 1-11). CS401 is deliberately not offered yet (used in LEFT/RIGHT JOIN demos).
INSERT INTO course (course_code, course_name, credits, department_id) VALUES
 ('CS201', 'Data Structures and Algorithms', 4, 1),
 ('CS202', 'Database Management Systems',   4, 1),
 ('CS301', 'Computer Networks',              3, 1),
 ('CS302', 'Operating Systems',              4, 1),
 ('EC201', 'Digital Electronics',            4, 2),
 ('EC301', 'Signals and Systems',            3, 2),
 ('ME201', 'Thermodynamics',                 4, 3),
 ('ME301', 'Fluid Mechanics',                3, 3),
 ('BA201', 'Principles of Management',       3, 4),
 ('BA301', 'Marketing Management',           3, 4),
 ('CS401', 'Machine Learning',               4, 1);

-- 16 students (ids 1-16). Students 1-8 are in Semester 3 (id 1), students 9-16 in Semester 5 (id 2).
INSERT INTO student (enrollment_number, first_name, last_name, email, phone, gender,
                     date_of_birth, admission_date, department_id, semester_id, status) VALUES
 ('KRM25CSE001', 'Aarav',     'Sharma',   'aarav.sharma@student.unitrack.edu',   '9876500001', 'Male',   '2006-03-14', '2025-08-04', 1, 1, 'Active'),
 ('KRM25CSE002', 'Ananya',    'Verma',    'ananya.verma@student.unitrack.edu',   '9876500002', 'Female', '2006-07-21', '2025-08-04', 1, 1, 'Active'),
 ('KRM25CSE003', 'Rohan',     'Gupta',    'rohan.gupta@student.unitrack.edu',    '9876500003', 'Male',   '2005-11-02', '2025-08-04', 1, 1, 'Active'),
 ('KRM25ECE001', 'Ishita',    'Mehta',    'ishita.mehta@student.unitrack.edu',   '9876500004', 'Female', '2006-01-30', '2025-08-04', 2, 1, 'Active'),
 ('KRM25ECE002', 'Kabir',     'Singh',    'kabir.singh@student.unitrack.edu',    '9876500005', 'Male',   '2005-09-18', '2025-08-04', 2, 1, 'Active'),
 ('KRM25ME001',  'Mohit',     'Yadav',    'mohit.yadav@student.unitrack.edu',    '9876500006', 'Male',   '2006-05-09', '2025-08-04', 3, 1, 'Active'),
 ('KRM25BBA001', 'Priya',     'Nair',     'priya.nair@student.unitrack.edu',     '9876500007', 'Female', '2006-12-25', '2025-08-04', 4, 1, 'Active'),
 ('KRM25BBA002', 'Siddharth', 'Rao',      'siddharth.rao@student.unitrack.edu',  '9876500008', 'Male',   '2005-08-11', '2025-08-04', 4, 1, 'Active'),
 ('KRM24CSE001', 'Diya',      'Kapoor',   'diya.kapoor@student.unitrack.edu',    '9876500009', 'Female', '2005-04-17', '2024-08-05', 1, 2, 'Active'),
 ('KRM24CSE002', 'Arjun',     'Malhotra', 'arjun.malhotra@student.unitrack.edu', '9876500010', 'Male',   '2005-02-06', '2024-08-05', 1, 2, 'Active'),
 ('KRM24CSE003', 'Meera',     'Joshi',    'meera.joshi@student.unitrack.edu',    '9876500011', 'Female', '2005-10-28', '2024-08-05', 1, 2, 'Active'),
 ('KRM24ECE001', 'Karan',     'Bansal',   'karan.bansal@student.unitrack.edu',   '9876500012', 'Male',   '2005-06-12', '2024-08-05', 2, 2, 'Active'),
 ('KRM24ECE002', 'Sneha',     'Reddy',    'sneha.reddy@student.unitrack.edu',    '9876500013', 'Female', '2005-01-23', '2024-08-05', 2, 2, 'Active'),
 ('KRM24ME001',  'Vivek',     'Chauhan',  'vivek.chauhan@student.unitrack.edu',  '9876500014', 'Male',   '2004-12-03', '2024-08-05', 3, 2, 'Active'),
 ('KRM24BBA001', 'Tanya',     'Arora',    'tanya.arora@student.unitrack.edu',    '9876500015', 'Female', '2005-03-19', '2024-08-05', 4, 2, 'Active'),
 ('KRM24BBA002', 'Rahul',     'Khanna',   'rahul.khanna@student.unitrack.edu',   '9876500016', 'Male',   '2005-07-07', '2024-08-05', 4, 2, 'Inactive');

-- 11 course offerings (ids 1-11). CS202 has two sections (A and B) in Semester 3.
INSERT INTO course_offering (course_id, faculty_id, semester_id, section, capacity) VALUES
 (1, 1, 1, 'A', 60),   -- 1  CS201 DSA            Dr. Anita Sharma    Sem 3
 (2, 2, 1, 'A', 60),   -- 2  CS202 DBMS (A)       Prof. Rajesh Verma  Sem 3
 (3, 3, 2, 'A', 60),   -- 3  CS301 Networks       Dr. Neha Gupta      Sem 5
 (4, 1, 2, 'A', 60),   -- 4  CS302 OS             Dr. Anita Sharma    Sem 5
 (5, 4, 1, 'A', 40),   -- 5  EC201 Digital Elec.  Dr. Sanjay Mehta    Sem 3
 (6, 5, 2, 'A', 40),   -- 6  EC301 Signals        Prof. Kavita Rao    Sem 5
 (7, 6, 1, 'A', 40),   -- 7  ME201 Thermodynamics Dr. Vikram Singh    Sem 3
 (8, 6, 2, 'A', 40),   -- 8  ME301 Fluid Mech.    Dr. Vikram Singh    Sem 5
 (9, 7, 1, 'A', 50),   -- 9  BA201 Management     Dr. Pooja Malhotra  Sem 3
 (10, 8, 2, 'A', 50),  -- 10 BA301 Marketing      Prof. Arjun Kapoor  Sem 5
 (2, 3, 1, 'B', 60);   -- 11 CS202 DBMS (B)       Dr. Neha Gupta      Sem 3

-- 30 enrolments (ids 1-30). Student 16 (Inactive) has no enrolment on purpose.
-- Enrolment 16 is 'Dropped': it has no attendance rows and no results.
INSERT INTO enrollment (student_id, offering_id, enrollment_date, enrollment_status) VALUES
 (1, 1, '2026-07-28', 'Enrolled'),  (1, 2, '2026-07-28', 'Enrolled'),    -- 1,2
 (2, 1, '2026-07-28', 'Enrolled'),  (2, 2, '2026-07-28', 'Enrolled'),    -- 3,4
 (3, 1, '2026-07-29', 'Enrolled'),  (3, 11,'2026-07-29', 'Enrolled'),    -- 5,6
 (4, 5, '2026-07-29', 'Enrolled'),  (4, 9, '2026-07-29', 'Enrolled'),    -- 7,8
 (5, 5, '2026-07-29', 'Enrolled'),  (5, 1, '2026-07-30', 'Enrolled'),    -- 9,10
 (6, 7, '2026-07-30', 'Enrolled'),  (6, 9, '2026-07-30', 'Enrolled'),    -- 11,12
 (7, 9, '2026-07-30', 'Enrolled'),  (7, 11,'2026-07-30', 'Enrolled'),    -- 13,14
 (8, 9, '2026-07-31', 'Enrolled'),  (8, 2, '2026-07-31', 'Dropped'),     -- 15,16
 (9, 3, '2026-07-28', 'Enrolled'),  (9, 4, '2026-07-28', 'Enrolled'),    -- 17,18
 (10, 3, '2026-07-28', 'Enrolled'), (10, 4, '2026-07-28', 'Enrolled'),   -- 19,20
 (11, 3, '2026-07-29', 'Enrolled'), (11, 10,'2026-07-29', 'Enrolled'),   -- 21,22
 (12, 6, '2026-07-29', 'Enrolled'), (12, 4, '2026-07-29', 'Enrolled'),   -- 23,24
 (13, 6, '2026-07-30', 'Enrolled'), (13, 10,'2026-07-30', 'Enrolled'),   -- 25,26
 (14, 8, '2026-07-30', 'Enrolled'), (14, 10,'2026-07-30', 'Enrolled'),   -- 27,28
 (15, 10,'2026-07-31', 'Enrolled'), (15, 3, '2026-07-31', 'Enrolled');   -- 29,30

-- Attendance: 10 class days per enrolment (3 days apart, from 3 Aug 2026), skipping the dropped
-- enrolment. The status comes from a fixed formula, so the data is realistic and reproducible:
-- every enrolment has its own absence rate, and a few students end up below 75 %.
INSERT INTO attendance (enrollment_id, attendance_date, attendance_status)
SELECT e.enrollment_id,
       DATE '2026-08-03' + (d.n * 3),
       CASE
         WHEN (e.enrollment_id * 13 + d.n * 7) % 100 <
              CASE e.enrollment_id % 6 WHEN 0 THEN 45 WHEN 1 THEN 5 WHEN 2 THEN 10
                                       WHEN 3 THEN 15 WHEN 4 THEN 30 ELSE 8 END
              THEN 'Absent'
         WHEN (e.enrollment_id * 13 + d.n * 7) % 100 <
              CASE e.enrollment_id % 6 WHEN 0 THEN 45 WHEN 1 THEN 5 WHEN 2 THEN 10
                                       WHEN 3 THEN 15 WHEN 4 THEN 30 ELSE 8 END + 8
              THEN 'Late'
         ELSE 'Present'
       END
FROM enrollment e
CROSS JOIN generate_series(0, 9) AS d(n)
WHERE e.enrollment_status <> 'Dropped';

-- 15 examinations (ids 1-15): a Mid-Term for each offering (max 50), plus Quiz 1 (max 20)
-- for the four computer-science offerings.
INSERT INTO examination (offering_id, exam_name, exam_date, maximum_marks) VALUES
 (1, 'Mid-Term Exam', '2026-10-12', 50), (2, 'Mid-Term Exam', '2026-10-13', 50),
 (3, 'Mid-Term Exam', '2026-10-14', 50), (4, 'Mid-Term Exam', '2026-10-15', 50),
 (5, 'Mid-Term Exam', '2026-10-16', 50), (6, 'Mid-Term Exam', '2026-10-17', 50),
 (7, 'Mid-Term Exam', '2026-10-19', 50), (8, 'Mid-Term Exam', '2026-10-20', 50),
 (9, 'Mid-Term Exam', '2026-10-21', 50), (10,'Mid-Term Exam', '2026-10-22', 50),
 (11,'Mid-Term Exam', '2026-10-13', 50),
 (1, 'Quiz 1', '2026-09-14', 20), (2, 'Quiz 1', '2026-09-15', 20),
 (3, 'Quiz 1', '2026-09-16', 20), (4, 'Quiz 1', '2026-09-17', 20);

-- Results: one row per exam for every non-dropped enrolment of that offering.
-- Marks come from a fixed formula (about 30 % - 94 % of the maximum, in steps of 0.5).
-- trg_validate_result checks the marks and fills grade + result_status automatically.
INSERT INTO results (exam_id, enrollment_id, marks_obtained)
SELECT ex.exam_id,
       e.enrollment_id,
       ROUND(ex.maximum_marks * (30 + ((e.enrollment_id * 37 + ex.exam_id * 11) % 65)) / 100.0 * 2) / 2
FROM examination ex
JOIN enrollment e ON e.offering_id = ex.offering_id
WHERE e.enrollment_status <> 'Dropped';

-- ---- UPDATE examples -------------------------------------------------
-- 1) Correct a student's phone number
UPDATE student SET phone = '9999900008' WHERE enrollment_number = 'KRM25BBA002';

-- 2) Give Section B of DBMS a larger capacity (sub-query finds the course_id from the course code)
UPDATE course_offering SET capacity = 70
WHERE course_id = (SELECT course_id FROM course WHERE course_code = 'CS202') AND section = 'B';

-- ---- DELETE example --------------------------------------------------
-- Add a temporary student, change them, then delete them (so sample data stays untouched).
INSERT INTO student (enrollment_number, first_name, last_name, email, gender, department_id, semester_id)
VALUES ('KRM25TMP999', 'Temp', 'Student', 'temp.student@student.unitrack.edu', 'Other', 1, 1);
UPDATE student SET status = 'Inactive' WHERE enrollment_number = 'KRM25TMP999';
DELETE FROM student WHERE enrollment_number = 'KRM25TMP999';

-- Quick row-count check. Expected: department 4, semester 2, faculty 8, course 11, student 16,
-- course_offering 11, enrollment 30, attendance 290, examination 15, results 42
SELECT 'department' AS tbl, COUNT(*) FROM department UNION ALL
SELECT 'semester', COUNT(*) FROM semester UNION ALL
SELECT 'faculty', COUNT(*) FROM faculty UNION ALL
SELECT 'course', COUNT(*) FROM course UNION ALL
SELECT 'student', COUNT(*) FROM student UNION ALL
SELECT 'course_offering', COUNT(*) FROM course_offering UNION ALL
SELECT 'enrollment', COUNT(*) FROM enrollment UNION ALL
SELECT 'attendance', COUNT(*) FROM attendance UNION ALL
SELECT 'examination', COUNT(*) FROM examination UNION ALL
SELECT 'results', COUNT(*) FROM results;


/* =====================================================================
   PART 4 : SQL QUERIES
   ===================================================================== */

-- Q1. SELECT, WHERE, ORDER BY, DISTINCT --------------------------------
-- Active Computer Science students, alphabetical
SELECT enrollment_number, first_name, last_name, email
FROM student
WHERE department_id = 1 AND status = 'Active'
ORDER BY first_name;

-- Distinct designations held by the faculty
SELECT DISTINCT designation FROM faculty ORDER BY designation;

-- Q2. Aggregate functions ----------------------------------------------
SELECT COUNT(*)                           AS total_results,
       SUM(marks_obtained)                AS total_marks,
       ROUND(AVG(marks_obtained), 2)      AS average_marks,
       MIN(marks_obtained)                AS lowest_marks,
       MAX(marks_obtained)                AS highest_marks
FROM results;

-- Q3. GROUP BY and HAVING ----------------------------------------------
-- Departments with more than 2 students
SELECT d.department_name, COUNT(s.student_id) AS student_count
FROM department d
JOIN student s ON s.department_id = d.department_id
GROUP BY d.department_name
HAVING COUNT(s.student_id) > 2
ORDER BY student_count DESC;

-- Q4. INNER JOIN -------------------------------------------------------
-- Students with their department and current semester
SELECT s.enrollment_number, s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
       d.department_name, sem.semester_number
FROM student s
INNER JOIN department d ON d.department_id = s.department_id
INNER JOIN semester sem ON sem.semester_id = s.semester_id
ORDER BY sem.semester_number, s.enrollment_number;

-- Q5. LEFT JOIN --------------------------------------------------------
-- All students, including those with no enrolment (student 16 appears with NULL)
SELECT s.enrollment_number, s.first_name, s.status, COUNT(en.enrollment_id) AS courses_enrolled
FROM student s
LEFT JOIN enrollment en ON en.student_id = s.student_id
GROUP BY s.student_id, s.enrollment_number, s.first_name, s.status
ORDER BY courses_enrolled, s.enrollment_number;

-- Q6. RIGHT JOIN -------------------------------------------------------
-- All courses, including ones never offered (CS401 appears with NULL offering)
SELECT c.course_code, c.course_name, o.offering_id, o.section
FROM course_offering o
RIGHT JOIN course c ON c.course_id = o.course_id
ORDER BY c.course_code;

-- Q7. SELF JOIN --------------------------------------------------------
-- Pairs of faculty colleagues in the same department
SELECT d.department_code, f1.faculty_name AS faculty_1, f2.faculty_name AS faculty_2
FROM faculty f1
JOIN faculty f2 ON f1.department_id = f2.department_id AND f1.faculty_id < f2.faculty_id
JOIN department d ON d.department_id = f1.department_id
ORDER BY d.department_code;

-- Q8. Multiple-table join (6 tables) -----------------------------------
-- Every examination result with student, course, faculty and exam
SELECT s.enrollment_number, s.first_name, c.course_code, f.faculty_name,
       ex.exam_name, r.marks_obtained, ex.maximum_marks, r.grade, r.result_status
FROM results r
JOIN examination ex      ON ex.exam_id      = r.exam_id
JOIN enrollment en       ON en.enrollment_id = r.enrollment_id
JOIN student s           ON s.student_id    = en.student_id
JOIN course_offering o   ON o.offering_id   = ex.offering_id
JOIN course c            ON c.course_id     = o.course_id
JOIN faculty f           ON f.faculty_id    = o.faculty_id
ORDER BY s.enrollment_number, c.course_code, ex.exam_name
LIMIT 20;

-- Q9. Nested (non-correlated) subquery ---------------------------------
-- Results scoring above the overall average percentage
SELECT s.first_name, c.course_code, ex.exam_name,
       ROUND(r.marks_obtained * 100 / ex.maximum_marks, 1) AS percentage
FROM results r
JOIN examination ex    ON ex.exam_id = r.exam_id
JOIN enrollment en     ON en.enrollment_id = r.enrollment_id
JOIN student s         ON s.student_id = en.student_id
JOIN course_offering o ON o.offering_id = ex.offering_id
JOIN course c          ON c.course_id = o.course_id
WHERE r.marks_obtained * 100 / ex.maximum_marks >
      (SELECT AVG(r2.marks_obtained * 100 / ex2.maximum_marks)
       FROM results r2 JOIN examination ex2 ON ex2.exam_id = r2.exam_id)
ORDER BY percentage DESC
LIMIT 10;

-- Q10. Correlated subquery ---------------------------------------------
-- Students who scored above the average of the SAME exam (inner query uses the outer row)
SELECT s.first_name, ex.exam_name, o.offering_id, r.marks_obtained
FROM results r
JOIN examination ex    ON ex.exam_id = r.exam_id
JOIN enrollment en     ON en.enrollment_id = r.enrollment_id
JOIN student s         ON s.student_id = en.student_id
JOIN course_offering o ON o.offering_id = ex.offering_id
WHERE r.marks_obtained > (SELECT AVG(r2.marks_obtained)
                          FROM results r2
                          WHERE r2.exam_id = r.exam_id)
ORDER BY o.offering_id, r.marks_obtained DESC
LIMIT 15;

-- Q11. UNION -----------------------------------------------------------
-- Students needing attention: failed at least one exam OR attendance below 75 %
SELECT student_id, 'Failed an exam' AS reason
FROM enrollment en JOIN results r ON r.enrollment_id = en.enrollment_id
WHERE r.result_status = 'Fail'
UNION
SELECT en.student_id, 'Low attendance'
FROM enrollment en JOIN attendance a ON a.enrollment_id = en.enrollment_id
GROUP BY en.student_id
HAVING 100.0 * COUNT(*) FILTER (WHERE a.attendance_status IN ('Present','Late')) / COUNT(*) < 75
ORDER BY student_id;

-- Q12. INTERSECT -------------------------------------------------------
-- Students who BOTH failed an exam AND have attendance below 75 %
SELECT en.student_id
FROM enrollment en JOIN results r ON r.enrollment_id = en.enrollment_id
WHERE r.result_status = 'Fail'
INTERSECT
SELECT en.student_id
FROM enrollment en JOIN attendance a ON a.enrollment_id = en.enrollment_id
GROUP BY en.student_id
HAVING 100.0 * COUNT(*) FILTER (WHERE a.attendance_status IN ('Present','Late')) / COUNT(*) < 75;

-- Q13. EXCEPT ----------------------------------------------------------
-- Students who are enrolled in some course but have never failed an exam
SELECT student_id FROM enrollment WHERE enrollment_status <> 'Dropped'
EXCEPT
SELECT en.student_id
FROM enrollment en JOIN results r ON r.enrollment_id = en.enrollment_id
WHERE r.result_status = 'Fail'
ORDER BY student_id;

-- (Q14 - UPDATE and DELETE - are in Part 3 and Part 6.)


/* =====================================================================
   PART 5 : ADVANCED SQL
   ===================================================================== */

-- ---------------------------------------------------------------------
-- 5.1  VIEW : student_academic_view  (one row per student)
-- Attendance counts 'Present' and 'Late' as attended.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW student_academic_view AS
WITH att AS (
    SELECT en.student_id,
           COUNT(*)                                                         AS total_classes,
           COUNT(*) FILTER (WHERE a.attendance_status IN ('Present','Late')) AS attended,
           ROUND(100.0 * COUNT(*) FILTER (WHERE a.attendance_status IN ('Present','Late'))
                 / COUNT(*), 2)                                             AS attendance_pct
    FROM enrollment en
    JOIN attendance a ON a.enrollment_id = en.enrollment_id
    GROUP BY en.student_id
),
perf AS (
    SELECT en.student_id,
           ROUND(AVG(r.marks_obtained * 100 / ex.maximum_marks), 2)  AS avg_percentage,
           COUNT(*) FILTER (WHERE r.result_status = 'Fail')           AS failed_exams
    FROM enrollment en
    JOIN results r      ON r.enrollment_id = en.enrollment_id
    JOIN examination ex ON ex.exam_id = r.exam_id
    GROUP BY en.student_id
),
crs AS (
    SELECT student_id, COUNT(*) AS courses_enrolled
    FROM enrollment WHERE enrollment_status <> 'Dropped'
    GROUP BY student_id
)
SELECT s.student_id,
       s.enrollment_number,
       s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
       d.department_id,
       d.department_name,
       sem.semester_number,
       s.status,
       COALESCE(crs.courses_enrolled, 0)  AS courses_enrolled,
       att.attendance_pct,
       perf.avg_percentage,
       COALESCE(perf.failed_exams, 0)     AS failed_exams
FROM student s
JOIN department d   ON d.department_id = s.department_id
JOIN semester sem   ON sem.semester_id = s.semester_id
LEFT JOIN att       ON att.student_id  = s.student_id
LEFT JOIN perf      ON perf.student_id = s.student_id
LEFT JOIN crs       ON crs.student_id  = s.student_id;

-- ---------------------------------------------------------------------
-- 5.2  VIEW : course_performance_view  (one row per course offering)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW course_performance_view AS
SELECT o.offering_id,
       c.course_code,
       c.course_name,
       o.section,
       f.faculty_name,
       sem.semester_number,
       COUNT(DISTINCT en.enrollment_id) FILTER (WHERE en.enrollment_status <> 'Dropped') AS students_enrolled,
       ROUND(AVG(r.marks_obtained * 100 / ex.maximum_marks), 2)                          AS avg_percentage,
       ROUND(MAX(r.marks_obtained * 100 / ex.maximum_marks), 2)                          AS highest_percentage,
       ROUND(MIN(r.marks_obtained * 100 / ex.maximum_marks), 2)                          AS lowest_percentage,
       COUNT(r.result_id) FILTER (WHERE r.result_status = 'Pass')                        AS passes,
       COUNT(r.result_id) FILTER (WHERE r.result_status = 'Fail')                        AS fails
FROM course_offering o
JOIN course c        ON c.course_id   = o.course_id
JOIN faculty f       ON f.faculty_id  = o.faculty_id
JOIN semester sem    ON sem.semester_id = o.semester_id
LEFT JOIN enrollment en ON en.offering_id = o.offering_id
LEFT JOIN examination ex ON ex.offering_id = o.offering_id
LEFT JOIN results r  ON r.exam_id = ex.exam_id AND r.enrollment_id = en.enrollment_id
GROUP BY o.offering_id, c.course_code, c.course_name, o.section, f.faculty_name, sem.semester_number;

SELECT * FROM student_academic_view ORDER BY avg_percentage DESC NULLS LAST;
SELECT * FROM course_performance_view ORDER BY offering_id;

-- ---------------------------------------------------------------------
-- 5.3  Window functions : student rankings (uses the view above)
-- ROW_NUMBER = unique position, RANK = ties share a rank and leave a gap,
-- DENSE_RANK = ties share a rank with no gap.
-- ---------------------------------------------------------------------
SELECT student_name,
       department_name,
       avg_percentage,
       ROW_NUMBER() OVER (ORDER BY avg_percentage DESC) AS row_num,
       RANK()       OVER (ORDER BY avg_percentage DESC) AS overall_rank,
       DENSE_RANK() OVER (ORDER BY avg_percentage DESC) AS overall_dense_rank
FROM student_academic_view
WHERE avg_percentage IS NOT NULL
ORDER BY overall_rank;

-- Department-wise ranking with PARTITION BY and AVG() OVER
SELECT department_name,
       student_name,
       avg_percentage,
       RANK() OVER (PARTITION BY department_id ORDER BY avg_percentage DESC) AS rank_in_department,
       ROUND(AVG(avg_percentage) OVER (PARTITION BY department_id), 2)       AS department_average,
       ROUND(avg_percentage - AVG(avg_percentage) OVER (PARTITION BY department_id), 2) AS diff_from_dept_avg
FROM student_academic_view
WHERE avg_percentage IS NOT NULL
ORDER BY department_name, rank_in_department;

-- ---------------------------------------------------------------------
-- 5.4  CTEs (WITH clauses)
-- ---------------------------------------------------------------------
-- (a) Attendance percentage per student, then keep those below 75 %
WITH attendance_summary AS (
    SELECT en.student_id,
           COUNT(*) AS total_classes,
           COUNT(*) FILTER (WHERE a.attendance_status IN ('Present','Late')) AS attended
    FROM enrollment en
    JOIN attendance a ON a.enrollment_id = en.enrollment_id
    GROUP BY en.student_id
),
attendance_pct AS (
    SELECT student_id, ROUND(100.0 * attended / total_classes, 2) AS pct
    FROM attendance_summary
)
SELECT s.enrollment_number, s.first_name, p.pct AS attendance_percentage
FROM attendance_pct p
JOIN student s ON s.student_id = p.student_id
WHERE p.pct < 75
ORDER BY p.pct;

-- (b) Course-wise average marks
WITH course_marks AS (
    SELECT c.course_code, c.course_name,
           r.marks_obtained * 100 / ex.maximum_marks AS pct
    FROM results r
    JOIN examination ex    ON ex.exam_id = r.exam_id
    JOIN course_offering o ON o.offering_id = ex.offering_id
    JOIN course c          ON c.course_id = o.course_id
)
SELECT course_code, course_name, ROUND(AVG(pct), 2) AS avg_percentage, COUNT(*) AS results_count
FROM course_marks
GROUP BY course_code, course_name
ORDER BY avg_percentage DESC;

-- ---------------------------------------------------------------------
-- 5.5  Indexes : why they help
-- Without an index PostgreSQL scans every row (sequential scan). A B-tree
-- index is a sorted structure, so an equality search needs only a few
-- page reads (O(log n)) instead of reading the whole table (O(n)). Joins on
-- foreign keys (student_id, enrollment_id...) benefit in the same way.
-- With only 16 students the planner may still choose a sequential scan
-- because the table is tiny; the benefit shows on large tables.
-- ---------------------------------------------------------------------
EXPLAIN SELECT * FROM student WHERE enrollment_number = 'KRM25CSE001';
EXPLAIN SELECT * FROM course  WHERE course_code = 'CS202';


/* =====================================================================
   PART 6 : TCL  (Transaction Control Language)
   Scenario: enrolling a student in courses. All steps succeed together or
   not at all.
   ===================================================================== */

-- 6.1 COMMIT : enrol Meera (student 11) in Operating Systems (offering 4)
BEGIN;
    INSERT INTO enrollment (student_id, offering_id) VALUES (11, 4);
    SELECT enrollment_id, student_id, offering_id, enrollment_status
    FROM enrollment WHERE student_id = 11;
COMMIT;                                   -- change is now permanent

-- 6.2 SAVEPOINT and ROLLBACK TO SAVEPOINT
BEGIN;
    INSERT INTO enrollment (student_id, offering_id) VALUES (12, 3);   -- Karan -> Networks (keep)
    SAVEPOINT after_first_enrollment;
    INSERT INTO enrollment (student_id, offering_id) VALUES (12, 8);   -- Karan -> Fluid Mechanics (mistake)
    ROLLBACK TO SAVEPOINT after_first_enrollment;                      -- undo only the mistake
COMMIT;                                   -- keeps the Networks enrolment only

-- 6.3 ROLLBACK : a whole transaction is cancelled
BEGIN;
    UPDATE student SET status = 'Graduated' WHERE enrollment_number = 'KRM24BBA001';
    SELECT enrollment_number, status FROM student WHERE enrollment_number = 'KRM24BBA001';   -- shows Graduated
ROLLBACK;                                 -- status goes back to Active
SELECT enrollment_number, status FROM student WHERE enrollment_number = 'KRM24BBA001';       -- shows Active


/* =====================================================================
   PART 7 : DCL  (Data Control Language)
   A read-only role for a report viewer / examiner.
   ===================================================================== */

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'unitrack_readonly') THEN
        CREATE ROLE unitrack_readonly NOLOGIN;      -- group role: no password stored in this file
    END IF;
END $$;

GRANT CONNECT ON DATABASE unitrack TO unitrack_readonly;
GRANT USAGE   ON SCHEMA public     TO unitrack_readonly;
GRANT SELECT  ON ALL TABLES IN SCHEMA public TO unitrack_readonly;   -- read everything...

REVOKE SELECT ON student FROM unitrack_readonly;                      -- ...except raw student data
GRANT  SELECT ON student_academic_view TO unitrack_readonly;          -- they use the summary view instead

-- To give a real person this access (choose your own password):
--   CREATE ROLE examiner LOGIN PASSWORD '<your-password>' IN ROLE unitrack_readonly;

-- Test as the read-only role: SELECT works, INSERT/DELETE would be denied.
SET ROLE unitrack_readonly;
SELECT COUNT(*) AS visible_faculty FROM faculty;
-- DELETE FROM faculty;     -- would fail: permission denied for table faculty
-- SELECT * FROM student;   -- would fail: permission denied for table student
RESET ROLE;


/* =====================================================================
   PART 8 : STORED PROCEDURE - enrol a student safely
   Checks: student exists and is Active, offering exists, not already
   enrolled, capacity not full. Raises a clear error otherwise.
   ===================================================================== */

CREATE OR REPLACE PROCEDURE sp_enroll_student(p_student_id INTEGER, p_offering_id INTEGER)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status    VARCHAR;
    v_capacity  INTEGER;
    v_enrolled  INTEGER;
BEGIN
    SELECT status INTO v_status FROM student WHERE student_id = p_student_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Student % does not exist', p_student_id;
    ELSIF v_status <> 'Active' THEN
        RAISE EXCEPTION 'Student % is % and cannot enrol', p_student_id, v_status;
    END IF;

    SELECT capacity INTO v_capacity FROM course_offering WHERE offering_id = p_offering_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Course offering % does not exist', p_offering_id;
    END IF;

    IF EXISTS (SELECT 1 FROM enrollment
               WHERE student_id = p_student_id AND offering_id = p_offering_id) THEN
        RAISE EXCEPTION 'Student % is already enrolled in offering %', p_student_id, p_offering_id;
    END IF;

    SELECT COUNT(*) INTO v_enrolled FROM enrollment
    WHERE offering_id = p_offering_id AND enrollment_status <> 'Dropped';
    IF v_enrolled >= v_capacity THEN
        RAISE EXCEPTION 'Offering % is full (% of % seats taken)', p_offering_id, v_enrolled, v_capacity;
    END IF;

    INSERT INTO enrollment (student_id, offering_id) VALUES (p_student_id, p_offering_id);
END;
$$;

-- Success: enrol Diya (student 9) in Marketing Management (offering 10)
CALL sp_enroll_student(9, 10);

-- Failure is caught here so the script keeps running; the rejection message appears
-- in pgAdmin's "Messages" tab. (Student 11 is already in offering 4 from Part 6.)
DO $$
BEGIN
    CALL sp_enroll_student(11, 4);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Enrolment rejected: %', SQLERRM;
END $$;

-- Trigger demo: marks above the maximum are rejected (message shown, script continues)
DO $$
BEGIN
    INSERT INTO results (exam_id, enrollment_id, marks_obtained) VALUES (12, 1, 99);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Result rejected: %', SQLERRM;
END $$;

-- ===================== END OF database.sql ==========================
