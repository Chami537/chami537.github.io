"""Executable tests for small browser-side helpers without a frontend test runner."""

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _run_node(script):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is unavailable')
    subprocess.run([node, '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_public_renderers_escape_attribute_quotes_and_dates():
    core_path = (ROOT / 'assets' / 'js' / 'index-core.js').as_posix()
    gallery_path = (ROOT / 'assets' / 'js' / 'index-photo-gallery.js').as_posix()
    script = f"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const storyContainer = {{style: {{}}, innerHTML: ''}};
const document = {{
  querySelector() {{ return {{style: {{}}, classList: {{add() {{}}, remove() {{}}, toggle() {{}}}}}}; }},
  querySelectorAll() {{ return []; }},
  getElementById(id) {{ return id === 'photo-stories' ? storyContainer : null; }},
  createElement() {{
    return {{
      _text: '',
      set textContent(value) {{ this._text = String(value); }},
      get innerHTML() {{
        return this._text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      }}
    }};
  }}
}};
const context = {{
  document,
  window: {{}},
  addEventListener() {{}},
  scrollY: 0,
  innerHeight: 800,
  console,
  encodeURIComponent,
  Set,
}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('{core_path}', 'utf8'), context);
vm.runInContext(fs.readFileSync('{gallery_path}', 'utf8'), context);

assert.strictEqual(context.htmlEncode('"'), '&quot;');
const work = context.renderWork([{{
  id: 1,
  title: 'X',
  description: 'Y',
  tags: [],
  url: 'https://safe.test/" onmouseover="alert(1)'
}}]);
assert(!work.includes('" onmouseover="'));
assert(work.includes('&quot; onmouseover=&quot;'));

const photo = context._photoItemHtml({{
  filename: 'x.jpg',
  date: '<img src=x onerror=alert(1)>'
}});
assert(photo.includes('&lt;img src=x onerror=alert(1)&gt;'));
assert(!photo.includes('<span class="photo-date"><img'));

context.renderPhotoStories([{{
  id: 'story',
  name: 'Story',
  photos: ['x.jpg'],
  date: '<img src=x onerror=alert(1)>'
}}]);
assert(storyContainer.innerHTML.includes('&lt;img src=x onerror=alert(1)&gt;'));
assert(!storyContainer.innerHTML.includes('<span class="story-meta"><img'));
"""
    _run_node(script)


def test_gpx_parser_calculates_points_distance_and_elevation_gain():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is unavailable')

    source_path = (ROOT / 'assets' / 'js' / 'index-photo-map.js').as_posix()
    script = f"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

class TestDOMParser {{
  parseFromString(xml) {{
    const matches = [...xml.matchAll(/<trkpt\\s+lat=\\"([^\\"]+)\\"\\s+lon=\\"([^\\"]+)\\">([\\s\\S]*?)<\\/trkpt>/g)];
    return {{
      querySelectorAll() {{
        return matches.map(match => ({{
          getAttribute(name) {{ return name === 'lat' ? match[1] : match[2]; }},
          querySelector() {{
            const elevation = match[3].match(/<ele>([^<]+)<\\/ele>/);
            return elevation ? {{textContent: elevation[1]}} : null;
          }}
        }}));
      }}
    }};
  }}
}}

const context = {{DOMParser: TestDOMParser}};
vm.runInNewContext(fs.readFileSync('{source_path}', 'utf8'), context);
const summary = context._parseGpxTrack(
  '<gpx><trk><trkseg>' +
  '<trkpt lat=\"22.5000\" lon=\"113.9000\"><ele>10</ele></trkpt>' +
  '<trkpt lat=\"22.5010\" lon=\"113.9010\"><ele>15</ele></trkpt>' +
  '<trkpt lat=\"22.5020\" lon=\"113.9020\"><ele>12</ele></trkpt>' +
  '</trkseg></trk></gpx>'
);
assert.strictEqual(summary.points.length, 3);
assert(summary.distance > 0);
assert.strictEqual(summary.gain, 5);
assert.strictEqual(context._fmtDist(1250), '1.3 km');
"""
    subprocess.run([node, '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)
