import sqlite3
import os

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_db_connection(db_path)
    
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
            match_score REAL,          -- new column
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # For existing databases, add match_score if missing
    try:
        conn.execute("ALTER TABLE articles ADD COLUMN match_score REAL")
    except sqlite3.OperationalError:
        pass  # already exists

    conn.commit()
    conn.close()