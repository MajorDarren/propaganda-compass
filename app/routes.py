from flask import Blueprint, render_template, request, jsonify, current_app
import sqlite3
from datetime import datetime
from app.database import get_db_connection

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    conn = get_db_connection(current_app.config['DATABASE_PATH'])
    
    # Fetch matched pairs, sorted by match_score descending
    matched_rows = conn.execute('''
        SELECT 
            w.title as w_title, w.url as w_url, w.source as w_source, w.summary as w_summary, 
            w.match_score as w_score, w.time_diff_hours as w_time_diff,
            e.title as e_title, e.url as e_url, e.source as e_source, e.summary as e_summary,
            e.match_score as e_score, e.time_diff_hours as e_time_diff
        FROM articles w
        JOIN articles e ON w.topic_id = e.topic_id
        WHERE w.viewpoint = 'West' AND e.viewpoint = 'East'
        ORDER BY w.match_score DESC
        LIMIT 15
    ''').fetchall()

    # Get last updated timestamp (max created_at from all articles)
    last_updated_row = conn.execute('SELECT MAX(created_at) as last_updated FROM articles').fetchone()
    last_updated_raw = last_updated_row['last_updated'] if last_updated_row else None
    
    # Convert string to datetime object for template formatting
    last_updated = None
    if last_updated_raw:
        try:
            # SQLite returns ISO format string: 'YYYY-MM-DD HH:MM:SS'
            last_updated = datetime.fromisoformat(last_updated_raw)
        except (ValueError, TypeError):
            # Fallback: keep as string if parsing fails
            last_updated = last_updated_raw

    # Solo articles
    west_solos = conn.execute('''
        SELECT * FROM articles 
        WHERE viewpoint = 'West' 
        AND topic_id NOT IN (SELECT topic_id FROM articles WHERE viewpoint = 'East')
        ORDER BY id DESC LIMIT 10
    ''').fetchall()

    east_solos = conn.execute('''
        SELECT * FROM articles 
        WHERE viewpoint = 'East' 
        AND topic_id NOT IN (SELECT topic_id FROM articles WHERE viewpoint = 'West')
        ORDER BY id DESC LIMIT 10
    ''').fetchall()

    conn.close()
    return render_template('index.html', 
                           pairs=matched_rows, 
                           west_solos=west_solos, 
                           east_solos=east_solos,
                           last_updated=last_updated)

@main_bp.route('/api/ingest', methods=['POST'])
def ingest():
    secret = request.headers.get('X-Webhook-Secret')
    if secret != current_app.config['WEBHOOK_SECRET']:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    articles = data.get('articles', [])
    
    conn = get_db_connection(current_app.config['DATABASE_PATH'])
    conn.execute('DELETE FROM articles;')
    
    inserted_count = 0
    for item in articles:
        try:
            conn.execute('''
                INSERT INTO articles (title, url, source, summary, viewpoint, published_at, topic_id, match_score, time_diff_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['title'],
                item['url'],
                item['source'],
                item.get('summary', ''),
                item['viewpoint'],
                item.get('published_at', ''),
                item.get('topic_id', ''),
                item.get('match_score'),
                item.get('time_diff_hours')
            ))
            inserted_count += 1
        except Exception as e:
            print(f"Error inserting article: {e}")

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'inserted': inserted_count}), 200