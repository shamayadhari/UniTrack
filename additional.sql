
-- 1. SEMESTER-WISE STUDENT RANKING

WITH semester_performance AS (
    SELECT
        s.student_id,
        s.enrollment_number,
        s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
        sem.semester_number,
        sem.academic_year,

        ROUND(
            AVG(
                r.marks_obtained * 100.0 / ex.maximum_marks
            ), 2
        ) AS avg_percentage

    FROM student s
    JOIN enrollment en
        ON s.student_id = en.student_id
    JOIN course_offering co
        ON en.offering_id = co.offering_id
    JOIN semester sem
        ON co.semester_id = sem.semester_id
    JOIN examination ex
        ON co.offering_id = ex.offering_id
    JOIN results r
        ON r.exam_id = ex.exam_id
        AND r.enrollment_id = en.enrollment_id

    WHERE en.enrollment_status <> 'Dropped'

    GROUP BY
        s.student_id,
        s.enrollment_number,
        s.first_name,
        s.last_name,
        sem.semester_id,
        
        sem.semester_number,
        sem.academic_year
)

SELECT
    student_name,
    enrollment_number,
    semester_number,
    academic_year,
    avg_percentage,

    RANK() OVER (
        PARTITION BY semester_number, academic_year
        ORDER BY avg_percentage DESC
    ) AS semester_rank

FROM semester_performance
ORDER BY semester_number, semester_rank;


-- 2. SEMESTER TOPPER IDENTIFICATION

WITH semester_performance AS (
    SELECT
        s.student_id,
        s.enrollment_number,
        s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
        sem.semester_number,
        sem.academic_year,

        ROUND(
            AVG(
                r.marks_obtained * 100.0 / ex.maximum_marks
            ), 2
        ) AS avg_percentage

    FROM student s
    JOIN enrollment en
        ON s.student_id = en.student_id
    JOIN course_offering co
        ON en.offering_id = co.offering_id
    JOIN semester sem
        ON co.semester_id = sem.semester_id
    JOIN examination ex
        ON co.offering_id = ex.offering_id
    JOIN results r
        ON r.exam_id = ex.exam_id
        AND r.enrollment_id = en.enrollment_id

    WHERE en.enrollment_status <> 'Dropped'

    GROUP BY
        s.student_id,
        s.enrollment_number,
        s.first_name,
        s.last_name,
        sem.semester_id,
        sem.semester_number,
        sem.academic_year
),

ranked_students AS (
    SELECT *,
        RANK() OVER (
            PARTITION BY semester_number, academic_year
            ORDER BY avg_percentage DESC
        ) AS student_rank

    FROM semester_performance
)

SELECT
    student_name,
    enrollment_number,
    semester_number,
    academic_year,
    avg_percentage,
    student_rank

FROM ranked_students
WHERE student_rank = 1
ORDER BY semester_number;


-- 3. STUDENT ACADEMIC PROGRESSION

WITH semester_performance AS (
    SELECT
        s.student_id,
        s.enrollment_number,
        s.first_name || ' ' || COALESCE(s.last_name, '') AS student_name,
        sem.semester_number,
        sem.academic_year,

        ROUND(
            AVG(
                r.marks_obtained * 100.0 / ex.maximum_marks
            ), 2
        ) AS avg_percentage

    FROM student s
    JOIN enrollment en
        ON s.student_id = en.student_id
    JOIN course_offering co
        ON en.offering_id = co.offering_id
    JOIN semester sem
        ON co.semester_id = sem.semester_id
    JOIN examination ex
        ON co.offering_id = ex.offering_id
    JOIN results r
        ON r.exam_id = ex.exam_id
        AND r.enrollment_id = en.enrollment_id

    WHERE en.enrollment_status <> 'Dropped'

    GROUP BY
        s.student_id,
        s.enrollment_number,
        s.first_name,
        s.last_name,
        sem.semester_id,
        sem.semester_number,
        sem.academic_year
),

progression AS (
    SELECT
        *,
        LAG(avg_percentage) OVER (
            PARTITION BY student_id
            ORDER BY academic_year, semester_number
        ) AS previous_semester_percentage

    FROM semester_performance
)

SELECT
    student_name,
    semester_number,
    academic_year,
    avg_percentage,
    previous_semester_percentage,

    CASE
        WHEN previous_semester_percentage IS NULL
            THEN 'First recorded semester'
        WHEN avg_percentage > previous_semester_percentage
            THEN 'Improved'
        WHEN avg_percentage < previous_semester_percentage
            THEN 'Declined'
        ELSE 'No change'
    END AS performance_trend

FROM progression
ORDER BY student_id, academic_year, semester_number;
