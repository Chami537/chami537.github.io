"""Minimal real-browser checks for the static admin and homepage shells."""

import threading

import pytest
from werkzeug.serving import make_server

from backend.app import app


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
    playwright = pytest.importorskip('playwright.sync_api')
    driver = playwright.sync_playwright().start()
    try:
        yield driver.chromium.launch(headless=True)
    except Exception as exc:
        pytest.skip(f'Chromium is unavailable: {exc}')
    finally:
        driver.stop()


def test_admin_shell_loads_shared_modules_and_switches_tabs(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/', wait_until='networkidle')
        assert page.title() == 'Chami — Site Admin'
        assert page.evaluate("typeof api") == 'function'
        assert page.evaluate("typeof switchTab") == 'function'
        page.locator('.tab-btn[data-tab="essays"]').click()
        page.wait_for_timeout(150)
        assert page.locator('#essay-list').count() == 1
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
        page.goto(live_server + '/', wait_until='networkidle')
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
        page.goto(live_server + '/', wait_until='networkidle')
        page.locator('#dashboard-content').wait_for(state='visible')
        assert page.locator('#dashboard-counts .dashboard-count-item').count() > 0

        page.locator('.tab-btn[data-tab="photos"]').click()
        page.locator('#photo-grid .photo-card').first.wait_for(state='visible')
        assert page.locator('#story-editor-list .story-edit-card').count() > 0

        page.locator('.tab-btn[data-tab="music"]').click()
        page.locator('#music-list .card').first.wait_for(state='visible')
        assert page.locator('#music-list .card').count() > 0
    finally:
        page.close()


def test_admin_health_tab_renders_checks_and_filters(live_server, browser):
    page = browser.new_page()
    try:
        page.goto(live_server + '/', wait_until='networkidle')
        page.locator('.tab-btn[data-tab="health"]').click()
        page.locator('#health-content').wait_for(state='visible')
        assert page.locator('#health-checks .health-check').count() >= 8
        page.locator('.health-filter button').nth(2).click()
        assert page.locator('#health-checks .health-check:not([hidden])').count() == 0
        assert page.locator('#health-history-list').count() == 1
    finally:
        page.close()


def test_admin_tabs_keep_active_health_tab_aligned_on_narrow_viewport(live_server, browser):
    page = browser.new_page(viewport={'width': 634, 'height': 400})
    try:
        page.goto(live_server + '/', wait_until='networkidle')
        page.locator('.tab-btn[data-tab="health"]').click()
        box = page.locator('.tabs').bounding_box()
        tab = page.locator('.tab-btn[data-tab="health"]').bounding_box()
        assert box['x'] <= tab['x']
        assert tab['x'] + tab['width'] <= box['x'] + box['width']
    finally:
        page.close()
