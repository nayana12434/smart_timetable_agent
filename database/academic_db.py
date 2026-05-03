import sqlite3

DB_PATH = "database/tasks.db"

def init_academic_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            credits INTEGER,
            professor TEXT
        )
    ''')

    # Schedule table (lectures, labs, tutorials)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS class_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            class_type TEXT,
            day_of_week TEXT,
            start_time TEXT,
            end_time TEXT,
            room TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    # Exams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            exam_type TEXT,
            exam_date TEXT,
            start_time TEXT,
            room TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    conn.commit()
    conn.close()

def add_course(name, code, credits, professor):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO courses (name, code, credits, professor) VALUES (?, ?, ?, ?)",
        (name, code, credits, professor)
    )
    conn.commit()
    conn.close()

def get_all_courses():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()
    conn.close()
    return courses

def add_class_schedule(course_id, class_type, day, start_time, end_time, room):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO class_schedule (course_id, class_type, day_of_week, start_time, end_time, room) VALUES (?, ?, ?, ?, ?, ?)",
        (course_id, class_type, day, start_time, end_time, room)
    )
    conn.commit()
    conn.close()

def get_schedule_by_day(day):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.name, cs.class_type, cs.start_time, cs.end_time, cs.room
        FROM class_schedule cs
        JOIN courses c ON cs.course_id = c.id
        WHERE cs.day_of_week = ?
        ORDER BY cs.start_time
    ''', (day,))
    schedule = cursor.fetchall()
    conn.close()
    return schedule

def add_exam(course_id, exam_type, exam_date, start_time, room):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO exams (course_id, exam_type, exam_date, start_time, room) VALUES (?, ?, ?, ?, ?)",
        (course_id, exam_type, exam_date, start_time, room)
    )
    conn.commit()
    conn.close()

def get_upcoming_exams():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.name, e.exam_type, e.exam_date, e.start_time, e.room
        FROM exams e
        JOIN courses c ON e.course_id = c.id
        ORDER BY e.exam_date
    ''')
    exams = cursor.fetchall()
    conn.close()
    return exams