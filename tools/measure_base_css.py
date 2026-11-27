"""Read-only C7 measurement: in-memory pages, local Chromium, no SSG writes.

Usage: ~/projects/pw-venv/bin/python tools/measure_base_css.py --output /artifact/dir
Requires an existing Chromium headless shell; installs nothing.
External scripts/fonts are blocked. Font output describes computed CSS requests,
not font downloads or the physical font used for each glyph.
"""

import argparse
import gzip
import html
import json
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Response, request
from werkzeug.serving import make_server
from backend.app import app
from backend.essay_crypto import is_encrypted_content
from backend.essay_renderer import render_essay_html
from backend.markdown_utils import render_markdown
from backend.ssg import _env, _parse_date, _prepare_archive_data, _prepare_map_data

ROOT = Path(__file__).resolve().parents[1]
MEASURE = r"""<script>
window.addEventListener('load', function() { setTimeout(function() {
  var groups = {}, weights = new Set();
  document.querySelectorAll('body *').forEach(function(el) {
    if (/^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName) || !el.getClientRects().length) return;
    var text = Array.from(el.childNodes).filter(function(n) {return n.nodeType === 3;})
      .map(function(n) {return n.textContent;}).join('').trim();
    if (!text) return;
    var style = getComputedStyle(el);
    if (style.visibility === 'hidden') return;
    var key = style.fontFamily + ' | ' + style.fontWeight + ' | ' + style.fontStyle;
    weights.add(style.fontWeight);
    if (!groups[key]) groups[key] = {count: 0, example: text.slice(0, 60)};
    groups[key].count++;
  });
  var pre = document.createElement('pre'); pre.id = 'c7-measure';
  pre.textContent = JSON.stringify({weights: Array.from(weights).sort(), groups: groups});
  document.body.appendChild(pre);
}, 500); });
</script>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--chromium', type=Path, default=Path.home() / '.cache/ms-playwright/chromium_headless_shell-1169/chrome-linux/headless_shell')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    essays = json.loads((ROOT / 'data/essays.json').read_text())
    photos = json.loads((ROOT / 'data/photos.json').read_text())
    pages = {
        '/__c7/404': (ROOT / '404.html').read_text(),
        '/__c7/archive': _env.get_template('archive.html').render(**_prepare_archive_data(essays), build_ts=0),
        '/__c7/map': _env.get_template('map.html').render(**_prepare_map_data(photos), build_ts=0),
    }
    for essay in essays:
        source = ROOT / 'md' / (essay['slug'] + '.md')
        raw = source.read_text() if source.is_file() else ''
        protected = is_encrypted_content(raw)
        body = {'body_html': '' if protected else render_markdown(raw, essays, ROOT),
                'encrypted_body': raw if protected else '', 'password_protected': protected,
                'encrypted_is_md': protected, 'og_image': '', 'raw_md': ''}
        pages['/__c7/' + essay['slug']] = render_essay_html(
            essay, body, essays, _env.get_template('essay.html'), _parse_date, ROOT)

    @app.route('/__c7/<name>')
    def snapshot(name):
        return Response(pages[request.path], mimetype='text/html')

    @app.after_request
    def measurement(response):
        if response.mimetype == 'text/html':
            response.direct_passthrough = False
            text = response.get_data(as_text=True)
            if request.path == '/shelf.html':
                text = re.sub(r'<meta http-equiv="refresh"[^>]*>', '', text)
            response.set_data(text.replace('</body>', MEASURE + '</body>'))
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                "connect-src 'self'; font-src 'none'; frame-src 'none'")
        return response

    app.config['TESTING'] = True
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = {}
    try:
        with tempfile.TemporaryDirectory(prefix='pw-c7-chromium-') as profile:
            for route in ['/index.html', '/', '/shelf.html', *pages]:
                process = subprocess.run([
                    str(args.chromium), '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
                    '--user-data-dir=' + profile, '--dump-dom', '--virtual-time-budget=5000',
                    f'http://127.0.0.1:{server.server_port}{route}',
                ], capture_output=True, text=True, timeout=30, check=True)
                match = re.search(r'<pre id="c7-measure">(.*?)</pre>', process.stdout, re.S)
                if not match:
                    raise RuntimeError('Missing browser result: ' + route + '\n' + process.stderr[-1000:])
                results[route] = json.loads(html.unescape(match[1]))
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    css = (ROOT / 'templates/includes/base.css').read_bytes()
    full = pages['/__c7/' + essays[0]['slug']].encode()
    # Jinja drops the included file's trailing newline. Measure the actual block.
    match = re.search(rb'<style>\n(.*?)\n</style>', full, re.S)
    inline = match[1]
    external = full[:match.start()] + b'<link rel="stylesheet" href="/assets/css/base.css?v=0123456789abcdef">' + full[match.end():]
    deltas = []
    for essay in essays:
        page = pages['/__c7/' + essay['slug']].encode()
        stripped = re.sub(rb'<style>\n.*?\n</style>',
                          b'<link rel="stylesheet" href="/assets/css/base.css?v=0123456789abcdef">',
                          page, count=1, flags=re.S)
        deltas.append(len(gzip.compress(page, mtime=0)) - len(gzip.compress(stripped, mtime=0)))
    summary = {
        'base_css_bytes': len(css), 'base_css_gzip9_bytes': len(gzip.compress(css, mtime=0)),
        'inline_bytes_per_essay': len(inline), 'essay_count': len(essays),
        'total_inline_bytes': len(inline) * len(essays),
        'gzip9_sample_html_with_inline': len(gzip.compress(full, mtime=0)),
        'gzip9_sample_html_with_external': len(gzip.compress(external, mtime=0)),
        'gzip9_html_savings_per_sample': len(gzip.compress(full, mtime=0)) - len(gzip.compress(external, mtime=0)),
        'gzip9_all_essay_html_savings': sum(deltas),
        'gzip9_savings_range_per_essay': [min(deltas), max(deltas)],
        'gzip9_all_essays_net_savings_with_one_css_download': sum(deltas) - len(gzip.compress(css, mtime=0)),
        'font_method': 'Chromium computed CSS on direct visible text nodes; remote fonts/scripts blocked; desktop viewport; dynamic tabs/iframes excluded',
        'fonts_by_page': results,
    }
    (args.output / 'c7-measurements.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key != 'fonts_by_page'}, ensure_ascii=False, indent=2))
    print('Page weights:', {name: data['weights'] for name, data in results.items()})


if __name__ == '__main__':
    main()
