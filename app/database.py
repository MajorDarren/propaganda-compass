import sqlite3
import os

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_db_connection(db_path)
    
    # Articles table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            summary TEXT,
            viewpoint TEXT NOT NULL,
            published_at TEXT,
            topic_id TEXT,
            match_score REAL,
            time_diff_hours REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add missing columns (safe migrations)
    for col in ['match_score', 'time_diff_hours']:
        try:
            conn.execute(f"ALTER TABLE articles ADD COLUMN {col} REAL")
        except sqlite3.OperationalError:
            pass

    # Match history table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            west_source TEXT NOT NULL,
            east_source TEXT NOT NULL,
            score REAL NOT NULL,
            time_diff_hours REAL,
            matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()