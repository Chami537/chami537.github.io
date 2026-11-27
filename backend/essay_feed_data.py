"""Shared Essay data shaping for RSS and sitemap feeds."""

from datetime import datetime
from backend.essay_service import is_essay_visible, public_essay_metadata


def strip_enrich(essays, date_key, date_fmt, limit=None):
    """Project public metadata, newest first, before limiting a feed."""
    essays = sorted(
        (essay for essay in essays if is_essay_visible(essay)),
        key=lambda essay: essay.get('date', ''), reverse=True,
    )
    enriched = []
    for essay in essays[:limit] if limit else essays:
        item = public_essay_metadata(essay)
        item[date_key] = ''
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                item[date_key] = datetime.strptime(essay.get('date', ''), fmt).strftime(date_fmt)
                break
            except ValueError:
                continue
        enriched.append(item)
    return enriched
