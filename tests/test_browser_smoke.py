"""Minimal real-browser checks for the static admin and homepage shells."""

import os
import json
import threading
import time
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from backend.app import app


ROOT = Path(__file__).parents[1]


@pytest.fixture(scope='module')
def live_server():
    app.config['TESTING'] = True
    server = make_server('127.0.0.1', 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    thread.join(timeout=2)


@pytest.fixture(scope='module')
def browser():
    required = os.environ.get('BROWSER_SMOKE_REQUIRED') == '1'
    try:
        import playwright.sync_api as playwright
    except ImportError:
        if required:
            raise
        pytest.skip('Playwright is unavailable')

    driver = playwright.sync_playwright().start()
    try:
        browser_instance = driver.chromium.launch(headless=True)
    except Exception as exc:
        driver.stop()
        if required:
            raise
        pytest.skip(f'Chromium is unavailable: {exc}')

    try:
        yield browser_instance
    finally:
        browser_instance.close()
        driver.stop()


def test_admin_shell_loads_shared_modules_and_switches_tabs(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        assert page.title() == 'Chami — Site Admin'
        assert page.evaluate("typeof api") == 'function'
        assert page.evaluate("typeof switchTab") == 'function'
        page.locator('.tab-btn[data-tab="essays"]').click()
        assert page.locator('#essay-list').count() == 1
        for name in (
            'saveEssay', 'editEssayContent', '_wrapSelection', 'previewEssayContent',
            '_essayTagParts', 'renderEssayTaxonomy', 'saveTagOrder', 'switchEssayTag',
            'markDirty', 'requestEssayAi', 'applyEssayAiResult', 'updateEssayAiAvailability',
        ):
            deadline = time.monotonic() + 5
            while page.evaluate('typeof ' + name) != 'function':
                if time.monotonic() >= deadline:
                    pytest.fail(f'{name} was not exposed after essay modules loaded')
                page.wait_for_timeout(25)
            assert page.evaluate('typeof ' + name) == 'function'
        assert page.locator('#essay-ai-panel').count() == 1
        assert page.locator('#essay-ai-actions button').count() == 6
        page.locator('#essay-list button', has_text='元数据').first.click()
        page.locator('#essay-form').wait_for(state='visible')
        page.evaluate("renderEssayTaxonomy('技术, Python, 教程, 复盘')")
        assert page.locator('#essay-tag').input_value() == '技术, Python, 教程, 复盘'
        assert page.locator('#essay-form .taxonomy-grid.is-tech').count() == 1
        page.locator('#essay-list button', has_text='编辑正文').first.click()
        page.locator('#essay-content-editor').wait_for(state='visible')
    finally:
        page.close()


def test_admin_ai_suggestions_require_explicit_safe_apply(live_server, browser):
    page = browser.new_page()
    essay_writes = []
    ai_requests = []
    style_writes = []

    def fulfill_ai(route):
        request_data = route.request.post_data_json
        ai_requests.append(request_data)
        task = request_data['task']
        results = {
            'summary': {'excerpt': '<img src=x onerror=alert(1)>摘要'},
            'tags': {'tags': ['技术', 'Python', '教程']},
            'polish': {'content': '润色'},
            'title': {'titles': ['<img src=x>标题', '克制的标题', '第三个标题']},
            'continue': {'content': '续写内容'},
            'review': {
                'issues': [{
                    'type': '文字',
                    'message': '存在重复',
                    'suggestion': '删除重复内容',
                }],
            },
        }
        route.fulfill(json={
            'task': task,
            'result': results[task],
            'usage': {'prompt_tokens': 3, 'completion_tokens': 2},
            'style_reference_count': 0 if task == 'tags' else 3,
            'style_profile_used': task != 'tags',
        })

    def fulfill_style(route):
        if route.request.url.endswith('/analyze'):
            route.fulfill(json={
                'result': {'profile': '## AI 总结\n克制、直接'},
                'usage': {'prompt_tokens': 5, 'completion_tokens': 3},
                'style_reference_count': 4,
            })
        elif route.request.method == 'PUT':
            profile = route.request.post_data_json['profile']
            style_writes.append(profile)
            route.fulfill(json={'profile': profile, 'updated_at': '2026-07-31T00:00:00Z'})
        else:
            route.fulfill(json={
                'profile': '## 已确认\n保留口语',
                'updated_at': '2026-07-31T00:00:00Z',
            })

    page.route('**/api/ai/essay-assist', fulfill_ai)
    page.route('**/api/ai/writing-style', fulfill_style)
    page.route('**/api/ai/writing-style/analyze', fulfill_style)
    page.on('request', lambda request: essay_writes.append(request.url) if (
        request.method == 'PUT' and '/api/essays/' in request.url
    ) else None)
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        page.locator('.tab-btn[data-tab="essays"]').click()
        page.wait_for_timeout(150)
        page.evaluate("""
          _essayAllData = [{
            slug: 'essay-demo',
            title: '演示文章',
            tag: '技术',
            date: '2026-07-31',
            epigraph: '',
            excerpt: '',
            password_set: false
          }];
          var editor = document.getElementById('essay-content-editor');
          editor.style.display = 'block';
          editor.dataset.slug = 'essay-demo';
          var textarea = document.getElementById('essay-content-md');
          textarea.value = '原始正文';
          updateEssayAiAvailability('essay-demo');
        """)
        page.wait_for_timeout(100)
        assert '保留口语' in page.locator('#essay-ai-style-profile').input_value()
        page.locator('#essay-ai-style-profile').fill('手动修改')
        assert '未保存' in page.locator('#essay-ai-style-status').inner_text()
        page.locator('#essay-ai-style-analyze').click()
        page.wait_for_timeout(100)
        assert 'AI 总结' in page.locator('#essay-ai-style-profile').input_value()
        page.locator('#essay-ai-style-save').click()
        page.wait_for_timeout(100)
        assert '已保存' in page.locator('#essay-ai-style-status').inner_text()
        assert style_writes == ['## AI 总结\n克制、直接']

        page.locator('[data-ai-task="summary"]').click()
        page.locator('#essay-ai-result').wait_for(state='visible')
        assert '<img src=x onerror=alert(1)>摘要' in page.locator('#essay-ai-result').inner_text()
        assert page.locator('#essay-ai-result img').count() == 0
        assert '已参考 3 篇公开随笔' in page.locator('#essay-ai-status').inner_text()
        assert '已引用文风画像' in page.locator('#essay-ai-status').inner_text()
        page.locator('.essay-ai-apply').click()
        assert page.locator('#essay-excerpt').input_value() == '<img src=x onerror=alert(1)>摘要'
        assert essay_writes == []

        page.locator('[data-ai-task="tags"]').click()
        page.locator('.essay-ai-apply').click()
        assert page.locator('#essay-tag').input_value() == '技术, Python, 教程'

        page.evaluate("""
          var textarea = document.getElementById('essay-content-md');
          textarea.focus();
          textarea.setSelectionRange(0, 2);
        """)
        assert page.locator('#essay-ai-polish-mode').input_value() == 'light'
        page.locator('#essay-ai-polish-mode').select_option('rewrite')
        page.locator('#essay-ai-instruction').fill('保留口语')
        page.locator('[data-ai-task="polish"]').click()
        assert ai_requests[-1]['polish_mode'] == 'rewrite'
        assert ai_requests[-1]['instruction'] == '保留口语'
        assert ai_requests[-1]['surrounding_context']['after'] == '正文'
        page.locator('.essay-ai-apply').click()
        assert page.locator('#essay-content-md').input_value() == '润色正文'

        page.locator('#essay-ai-instruction').fill('无需修改测试')
        page.evaluate("""
          var textarea = document.getElementById('essay-content-md');
          textarea.focus();
          textarea.setSelectionRange(0, 2);
        """)
        page.locator('[data-ai-task="polish"]').click()
        page.locator('#essay-ai-result').wait_for(state='visible')
        assert '不建议为了润色而改' in page.locator('#essay-ai-result').inner_text()
        assert page.locator('.essay-ai-apply').count() == 0

        page.locator('[data-ai-task="review"]').click()
        page.locator('#essay-ai-result').wait_for(state='visible')
        assert '存在重复' in page.locator('#essay-ai-result').inner_text()
        assert page.locator('.essay-ai-apply').count() == 0

        page.locator('[data-ai-task="title"]').click()
        page.locator('.essay-ai-title-choice').first.wait_for(state='visible')
        assert page.locator('.essay-ai-title-choice').count() == 3
        assert page.locator('#essay-ai-result img').count() == 0
        page.locator('.essay-ai-title-choice').nth(1).click()
        assert page.locator('#essay-title').input_value() == '克制的标题'
        assert page.locator('.essay-ai-title-choice:disabled').count() == 3
        assert essay_writes == []

        page.locator('[data-ai-task="continue"]').click()
        page.locator('.essay-ai-apply').click()
        assert page.locator('#essay-content-md').input_value() == '润色正文\n\n续写内容'

        page.locator('[data-ai-task="continue"]').click()
        page.evaluate("document.getElementById('essay-content-md').value += '\\n用户新写'")
        page.locator('.essay-ai-apply').click()
        assert page.locator('#essay-content-md').input_value().endswith('用户新写')
        assert not page.locator('#essay-content-md').input_value().endswith('续写内容')

        page.evaluate("""
          _essayAllData[0].password_set = true;
          updateEssayAiAvailability('essay-demo');
        """)
        assert page.locator('#essay-ai-actions button:disabled').count() == 6
        assert '密码保护文章' in page.locator('#essay-ai-status').inner_text()
    finally:
        page.close()


def test_public_homepage_shell_loads_essay_surface(live_server, browser):
    from playwright.sync_api import expect
    page = browser.new_page()
    try:
        page.goto(live_server + '/index.html', wait_until='domcontentloaded')
        expect(page.locator('#work-container')).to_have_attribute('aria-busy', 'false')
        assert page.locator('#essays-list').count() == 1
        assert page.locator('#work-container .num').all_text_contents() == ['01', '02', '03']
        assert page.locator('script[src*="index-essays.js"]').count() == 1
        assert page.evaluate("safeExternalUrl('javascript:alert(1)')") == ''
        assert 'href=' not in page.evaluate("renderContact([{label:'X',handle:'Y',url:'javascript:alert(1)'}])")
        assert page.evaluate("renderWork([{id:1,title:'X',description:'Y',url:'data:text/html,x',tags:[]}])").startswith('<div')
    finally:
        page.close()


def test_public_homepage_does_not_show_stale_projects_before_data_load(live_server, browser):
    page = browser.new_page()
    try:
        page.route('**/data/work.json*', lambda route: None)
        page.goto(live_server + '/index.html', wait_until='domcontentloaded')

        assert page.locator('#work-container .work-card').count() == 0
        assert page.locator('#work-container').get_attribute('aria-busy') == 'true'
        assert page.locator('#work-container').inner_text() == '项目加载中…'
    finally:
        page.close()


def test_archive_combines_search_and_tag_filters_with_accessible_controls(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/archive.html', wait_until='domcontentloaded')

        search = page.get_by_label('搜索随笔')
        search.fill('滑动窗口')
        page.wait_for_timeout(150)
        assert page.locator('.archive-row').count() == 1

        reading_filter = page.get_by_role('button', name='阅读', exact=True)
        reading_filter.click()
        assert reading_filter.get_attribute('aria-pressed') == 'true'
        assert page.locator('.archive-row').count() == 0
        assert search.input_value() == '滑动窗口'
    finally:
        page.close()


def test_archive_mobile_keeps_article_tags_visible(live_server, browser):
    page = browser.new_page(viewport={'width': 390, 'height': 844})
    try:
        page.goto(live_server + '/archive.html', wait_until='domcontentloaded')

        assert page.locator('.archive-tag').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth === document.documentElement.clientWidth')
    finally:
        page.close()


def test_admin_api_error_and_password_dialog(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        status = page.evaluate("fetch('/api/essays/__browser_missing__/content').then(function(r) { return r.status; })")
        assert status == 404
        page.locator('.tab-btn[data-tab="essays"]').click()
        page.wait_for_timeout(150)
        password_button = page.locator('.password-btn').first
        assert password_button.count() == 1
        password_button.click()
        assert page.locator('#password-dialog[open]').count() == 1
        page.keyboard.press('Escape')
    finally:
        page.close()


def test_admin_dashboard_photo_story_and_music_tabs_render(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        page.locator('#dashboard-content').wait_for(state='visible')
        assert page.locator('#dashboard-counts .dashboard-count-item').count() > 0

        page.locator('.tab-btn[data-tab="photos"]').click()
        page.locator('#photo-grid .photo-card').first.wait_for(state='visible')
        assert page.locator('#story-editor-list .story-edit-card').count() > 0
        for name in ('loadPhotos', 'openPhotoTagModal', 'showPhotoEditor', 'handlePhotoFiles'):
            assert page.evaluate('typeof ' + name) == 'function'
        page.locator('#photo-grid .photo-card').first.click()
        page.locator('#photo-editor').wait_for(state='visible')
        page.evaluate('clearPhotoEditor()')

        page.locator('.tab-btn[data-tab="music"]').click()
        page.locator('#music-list .card').first.wait_for(state='visible')
        assert page.locator('#music-list .card').count() > 0
    finally:
        page.close()


def test_admin_ai_tools_preview_before_applying_to_forms(live_server, browser):
    from playwright.sync_api import expect
    page = browser.new_page()
    writes = []

    def fulfill_copy(route):
        task = route.request.post_data_json['task']
        counts = {'about': 2, 'project': 3, 'photo_story': 3}
        suggestions = [{
            'title': ('故事名' if task == 'photo_story' else '方案') + str(index + 1),
            'content': task + '候选文案' + str(index + 1),
        } for index in range(counts[task])]
        route.fulfill(json={
            'task': task,
            'result': {'suggestions': suggestions},
            'usage': {'prompt_tokens': 3, 'completion_tokens': 2},
            'style_profile_used': True,
        })

    def fulfill_audit(route):
        route.fulfill(json={
            'result': {'findings': [{
                'priority': 'high',
                'area': '项目',
                'issue': '<img src=x onerror=alert(1)>描述缺失',
                'suggestion': '补充已知功能',
            }]},
            'usage': {'prompt_tokens': 8, 'completion_tokens': 4},
        })

    page.route('**/api/ai/admin-assist', fulfill_copy)
    page.route('**/api/ai/site-content-audit', fulfill_audit)
    page.on('request', lambda request: writes.append(request.url) if (
        request.method in ('PUT', 'POST') and
        request.url.endswith(('/api/about', '/api/work', '/api/photo-stories'))
    ) else None)
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')

        page.locator('.tab-btn[data-tab="about"]').click()
        page.locator('#about-content').wait_for(state='visible')
        page.locator('#about-content').fill('原始简介')
        page.locator('button', has_text='AI 优化简介').click()
        page.locator('#admin-ai-copy-dialog').wait_for(state='visible')
        expect(page.locator('.admin-ai-copy-option')).to_have_count(2)
        page.locator('.admin-ai-copy-option .btn').first.click()
        assert page.locator('#about-content').input_value() == 'about候选文案1'
        assert writes == []

        page.locator('.tab-btn[data-tab="work"]').click()
        page.locator('button', has_text='+ 添加项目').click()
        page.locator('#work-title').fill('项目')
        page.locator('#work-desc').fill('原始描述')
        page.locator('button', has_text='AI 优化描述').click()
        expect(page.locator('.admin-ai-copy-option')).to_have_count(3)
        page.locator('.admin-ai-copy-option .btn').nth(1).click()
        assert page.locator('#work-desc').input_value() == 'project候选文案2'
        assert writes == []

        page.locator('.tab-btn[data-tab="photos"]').click()
        page.locator('#story-editor-list .story-edit-card').first.wait_for(state='visible')
        page.evaluate("""
          _photoData = [{filename: 'one.jpg', date: 'Jul 2026', tags: ['City']}];
          _storyData = [{
            id: 'demo', name: '原名', date: 'Jul 2026', caption: '原文',
            cover: 'one.jpg', photos: ['one.jpg']
          }];
          renderStoryEditor();
        """)
        page.locator('#story-editor-list button', has_text='AI 润色').click()
        expect(page.locator('.admin-ai-copy-option')).to_have_count(3)
        page.locator('.admin-ai-copy-option .btn').nth(2).click()
        assert page.evaluate("_storyData[0].name") == '原名'
        assert page.evaluate("_storyData[0].caption") == 'photo_story候选文案3'
        assert writes == []

        page.locator('.tab-btn[data-tab="dashboard"]').click()
        page.locator('#admin-ai-audit-button').click()
        page.locator('.admin-ai-finding').wait_for(state='visible')
        assert '<img src=x onerror=alert(1)>描述缺失' in page.locator(
            '.admin-ai-finding'
        ).inner_text()
        assert page.locator('.admin-ai-finding img').count() == 0
        assert '8输入 / 4输出 tokens' in page.locator(
            '#admin-ai-audit-status'
        ).inner_text()
    finally:
        page.close()


def test_admin_health_tab_renders_checks_and_filters(live_server, browser):
    page = browser.new_page()
    try:
        checks = [
            {'id': f'passed-{index}', 'label': f'Passed {index}', 'status': 'passed', 'message': 'ok', 'details': []}
            for index in range(8)
        ] + [
            {'id': 'error-1', 'label': 'Error', 'status': 'error', 'message': 'broken', 'details': []}
        ]
        page.route('**/api/site-health', lambda route: route.fulfill(json={
            'status': 'error',
            'summary': {'passed': 8, 'warnings': 0, 'errors': 1},
            'checks': checks,
        }))
        page.goto(live_server + '/', wait_until='domcontentloaded')
        page.locator('.tab-btn[data-tab="health"]').click()
        page.locator('#health-content').wait_for(state='visible')
        assert page.locator('#health-checks .health-check').count() >= 8
        page.locator('.health-filter button').nth(2).click()
        visible = page.locator('#health-checks .health-check:not([hidden])')
        assert visible.count() == 1
        assert 'health-error' in visible.first.get_attribute('class').split()
        assert page.locator('#health-checks .health-passed:not([hidden])').count() == 0
        assert page.locator('#health-history-list').count() == 1
    finally:
        page.close()


def test_admin_tabs_keep_active_health_tab_aligned_on_narrow_viewport(live_server, browser):
    page = browser.new_page(viewport={'width': 634, 'height': 400})
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        page.locator('.tab-btn[data-tab="health"]').click()
        box = page.locator('.tabs').bounding_box()
        tab = page.locator('.tab-btn[data-tab="health"]').bounding_box()
        assert box['x'] <= tab['x']
        assert tab['x'] + tab['width'] <= box['x'] + box['width']
    finally:
        page.close()


def test_admin_about_tracks_and_readme_modules_load(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        for name in ('loadAbout', 'loadTracks', 'loadReadme'):
            assert page.evaluate('typeof ' + name) == 'function'
        assert page.evaluate('typeof window._renderAdminEditor') == 'function'

        page.locator('.tab-btn[data-tab="about"]').click()
        page.locator('#about-content').wait_for(state='visible')
        page.locator('.tab-btn[data-tab="tracks"]').click()
        page.locator('#tracks-list').wait_for(state='visible')
        page.locator('.tab-btn[data-tab="readme"]').click()
        page.locator('#readme-content').wait_for(state='visible')
    finally:
        page.close()


def test_shared_code_renderer_runs_in_admin_and_essay_pages(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        page.wait_for_function("typeof highlightCodeBlocks === 'function'")
        rendered = page.evaluate("""
          (function() {
            var root = document.createElement('div');
            root.innerHTML = '<pre><code class="language-python">def main():\\n    return 1</code></pre>';
            highlightCodeBlocks(root);
            return {
              highlighted: root.querySelector('.hljs-keyword') !== null,
              button: root.querySelector('.code-language').textContent
            };
          })()
        """)
        assert rendered == {'highlighted': True, 'button': 'Python'}

        essays = json.loads((ROOT / 'data' / 'essays.json').read_text(encoding='utf-8'))
        page.goto(live_server + f"/essays/{essays[0]['slug']}.html", wait_until='domcontentloaded')
        page.wait_for_function("typeof highlightCodeBlocks === 'function'")
        assert page.locator('script[src*="code-rendering.js"]').count() == 1
    finally:
        page.close()


def test_essay_toc_builds_heading_anchors_and_supports_group_collapse(live_server, browser):
    page = browser.new_page()
    try:
        page.set_viewport_size({'width': 1100, 'height': 700})
        essays = json.loads((ROOT / 'data' / 'essays.json').read_text(encoding='utf-8'))
        page.goto(live_server + f"/essays/{essays[0]['slug']}.html", wait_until='domcontentloaded')
        page.wait_for_function("typeof buildEssayToc === 'function'")
        result = page.evaluate("""
          (function() {
            var body = document.querySelector('.essay-body');
            body.innerHTML = '<h1>第一章</h1><h2>背景与目标</h2><h3>实现细节</h3><h2>背景与目标</h2><h1>第二章</h1>';
            buildEssayToc(body);
            var links = Array.from(document.querySelectorAll('#essay-toc-list a'));
            var firstToggle = document.querySelector('.essay-toc-toggle');
            firstToggle.click();
            return {
              visible: !document.getElementById('essay-toc').hidden,
              display: getComputedStyle(document.getElementById('essay-toc')).display,
              beforeComments: document.getElementById('essay-toc').compareDocumentPosition(
                document.getElementById('giscus-container')
              ) & Node.DOCUMENT_POSITION_FOLLOWING,
              ids: Array.from(body.querySelectorAll('h1, h2, h3')).map(function(h) { return h.id; }),
              links: links.map(function(link) { return link.getAttribute('href'); }),
              collapsed: document.querySelector('.essay-toc-sublist').hidden,
              h3Parent: document.querySelector('.essay-toc-h3').parentElement.parentElement.classList.contains('essay-toc-h2'),
              labels: links.map(function(link) { return link.textContent; })
            };
          })()
        """)
        assert result == {
            'visible': True,
            'display': 'none',
            'beforeComments': 4,
            'ids': ['heading-第一章', 'heading-背景与目标', 'heading-实现细节', 'heading-背景与目标-2', 'heading-第二章'],
            'links': ['#heading-第一章', '#heading-背景与目标', '#heading-实现细节', '#heading-背景与目标-2', '#heading-第二章'],
            'collapsed': True,
            'h3Parent': True,
            'labels': ['第一章', '背景与目标', '实现细节', '背景与目标', '第二章'],
        }
    finally:
        page.close()


def test_archive_navigation_shows_essay_toc_on_desktop(live_server, browser):
    page = browser.new_page()
    try:
        page.set_viewport_size({'width': 1366, 'height': 768})
        page.goto(live_server + '/archive.html', wait_until='domcontentloaded')
        # Pick the first essay dynamically instead of hardcoding a slug,
        # so the test doesn't break when essays are added/removed/renamed.
        essay_link = page.locator('.archive-row').first
        essay_href = essay_link.get_attribute('href')
        assert essay_href and essay_href.startswith('essays/') and essay_href.endswith('.html')
        essay_link.click()
        page.wait_for_url(f'**/{essay_href}')
        page.wait_for_function("document.querySelectorAll('#essay-toc-list a').length > 0")

        toc = page.locator('#essay-toc')
        assert toc.is_visible()
        assert page.locator('#essay-toc-list a').count() == page.locator(
            '.essay-body h1, .essay-body h2, .essay-body h3'
        ).count()
    finally:
        page.close()


def test_stories_admin_crud_sort_and_failed_save_preserves_form(live_server, browser, data_backup, monkeypatch):
    from backend.repositories import repository_for
    from playwright.sync_api import expect
    repository_for('stories.json').save([])
    # The real write path must trust the ephemeral test server origin.
    monkeypatch.setitem(app.config, 'TRUSTED_ORIGINS', (*app.config['TRUSTED_ORIGINS'], live_server))
    page = browser.new_page()
    page.route('**/api/essays', lambda route: route.fulfill(json=[
        {'slug':'secret','title':'加密随笔','password_set':True},
        {'slug':'hidden','title':'隐藏随笔','hidden':True},
    ]))
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        page.locator('[data-tab="stories"]').click()
        page.locator('#stories-admin-list').get_by_text('还没有收录作品，添加第一部喜欢的故事吧。').wait_for()
        for title, kind in [('电影甲','movie'), ('电视剧乙','series'), ('小说丙','novel')]:
            page.get_by_role('button', name='添加作品', exact=True).click()
            assert page.locator('#story-essay_slug option').count() == 1
            page.locator('#story-title').fill(title)
            page.locator('#story-type').select_option(kind)
            page.locator('#story-recommendation').fill('留在心里的故事 <script>bad()</script>')
            assert page.locator('#story-featured').count() == 0
            page.locator('#story-save').click()
            page.locator('#story-form').wait_for(state='hidden')
            page.locator('#stories-admin-list h3', has_text=title).wait_for()
        page.get_by_role('button', name='上移 小说丙', exact=True).click()
        expect(page.locator('#stories-admin-list h3').nth(1)).to_have_text('小说丙')
        page.get_by_role('button', name='编辑 电影甲', exact=True).click()
        page.locator('#story-title').fill('电影甲（修改）')
        page.locator('#story-rating').fill('4.5')
        # Server validation must preserve the form on a failed request.
        page.route('**/api/stories/*', lambda route: route.fulfill(status=400, json={'error':'保存失败测试'}) if route.request.method == 'PUT' else route.continue_())
        page.locator('#story-save').click()
        page.get_by_text('保存失败测试', exact=True).wait_for()
        assert page.locator('#story-title').input_value() == '电影甲（修改）'
        assert page.locator('#story-form').is_visible()
        page.unroute('**/api/stories/*')
        page.locator('#story-save').click()
        page.locator('#story-form').wait_for(state='hidden')
        page.locator('#stories-admin-list h3', has_text='电影甲（修改）').wait_for()
        page.reload(wait_until='domcontentloaded')
        page.locator('[data-tab="stories"]').click()
        page.locator('#stories-admin-list h3', has_text='电影甲（修改）').wait_for()
        assert page.locator('#stories-admin-list h3').all_text_contents() == ['电影甲（修改）','小说丙','电视剧乙']
        page.evaluate('window.confirmDialog = async function() { return true; }')
        page.get_by_role('button', name='删除 电视剧乙', exact=True).click()
        expect(page.locator('#stories-admin-list h3')).to_have_count(2)
        assert len(repository_for('stories.json').list()) == 2
    finally:
        page.evaluate('if (typeof markClean === "function") markClean()')
        page.close()


def test_stories_gallery_mixed_order_expansion_themes_and_mobile(live_server, browser):
    from playwright.sync_api import expect

    sample = [
        {'id': 1, 'title': '电影 <script>bad()</script>', 'type': 'movie',
         'recommendation': '第一行\n第二行\n\n第三行\n\n第四行\n第五行',
         'featured': True, 'favorite': True, 'rating': 4.5,
         'cover': 'images/stories/missing.png', 'essay_slug': 'open'},
        {'id': 2, 'title': '电视剧', 'type': 'series', 'recommendation': '这是一部电视剧。',
         'featured': False, 'essay_slug': 'private'},
        {'id': 3, 'title': '小说', 'type': 'novel', 'recommendation': '这是一部小说。'},
    ] + [{'id': i, 'title': '作品' + str(i), 'type': 'movie', 'recommendation': '长' * 180}
         for i in range(4, 9)]
    page = browser.new_page(viewport={'width': 390, 'height': 844}, color_scheme='light')
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('**/data/stories.json*', lambda route: route.fulfill(json=sample))
    page.route('**/data/essays_public.json*', lambda route: route.fulfill(json={'essays': [
        {'slug': 'open', 'title': '公开文章'}, {'slug': 'private', 'password_protected': True},
    ]}))
    try:
        page.goto(live_server + '/index.html', wait_until='domcontentloaded')
        page.locator('#stories').wait_for(state='visible')
        assert page.locator('#stories-list .shelf-card').count() == 8
        assert page.locator('#stories-list .shelf-title').all_text_contents() == [
            s['title'] for s in sample
        ]
        assert page.locator('#stories-list script').count() == 0
        assert page.locator('#stories-nav').is_visible()
        assert page.locator('#stories .shelf-all, #stories .shelf-filters, #stories a[href*=shelf]').count() == 0
        assert page.locator('#stories-list').evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').length") == 2
        cover = page.locator('#story-1 .shelf-cover').bounding_box()
        title = page.locator('#story-1 .shelf-title').bounding_box()
        assert 120 <= cover['width'] <= 180
        assert title['y'] >= cover['y'] + cover['height']
        assert 'Noto Serif SC' in page.locator('#story-1 .shelf-excerpt').evaluate('el => getComputedStyle(el).fontFamily')
        panel = page.locator('#stories-list-detail')
        assert panel.is_hidden()
        button = page.locator('#story-button-1')
        assert button.get_attribute('aria-controls') == 'stories-list-detail'
        button.focus()
        page.keyboard.press('Enter')
        assert button.get_attribute('aria-expanded') == 'true'
        panel.wait_for(state='visible')
        expect(panel).to_have_class('shelf-expanded')
        assert panel.is_visible()
        assert panel.locator('.shelf-recommendation p').all_text_contents() == sample[0]['recommendation'].split('\n\n')
        assert '我的评分 4.5 / 5' in panel.inner_text()
        assert panel.locator('.shelf-essay').get_attribute('href') == 'essays/open.html'
        assert panel.bounding_box()['y'] < page.locator('#story-3').bounding_box()['y']
        cover = page.locator('#story-1 .shelf-cover').bounding_box()
        assert panel.bounding_box()['y'] >= cover['y'] + cover['height']
        assert panel.bounding_box()['width'] > cover['width'] * 2
        page.locator('#story-button-2').click()
        expect(panel).to_have_class('shelf-expanded')
        assert button.get_attribute('aria-expanded') == 'false'
        assert panel.locator('h3').inner_text() == '电视剧'
        assert panel.locator('.shelf-essay').count() == 0
        panel.locator('.shelf-close').click()
        panel.wait_for(state='hidden')
        assert panel.is_hidden()
        assert page.locator('#story-button-2').evaluate('el => document.activeElement === el')
        page.keyboard.press('Space')
        panel.wait_for(state='visible')
        expect(panel).to_have_class('shelf-expanded')
        assert panel.is_visible()
        page.keyboard.press('Enter')
        panel.wait_for(state='hidden')
        assert panel.is_hidden()
        assert '/index.html' in page.url and '/shelf.html' not in page.url
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        page.evaluate("localStorage.setItem('theme','light'); _applyTheme('light','light')")
        page.locator('#theme-btn').click()
        assert page.locator('html').evaluate("el => el.classList.contains('dark')") is False
        page.evaluate("localStorage.setItem('theme','system')")
        page.locator('#theme-btn').click()
        assert page.locator('html').evaluate("el => el.classList.contains('dark')") is True
        page.set_viewport_size({'width': 1280, 'height': 900})
        assert page.locator('#stories-list').evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').length") == 3
        assert 180 <= page.locator('#stories .shelf-cover').first.bounding_box()['width'] <= 220
        page.locator('#story-button-4').click()
        expect(panel).to_have_class('shelf-expanded')
        assert panel.locator('.shelf-recommendation').inner_text() == sample[3]['recommendation']
        assert panel.bounding_box()['width'] <= 620
        assert panel.bounding_box()['y'] < page.locator('#story-7').bounding_box()['y']
        assert panel.bounding_box()['y'] > page.locator('#story-6').bounding_box()['y']
        page.set_viewport_size({'width': 390, 'height': 844})
        expect(panel).to_have_css('order', '7')
        assert panel.bounding_box()['y'] < page.locator('#story-5').bounding_box()['y']
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.set_viewport_size({'width': 320, 'height': 700})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        # Interrupt both opening and closing before the browser paints another frame.
        page.evaluate("""() => {
            document.getElementById('story-button-4').click();
            document.getElementById('story-button-1').click();
            document.getElementById('story-button-1').click();
            document.getElementById('story-button-2').click();
        }""")
        expect(panel).to_have_class('shelf-expanded')
        assert panel.is_visible()
        assert panel.locator('h3').inner_text() == '电视剧'
        assert page.locator('#stories .shelf-card-button[aria-expanded=true]').count() == 1
        assert not panel.evaluate('el => el.inert')
        assert panel.evaluate('el => el.style.height') == ''
        page.emulate_media(reduced_motion='reduce')
        panel.locator('.shelf-close').click()
        assert panel.is_hidden()
        page.locator('#story-button-1').click()
        assert panel.is_visible()
        assert panel.evaluate('el => el.getAnimations().length') == 0
        assert not errors
    finally:
        page.close()


def test_stories_empty_failure_and_legacy_redirect(live_server, browser):
    page = browser.new_page()
    page.route('**/data/stories.json*', lambda route: route.fulfill(status=500, body='failed'))
    try:
        page.goto(live_server + '/index.html', wait_until='domcontentloaded')
        assert page.locator('#stories').is_hidden()
        assert page.locator('#stories-nav').is_hidden()
        page.unroute('**/data/stories.json*')
        page.route('**/data/stories.json*', lambda route: route.fulfill(json=[]))
        page.goto(live_server + '/shelf.html', wait_until='domcontentloaded')
        page.wait_for_url('**/index.html#stories', wait_until='domcontentloaded')
        assert page.locator('#stories').is_hidden()
        assert page.locator('#stories-nav').is_hidden()
    finally:
        page.close()


def test_admin_essay_visibility_form_roundtrip(live_server, browser):
    page = browser.new_page()
    essays = [{'slug': 'hidden-demo', 'title': '隐藏测试', 'tag': '随笔', 'visible': False}]
    writes = []
    page.route('**/api/essays', lambda route: route.fulfill(json=essays))

    def save(route):
        writes.append(route.request.post_data_json)
        route.fulfill(json={**essays[0], **writes[-1]})

    page.route('**/api/essays/hidden-demo', save)
    try:
        page.goto(live_server + '/', wait_until='domcontentloaded')
        page.locator('.tab-btn[data-tab="essays"]').click()
        page.locator('#essay-list button', has_text='元数据').first.click()
        page.locator('#essay-form').wait_for(state='visible')
        assert '已隐藏' in page.locator('#essay-list').inner_text()
        assert page.locator('#essay-visible').input_value() == 'false'
        page.locator('#essay-visible').select_option('true')
        page.evaluate('saveEssay()')
        assert writes[-1]['visible'] is True
        page.evaluate('_fillEssayMetaForm({slug: "legacy", title: "Legacy"})')
        assert page.locator('#essay-visible').input_value() == 'true'
        page.locator('#essay-visible').select_option('false')
        page.evaluate('showEssayForm()')
        assert page.locator('#essay-visible').input_value() == 'true'
    finally:
        page.close()
