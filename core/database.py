import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'simployee.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Tabla de usuarios
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de progreso del usuario en un path
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_path_id TEXT NOT NULL,
            current_week INTEGER DEFAULT 1,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Tabla de tareas generadas
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            deliverable TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            submission TEXT,
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

def create_user(username, password, full_name):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO users (username, password, full_name) VALUES (?, ?, ?)',
            (username, password, full_name)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_progress(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM user_progress WHERE user_id = ?', (user_id,))
    progress = c.fetchone()
    conn.close()
    return progress

def create_user_progress(user_id, job_path_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'INSERT INTO user_progress (user_id, job_path_id) VALUES (?, ?)',
        (user_id, job_path_id)
    )
    conn.commit()
    conn.close()

def get_tasks(user_id, week):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM tasks WHERE user_id = ? AND week = ?',
        (user_id, week)
    )
    tasks = c.fetchall()
    conn.close()
    return tasks

def save_task(user_id, week, title, description, deliverable):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'INSERT INTO tasks (user_id, week, title, description, deliverable) VALUES (?, ?, ?, ?, ?)',
        (user_id, week, title, description, deliverable)
    )
    conn.commit()
    conn.close()

def submit_task(task_id, submission):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'UPDATE tasks SET submission = ?, status = ? WHERE id = ?',
        (submission, 'submitted', task_id)
    )
    conn.commit()
    conn.close()

def save_feedback(task_id, feedback):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'UPDATE tasks SET feedback = ?, status = ? WHERE id = ?',
        (feedback, 'reviewed', task_id)
    )
    conn.commit()
    conn.close()

def advance_week(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'UPDATE user_progress SET current_week = current_week + 1 WHERE user_id = ?',
        (user_id,)
    )
    conn.commit()
    conn.close()

def resubmit_task(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        'UPDATE tasks SET status = ?, submission = NULL, feedback = NULL WHERE id = ?',
        ('pending', task_id)
    )
    conn.commit()
    conn.close()