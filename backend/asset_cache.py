"""Content fingerprints shared by templates and generated HTML entry points."""

import hashlib
import os
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.file_utils import atomic_write_text


_ASSET_REFERENCE_RE = re.compile(
    r'(?P<prefix>\b(?:href|src|data-lazy-src)\s*=\s*)'
    r'(?P<quote>["\'])'
    r'(?P<url>(?:/|\.\./)?assets/(?:css|js)/[^"\']+)'
    r'(?P=quote)',
)
_TEMPLATE_ASSET_RE = re.compile(r'asset_url\(["\']([^"\']+)["\']\)')


def asset_path(base_dir, url):
    """Resolve only this site's local CSS/JS URLs under its asset directory."""
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    relative = parsed.path.removeprefix('../').lstrip('/')
    if not relative.startswith(('assets/css/', 'assets/js/')):
        return None
    root = Path(base_dir).resolve() / 'assets'
    path = (Path(base_dir) / relative).resolve()
    return path if path.is_relative_to(root) else None


def asset_fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def asset_url(url, base_dir):
    """Keep URL spelling/other parameters; replace v with a content hash."""
    path = asset_path(base_dir, url)
    if path is None or not path.is_file():
        return url
    parsed = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != 'v']
    query.append(('v', asset_fingerprint(path)))
    return urlunsplit(parsed._replace(query=urlencode(query)))


def version_asset_references(html, base_dir):
    def replace(match):
        return (f"{match.group('prefix')}{match.group('quote')}"
                f"{asset_url(match.group('url'), base_dir)}{match.group('quote')}")
    # RAW_MD comments are source snapshots and must remain byte-for-byte intact.
    return ''.join(part if part.startswith('<!--') else _ASSET_REFERENCE_RE.sub(replace, part)
                   for part in re.split(r'(<!--[\s\S]*?-->)', html))


def referenced_asset_paths(source, base_dir):
    """Read literal HTML and Jinja asset_url references for build dependencies."""
    urls = [match.group('url') for match in _ASSET_REFERENCE_RE.finditer(source)]
    urls.extend(_TEMPLATE_ASSET_RE.findall(source))
    return sorted({str(path) for url in urls
                   if (path := asset_path(base_dir, url)) is not None and path.is_file()})


def cache_bust_assets(base_dir):
    """Fingerprint entry pages and every generated essay, writing only changes."""
    root = Path(base_dir)
    pages = [root / name for name in ('index.html', 'admin.html', 'shelf.html')]
    pages.extend(sorted((root / 'essays').glob('*.html')))
    for page in pages:
        if not page.is_file():
            continue
        html = page.read_text(encoding='utf-8')
        updated = version_asset_references(html, base_dir)
        if updated != html:
            atomic_write_text(os.fspath(page), updated)
