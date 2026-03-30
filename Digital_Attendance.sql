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
