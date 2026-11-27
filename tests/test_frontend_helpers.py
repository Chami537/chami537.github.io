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


def test_shared_code_renderer_applies_fallback_highlighting():
    renderer_path = (ROOT / 'assets' / 'js' / 'code-rendering.js').as_posix()
    script = f"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

let button = null;
const pre = {{
  dataset: {{}},
  querySelector() {{ return null; }},
  appendChild(value) {{ button = value; }}
}};
const classes = ['language-python'];
classes.add = function(value) {{ this.push(value); }};
const code = {{
  textContent: 'def main():\\n    return 1',
  innerHTML: '',
  classList: classes,
  parentElement: pre,
  querySelector() {{ return null; }}
}};
const context = {{
  window: null,
  navigator: {{}},
  document: {{
    createElement() {{
      return {{
        dataset: {{}},
        setAttribute() {{}},
        addEventListener() {{}},
      }};
    }}
  }},
  setTimeout() {{}},
}};
context.window = context;
vm.createContext(context);
vm.runInContext(fs.readFileSync('{renderer_path}', 'utf8'), context);
context.highlightCodeBlocks({{querySelectorAll() {{ return [code]; }}}});

assert(code.innerHTML.includes('hljs-keyword'));
assert(code.classList.includes('hljs'));
assert.strictEqual(pre.dataset.language, 'Python');
assert.strictEqual(button.textContent, 'Python');
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


def test_essay_subtags_keep_the_selected_primary_category():
    state_path = (ROOT / 'assets' / 'js' / 'admin-essay-tag-state.js').as_posix()
    taxonomy_path = (ROOT / 'assets' / 'js' / 'admin-essay-taxonomy.js').as_posix()
    actions_path = (ROOT / 'assets' / 'js' / 'admin-essay-tag-actions.js').as_posix()
    script = f"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const elements = {{}};
const context = {{
  document: {{
    getElementById(id) {{ return elements[id] || (elements[id] = {{value:'', style:{{}}, classList:{{toggle(){{}}}}}}); }},
    querySelector() {{ return {{classList:{{toggle(){{}}}}, textContent:''}}; }}
  }},
  window: {{}}, console, _essayAllData: []
}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('{state_path}', 'utf8'), context);
vm.runInContext(fs.readFileSync('{taxonomy_path}', 'utf8'), context);
vm.runInContext(fs.readFileSync('{actions_path}', 'utf8'), context);
vm.runInContext("currentEssayTag = '阅读'; currentEssayChildTag = '消费';", context);
assert.strictEqual(context._defaultEssayTagForFilter('消费'), '阅读, 消费');
context.hidePanel = () => {{}};
context.hideEssayContentEditor = () => {{}};
context.window.essayEntry = () => {{}};
vm.runInContext("switchEssayChildTag('旅行');", context);
assert.strictEqual(vm.runInContext('currentEssayTag', context), '阅读');
"""
    _run_node(script)


def test_markdown_import_prefers_obsidian_filename_over_body_heading():
    meta_path = (ROOT / 'assets' / 'js' / 'admin-essay-meta.js').as_posix()
    script = f"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const context = {{}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('{meta_path}', 'utf8'), context);

const fromFilename = context._markdownMeta('# 283.移动零\\n\\n正文', '双指针法.md');
assert.strictEqual(fromFilename.title, '双指针法');
const fromFrontmatter = context._markdownMeta('---\\ntitle: 指定标题\\n---\\n# 正文标题', '文件标题.md');
assert.strictEqual(fromFrontmatter.title, '指定标题');
"""
    _run_node(script)


def test_shared_essays_fetch_and_timeout_in_index_core():
    core_path = (ROOT / 'assets' / 'js' / 'index-core.js').as_posix()
    script = f"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const fetchCalls = [];
let abortCount = 0;
class FakeAbortController {{
  constructor() {{
    const listeners = [];
    this.signal = {{
      aborted: false,
      addEventListener(type, fn) {{ if (type === 'abort') listeners.push(fn); }},
      _fire() {{ listeners.forEach(fn => fn()); }}
    }};
  }}
  abort() {{ this.signal.aborted = true; abortCount += 1; this.signal._fire(); }}
}}

const context = {{
  document: {{
    currentScript: {{ src: 'https://example.test/assets/js/index-core.js?v=abc123' }},
    querySelector() {{ return {{ style: {{}}, classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }} }}; }},
    querySelectorAll() {{ return []; }},
  }},
  window: {{}},
  addEventListener() {{}},
  scrollY: 0,
  innerHeight: 800,
  console,
  encodeURIComponent,
  AbortController: FakeAbortController,
  setTimeout,
  clearTimeout,
  fetch(url, opts) {{
    fetchCalls.push({{ url, opts }});
    if (url.includes('slow.json')) {{
      // A truly hanging request: it can only ever settle via abort, like a
      // stalled network fetch. Without a working abort in the code under
      // test the promise never settles and the watchdog below fails the run.
      return new Promise((_, reject) => {{
        if (opts && opts.signal) {{
          opts.signal.addEventListener('abort', () => reject(new Error('Aborted')));
        }}
      }});
    }}
    return Promise.resolve({{
      ok: true,
      json: async () => ({{ essays: [{{ slug: 'hello' }}], _tags: ['随笔'] }})
    }});
  }}
}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('{core_path}', 'utf8'), context);

(async () => {{
  const watchdog = setTimeout(() => {{
    console.error('WATCHDOG: async assertions did not complete');
    process.exit(3);
  }}, 3000);
  assert.strictEqual(context.TS, 'abc123');
  assert.strictEqual(context.dataUrl('data/essays_public.json'), 'data/essays_public.json?v=abc123');

  const p1 = context.fetchEssaysPublic();
  const p2 = context.fetchEssaysPublic();
  assert.strictEqual(p1, p2);
  const [d1, d2] = await Promise.all([p1, p2]);
  assert.deepStrictEqual(d1, d2);
  assert.strictEqual(fetchCalls.length, 1);

  await assert.rejects(() => context.fetchJsonWithTimeout('data/slow.json', 10), /Aborted/);
  assert.strictEqual(abortCount, 1);
  clearTimeout(watchdog);
}})().catch(err => {{ console.error(err); process.exit(1); }});
"""
    _run_node(script)


def test_independent_section_rendering_does_not_block_on_failure():
    core_path = (ROOT / 'assets' / 'js' / 'index-core.js').as_posix()
    index_path = (ROOT / 'assets' / 'js' / 'index.js').as_posix()
    script = f"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function makeEl(id, extra) {{
  const classes = new Set(['skeleton-loading']);
  return Object.assign({{
    id,
    innerHTML: '',
    style: {{}},
    attrs: {{}},
    classList: {{
      remove(c) {{ classes.delete(c); }},
      add(c) {{ classes.add(c); }},
      contains(c) {{ return classes.has(c); }},
      toggle(c, f) {{ if (f) classes.add(c); else classes.delete(c); }}
    }},
    setAttribute(k, v) {{ this.attrs[k] = v; }},
    getAttribute(k) {{ return this.attrs[k]; }},
    querySelectorAll() {{ return []; }},
  }}, extra || {{}});
}}

const elements = {{
  'about-text': makeEl('about-text', {{ innerHTML: 'fallback' }}),
  'portrait-img': makeEl('portrait-img'),
  'hero-meta': makeEl('hero-meta'),
  'work-container': makeEl('work-container'),
  'stack-cloud': makeEl('stack-cloud'),
  'essays-list': makeEl('essays-list'),
  'photo-masonry': makeEl('photo-masonry'),
  'photo-load-more': makeEl('photo-load-more'),
  'gps-count': makeEl('gps-count'),
  'contact-list': makeEl('contact-list', {{ innerHTML: 'static-contact' }}),
  'friends-container': makeEl('friends-container'),
  'music-list': makeEl('music-list', {{ innerHTML: 'static-music' }}),
  'photo-map-container': makeEl('photo-map-container'),
}};

let domReadyCb = null;
let essaysBuilt = false;
let musicInitCalled = false;

const context = {{
  document: {{
    currentScript: null,
    getElementById(id) {{ return elements[id] || null; }},
    querySelector() {{ return makeEl('q'); }},
    querySelectorAll() {{ return []; }},
    addEventListener(ev, cb) {{ if (ev === 'DOMContentLoaded') domReadyCb = cb; }},
  }},
  window: {{ addEventListener() {{}} }},
  addEventListener() {{}},
  scrollY: 0,
  innerHeight: 800,
  console,
  encodeURIComponent,
  decodeURIComponent,
  setTimeout,
  clearTimeout,
  renderWork(d) {{ return 'WORK:' + d.length; }},
  renderStack(d) {{ return 'STACK:' + d.length; }},
  renderPhotos(d) {{ return 'PHOTOS:' + d.length; }},
  renderContact(d) {{ return 'CONTACT:' + d.length; }},
  renderFriends(d) {{ return 'FRIENDS:' + d.length; }},
  renderMusic(d) {{ return 'MUSIC:' + d.length; }},
  buildEssayFilter() {{ essaysBuilt = true; }},
  renderEssayList() {{ elements['essays-list'].innerHTML = 'ESSAYS:ok'; }},
  buildPhotoTagFilter() {{}},
  renderPhotoStories() {{}},
  initLB() {{}},
  initMusicPlayer() {{ musicInitCalled = true; }},
  fetch(url) {{
    if (url.includes('work.json')) {{
      return Promise.reject(new Error('work down'));
    }}
    if (url.includes('essays_public.json')) {{
      return Promise.resolve({{ ok: true, json: async () => ({{ essays: [{{ slug: 'a' }}], _tags: [] }}) }});
    }}
    if (url.includes('about.json')) {{
      return Promise.resolve({{ ok: true, json: async () => ({{ content: 'Hi', tags: ['CS'] }}) }});
    }}
    return Promise.resolve({{ ok: false, status: 500 }});
  }}
}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('{core_path}', 'utf8'), context);
context.initMusicPlayer = () => {{ musicInitCalled = true; }};
vm.runInContext(fs.readFileSync('{index_path}', 'utf8'), context);

(async () => {{
  domReadyCb();
  await new Promise(r => setTimeout(r, 30));
  assert.strictEqual(essaysBuilt, true);
  assert.strictEqual(elements['essays-list'].innerHTML, 'ESSAYS:ok');
  assert(!elements['essays-list'].classList.contains('skeleton-loading'));

  assert(elements['work-container'].innerHTML.includes('项目暂时无法加载'));
  assert(!elements['work-container'].classList.contains('skeleton-loading'));
  assert.strictEqual(elements['work-container'].attrs['aria-busy'], 'false');

  assert.strictEqual(elements['contact-list'].innerHTML, 'static-contact');
  assert(!elements['contact-list'].classList.contains('skeleton-loading'));
  assert.strictEqual(musicInitCalled, true);
}})().catch(err => {{ console.error(err); process.exit(1); }});
"""
    _run_node(script)


def test_photo_alt_and_essay_lightbox_caption():
    core_path = (ROOT / 'assets' / 'js' / 'index-core.js').as_posix()
    lb_path = (ROOT / 'assets' / 'js' / 'essay-lightbox.js').as_posix()
    photos_path = (ROOT / 'data' / 'photos.json').as_posix()
    stories_path = (ROOT / 'data' / 'photo_stories.json').as_posix()
    map_html = (ROOT / 'templates' / 'map.html').read_text(encoding='utf-8')
    assert 'alt="' in map_html

    script = f"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const photos = JSON.parse(fs.readFileSync('{photos_path}', 'utf8'));
const stories = JSON.parse(fs.readFileSync('{stories_path}', 'utf8'));
const storyMap = {{}};
stories.forEach(s => (s.photos || []).forEach(f => {{ storyMap[f] = s.name; }}));

const coreCtx = {{
  document: {{ querySelector() {{ return {{ style: {{}}, classList: {{ add() {{}}, remove() {{}}, toggle() {{}} }} }}; }}, querySelectorAll() {{ return []; }} }},
  window: {{}}, addEventListener() {{}}, scrollY: 0, innerHeight: 800, console
}};
vm.createContext(coreCtx);
vm.runInContext(fs.readFileSync('{core_path}', 'utf8'), coreCtx);

const altWithStory = coreCtx.buildPhotoAlt(photos.find(p => p.filename === '11f6710f.jpg'), storyMap['11f6710f.jpg']);
assert(altWithStory.includes('重庆 · 解放碑'));
assert(altWithStory.includes('City'));
assert(altWithStory.includes('Jul 8, 2025'));

const altNoTags = coreCtx.buildPhotoAlt(photos.find(p => p.filename === '03c4c220.jpg'), '');
assert(altNoTags.includes('Jul 22, 2026'));
assert(altNoTags.includes('35.66°N'));

// Essay lightbox caption behavior
let clickHandler = null;
const lbEl = {{
  children: [],
  classList: {{ add() {{}}, remove() {{}}, contains() {{ return false; }} }},
  addEventListener() {{}},
  insertBefore(node) {{ this.children.push(node); }},
  appendChild(node) {{ this.children.push(node); }},
}};
const lbImg = {{ src: '', alt: '' }};
const lbCounter = {{ textContent: '', parentNode: lbEl }};
const lbCaption = {{ textContent: '', hidden: true, style: {{ display: 'none' }} }};
const imgWithAlt = {{ tagName: 'IMG', src: 'a.jpg', getAttribute(k) {{ return k === 'alt' ? '窗边的光' : ''; }} }};
const imgWithoutAlt = {{ tagName: 'IMG', src: 'b.jpg', getAttribute() {{ return ''; }} }};

const lbCtx = {{
  document: {{
    readyState: 'complete',
    body: {{ style: {{}} }},
    getElementById(id) {{
      if (id === 'lb') return lbEl;
      if (id === 'lb-img') return lbImg;
      if (id === 'lb-counter') return lbCounter;
      if (id === 'lb-caption') return lbCaption;
      return null;
    }},
    querySelector(sel) {{
      if (sel === '.essay-body') return {{ addEventListener(ev, fn) {{ if (ev === 'click') clickHandler = fn; }} }};
      return null;
    }},
    querySelectorAll(sel) {{
      if (sel === '.essay-body img') return [imgWithAlt, imgWithoutAlt];
      return [];
    }},
    addEventListener() {{}},
  }},
  console,
}};
vm.createContext(lbCtx);
vm.runInContext(fs.readFileSync('{lb_path}', 'utf8'), lbCtx);

clickHandler({{ target: imgWithAlt }});
assert.strictEqual(lbCaption.textContent, '窗边的光');
assert.strictEqual(lbCaption.hidden, false);
assert.strictEqual(lbCaption.style.display, '');
assert.strictEqual(lbCounter.textContent, '1 / 2');

lbCtx.lbNav(1);
assert.strictEqual(lbCaption.textContent, '');
assert.strictEqual(lbCaption.hidden, true);
assert.strictEqual(lbCaption.style.display, 'none');
assert.strictEqual(lbCounter.textContent, '2 / 2');
"""
    _run_node(script)
