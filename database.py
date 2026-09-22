import sqlite3

DB_NAME = "attendance.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # کاربران
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)

    # گروه‌ها
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY,
            group_name TEXT NOT NULL,
            attendance_topic_id INTEGER,
            entry_time TEXT DEFAULT '08:00',
            exit_time TEXT DEFAULT '17:00',
            late_entry_fine INTEGER DEFAULT 50,
            early_exit_fine INTEGER DEFAULT 50
        )
    """)

    # حضور و غیاب
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            entry_time TEXT,
            exit_time TEXT,
            entry_fine INTEGER DEFAULT 0,
            exit_fine INTEGER DEFAULT 0,

            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (group_id) REFERENCES groups(group_id)
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# کاربران
# ==========================================

def add_user(user_id, name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (user_id, name)
        VALUES (?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET name = excluded.name
    """, (user_id, name))

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, name, status
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()

    conn.close()
    return result


# ==========================================
# گروه‌ها
# ==========================================

def add_group(group_id, group_name, topic_id=205):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO groups (
            group_id,
            group_name,
            attendance_topic_id
        )
        VALUES (?, ?, ?)
        ON CONFLICT(group_id)
        DO UPDATE SET
            group_name = excluded.group_name,
            attendance_topic_id = excluded.attendance_topic_id
    """, (
        group_id,
        group_name,
        topic_id
    ))

    conn.commit()
    conn.close()


def get_group(group_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            group_id,
            group_name,
            attendance_topic_id,
            entry_time,
            exit_time,
            late_entry_fine,
            early_exit_fine
        FROM groups
        WHERE group_id = ?
    """, (group_id,))

    result = cursor.fetchone()

    conn.close()
    return result


# ==========================================
# حضور و غیاب
# ==========================================

def get_today_attendance(user_id, group_id, date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            user_id,
            group_id,
            date,
            entry_time,
            exit_time,
            entry_fine,
            exit_fine
        FROM attendance
        WHERE user_id = ?
        AND group_id = ?
        AND date = ?
        LIMIT 1
    """, (
        user_id,
        group_id,
        date
    ))

    result = cursor.fetchone()

    conn.close()
    return result


def create_today_attendance(
    user_id,
    group_id,
    date,
    entry_time,
    entry_fine
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO attendance (
            user_id,
            group_id,
            date,
            entry_time,
            entry_fine
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        group_id,
        date,
        entry_time,
        entry_fine
    ))

    conn.commit()
    conn.close()


def update_exit(
    attendance_id,
    exit_time,
    exit_fine
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE attendance
        SET
            exit_time = ?,
            exit_fine = ?
        WHERE id = ?
    """, (
        exit_time,
        exit_fine,
        attendance_id
    ))

    conn.commit()
    conn.close()

def update_group_settings(
    group_id,
    entry_time=None,
    exit_time=None,
    late_entry_fine=None,
    early_exit_fine=None
):
    conn = get_connection()
    cursor = conn.cursor()

    group = get_group(group_id)

    if not group:
        conn.close()
        return False

    current_entry_time = group[3]
    current_exit_time = group[4]
    current_late_fine = group[5]
    current_early_fine = group[6]

    cursor.execute("""
        UPDATE groups
        SET
            entry_time = ?,
            exit_time = ?,
            late_entry_fine = ?,
            early_exit_fine = ?
        WHERE group_id = ?
    """, (
        entry_time if entry_time is not None else current_entry_time,
        exit_time if exit_time is not None else current_exit_time,
        late_entry_fine if late_entry_fine is not None else current_late_fine,
        early_exit_fine if early_exit_fine is not None else current_early_fine,
        group_id
    ))

    conn.commit()
    conn.close()

    return True

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, name, status
        FROM users
        ORDER BY name
    """)

    result = cursor.fetchall()

    conn.close()
    return result


def get_daily_report(group_id, date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            users.name,
            attendance.entry_time,
            attendance.exit_time,
            attendance.entry_fine,
            attendance.exit_fine
        FROM attendance
        INNER JOIN users
            ON attendance.user_id = users.user_id
        WHERE attendance.group_id = ?
        AND attendance.date = ?
        ORDER BY attendance.id
    """, (
        group_id,
        date
    ))

    result = cursor.fetchall()

    conn.close()
    return result

def get_monthly_user_report(user_id, group_id, year, month):
    conn = get_connection()
    cursor = conn.cursor()

    prefix = f"{year:04d}-{month:02d}-%"

    cursor.execute("""
        SELECT
            COUNT(*),
            SUM(CASE WHEN entry_fine > 0 THEN 1 ELSE 0 END),
            SUM(CASE WHEN exit_fine > 0 THEN 1 ELSE 0 END),
            COALESCE(SUM(entry_fine), 0),
            COALESCE(SUM(exit_fine), 0)
        FROM attendance
        WHERE user_id = ?
        AND group_id = ?
        AND date LIKE ?
    """, (
        user_id,
        group_id,
        prefix
    ))

    result = cursor.fetchone()

    conn.close()
    return result