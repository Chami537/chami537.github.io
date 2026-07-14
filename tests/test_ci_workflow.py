"""Contracts for CI jobs that must not silently skip important checks."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_browser_smoke_job_installs_and_requires_chromium():
    workflow = (ROOT / '.github' / 'workflows' / 'build-deploy.yml').read_text(encoding='utf-8')

    assert 'browser-smoke:' in workflow
    assert 'needs: browser-smoke' in workflow
    assert 'pip install playwright==1.52.0' in workflow
    assert 'python -m playwright install --with-deps chromium' in workflow
    assert "BROWSER_SMOKE_REQUIRED: '1'" in workflow
    assert 'python -m pytest tests/test_browser_smoke.py -v' in workflow
