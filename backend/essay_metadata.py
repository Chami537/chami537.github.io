"""Persistence policy for essay metadata shipped with the static site."""


ESSAY_BODY_FIELDS = frozenset({
    'body', 'content', 'markdown', 'raw_md', 'body_html', 'html',
})


def without_essay_body(essay):
    """Keep metadata only; the Markdown/RAW_MD source owns the essay body.

    Apply this to public essays too, so protecting one later cannot leave a
    plaintext copy behind. This policy needs no local passwords during builds.
    """
    return {key: value for key, value in essay.items() if key not in ESSAY_BODY_FIELDS}
