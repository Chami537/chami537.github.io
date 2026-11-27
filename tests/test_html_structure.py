from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_index_html_has_closing_head_before_body():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    head_close = html.find('</head>')
    body_open = html.find('<body>')
    assert head_close != -1, 'index.html is missing </head>'
    assert body_open != -1, 'index.html is missing <body>'
    assert head_close < body_open, '</head> must appear before <body> in index.html'


def test_map_template_has_no_unclosed_script_tags():
    html = (ROOT / 'templates' / 'map.html').read_text(encoding='utf-8')
    opens = len(re.findall(r'<script\b', html))
    closes = len(re.findall(r'</script>', html))
    assert opens == closes, f'templates/map.html has {opens} <script> tags but {closes} </script> tags'
