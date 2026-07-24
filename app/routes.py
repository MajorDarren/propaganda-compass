from flask import Blueprint, render_template, request, jsonify, current_app
import sqlite3
from app.database import get_db_connection

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    conn = get_db_connection(current_app.config['DATABASE_PATH'])
    
    # 1. Fetch matched pairs (where both West & East exist for same topic_id)
    matched_rows = conn.execute('''
        SELECT 
            w.title as w_title, w.url as w_url, w.source as w_source, w.summary as w_summary,
            e.title as e_title, e.url as e_url, e.source as e_source, e.summary as e_summary
        FROM articles w
        JOIN articles e ON w.topic_id = e.topic_id
        WHERE w.viewpoint = 'West' AND e.viewpoint = 'East'
        ORDER BY w.id DESC LIMIT 15
    ''').fetchall()

    # 2. Fetch solo unmatched articles for each side
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
    return render_template('index.html', pairs=matched_rows, west_solos=west_solos, east_solos=east_solos)

@main_bp.route('/api/ingest', methods=['POST'])
def ingest():
    secret = request.headers.get('X-Webhook-Secret')
    if secret != current_app.config['WEBHOOK_SECRET']:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    articles = data.get('articles', [])
    
    conn = get_db_connection(current_app.config['DATABASE_PATH'])
    inserted_count = 0

    for item in articles:
        try:
            conn.execute('''
                INSERT INTO articles (title, url, source, summary, viewpoint, published_at, topic_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['title'], 
                item['url'], 
                item['source'], 
                item.get('summary', ''), 
                item['viewpoint'], 
                item.get('published_at', ''),
                item.get('topic_id', '')
            ))
            inserted_count += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'inserted': inserted_count}), 200