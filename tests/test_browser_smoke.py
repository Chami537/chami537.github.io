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
    finally:
        page.close()
