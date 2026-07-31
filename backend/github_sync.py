"""GitHub metadata synchronization for work items."""

import json
import os
import urllib.request

from backend.data import DATA_DIR
from backend.repositories import repository_for


def _load_etags(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _update_stars(item, etags):
    repo = item.get('repo', '')
    if not repo:
        return False

    request = urllib.request.Request(f'https://api.github.com/repos/{repo}')
    request.add_header('Accept', 'application/vnd.github.v3+json')
    request.add_header('User-Agent', 'Chami-SSG/1.0')
    if repo in etags:
        request.add_header('If-None-Match', etags[repo])

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 304:
                return False
            if response.status != 200:
                print(f"  WARNING: GitHub API returned {response.status} for {repo}")
                return False
            stars = json.loads(response.read().decode()).get('stargazers_count', 0)
            etag = response.headers.get('ETag')
    except Exception as exc:
        print(f"  WARNING: failed to fetch stars for {repo}: {exc}")
        return False

    if etag:
        etags[repo] = etag
    if item.get('stars') == stars:
        return False
    item['stars'] = stars
    return True


def fetch_stars():
    """Fetch GitHub star counts with conditional requests and an ETag cache."""
    repository = repository_for('work.json')
    work = repository.list()
    etag_path = os.path.join(DATA_DIR, '_stars_etag.json')
    etags = _load_etags(etag_path)

    changed = [_update_stars(item, etags) for item in work]
    if any(changed):
        repository.save(work)
    etag_tmp = etag_path + '.tmp'
    with open(etag_tmp, 'w', encoding='utf-8') as f:
        json.dump(etags, f)
    os.replace(etag_tmp, etag_path)
