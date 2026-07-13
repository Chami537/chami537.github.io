"""Shared Essay data shaping for RSS and sitemap feeds."""

from datetime import datetime


def strip_enrich(essays, date_key, date_fmt, limit=None):
    """Remove passwords and format publication dates for a feed."""
    enriched = []
    for essay in essays[:limit] if limit else essays:
        item = {k: v for k, v in essay.items() if k != 'password'}
        item[date_key] = ''
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                item[date_key] = datetime.strptime(essay.get('date', ''), fmt).strftime(date_fmt)
                break
            except ValueError:
                continue
        enriched.append(item)
    return enriched
