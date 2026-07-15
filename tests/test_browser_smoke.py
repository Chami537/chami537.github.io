"""Minimal real-browser checks for the static admin and homepage shells."""

import os
import json
import threading
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
        page.wait_for_timeout(150)
        assert page.locator('#essay-list').count() == 1
        for name in (
            'saveEssay', 'editEssayContent', '_wrapSelection', 'previewEssayContent',
            '_essayTagParts', 'renderEssayTaxonomy', 'saveTagOrder', 'switchEssayTag',
        ):
            assert page.evaluate('typeof ' + name) == 'function'
        page.locator('#essay-list button', has_text='元数据').first.click()
        page.locator('#essay-form').wait_for(state='visible')
        page.evaluate("renderEssayTaxonomy('技术, Python, 教程, 复盘')")
        assert page.locator('#essay-tag').input_value() == '技术, Python, 教程, 复盘'
        assert page.locator('#essay-form .taxonomy-grid.is-tech').count() == 1
        page.locator('#essay-list button', has_text='编辑正文').first.click()
        page.locator('#essay-content-editor').wait_for(state='visible')
    finally:
        page.close()


def test_public_homepage_shell_loads_essay_surface(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/index.html', wait_until='domcontentloaded')
        assert page.locator('#essays-list').count() == 1
        assert page.locator('script[src*="index-essays.js"]').count() == 1
        assert page.evaluate("safeExternalUrl('javascript:alert(1)')") == ''
        assert 'href=' not in page.evaluate("renderContact([{label:'X',handle:'Y',url:'javascript:alert(1)'}])")
        assert page.evaluate("renderWork([{id:1,title:'X',description:'Y',url:'data:text/html,x',tags:[]}])").startswith('<div')
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
