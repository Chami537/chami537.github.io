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


def test_build_job_validates_generated_artifacts_after_build():
    workflow = (ROOT / '.github' / 'workflows' / 'build-deploy.yml').read_text(encoding='utf-8')
    unit_tests = 'python -m pytest tests/ -v --ignore=tests/test_build_artifacts.py'
    build = 'python manage.py build'
    artifact_tests = 'python -m pytest tests/test_build_artifacts.py -v'

    assert unit_tests in workflow
    assert artifact_tests in workflow
    assert workflow.index(unit_tests) < workflow.rindex(build) < workflow.index(artifact_tests)


def test_browser_smoke_builds_before_launching_chromium_tests():
    workflow = (ROOT / '.github' / 'workflows' / 'build-deploy.yml').read_text(encoding='utf-8')
    browser_job = workflow.split('  browser-smoke:', 1)[1].split('\n  build:', 1)[0]

    assert 'python manage.py build' in browser_job
    assert browser_job.index('python manage.py build') < browser_job.index(
        'python -m pytest tests/test_browser_smoke.py -v'
    )
