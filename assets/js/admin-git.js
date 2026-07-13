// Admin Git actions.

async function refreshGitStatus() {
  try {
    const data = await api('GET', '/api/git/status');
    document.getElementById('git-badge').textContent = data.branch + (data.clean ? '  ✓' : '  ✗');
    var html = '<div class="card">';
    html += '<div class="git-branch">' + esc(data.branch) + '</div>';
    html += '<div class="git-clean' + (data.clean ? ' clean' : ' dirty') + '">' + (data.clean ? '工作区干净' : '有未提交的改动') + '</div>';
    if (data.files && data.files.length > 0) {
      html += '<div class="git-files-label">变更文件:</div>';
      data.files.forEach(function(f) {
        var cls = f.startsWith('??') ? ' untracked' : f.startsWith(' M') || f.startsWith('M ') ? ' modified' : ' added';
        html += '<div class="git-file-row' + cls + '">' + esc(f) + '</div>';
      });
    }
    if (data.diffStat) {
      html += '<div class="git-diff-stat">' + esc(data.diffStat) + '</div>';
    }
    html += '</div>';
    document.getElementById('git-status-cards').innerHTML = html;
  } catch(e) {
    document.getElementById('git-status-cards').innerHTML = '<div class="card" style="color:var(--danger);">错误: ' + esc(e.message) + '</div>';
  }
}

function showCommitDialog() {
  document.getElementById('commit-dialog').showModal();
}

document.getElementById('commit-form').addEventListener('submit', async (e) => {
  const msg = document.getElementById('commit-msg').value;
  try {
    const result = await api('POST', '/api/git/commit', { message: msg });
    toast('Committed: ' + (result.output || ''));
    document.getElementById('commit-dialog').close();
    document.getElementById('commit-msg').value = '';
    refreshGitStatus();
  } catch(e) { toast(e.message, true); }
});

async function confirmRevert() {  const confirmed = await confirmDialog('确定撤销所有未提交的改动？此操作不可恢复。');
  if (!confirmed) return;
  await api('POST', '/api/git/revert', { confirm: true });
  toast('已撤销');
  refreshGitStatus();
  loadWork(); loadFriends(); loadContact(); loadMusic();
  document.dispatchEvent(new Event('admin:data-reset'));
}

async function showGitDiff() {
  try {
    var data = await api('GET', '/api/git/diff');
    var el = document.getElementById('diff-content');
    // Simple color: + lines green, - lines red
    var html = (data.diff || '(no changes)').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    html = html.replace(/^(\+.*)$/gm, '<span class="diff-added">$1</span>');
    html = html.replace(/^(-.*)$/gm, '<span class="diff-removed">$1</span>');
    html = html.replace(/^(@@.*@@)$/gm, '<span class="diff-hunk">$1</span>');
    el.innerHTML = html;
    document.getElementById('diff-dialog').showModal();
  } catch(e) { toast(e.message, true); }
}

async function handlePush() {
  try {
  const confirmed = await confirmDialog('确定推送到远程仓库？');
  if (!confirmed) return;    await api('POST', '/api/git/push');
    toast('Push 成功');
    refreshGitStatus();
  } catch(e) { toast(e.message, true); }
}

