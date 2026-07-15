"""GitHub metadata synchronization for work items."""

import json
import os
import urllib.request

from backend.data import DATA_DIR
from backend.repositories import repository_for


def fetch_stars():
    """Fetch GitHub star counts with conditional requests and an ETag cache."""
    repository = repository_for('work.json')
    work = repository.list()
    etag_path = os.path.join(DATA_DIR, '_stars_etag.json')
    etags = {}
    if os.path.exists(etag_path):
        try:
            with open(etag_path, 'r', encoding='utf-8') as f:
                etags = json.load(f)
        except (json.JSONDecodeError, ValueError):
            etags = {}

    updated = False
    for item in work:
        repo = item.get('repo', '')
        if not repo:
            continue
        req = urllib.request.Request(f'https://api.github.com/repos/{repo}')
        req.add_header('Accept', 'application/vnd.github.v3+json')
        req.add_header('User-Agent', 'Chami-SSG/1.0')
        if etags.get(repo):
            req.add_header('If-None-Match', etags[repo])
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 304:
                    continue
                if resp.status != 200:
                    print(f"  WARNING: GitHub API returned {resp.status} for {repo}")
                    continue
                stars = json.loads(resp.read().decode()).get('stargazers_count', 0)
                if item.get('stars') != stars:
                    item['stars'] = stars
                    updated = True
                if resp.headers.get('ETag'):
                    etags[repo] = resp.headers['ETag']
        except Exception as exc:
            print(f"  WARNING: failed to fetch stars for {repo}: {exc}")

    if updated:
        repository.save(work)
    etag_tmp = etag_path + '.tmp'
    with open(etag_tmp, 'w', encoding='utf-8') as f:
        json.dump(etags, f)
    os.replace(etag_tmp, etag_path)
