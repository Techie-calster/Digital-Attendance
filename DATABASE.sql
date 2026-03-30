-- ========================
-- 1. Students Table
-- ========================
CREATE TABLE Students (
    student_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    enrollment_no VARCHAR(50) UNIQUE,
    roll_no VARCHAR(20),
    year INT,
    branch VARCHAR(50),
    section VARCHAR(10),
    password VARCHAR(100) NOT NULL
);

-- ========================
-- 2. Faculty Table
-- ========================
CREATE TABLE Faculty (
    faculty_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    employee_id VARCHAR(50) UNIQUE,
    department VARCHAR(100),
    password VARCHAR(100) NOT NULL
);

-- ========================
-- 3. Subjects Table
-- ========================
CREATE TABLE Subjects (
    subject_id SERIAL PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL,
    faculty_id INT,
    FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id)
        ON DELETE SET NULL
);

-- ========================
-- 4. Student_Subject Table
-- ========================
CREATE TABLE Student_Subject (
    id SERIAL PRIMARY KEY,
    student_id INT,
    subject_id INT,
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES Subjects(subject_id) ON DELETE CASCADE,
    UNIQUE (student_id, subject_id)
);

-- ========================
-- 5. Attendance Table
-- ========================
CREATE TABLE Attendance (
    attendance_id SERIAL PRIMARY KEY,
    student_id INT,
    subject_id INT,
    date DATE,
    status VARCHAR(10) CHECK (status IN ('Present','Absent')),
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES Subjects(subject_id) ON DELETE CASCADE
);

-- ========================
-- 6. Marks Table
-- ========================
CREATE TABLE Marks (
    marks_id SERIAL PRIMARY KEY,
    student_id INT,
    subject_id INT,
    marks NUMERIC(5,2),
    FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES Subjects(subject_id) ON DELETE CASCADE,
    UNIQUE (student_id, subject_id)
);

INSERT INTO Faculty (faculty_id, name, employee_id, department, password) VALUES
(1, 'Dr. Amit Verma', 'EMP001', 'CSE', 'amit123'),
(2, 'Dr. Neha Sharma', 'EMP002', 'IT', 'neha123'),
(3, 'Dr. Rajesh Kumar', 'EMP003', 'Humanities', 'rajesh123'),
(4, 'Dr. Sunita Rao', 'EMP004', 'Sports', 'sunita123'),
(5, 'Dr. Vivek Singh', 'EMP005', 'Data Science', 'vivek123'),
(6, 'Dr. Anjali Mehta', 'EMP006', 'Architecture', 'anjali123');

INSERT INTO Subjects (subject_id, subject_name, faculty_id) VALUES
(1, 'Operating System', 1),
(2, 'Software Engineering', 2),
(3, 'Fundamentals of Data Analytics', 5),
(4, 'Computer System Architecture', 6),
(5, 'Sanskrit', 3),
(6, 'Sports for Life', 4);

INSERT INTO Attendance (student_id, subject_id, date, status)
SELECT 
    s.student_id,
    sub.subject_id,
    CURRENT_DATE - (g.day || ' days')::interval,
    CASE 
        WHEN RANDOM() > 0.25 THEN 'Present'
        ELSE 'Absent'
    END
FROM Students s
CROSS JOIN Subjects sub
CROSS JOIN generate_series(1, 10) AS g(day);

INSERT INTO Marks (student_id, subject_id, marks)
SELECT 
    s.student_id,
    sub.subject_id,
    ROUND((60 + RANDOM()*40)::numeric, 2)
FROM Students s
CROSS JOIN Subjects sub;

INSERT INTO Student_Subject (student_id, subject_id)
SELECT s.student_id, sub.subject_id
FROM Students s
CROSS JOIN Subjects sub;