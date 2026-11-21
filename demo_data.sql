/* =====================================================================
   UniTrack v4 - SAFE DEMONSTRATION DATA
   Adds realistic records for the Admin, Dr. Anita Sharma (Faculty), and
   student account KRM24BBA001. Does NOT reset passwords or delete data.

   Run only after database.sql and schema_upgrade.sql have been applied.
   Safe to re-run: inserts are guarded against duplicate demo records.
   ===================================================================== */

BEGIN;

-- 1) Admin: notices visible to all three portals.
INSERT INTO announcement (title, body, audience, department_id, posted_by)
SELECT v.title, v.body, v.audience, NULL, 'admin'
FROM (VALUES
 ('Semester 3 Academic Updates',
  'Please review your course schedules and internal assessment updates. Contact your department office if any academic record needs correction.',
  'All'),
 ('Library and Digital Resources',
  'The central library and digital learning resources are available during university working hours. Please return issued material by the due date.',
  'Students'),
 ('Faculty Meeting and Assessment Review',
  'Faculty members are requested to review attendance and internal assessment records before the next departmental review meeting.',
  'Faculty')
) AS v(title, body, audience)
WHERE NOT EXISTS (
  SELECT 1 FROM announcement a
  WHERE a.title = v.title AND a.audience = v.audience AND a.posted_by = 'admin'
);

-- 2) Faculty: timetable entries for Dr. Anita Sharma's existing offerings.
-- One current-day class makes the faculty dashboard's "Today's classes" useful
-- during a live demo; two weekday slots populate the weekly timetable as well.
WITH target AS (
  SELECT f.faculty_id, o.offering_id, c.course_code,
         ROW_NUMBER() OVER (ORDER BY c.course_code, o.section) AS rn
  FROM faculty f
  JOIN course_offering o ON o.faculty_id = f.faculty_id
  JOIN course c ON c.course_id = o.course_id
  WHERE LOWER(f.email) = 'anita.sharma@unitrack.edu'
), slots AS (
  SELECT offering_id, (EXTRACT(ISODOW FROM CURRENT_DATE)::int) AS day_no,
         TIME '09:00', TIME '10:00', 'DEMO-101'::varchar(30)
  FROM target WHERE rn = 1
  UNION ALL
  SELECT offering_id, 1, TIME '11:00', TIME '12:00', 'CSE-204'::varchar(30)
  FROM target WHERE rn = 1
  UNION ALL
  SELECT offering_id, 3, TIME '10:00', TIME '11:00', 'CSE-205'::varchar(30)
  FROM target WHERE rn = 2
)
INSERT INTO timetable (offering_id, day_of_week, start_time, end_time, room)
SELECT s.offering_id, s.day_no, s.start_time, s.end_time, s.room
FROM slots s
WHERE NOT EXISTS (
  SELECT 1 FROM timetable t
  WHERE t.offering_id = s.offering_id
    AND t.day_of_week = s.day_no
    AND t.start_time = s.start_time
);

-- 3) Student: timetable entries for one enrolled course on the current day
-- and a weekday slot. These are sample/demo schedule records.
WITH target_student AS (
  SELECT s.student_id
  FROM student s
  WHERE s.enrollment_number = 'KRM24BBA001'
), target_offering AS (
  SELECT DISTINCT ON (o.offering_id) o.offering_id
  FROM target_student ts
  JOIN enrollment e ON e.student_id = ts.student_id
  JOIN course_offering o ON o.offering_id = e.offering_id
  WHERE e.enrollment_status = 'Enrolled'
  ORDER BY o.offering_id
  LIMIT 1
), slots AS (
  SELECT offering_id, EXTRACT(ISODOW FROM CURRENT_DATE)::int AS day_no,
         TIME '12:00' AS starts, TIME '13:00' AS ends, 'DEMO-202'::varchar(30) AS room
  FROM target_offering
)
INSERT INTO timetable (offering_id, day_of_week, start_time, end_time, room)
SELECT s.offering_id, s.day_no, s.starts, s.ends, s.room
FROM slots s
WHERE NOT EXISTS (
  SELECT 1 FROM timetable t
  WHERE t.offering_id = s.offering_id
    AND t.day_of_week = s.day_no
    AND t.start_time = s.starts
);

-- 4) Student: fee records (one paid + one pending) for the selected account.
INSERT INTO fee (student_id, title, amount, due_date, status, paid_on, receipt_no)
SELECT s.student_id, v.title, v.amount, v.due_date, v.status, v.paid_on, v.receipt_no
FROM student s
CROSS JOIN (VALUES
 ('Semester Tuition Fee - Demo', 18500.00::numeric, CURRENT_DATE - 20, 'Paid', CURRENT_DATE - 18, 'UT-DEMO-PAID-001'),
 ('Laboratory and Library Fee - Demo', 2500.00::numeric, CURRENT_DATE + 14, 'Pending', NULL::date, NULL::varchar(30))
) AS v(title, amount, due_date, status, paid_on, receipt_no)
WHERE s.enrollment_number = 'KRM24BBA001'
  AND NOT EXISTS (
    SELECT 1 FROM fee f WHERE f.student_id = s.student_id AND f.title = v.title
  );

-- 5) Student: one pending leave request for admin review.
INSERT INTO leave_request (student_id, from_date, to_date, reason, status)
SELECT s.student_id, CURRENT_DATE + 7, CURRENT_DATE + 8,
       'Request for leave due to a family commitment. Kindly review and approve.', 'Pending'
FROM student s
WHERE s.enrollment_number = 'KRM24BBA001'
  AND NOT EXISTS (
    SELECT 1 FROM leave_request l
    WHERE l.student_id = s.student_id AND l.reason LIKE 'Request for leave due to a family commitment%'
  );

-- 6) Student: one open support ticket for the admin support queue.
INSERT INTO support_ticket (student_id, subject, message, status)
SELECT s.student_id, 'Demo: Update contact details',
       'I would like to confirm the process for updating my contact details in the student profile.',
       'Open'
FROM student s
WHERE s.enrollment_number = 'KRM24BBA001'
  AND NOT EXISTS (
    SELECT 1 FROM support_ticket t
    WHERE t.student_id = s.student_id AND t.subject = 'Demo: Update contact details'
  );

-- 7) Faculty: one feedback record for an actual enrolled student in
-- Dr. Anita Sharma's course. This populates the faculty rating widget.
INSERT INTO feedback (enrollment_id, rating, comment)
SELECT e.enrollment_id, 5,
       'Clear explanations and helpful guidance during practical sessions.'
FROM faculty f
JOIN course_offering o ON o.faculty_id = f.faculty_id
JOIN enrollment e ON e.offering_id = o.offering_id
WHERE LOWER(f.email) = 'anita.sharma@unitrack.edu'
  AND e.enrollment_status <> 'Dropped'
  AND NOT EXISTS (SELECT 1 FROM feedback fb WHERE fb.enrollment_id = e.enrollment_id)
ORDER BY e.enrollment_id
LIMIT 1;

-- 8) Admin activity: add a clearly labelled demo audit entry.
INSERT INTO activity_log (actor, role, action, details)
SELECT 'admin', 'admin', 'Prepared demonstration records',
       'Sample notices, timetable, fee, leave, support and feedback records added for project presentation.'
WHERE NOT EXISTS (
  SELECT 1 FROM activity_log
  WHERE actor = 'admin' AND action = 'Prepared demonstration records'
    AND details LIKE 'Sample notices, timetable, fee, leave, support and feedback records%'
);

COMMIT;

-- Verification: check the selected student, faculty and demo record counts.
SELECT 'Selected student' AS item, s.enrollment_number AS details
FROM student s WHERE s.enrollment_number = 'KRM24BBA001'
UNION ALL
SELECT 'Selected faculty', f.email
FROM faculty f WHERE LOWER(f.email) = 'anita.sharma@unitrack.edu';

SELECT 'Announcements' AS item, COUNT(*) AS total FROM announcement WHERE posted_by = 'admin'
UNION ALL SELECT 'Timetable slots', COUNT(*) FROM timetable
UNION ALL SELECT 'Fees for demo student', COUNT(*) FROM fee f JOIN student s ON s.student_id = f.student_id WHERE s.enrollment_number = 'KRM24BBA001'
UNION ALL SELECT 'Leave requests for demo student', COUNT(*) FROM leave_request l JOIN student s ON s.student_id = l.student_id WHERE s.enrollment_number = 'KRM24BBA001'
UNION ALL SELECT 'Support tickets for demo student', COUNT(*) FROM support_ticket t JOIN student s ON s.student_id = t.student_id WHERE s.enrollment_number = 'KRM24BBA001'
UNION ALL SELECT 'Faculty feedback entries', COUNT(*) FROM feedback fb JOIN enrollment e ON e.enrollment_id = fb.enrollment_id JOIN course_offering o ON o.offering_id = e.offering_id JOIN faculty f ON f.faculty_id = o.faculty_id WHERE LOWER(f.email) = 'anita.sharma@unitrack.edu';
