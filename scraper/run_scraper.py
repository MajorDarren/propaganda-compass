import os
import json
import re
import uuid
import feedparser
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub('<.*?>', '', raw_html)
    return clean_text.strip()[:250] + "..." if len(clean_text) > 250 else clean_text.strip()

def match_articles(west_articles, east_articles, similarity_threshold=0.50):
    """Calculates cosine similarity between West and East headlines and tags matching pairs."""
    if not west_articles or not east_articles:
        return west_articles + east_articles

    print("Loading AI Embedding Model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    west_titles = [a['title'] for a in west_articles]
    east_titles = [a['title'] for a in east_articles]

    # Generate vector embeddings
    west_vecs = model.encode(west_titles)
    east_vecs = model.encode(east_titles)

    # Compute similarity matrix (West x East)
    sim_matrix = cosine_similarity(west_vecs, east_vecs)

    # Find candidate pairs above threshold
    candidate_pairs = []
    for w_idx in range(len(west_articles)):
        for e_idx in range(len(east_articles)):
            score = sim_matrix[w_idx][e_idx]
            if score >= similarity_threshold:
                candidate_pairs.append((score, w_idx, e_idx))

    # Sort candidate pairs highest score first (greedy matching)
    candidate_pairs.sort(key=lambda x: x[0], reverse=True)

    used_west = set()
    used_east = set()

    # Link best-matching pairs with a shared topic_id
    for score, w_idx, e_idx in candidate_pairs:
        if w_idx not in used_west and e_idx not in used_east:
            topic_id = f"match-{uuid.uuid4().hex[:8]}"
            west_articles[w_idx]['topic_id'] = topic_id
            east_articles[e_idx]['topic_id'] = topic_id
            used_west.add(w_idx)
            used_east.add(e_idx)
            print(f"Matched ({score:.2f}): '{west_titles[w_idx]}' <---> '{east_titles[e_idx]}'")

    # Assign solo topic_ids to unmatched articles
    for w_idx, item in enumerate(west_articles):
        if w_idx not in used_west:
            item['topic_id'] = f"solo-w-{uuid.uuid4().hex[:8]}"

    for e_idx, item in enumerate(east_articles):
        if e_idx not in used_east:
            item['topic_id'] = f"solo-e-{uuid.uuid4().hex[:8]}"

    return west_articles + east_articles

def scrape_and_push():
    api_url = os.environ.get('API_URL')
    secret = os.environ.get('WEBHOOK_SECRET')

    if not api_url or not secret:
        print("Missing API_URL or WEBHOOK_SECRET environment variables.")
        return

    base_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_path, 'sources.json'), 'r') as f:
        sources = json.load(f)

    west_articles = []
    east_articles = []

    for viewpoint, feed_list in sources.items():
        for source in feed_list:
            print(f"Fetching [{viewpoint}] {source['name']}...")
            feed = feedparser.parse(source['rss'])

            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                url = entry.get('link', '')
                summary = clean_html(entry.get('summary', entry.get('description', '')))
                published = entry.get('published', entry.get('updated', ''))

                if title and url:
                    item = {
                        'title': title,
                        'url': url,
                        'source': source['name'],
                        'summary': summary,
                        'viewpoint': viewpoint,
                        'published_at': published,
                        'topic_id': None
                    }
                    if viewpoint == 'West':
                        west_articles.append(item)
                    else:
                        east_articles.append(item)

    # Perform vector embedding matching
    all_articles = match_articles(west_articles, east_articles)

    headers = {'X-Webhook-Secret': secret, 'Content-Type': 'application/json'}
    response = requests.post(api_url, json={'articles': all_articles}, headers=headers)
    print(f"Server Response ({response.status_code}): {response.text}")

if __name__ == '__main__':
    scrape_and_push()