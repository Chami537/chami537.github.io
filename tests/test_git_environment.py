"""Real Git hooks must use the admin server's Python without shell activation."""
import os
import sys

import pytest

from backend.routes import git_api


@pytest.mark.parametrize('hook_exit', [0, 1])
def test_commit_hook_uses_server_python_and_still_blocks_failures(tmp_path, monkeypatch, hook_exit):
    monkeypatch.setattr(git_api, 'BASE_DIR', str(tmp_path))
    # Match launching the venv interpreter directly from an unactivated shell.
    monkeypatch.setenv('PATH', '/usr/bin:/bin')
    parent_path = os.environ['PATH']
    assert git_api._run_git(['init']).returncode == 0
    (tmp_path / 'content.txt').write_text('test content\n', encoding='utf-8')
    assert git_api._run_git(['add', 'content.txt']).returncode == 0
    hook = tmp_path / '.git' / 'hooks' / 'pre-commit'
    hook.write_text(
        '#!/bin/sh\n'
        f"python -c 'import sys; print(sys.prefix); sys.exit({hook_exit})'\n",
        encoding='utf-8',
    )
    hook.chmod(0o755)

    result = git_api._run_git([
        '-c', 'user.name=Hook Test', '-c', 'user.email=hook@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-m', 'Test hook interpreter',
    ])

    assert sys.prefix in result.stdout + result.stderr
    assert (result.returncode == 0) is (hook_exit == 0)
    head = git_api._run_git(['rev-parse', '--verify', 'HEAD'])
    assert (head.returncode == 0) is (hook_exit == 0)
    assert os.environ['PATH'] == parent_path
