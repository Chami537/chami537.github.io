import subprocess

from flask import Blueprint, current_app, request, jsonify

bp = Blueprint('git_api', __name__)
from backend.data import BASE_DIR
from backend.crud import require_json


def _run_git(args):
    return subprocess.run(['git'] + args, cwd=BASE_DIR, capture_output=True, text=True, encoding='utf-8')


def _git_error(action, result):
    return jsonify({"error": f"git {action} failed: {result.stderr.strip()}"}), 500


def _require_confirmed():
    data = request.get_json(silent=True) or {}
    if data.get('confirm') is True:
        return None
    return jsonify({"error": "confirm=true required"}), 400


@bp.route('/api/git/status', methods=['GET'])
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

@bp.route('/api/git/commit', methods=['POST'])
@require_json
def git_commit():
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({"error": "Commit message required"}), 400
    add_r = _run_git(['add', '-A'])
    if add_r.returncode != 0:
        return _git_error('add', add_r)
    r = _run_git(['commit', '-m', msg])
    if r.returncode != 0:
        return jsonify({"error": r.stderr.strip()}), 500
    return jsonify({"status": "success", "output": r.stdout.strip()})

@bp.route('/api/git/revert', methods=['POST'])
def git_revert():
    confirm_error = _require_confirmed()
    if confirm_error:
        return confirm_error
    # In test mode, don't actually run destructive git operations
    if current_app.config.get('TESTING'):
        return jsonify({"status": "reverted"})
    stash_r = _run_git(['stash', 'push', '--include-untracked', '-m', 'auto-backup-before-revert'])
    if stash_r.returncode != 0:
        return _git_error('stash', stash_r)
    r = _run_git(['checkout', '.'])
    if r.returncode != 0:
        return _git_error('checkout', r)
    clean_r = _run_git(['clean', '-fd'])
    if clean_r.returncode != 0:
        return _git_error('clean', clean_r)
    return jsonify({"status": "reverted"})

@bp.route('/api/git/diff', methods=['GET'])
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

@bp.route('/api/git/push', methods=['POST'])
def git_push():
    if current_app.config.get('TESTING'):
        return jsonify({"status": "success", "output": "test mode"})
    fetch_r = _run_git(['fetch'])
    if fetch_r.returncode != 0:
        return _git_error('fetch', fetch_r)
    status = _run_git(['status', '-sb']).stdout
    if 'behind' in status:
        return jsonify({"error": "检测到远程仓库有更新，请先通过终端执行 git pull 解决潜在冲突。"}), 409
    r = _run_git(['push'])
    if r.returncode != 0:
        return jsonify({"error": r.stderr.strip()}), 500
    return jsonify({"status": "success", "output": r.stdout.strip()})
