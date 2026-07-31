"""Public essay sampling for personal writing-style context."""

import base64

from backend.writing_style import (
    MAX_SAMPLE_CHARS,
    MAX_STYLE_ESSAYS,
    MAX_TOTAL_CHARS,
    load_style_reference,
)


def _write(tmp_path, slug, content):
    (tmp_path / f'{slug}.md').write_text(content, encoding='utf-8')


def test_load_style_reference_selects_recent_safe_samples(tmp_path):
    essays = [
        {'slug': 'current', 'title': 'Current', 'date': '2026-07-31'},
        {'slug': 'protected', 'title': 'Protected', 'date': '2026-07-30'},
        {'slug': 'public-old', 'title': 'Old', 'date': '2026-07-01'},
        {'slug': 'public-new', 'title': 'New', 'date': '2026-07-29'},
    ]
    for slug in ('current', 'protected', 'public-old', 'public-new'):
        _write(tmp_path, slug, f'{slug} content')

    result = load_style_reference(
        'current',
        metadata_loader=lambda _name: essays,
        password_checker=lambda slug: slug == 'protected',
        md_dir=tmp_path,
    )

    assert [sample['title'] for sample in result['samples']] == ['New', 'Old']
    assert result['count'] == 2


def test_load_style_reference_sanitizes_markdown_noise(tmp_path):
    _write(
        tmp_path,
        'sample',
        '---\ntitle: Hidden metadata\n---\n\n'
        '# 保留标题\n\n保留段落。\n\n'
        '```python\nprint("drop")\n```\n\n'
        '![drop](image.jpg)\nhttps://example.com/only-url\n\n'
        '> 保留引用\n\n- 保留列表\n',
    )

    result = load_style_reference(
        'current',
        metadata_loader=lambda _name: [
            {'slug': 'sample', 'title': 'Sample', 'date': '2026-07-01'},
        ],
        password_checker=lambda _slug: False,
        md_dir=tmp_path,
    )

    content = result['samples'][0]['content']
    assert '# 保留标题' in content
    assert '保留段落。' in content
    assert '> 保留引用' in content
    assert '- 保留列表' in content
    for removed in ('Hidden metadata', 'print("drop")', 'image.jpg', 'https://example.com'):
        assert removed not in content


def test_load_style_reference_skips_encrypted_missing_and_invalid_entries(tmp_path):
    encrypted = base64.b64encode(b'\x02' + b'0' * 17).decode('ascii')
    _write(tmp_path, 'encrypted', encrypted)
    _write(tmp_path, 'valid', '公开正文')
    essays = [
        None,
        {'slug': '../escape', 'title': 'Invalid', 'date': '2026-07-04'},
        {'slug': 'missing', 'title': 'Missing', 'date': '2026-07-03'},
        {'slug': 'encrypted', 'title': 'Encrypted', 'date': '2026-07-02'},
        {'slug': 'valid', 'title': 'Valid', 'date': 'not-a-date'},
    ]

    result = load_style_reference(
        'current',
        metadata_loader=lambda _name: essays,
        password_checker=lambda _slug: False,
        md_dir=tmp_path,
    )

    assert result == {
        'samples': [{'title': 'Valid', 'content': '公开正文'}],
        'count': 1,
    }


def test_load_style_reference_enforces_count_and_character_budgets(tmp_path):
    essays = []
    for index in range(8):
        slug = f'sample-{index}'
        essays.append({'slug': slug, 'title': slug, 'date': f'2026-07-{20 - index:02d}'})
        _write(tmp_path, slug, str(index) * (MAX_SAMPLE_CHARS + 200))

    result = load_style_reference(
        'current',
        metadata_loader=lambda _name: essays,
        password_checker=lambda _slug: False,
        md_dir=tmp_path,
    )

    assert result['count'] == MAX_STYLE_ESSAYS
    assert all(len(sample['content']) <= MAX_SAMPLE_CHARS for sample in result['samples'])
    assert sum(len(sample['content']) for sample in result['samples']) <= MAX_TOTAL_CHARS


def test_load_style_reference_degrades_when_metadata_cannot_load(tmp_path):
    def broken_loader(_name):
        raise OSError('unavailable')

    assert load_style_reference(
        'current',
        metadata_loader=broken_loader,
        password_checker=lambda _slug: False,
        md_dir=tmp_path,
    ) == {'samples': [], 'count': 0}
