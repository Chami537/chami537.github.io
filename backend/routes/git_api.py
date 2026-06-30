import subprocess

from flask import request, jsonify

from backend.app import app
from backend.data import BASE_DIR


def _run_git(args):
    return subprocess.run(['git'] + args, cwd=BASE_DIR, capture_output=True, text=True, encoding='utf-8')


@app.route('/api/git/status', methods=['GET'])
def git_status():
    r = _run_git(['status', '--short'])
    diff = _run_git(['diff', '--stat'])
    branch = _run_git(['branch', '--show-current'])
    return jsonify({
        "branch": branch.stdout.strip(),
        "files": r.stdout.strip().split('\n') if r.stdout.strip() else [],
        "diffStat": diff.stdout.strip(),
        "clean": r.stdout.strip() == ''
    })

@app.route('/api/git/commit', methods=['POST'])
def git_commit():
    if not isinstance(request.json, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({"error": "Commit message required"}), 400
    add_r = _run_git(['add', '-A'])
    if add_r.returncode != 0:
        return jsonify({"error": "git add failed: " + add_r.stderr.strip()}), 500
    r = _run_git(['commit', '-m', msg])
    if r.returncode != 0:
        return jsonify({"error": r.stderr.strip()}), 500
    return jsonify({"status": "success", "output": r.stdout.strip()})

@app.route('/api/git/revert', methods=['POST'])
def git_revert():
    # Auto-backup before destructive revert (include untracked files)
    _run_git(['stash', 'push', '--include-untracked', '-m', 'auto-backup-before-revert'])
    r = _run_git(['checkout', '.'])
    if r.returncode != 0:
        return jsonify({"error": "git checkout failed: " + r.stderr.strip()}), 500
    # Remove untracked files that checkout can't touch
    clean_r = _run_git(['clean', '-fd'])
    if clean_r.returncode != 0:
        return jsonify({"error": "git clean failed: " + clean_r.stderr.strip()}), 500
    return jsonify({"status": "reverted"})

@app.route('/api/git/diff', methods=['GET'])
def git_diff():
    unstaged = _run_git(['diff', '--color=never'])
    staged = _run_git(['diff', '--cached', '--color=never'])
    parts = []
    if staged.stdout.strip():
        parts.append('--- Staged (即将提交) ---\n' + staged.stdout)
    if unstaged.stdout.strip():
        if parts:
            parts.append('')
        parts.append('--- Unstaged (未暂存) ---\n' + unstaged.stdout)
    diff_text = '\n'.join(parts).strip() or '(no changes)'
    return jsonify({"diff": diff_text})

@app.route('/api/git/push', methods=['POST'])
def git_push():
    # Fetch remote first
    fetch_r = _run_git(['fetch'])
    if fetch_r.returncode != 0:
        return jsonify({"error": "git fetch failed: " + fetch_r.stderr.strip()}), 500
    status = _run_git(['status', '-sb']).stdout
    if 'behind' in status:
        return jsonify({"error": "检测到远程仓库有更新，请先通过终端执行 git pull 解决潜在冲突。"}), 409
    r = _run_git(['push'])
    if r.returncode != 0:
        return jsonify({"error": r.stderr.strip()}), 500
    return jsonify({"status": "success", "output": r.stdout.strip()})
