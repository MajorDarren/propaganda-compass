import os
import json
import re
import uuid
import time
import socket
from datetime import datetime, timezone
import feedparser
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Set a global timeout for all socket operations (30 seconds)
socket.setdefaulttimeout(30)

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub('<.*?>', '', raw_html)
    return clean_text.strip()[:250] + "..." if len(clean_text) > 250 else clean_text.strip()

def parse_published(entry):
    """Convert feedparser's published_parsed to a timezone-aware datetime, or None."""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    return None

def match_articles(west_articles, east_articles, similarity_threshold=0.45, max_time_hours=6):
    """Match West and East articles with similarity and time proximity."""
    if not west_articles or not east_articles:
        return west_articles + east_articles

    print("Loading AI Embedding Model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    west_texts = [f"{a['title']}. {a['summary']}" for a in west_articles]
    east_texts = [f"{a['title']}. {a['summary']}" for a in east_articles]
    west_dts = [a.get('published_dt') for a in west_articles]
    east_dts = [a.get('published_dt') for a in east_articles]

    west_vecs = model.encode(west_texts)
    east_vecs = model.encode(east_texts)

    sim_matrix = cosine_similarity(west_vecs, east_vecs)

    candidates = []
    for w_idx, w_dt in enumerate(west_dts):
        for e_idx, e_dt in enumerate(east_dts):
            score = float(sim_matrix[w_idx][e_idx])
            if score < similarity_threshold:
                continue
            if w_dt is not None and e_dt is not None:
                delta = abs((w_dt - e_dt).total_seconds()) / 3600.0
                if delta > max_time_hours:
                    continue
            candidates.append((score, w_idx, e_idx))

    candidates.sort(key=lambda x: x[0], reverse=True)

    used_west = set()
    used_east = set()

    for score, w_idx, e_idx in candidates:
        if w_idx not in used_west and e_idx not in used_east:
            topic_id = f"match-{uuid.uuid4().hex[:8]}"
            west_articles[w_idx]['topic_id'] = topic_id
            west_articles[w_idx]['match_score'] = score
            east_articles[e_idx]['topic_id'] = topic_id
            east_articles[e_idx]['match_score'] = score
            used_west.add(w_idx)
            used_east.add(e_idx)
            delta_str = "N/A"
            if west_dts[w_idx] and east_dts[e_idx]:
                delta_h = abs((west_dts[w_idx] - east_dts[e_idx]).total_seconds()) / 3600.0
                delta_str = f"{delta_h:.1f}h"
            print(f"Matched ({score:.2f}, Δt={delta_str}): '{west_articles[w_idx]['title']}' <---> '{east_articles[e_idx]['title']}'")

    for w_idx, item in enumerate(west_articles):
        if w_idx not in used_west:
            item['topic_id'] = f"solo-w-{uuid.uuid4().hex[:8]}"
            item['match_score'] = None
    for e_idx, item in enumerate(east_articles):
        if e_idx not in used_east:
            item['topic_id'] = f"solo-e-{uuid.uuid4().hex[:8]}"
            item['match_score'] = None

    return west_articles + east_articles

def scrape_and_push():
    api_url = os.environ.get('API_URL')
    secret = os.environ.get('WEBHOOK_SECRET')

    if not api_url or not secret:
        print("Missing API_URL or WEBHOOK_SECRET environment variables.")
        return

    base_path = os.path.dirname(os.path.abspath(__file__))
    sources_path = os.path.join(base_path, 'sources.json')
    if not os.path.exists(sources_path):
        sources_path = os.path.join(os.path.dirname(base_path), 'sources.json')
    with open(sources_path, 'r') as f:
        sources = json.load(f)

    west_articles = []
    east_articles = []

    for viewpoint, feed_list in sources.items():
        for source in feed_list:
            print(f"Fetching [{viewpoint}] {source['name']}...")
            try:
                feed = feedparser.parse(source['rss'], request_headers={'User-Agent': 'Mozilla/5.0'})
                if feed.bozo:
                    print(f"⚠️ Failed to parse {source['name']}: {feed.bozo_exception}")
                    continue
            except Exception as e:
                print(f"❌ Error fetching {source['name']}: {e}")
                continue

            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                url = entry.get('link', '')
                summary = clean_html(entry.get('summary', entry.get('description', '')))
                published = entry.get('published', entry.get('updated', ''))
                published_dt = parse_published(entry)

                if title and url:
                    item = {
                        'title': title,
                        'url': url,
                        'source': source['name'],
                        'summary': summary,
                        'viewpoint': viewpoint,
                        'published_at': published,
                        'published_dt': published_dt,
                        'topic_id': None,
                        'match_score': None
                    }
                    if viewpoint == 'West':
                        west_articles.append(item)
                    else:
                        east_articles.append(item)

    all_articles = match_articles(west_articles, east_articles,
                                  similarity_threshold=0.45,
                                  max_time_hours=6)

    # Remove datetime object before sending JSON
    for article in all_articles:
        article.pop('published_dt', None)

    headers = {'X-Webhook-Secret': secret, 'Content-Type': 'application/json'}
    response = requests.post(api_url, json={'articles': all_articles}, headers=headers)
    print(f"Server Response ({response.status_code}): {response.text}")

if __name__ == '__main__':
    scrape_and_push()