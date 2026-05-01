import sqlite3

def get_connection():
    # SQLite WAL Mode: Prevents "Database Locked" errors on mobile
    conn = sqlite3.connect("fleet_log.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Persistent Garage Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            mpg REAL
        )
    ''')
    
    # Mission Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            vehicle_name TEXT,
            start_odo REAL,
            end_odo REAL,
            gap_category TEXT,
            deduction_type TEXT,
            reimbursement REAL DEFAULT 750,
            total_deduction REAL
        )
    ''')
    
    # Self-Healing: Check for missing columns (Schema Migration)
    try:
        cursor.execute("SELECT reimbursement FROM logs LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE logs ADD COLUMN reimbursement REAL DEFAULT 750")
        
    conn.commit()
    conn.close()