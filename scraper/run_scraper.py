import os
import json
import re
import feedparser
import requests

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub('<.*?>', '', raw_html)
    return clean_text.strip()[:250] + "..." if len(clean_text) > 250 else clean_text.strip()

def scrape_and_push():
    api_url = os.environ.get('API_URL')
    secret = os.environ.get('WEBHOOK_SECRET')

    if not api_url or not secret:
        print("Missing API_URL or WEBHOOK_SECRET environment variables.")
        return

    base_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_path, 'sources.json'), 'r') as f:
        sources = json.load(f)

    payload_articles = []

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
                    payload_articles.append({
                        'title': title,
                        'url': url,
                        'source': source['name'],
                        'summary': summary,
                        'viewpoint': viewpoint,
                        'published_at': published
                    })

    headers = {'X-Webhook-Secret': secret, 'Content-Type': 'application/json'}
    response = requests.post(api_url, json={'articles': payload_articles}, headers=headers)
    print(f"Server Response ({response.status_code}): {response.text}")

if __name__ == '__main__':
    scrape_and_push()