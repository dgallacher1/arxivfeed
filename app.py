from flask import Flask, render_template, jsonify, request
import feedparser
import json
import os
import re
from datetime import datetime

app = Flask(__name__)
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

ARXIV_FEEDS = {
    "physics.ins-det": "Instrumentation & Detectors",
    "hep-ex":          "HEP Experiment",
    "hep-ph":          "HEP Phenomenology",
    "nucl-ex":         "Nuclear Experiment",
    "physics.acc-ph":  "Accelerator Physics",
    "nucl-th":         "Nuclear Theory",
    "hep-th":          "HEP Theory",
    "astro-ph.IM":     "Astrophysics: Instrumentation",
    "astro-ph.HE":     "Astrophysics: High Energy",
    "quant-ph":        "Quantum Physics",
    "cond-mat.supr-con":"Superconductivity",
}

DEFAULT_CONFIG = {
    "keywords": "liquid xenon, SiPM, LGAD, low background && detector, gaseous detector, ASIC readout",
    "feeds": ["physics.ins-det", "hep-ex"]
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

def parse_keyword_rules(keyword_str):
    """
    Parse comma-separated keywords where && means AND within a group.
    "liquid xenon, sipms, low background && detectors"
    -> [["liquid xenon"], ["sipms"], ["low background", "detectors"]]
    Each inner list is an AND group; outer list is OR between groups.
    """
    rules = []
    for phrase in keyword_str.split(','):
        phrase = phrase.strip()
        if not phrase:
            continue
        and_terms = [t.strip().lower() for t in phrase.split('&&') if t.strip()]
        if and_terms:
            rules.append(and_terms)
    return rules

def matches_rules(text, rules):
    """Return True if text matches any OR group (all AND terms in that group present)."""
    text_lower = text.lower()
    for and_group in rules:
        if all(term in text_lower for term in and_group):
            return True
    return False

def fetch_and_filter(feed_ids, keyword_str):
    rules = parse_keyword_rules(keyword_str)
    results = []
    errors = []

    for fid in feed_ids:
        url = f"https://rss.arxiv.org/rss/{fid}"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                combined = f"{title} {summary}"
                if not rules or matches_rules(combined, rules):
                    # Find which rules matched
                    matched = []
                    for and_group in rules:
                        if all(t in combined.lower() for t in and_group):
                            matched.append(' && '.join(and_group))

                    link = entry.get('link', '')
                    arxiv_id = ''
                    id_match = re.search(r'(\d{4}\.\d{4,5})', link)
                    if id_match:
                        arxiv_id = id_match.group(1)

                    authors = []
                    if hasattr(entry, 'authors'):
                        authors = [a.get('name','') for a in entry.authors[:3]]
                    elif 'author' in entry:
                        authors = [entry.author]

                    results.append({
                        'title': title.replace('\n', ' ').strip(),
                        'summary': summary[:400].replace('\n', ' ').strip() + ('…' if len(summary) > 400 else ''),
                        'link': link,
                        'arxiv_id': arxiv_id,
                        'authors': authors,
                        'feed': fid,
                        'feed_label': ARXIV_FEEDS.get(fid, fid),
                        'matched': matched,
                        'published': entry.get('published', ''),
                    })
        except Exception as e:
            errors.append(f"{fid}: {str(e)}")

    # Deduplicate by arxiv_id
    seen = set()
    unique = []
    for r in results:
        key = r['arxiv_id'] or r['title']
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique, errors

@app.route('/')
def index():
    cfg = load_config()
    return render_template('index.html', feeds=ARXIV_FEEDS, config=cfg)

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@app.route('/api/config', methods=['POST'])
def set_config():
    cfg = request.json
    save_config(cfg)
    return jsonify({'ok': True})

@app.route('/api/fetch', methods=['POST'])
def fetch():
    data = request.json
    keyword_str = data.get('keywords', '')
    feed_ids = data.get('feeds', [])
    results, errors = fetch_and_filter(feed_ids, keyword_str)
    return jsonify({'results': results, 'errors': errors, 'count': len(results)})

if __name__ == '__main__':
    app.run(debug=True, port=5099)