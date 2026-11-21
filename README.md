
# UniTrack – Smart University Management and Academic Analytics System


**A Database-Driven University Management and Academic Analytics Platform**

Built as a Database Management Systems (DBMS) Capstone Project


---

## 1. Project Overview

UniTrack is a Smart University Management and Academic Analytics System designed to simplify and centralize academic and administrative operations within a university.

The platform provides a unified environment where administrators, faculty members, and students can access information and perform their respective academic and administrative activities through role-based dashboards.

Traditional university management often involves disconnected systems, manual record maintenance, repetitive administrative tasks, and difficulty accessing updated academic information. UniTrack addresses these challenges by integrating essential university operations into a centralized relational database system.

The application uses PostgreSQL for structured data management and a Flask-based backend to process application requests and interact with the database.

## 2. Problem Statement

Universities manage large volumes of information related to students, faculty, courses, attendance, examinations, results, fees, and academic activities.

Managing these records independently can lead to:

- Data redundancy and inconsistency.
- Difficulty maintaining and retrieving academic records.
- Time-consuming administrative processes.
- Limited communication between students, faculty, and administration.
- Lack of centralized academic information.
- Difficulty monitoring attendance, performance, and fee records.

UniTrack aims to provide an integrated database-driven solution that improves data organization, accessibility, consistency, and operational efficiency.

## 3. Project Objectives

The primary objectives of UniTrack are:

1. Develop a centralized university management platform.
2. Implement role-based access for administrators, faculty, and students.
3. Design and implement a relational database using PostgreSQL.
4. Manage student enrollment, courses, attendance, examinations, and results.
5. Provide administrative facilities for announcements, fees, and academic management.
6. Enable faculty members to manage academic information and interact with students.
7. Allow students to access their academic records and submit requests.
8. Apply DBMS concepts such as primary keys, foreign keys, constraints, joins, views, triggers, and stored procedures where implemented.
9. Present relevant academic information through dashboards and analytics.

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python, Flask |
| Database | PostgreSQL |
| Database Management Tool | pgAdmin 4 |
| Database Connectivity | psycopg2 |
| Templating Engine | Jinja2 |
| Data Visualization | Chart.js |
| Version Control | Git and GitHub |

## 5. System Architecture

UniTrack follows a layered architecture in which the frontend communicates with the Flask backend, and the backend interacts with the PostgreSQL database.

        USER
         |
         v
  FRONTEND INTERFACE
  HTML | CSS | JavaScript
         |
         v
    FLASK BACKEND
  Application Logic
  Authentication
  Role Management
         |
         v
  DATABASE CONNECTIVITY
       psycopg2
         |
         v
   POSTGRESQL DATABASE
         |
         v
  Structured Academic Data


### Architecture Components

**Frontend Layer**

Provides the user interface through which administrators, faculty members, and students interact with the system.

**Backend Layer**

Flask handles incoming requests, authentication, application logic, session management, and database operations.

**Database Layer**

PostgreSQL stores and manages structured university information using relational tables, relationships, constraints, and SQL queries.

## 6. User Roles and Functional Modules

UniTrack implements three primary user roles.

### 6.1 Administrator Dashboard

The administrator has access to centralized university management functionalities.

Key functionalities include:

- Dashboard overview and academic statistics.
- Student and faculty record management.
- Department and semester management.
- Course and course offering management.
- Announcement management.
- Timetable management.
- Fee record monitoring.
- Activity monitoring and administrative oversight.

### 6.2 Faculty Dashboard

The faculty dashboard provides academic management facilities.

Key functionalities include:

- Faculty profile and dashboard.
- Assigned course and timetable access.
- Student-related academic information.
- Attendance management.
- Examination and result-related academic operations.
- Faculty feedback access.

### 6.3 Student Dashboard

The student dashboard provides access to individual academic and administrative information.

Key functionalities include:

- Student profile and academic details.
- Course and enrollment information.
- Attendance records.
- Examination and result information.
- Timetable access.
- Fee status and payment records.
- Leave request submission and tracking.
- Support ticket submission.
- Announcements and notifications.

## 7. Database Design

PostgreSQL is used as the primary relational database management system.

The database is designed to organize university information into related tables, reducing unnecessary duplication and maintaining referential integrity.

### Core Database Tables

| Table | Purpose |
|---|---|
| `department` | Stores department information. |
| `semester` | Maintains semester-related details. |
| `student` | Stores student records. |
| `faculty` | Stores faculty information. |
| `course` | Maintains course details. |
| `course_offering` | Connects courses with academic offerings. |
| `enrollment` | Records student course enrollment. |
| `attendance` | Stores student attendance records. |
| `examination` | Maintains examination information. |
| `results` | Stores examination results. |

### Additional Functional Tables

| Table | Purpose |
|---|---|
| `announcement` | Stores university announcements. |
| `timetable` | Maintains course timetable slots. |
| `fee` | Stores student fee information. |
| `leave_request` | Maintains student leave requests. |
| `feedback` | Stores faculty feedback entries. |
| `support_ticket` | Manages student support requests. |
| `activity_log` | Maintains system activity records. |

*The final database structure should be verified against the SQL schema included in the repository.*

## 8. Database Relationships

The database follows a relational structure in which entities are connected through primary keys and foreign keys.

Major relationships include:

- A department can have multiple students and faculty members.
- A department can offer multiple courses.
- A course can have multiple course offerings.
- Students can enroll in multiple course offerings.
- Faculty members can be assigned to course offerings.
- Attendance records are associated with students and academic offerings.
- Examination records are associated with academic courses or offerings.
- Results connect students with their examination performance.
- Fee records, leave requests, and support tickets are associated with individual students.

These relationships help maintain consistency and allow information to be retrieved through relational queries.

## 9. DBMS Concepts Implemented

UniTrack demonstrates the practical application of core Database Management System concepts.

### 9.1 Relational Database Design

Data is organized into structured relational tables with defined attributes and relationships.

### 9.2 Primary Keys

Primary keys uniquely identify individual records within database tables.

### 9.3 Foreign Keys

Foreign keys establish relationships between tables and help maintain referential integrity.

### 9.4 Constraints

Database constraints help ensure data accuracy and validity.

Examples include:

- `PRIMARY KEY`
- `FOREIGN KEY`
- `NOT NULL`
- `UNIQUE`
- `CHECK`

### 9.5 SQL Operations

The application uses SQL operations for:

- `CREATE` – Creating database structures.
- `INSERT` – Adding records.
- `SELECT` – Retrieving information.
- `UPDATE` – Modifying existing records.
- `DELETE` – Removing records when required.

### 9.6 Joins

Joins combine related information from multiple tables.

Examples include retrieving student enrollment information, faculty course assignments, attendance records, and examination results.

### 9.7 Aggregate Functions

Aggregate functions such as `COUNT()`, `SUM()`, and `AVG()` can be used to calculate academic and administrative statistics.

### 9.8 Views

Views can be used to present frequently accessed information through reusable SQL queries.

### 9.9 Triggers and Stored Procedures

Where implemented in the database scripts, triggers and stored procedures support automated database operations and reusable database-side logic.

## 10. Dashboard and Academic Analytics

UniTrack provides dashboard-based access to relevant academic and administrative information.

The dashboard can present summarized information such as:

- Total students and faculty.
- Course and enrollment statistics.
- Attendance summaries.
- Academic performance information.
- Fee-related statistics.
- Administrative activity information.

Chart.js is used to display supported information through graphical representations, making the data easier to understand.

## 11. Authentication and Role-Based Access

The application provides separate dashboards for different user roles.

After authentication, users are directed to the appropriate dashboard according to their assigned role.

The role-based structure helps ensure that users access the functionalities relevant to their responsibilities.


## 13. Installation and Setup

### Prerequisites

Install the following software:

- Python 3.x
- PostgreSQL
- pgAdmin 4
- Git

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd UniTrack
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment.

**Windows:**

```bash
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Create the PostgreSQL Database

Open pgAdmin 4 and create a database named:

```sql
CREATE DATABASE unitrack;
```

### Step 5: Configure Database Connectivity

Update the database configuration in the application according to your local PostgreSQL credentials.

Ensure the database name, username, password, host, and port are correctly configured.

### Step 6: Execute Database Scripts

Open the Query Tool in pgAdmin and execute the SQL scripts in the required order:

1. `database.sql`
2. `schema_upgrade.sql`
3. `demo_data.sql` (optional, for demonstration records)

Ensure that the required tables and database objects are successfully created before running the application.

### Step 7: Run the Application

```bash
python app.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

## 14. Demo Data

The project includes a demonstration SQL script to populate selected modules with sample records.

The demo data covers:

- University announcements.
- Timetable slots.
- Student fee records.
- Student leave requests.
- Student support tickets.
- Faculty feedback entries.

These records help demonstrate the interaction between different modules and the underlying relational database.

## 15. Testing

The application can be evaluated through the following testing scenarios:

| Test Scenario | Expected Outcome |
|---|---|
| Administrator login | Administrator dashboard opens. |
| Faculty login | Faculty dashboard opens. |
| Student login | Student dashboard opens. |
| Announcement retrieval | Available announcements are displayed. |
| Timetable retrieval | Relevant timetable slots are displayed. |
| Fee retrieval | Student fee records are displayed. |
| Leave request | Student leave request is recorded. |
| Support ticket | Student support request is recorded. |
| Faculty feedback | Faculty feedback entries are accessible. |
| Database operations | Records are stored and retrieved through PostgreSQL. |

## 16. Advantages of UniTrack

- Centralized university information management.
- Structured relational database architecture.
- Role-based access to application modules.
- Reduced dependence on disconnected manual records.
- Improved accessibility of academic information.
- Better organization of administrative workflows.
- Support for academic monitoring and analytics.
- Scalable foundation for additional university services.

## 17. Future Scope

UniTrack can be extended with additional functionalities, including:

- Online fee payment integration.
- Automated email and SMS notifications.
- Advanced academic performance analytics.
- Examination scheduling and management.
- Document upload and verification.
- Mobile application integration.
- Advanced audit logging and reporting.
- Integration with university ERP systems.
- Cloud database deployment and production hosting.

## 18. Conclusion

UniTrack demonstrates how database management concepts can be applied to solve practical university administration and academic management challenges.

By combining Flask, PostgreSQL, and a role-based user interface, the system provides a centralized platform for managing academic and administrative information.

The project highlights the importance of relational database design, data integrity, SQL operations, and structured application development in building practical information management systems.

UniTrack serves as a foundation for a more integrated, accessible, and efficient university management environment.

---

## 19. Project Information

| Detail | Information |
|---|---|
| Project Name | UniTrack |
| Project Type | DBMS Capstone Project |
| Domain | University Management System |
| Backend | Python Flask |
| Database | PostgreSQL |
| Frontend | HTML, CSS, JavaScript |
| Database Tool | pgAdmin 4 |
| Academic Session | 2026–27 |

**Developed as part of the Database Management Systems Capstone Project.**


