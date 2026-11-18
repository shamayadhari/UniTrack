/* =====================================================================
   UniTrack - crud.sql
   CRUD (Create / Read / Update / Delete) examples for every table.
   Run AFTER database.sql.  Each block inserts a temporary row, reads it,
   updates it and deletes it again, so the sample data is left unchanged.
   These are the same statements the Flask app runs from crud.py.
   ===================================================================== */

-- ---------------------------------------------------------------- department
INSERT INTO department (department_name, department_code) VALUES ('Physics', 'PHY');            -- CREATE
SELECT * FROM department WHERE department_code = 'PHY';                                         -- READ
UPDATE department SET department_name = 'Applied Physics' WHERE department_code = 'PHY';       -- UPDATE
DELETE FROM department WHERE department_code = 'PHY';                                           -- DELETE

-- ---------------------------------------------------------------- student
INSERT INTO student (enrollment_number, first_name, last_name, email, gender, department_id, semester_id)
VALUES ('KRM26TMP001', 'Test', 'Student', 'test.student@student.unitrack.edu', 'Other', 1, 1);  -- CREATE
SELECT student_id, enrollment_number, first_name, status FROM student
WHERE enrollment_number = 'KRM26TMP001';                                                        -- READ
UPDATE student SET status = 'Inactive', phone = '9000000001'
WHERE enrollment_number = 'KRM26TMP001';                                                        -- UPDATE
DELETE FROM student WHERE enrollment_number = 'KRM26TMP001';                                    -- DELETE

-- ---------------------------------------------------------------- faculty
INSERT INTO faculty (faculty_name, email, designation, department_id)
VALUES ('Dr. Temp Faculty', 'temp.faculty@unitrack.edu', 'Lecturer', 1);                        -- CREATE
SELECT * FROM faculty WHERE email = 'temp.faculty@unitrack.edu';                                -- READ
UPDATE faculty SET designation = 'Assistant Professor' WHERE email = 'temp.faculty@unitrack.edu'; -- UPDATE
DELETE FROM faculty WHERE email = 'temp.faculty@unitrack.edu';                                  -- DELETE

-- ---------------------------------------------------------------- course
INSERT INTO course (course_code, course_name, credits, department_id)
VALUES ('CS999', 'Temporary Course', 3, 1);                                                     -- CREATE
SELECT * FROM course WHERE course_code = 'CS999';                                               -- READ
UPDATE course SET credits = 4 WHERE course_code = 'CS999';                                      -- UPDATE
DELETE FROM course WHERE course_code = 'CS999';                                                 -- DELETE

-- ---------------------------------------------------------------- enrollment
-- CREATE through the stored procedure so capacity / duplicate / active checks run
CALL sp_enroll_student(1, 3);                                    -- Aarav -> Computer Networks (offering 3)
SELECT * FROM enrollment WHERE student_id = 1 AND offering_id = 3;                              -- READ
UPDATE enrollment SET enrollment_status = 'Dropped' WHERE student_id = 1 AND offering_id = 3;   -- UPDATE
DELETE FROM enrollment WHERE student_id = 1 AND offering_id = 3;                                -- DELETE

-- ---------------------------------------------------------------- attendance
INSERT INTO attendance (enrollment_id, attendance_date, attendance_status)
VALUES (1, '2026-12-01', 'Present');                                                            -- CREATE
SELECT * FROM attendance WHERE enrollment_id = 1 AND attendance_date = '2026-12-01';            -- READ
UPDATE attendance SET attendance_status = 'Late'
WHERE enrollment_id = 1 AND attendance_date = '2026-12-01';                                     -- UPDATE
DELETE FROM attendance WHERE enrollment_id = 1 AND attendance_date = '2026-12-01';              -- DELETE

-- ---------------------------------------------------------------- results
-- A temporary exam is created first so the demo never clashes with existing sample results.
INSERT INTO examination (offering_id, exam_name, exam_date, maximum_marks)
VALUES (1, 'Practical Test', '2026-12-05', 25);                                                 -- CREATE exam
INSERT INTO results (exam_id, enrollment_id, marks_obtained)
SELECT exam_id, 1, 21 FROM examination WHERE offering_id = 1 AND exam_name = 'Practical Test';  -- CREATE result
SELECT r.*, ex.exam_name FROM results r JOIN examination ex ON ex.exam_id = r.exam_id
WHERE ex.exam_name = 'Practical Test';                                                          -- READ (grade filled by trigger)
UPDATE results SET marks_obtained = 12
WHERE exam_id = (SELECT exam_id FROM examination WHERE exam_name = 'Practical Test') AND enrollment_id = 1; -- UPDATE (trigger re-grades)
DELETE FROM examination WHERE exam_name = 'Practical Test' AND offering_id = 1;                 -- DELETE (results cascade)

-- ===================== END OF crud.sql =====================
