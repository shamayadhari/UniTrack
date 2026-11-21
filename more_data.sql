/* =====================================================================
   UniTrack - MORE SAMPLE DATA  (run AFTER database.sql)
   Adds faculty, students, a second section for every course, enrolments,
   attendance, exams and results, so every course/department has several
   students AND several faculty to demo the Department / Course filters.

   Safe to run twice: everything uses natural keys + ON CONFLICT DO NOTHING.
   Sign in as any new student with enrollment number + email, e.g.
   KRM25ECE003 / neel.joshi@student.unitrack.edu
   ===================================================================== */

-- 1) Faculty: 8 more (2 per department) ---------------------------------
INSERT INTO faculty (faculty_name, email, phone, designation, department_id)
SELECT v.name, v.email, v.phone, v.designation, d.department_id
FROM (VALUES
 ('Dr. Meenakshi Iyer',   'meenakshi.iyer@unitrack.edu',   '9810011009', 'Associate Professor', 'CSE'),
 ('Prof. Amit Saxena',    'amit.saxena@unitrack.edu',      '9810011010', 'Assistant Professor', 'CSE'),
 ('Dr. Ramesh Pillai',    'ramesh.pillai@unitrack.edu',    '9810011011', 'Professor',           'ECE'),
 ('Prof. Shalini Desai',  'shalini.desai@unitrack.edu',    '9810011012', 'Lecturer',            'ECE'),
 ('Dr. Harpreet Kaur',    'harpreet.kaur@unitrack.edu',    '9810011013', 'Professor',           'ME'),
 ('Prof. Nikhil Bhatt',   'nikhil.bhatt@unitrack.edu',     '9810011014', 'Assistant Professor', 'ME'),
 ('Dr. Sunita Choudhary', 'sunita.choudhary@unitrack.edu', '9810011015', 'Associate Professor', 'BBA'),
 ('Prof. Deepak Tandon',  'deepak.tandon@unitrack.edu',    '9810011016', 'Lecturer',            'BBA')
) AS v(name, email, phone, designation, dept)
JOIN department d ON d.department_code = v.dept
ON CONFLICT (email) DO NOTHING;

-- 2) Students: 20 more across all departments and both semesters ---------
INSERT INTO student (enrollment_number, first_name, last_name, email, phone, gender,
                     date_of_birth, admission_date, department_id, semester_id, status)
SELECT v.enr, v.fn, v.ln, v.email, v.phone, v.gender, v.dob::date,
       CASE WHEN v.sem = 3 THEN DATE '2025-08-04' ELSE DATE '2024-08-05' END,
       d.department_id, sem.semester_id, 'Active'
FROM (VALUES
 -- CSE, semester 3
 ('KRM25CSE004','Aditya','Mishra',   'aditya.mishra@student.unitrack.edu',  '9876500017','Male',  '2006-02-11','CSE',3),
 ('KRM25CSE005','Riya',  'Agarwal',  'riya.agarwal@student.unitrack.edu',   '9876500018','Female','2006-06-19','CSE',3),
 ('KRM25CSE006','Harsh', 'Pandey',   'harsh.pandey@student.unitrack.edu',   '9876500019','Male',  '2005-12-08','CSE',3),
 -- CSE, semester 5
 ('KRM24CSE004','Nisha', 'Tiwari',   'nisha.tiwari@student.unitrack.edu',   '9876500020','Female','2005-05-27','CSE',5),
 ('KRM24CSE005','Yash',  'Bhardwaj', 'yash.bhardwaj@student.unitrack.edu',  '9876500021','Male',  '2005-09-02','CSE',5),
 -- ECE, semester 3 (Digital Electronics gets plenty of students)
 ('KRM25ECE003','Neel',  'Joshi',    'neel.joshi@student.unitrack.edu',     '9876500022','Male',  '2006-04-15','ECE',3),
 ('KRM25ECE004','Pooja', 'Menon',    'pooja.menon@student.unitrack.edu',    '9876500023','Female','2006-08-23','ECE',3),
 ('KRM25ECE005','Varun', 'Chopra',   'varun.chopra@student.unitrack.edu',   '9876500024','Male',  '2005-10-30','ECE',3),
 ('KRM25ECE006','Simran','Kaur',     'simran.kaur@student.unitrack.edu',    '9876500025','Female','2006-01-09','ECE',3),
 -- ECE, semester 5
 ('KRM24ECE003','Aman',  'Dubey',    'aman.dubey@student.unitrack.edu',     '9876500026','Male',  '2005-03-12','ECE',5),
 ('KRM24ECE004','Kritika','Sinha',   'kritika.sinha@student.unitrack.edu',  '9876500027','Female','2005-07-25','ECE',5),
 -- ME, semester 3
 ('KRM25ME002', 'Dev',   'Rathore',  'dev.rathore@student.unitrack.edu',    '9876500028','Male',  '2006-03-03','ME',3),
 ('KRM25ME003', 'Rahul', 'Sethi',    'rahul.sethi@student.unitrack.edu',    '9876500029','Male',  '2005-11-16','ME',3),
 ('KRM25ME004', 'Aisha', 'Khan',     'aisha.khan@student.unitrack.edu',     '9876500030','Female','2006-09-05','ME',3),
 -- ME, semester 5
 ('KRM24ME002', 'Lakshay','Grover',  'lakshay.grover@student.unitrack.edu', '9876500031','Male',  '2005-01-28','ME',5),
 ('KRM24ME003', 'Bhavna','Solanki',  'bhavna.solanki@student.unitrack.edu', '9876500032','Female','2005-06-14','ME',5),
 -- BBA, semester 3
 ('KRM25BBA003','Tushar','Goyal',    'tushar.goyal@student.unitrack.edu',   '9876500033','Male',  '2006-02-20','BBA',3),
 ('KRM25BBA004','Mansi', 'Bajaj',    'mansi.bajaj@student.unitrack.edu',    '9876500034','Female','2006-05-31','BBA',3),
 -- BBA, semester 5
 ('KRM24BBA003','Ritvik','Anand',    'ritvik.anand@student.unitrack.edu',   '9876500035','Male',  '2005-08-08','BBA',5),
 ('KRM24BBA004','Jiya',  'Kohli',    'jiya.kohli@student.unitrack.edu',     '9876500036','Female','2005-12-21','BBA',5)
) AS v(enr, fn, ln, email, phone, gender, dob, dept, sem)
JOIN department d   ON d.department_code = v.dept
JOIN semester   sem ON sem.semester_number = v.sem AND sem.academic_year = '2026-27'
ON CONFLICT (enrollment_number) DO NOTHING;

-- 3) A section B for every course that only had section A, each with a
--    different (new) faculty member, so courses now have 2 teachers ------
INSERT INTO course_offering (course_id, faculty_id, semester_id, section, capacity)
SELECT c.course_id, f.faculty_id, sem.semester_id, 'B', 40
FROM (VALUES
 ('CS201','meenakshi.iyer@unitrack.edu',   3),
 ('CS301','amit.saxena@unitrack.edu',      5),
 ('CS302','meenakshi.iyer@unitrack.edu',   5),
 ('EC201','ramesh.pillai@unitrack.edu',    3),
 ('EC301','shalini.desai@unitrack.edu',    5),
 ('ME201','harpreet.kaur@unitrack.edu',    3),
 ('ME301','nikhil.bhatt@unitrack.edu',     5),
 ('BA201','sunita.choudhary@unitrack.edu', 3),
 ('BA301','deepak.tandon@unitrack.edu',    5)
) AS v(course_code, faculty_email, sem_no)
JOIN course  c   ON c.course_code = v.course_code
JOIN faculty f   ON f.email = v.faculty_email
JOIN semester sem ON sem.semester_number = v.sem_no AND sem.academic_year = '2026-27'
ON CONFLICT (course_id, semester_id, section) DO NOTHING;

-- 4) Enrol every new student (anyone with no enrolment yet) in all the
--    courses of their department + semester. Odd student ids take section
--    B, even ids section A, so both sections fill up. -------------------
INSERT INTO enrollment (student_id, offering_id, enrollment_date, enrollment_status)
SELECT s.student_id, o.offering_id, DATE '2026-07-29' + (s.student_id % 3), 'Enrolled'
FROM student s
JOIN course c           ON c.department_id = s.department_id
JOIN course_offering o  ON o.course_id = c.course_id
                       AND o.semester_id = s.semester_id
                       AND o.section = CASE WHEN s.student_id % 2 = 0 THEN 'A' ELSE 'B' END
WHERE s.status = 'Active'
  AND NOT EXISTS (SELECT 1 FROM enrollment e WHERE e.student_id = s.student_id)
ON CONFLICT (student_id, offering_id) DO NOTHING;

-- 5) Attendance for the new enrolments (same formula as database.sql) ----
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
WHERE e.enrollment_status <> 'Dropped'
  AND NOT EXISTS (SELECT 1 FROM attendance a WHERE a.enrollment_id = e.enrollment_id)
ON CONFLICT (enrollment_id, attendance_date) DO NOTHING;

-- 6) Exams: a Mid-Term for the new sections, and an upcoming End-Term for
--    every offering (so students' "Upcoming exams" card has content) ------
INSERT INTO examination (offering_id, exam_name, exam_date, maximum_marks)
SELECT o.offering_id, 'Mid-Term Exam', DATE '2026-10-12' + (o.offering_id % 9), 50
FROM course_offering o
ON CONFLICT (offering_id, exam_name) DO NOTHING;

INSERT INTO examination (offering_id, exam_name, exam_date, maximum_marks)
SELECT o.offering_id, 'End-Term Exam', DATE '2026-12-02' + (o.offering_id % 12), 100
FROM course_offering o
ON CONFLICT (offering_id, exam_name) DO NOTHING;

-- 7) Results for Mid-Term / Quiz of the new enrolments (End-Term is still
--    upcoming, so it gets no results). The trigger fills grade + status. --
INSERT INTO results (exam_id, enrollment_id, marks_obtained)
SELECT ex.exam_id, e.enrollment_id,
       ROUND(ex.maximum_marks * (30 + ((e.enrollment_id * 37 + ex.exam_id * 11) % 65)) / 100.0 * 2) / 2
FROM examination ex
JOIN enrollment e ON e.offering_id = ex.offering_id
WHERE e.enrollment_status <> 'Dropped'
  AND ex.exam_name <> 'End-Term Exam'
  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.exam_id = ex.exam_id AND r.enrollment_id = e.enrollment_id)
ON CONFLICT (exam_id, enrollment_id) DO NOTHING;

-- Quick check: students and faculty per course
SELECT c.course_code, c.course_name,
       COUNT(DISTINCT en.student_id) AS students,
       COUNT(DISTINCT o.faculty_id)  AS faculty
FROM course c
LEFT JOIN course_offering o ON o.course_id = c.course_id
LEFT JOIN enrollment en     ON en.offering_id = o.offering_id AND en.enrollment_status <> 'Dropped'
GROUP BY c.course_code, c.course_name ORDER BY c.course_code;
