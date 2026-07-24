from flask import Blueprint, render_template, request, jsonify, current_app
import sqlite3
from app.database import get_db_connection

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    conn = get_db_connection(current_app.config['DATABASE_PATH'])
    
    west_articles = conn.execute(
        "SELECT * FROM articles WHERE viewpoint = 'West' ORDER BY id DESC LIMIT 20"
    ).fetchall()
    
    east_articles = conn.execute(
        "SELECT * FROM articles WHERE viewpoint = 'East' ORDER BY id DESC LIMIT 20"
    ).fetchall()
    
    conn.close()
    return render_template('index.html', west=west_articles, east=east_articles)

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
                INSERT INTO articles (title, url, source, summary, viewpoint, published_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                item['title'], 
                item['url'], 
                item['source'], 
                item.get('summary', ''), 
                item['viewpoint'], 
                item.get('published_at', '')
            ))
            inserted_count += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'inserted': inserted_count}), 200