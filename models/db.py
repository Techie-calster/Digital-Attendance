from __future__ import annotations

import os
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", str(BASE_DIR / "digital_attendance_runtime.db"))
)
USE_SHARED_MEMORY_DB = True
MEMORY_DATABASE_URI = "file:digital_attendance_runtime?mode=memory&cache=shared"
KEEPER_CONNECTION = None
DATABASE_READY = False

DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")

STUDENT_SEED_DATA = [
    ("Rahul Sharma", "ENR001", "R001", 1, "CSE", "A", "rahul123"),
    ("Amit Kumar", "ENR002", "R002", 2, "ECE", "B", "amit123"),
    ("Priya Singh", "ENR003", "R003", 1, "CSE", "A", "priya123"),
    ("Neha Gupta", "ENR004", "R004", 3, "IT", "C", "neha123"),
    ("Rohit Verma", "ENR005", "R005", 2, "ME", "B", "rohit123"),
    ("Anjali Mehta", "ENR006", "R006", 1, "CSE", "A", "anjali123"),
    ("Karan Patel", "ENR007", "R007", 4, "CSE", "D", "karan123"),
    ("Sneha Reddy", "ENR008", "R008", 2, "ECE", "B", "sneha123"),
    ("Vikas Sharma", "ENR009", "R009", 3, "IT", "C", "vikas123"),
    ("Pooja Verma", "ENR010", "R010", 1, "ME", "A", "pooja123"),
    ("Arjun Singh", "ENR011", "R011", 4, "CSE", "D", "arjun123"),
    ("Meera Joshi", "ENR012", "R012", 2, "IT", "B", "meera123"),
    ("Sahil Khan", "ENR013", "R013", 3, "ECE", "C", "sahil123"),
    ("Ritika Das", "ENR014", "R014", 1, "CSE", "A", "ritika123"),
    ("Deepak Yadav", "ENR015", "R015", 2, "ME", "B", "deepak123"),
]

FACULTY_SEED_DATA = [
    ("Dr. Amit Verma", "EMP001", "CSE", "amit123"),
    ("Dr. Neha Sharma", "EMP002", "IT", "neha123"),
    ("Dr. Rajesh Kumar", "EMP003", "Humanities", "rajesh123"),
    ("Dr. Sunita Rao", "EMP004", "Sports", "sunita123"),
    ("Dr. Vivek Singh", "EMP005", "Data Science", "vivek123"),
    ("Dr. Anjali Mehta", "EMP006", "Architecture", "anjali123"),
]

SUBJECT_SEED_DATA = [
    (1, "Operating System", 1),
    (2, "Software Engineering", 2),
    (3, "Fundamentals of Data Analytics", 5),
    (4, "Computer System Architecture", 6),
    (5, "Sanskrit", 3),
    (6, "Sports for Life", 4),
]

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    enrollment_no TEXT NOT NULL UNIQUE,
    roll_no TEXT,
    year INTEGER NOT NULL,
    branch TEXT NOT NULL,
    section TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS faculty (
    faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    employee_id TEXT NOT NULL UNIQUE,
    department TEXT,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subjects (
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name TEXT NOT NULL,
    faculty_id INTEGER,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS student_subject (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    UNIQUE (student_id, subject_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Present', 'Absent')),
    UNIQUE (student_id, subject_id, date),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS marks (
    marks_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    marks REAL NOT NULL,
    UNIQUE (student_id, subject_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rules (
    rule_id INTEGER PRIMARY KEY CHECK (rule_id = 1),
    eligibility_threshold INTEGER NOT NULL,
    warning_threshold INTEGER NOT NULL,
    high_threshold INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_users (
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    if USE_SHARED_MEMORY_DB:
        connection = sqlite3.connect(
            MEMORY_DATABASE_URI,
            uri=True,
            check_same_thread=False,
        )
    else:
        connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = MEMORY")
    connection.execute("PRAGMA temp_store = MEMORY")
    return connection


def _get_connection() -> sqlite3.Connection:
    global KEEPER_CONNECTION
    if USE_SHARED_MEMORY_DB:
        if KEEPER_CONNECTION is None:
            KEEPER_CONNECTION = _connect()
        return KEEPER_CONNECTION
    return _connect()


def _runtime_db_files() -> list[Path]:
    return [
        DATABASE_PATH,
        Path(f"{DATABASE_PATH}-journal"),
        Path(f"{DATABASE_PATH}-wal"),
        Path(f"{DATABASE_PATH}-shm"),
    ]


def _remove_runtime_database(include_main_db: bool = True) -> None:
    targets = _runtime_db_files() if include_main_db else _runtime_db_files()[1:]
    for path in targets:
        if path.exists():
            try:
                path.unlink()
            except PermissionError:
                continue


def _drop_all(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS attendance;
        DROP TABLE IF EXISTS marks;
        DROP TABLE IF EXISTS student_subject;
        DROP TABLE IF EXISTS subjects;
        DROP TABLE IF EXISTS faculty;
        DROP TABLE IF EXISTS students;
        DROP TABLE IF EXISTS rules;
        DROP TABLE IF EXISTS admin_users;
        """
    )


def _table_has_rows(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}").fetchone()
    return bool(row and row["row_count"])


def _seed_users(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT INTO students (name, enrollment_no, roll_no, year, branch, section, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                name,
                enrollment_no,
                roll_no,
                year,
                branch,
                section,
                generate_password_hash(password),
            )
            for name, enrollment_no, roll_no, year, branch, section, password in STUDENT_SEED_DATA
        ],
    )

    connection.executemany(
        """
        INSERT INTO faculty (name, employee_id, department, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        [
            (name, employee_id, department, generate_password_hash(password))
            for name, employee_id, department, password in FACULTY_SEED_DATA
        ],
    )

    connection.executemany(
        """
        INSERT INTO subjects (subject_id, subject_name, faculty_id)
        VALUES (?, ?, ?)
        """,
        SUBJECT_SEED_DATA,
    )

    student_ids = [row["student_id"] for row in connection.execute("SELECT student_id FROM students")]
    subject_ids = [row["subject_id"] for row in connection.execute("SELECT subject_id FROM subjects")]

    connection.executemany(
        "INSERT INTO student_subject (student_id, subject_id) VALUES (?, ?)",
        [(student_id, subject_id) for student_id in student_ids for subject_id in subject_ids],
    )


def _seed_attendance_and_marks(connection: sqlite3.Connection) -> None:
    generator = random.Random(2026)
    student_ids = [row["student_id"] for row in connection.execute("SELECT student_id FROM students")]
    subject_ids = [row["subject_id"] for row in connection.execute("SELECT subject_id FROM subjects")]
    base_day = date(2026, 2, 19)
    session_days = [base_day + timedelta(days=offset) for offset in range(10)]

    attendance_rows = []
    marks_rows = []
    for student_id in student_ids:
        for subject_id in subject_ids:
            for session_day in session_days:
                status = "Present" if generator.random() > 0.25 else "Absent"
                attendance_rows.append((student_id, subject_id, session_day.isoformat(), status))
            marks_rows.append((student_id, subject_id, round(60 + (generator.random() * 40), 2)))

    connection.executemany(
        """
        INSERT INTO attendance (student_id, subject_id, date, status)
        VALUES (?, ?, ?, ?)
        """,
        attendance_rows,
    )
    connection.executemany(
        """
        INSERT INTO marks (student_id, subject_id, marks)
        VALUES (?, ?, ?)
        """,
        marks_rows,
    )


def _seed_rules_and_admin(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO rules (rule_id, eligibility_threshold, warning_threshold, high_threshold)
        VALUES (1, 67, 75, 85)
        """
    )
    connection.execute(
        """
        INSERT INTO admin_users (username, display_name, password_hash)
        VALUES (?, ?, ?)
        """,
        (
            DEFAULT_ADMIN_USERNAME,
            "System Administrator",
            generate_password_hash(DEFAULT_ADMIN_PASSWORD),
        ),
    )


def initialize_database(force: bool = False, recovered: bool = False) -> None:
    global DATABASE_READY
    if USE_SHARED_MEMORY_DB and DATABASE_READY and not force:
        return

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = None
    try:
        if (
            not USE_SHARED_MEMORY_DB
            and not force
            and DATABASE_PATH.exists()
            and DATABASE_PATH.stat().st_size > 0
        ):
            connection = _connect()
            table_row = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'students'
                """
            ).fetchone()
            if table_row and _table_has_rows(connection, "students"):
                return
            connection.close()
            connection = None

        if force and not USE_SHARED_MEMORY_DB:
            _remove_runtime_database()

        connection = _get_connection()
        if force:
            _drop_all(connection)
        connection.executescript(SCHEMA)
        if _table_has_rows(connection, "students"):
            DATABASE_READY = True
            return
        _seed_users(connection)
        _seed_attendance_and_marks(connection)
        _seed_rules_and_admin(connection)
        connection.commit()
        DATABASE_READY = True
    except sqlite3.OperationalError as exc:
        if not recovered and (
            "disk i/o error" in str(exc).lower()
            or "database is locked" in str(exc).lower()
        ):
            if connection is not None and not USE_SHARED_MEMORY_DB:
                connection.close()
                connection = None
            if not USE_SHARED_MEMORY_DB:
                _remove_runtime_database(include_main_db=False)
            initialize_database(force=False, recovered=True)
            return
        raise
    finally:
        if connection is not None and not USE_SHARED_MEMORY_DB:
            connection.close()


def query_all(query: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    initialize_database()
    connection = _get_connection()
    try:
        rows = connection.execute(query, params or ()).fetchall()
        return [dict(row) for row in rows]
    finally:
        if not USE_SHARED_MEMORY_DB:
            connection.close()


def query_one(query: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    initialize_database()
    connection = _get_connection()
    try:
        row = connection.execute(query, params or ()).fetchone()
        return dict(row) if row else None
    finally:
        if not USE_SHARED_MEMORY_DB:
            connection.close()


def execute_write(query: str, params: Sequence[Any] | None = None) -> int:
    initialize_database()
    connection = _get_connection()
    try:
        cursor = connection.execute(query, params or ())
        connection.commit()
        return cursor.lastrowid
    finally:
        if not USE_SHARED_MEMORY_DB:
            connection.close()


def execute_many(query: str, rows: Iterable[Sequence[Any]]) -> int:
    initialize_database()
    connection = _get_connection()
    try:
        cursor = connection.executemany(query, list(rows))
        connection.commit()
        return cursor.rowcount
    finally:
        if not USE_SHARED_MEMORY_DB:
            connection.close()


def run_transaction(callback):
    initialize_database()
    connection = _get_connection()
    try:
        result = callback(connection)
        connection.commit()
        return result
    finally:
        if not USE_SHARED_MEMORY_DB:
            connection.close()


def make_password_hash(password: str) -> str:
    return generate_password_hash(password)


def check_password(password: str, password_hash: str | None) -> bool:
    return bool(password_hash) and check_password_hash(password_hash, password)


def get_rules() -> dict[str, int]:
    row = query_one(
        """
        SELECT eligibility_threshold, warning_threshold, high_threshold
        FROM rules
        WHERE rule_id = 1
        """
    )
    if row:
        return row
    return {
        "eligibility_threshold": 67,
        "warning_threshold": 75,
        "high_threshold": 85,
    }


def update_rules(eligibility_threshold: int, warning_threshold: int, high_threshold: int) -> None:
    execute_write(
        """
        UPDATE rules
        SET eligibility_threshold = ?, warning_threshold = ?, high_threshold = ?
        WHERE rule_id = 1
        """,
        (eligibility_threshold, warning_threshold, high_threshold),
    )


def reset_database() -> None:
    global DATABASE_READY, KEEPER_CONNECTION
    if USE_SHARED_MEMORY_DB and KEEPER_CONNECTION is not None:
        KEEPER_CONNECTION.close()
        KEEPER_CONNECTION = None
        DATABASE_READY = False
    initialize_database(force=True)
