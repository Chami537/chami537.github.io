// Detect and publish Markdown files edited outside the admin panel.

function _localSyncPanel() { return document.getElementById('essay-local-sync-panel'); }

function _renderLocalSyncChanges(changes) {
  var panel = _localSyncPanel();
  if (!panel) return;
  panel.style.display = 'block';
  var publishable = changes.filter(function(item) { return item.status === 'changed'; });
  var recoverable = changes.filter(function(item) { return item.status === 'missing_source'; });
  var html = '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">' +
    '<strong>本地 Markdown 改动</strong><button class="btn btn-sm" onclick="_localSyncPanel().style.display=\'none\'">关闭</button></div>';
  if (!changes.length) {
    panel.innerHTML = html + '<p class="card-meta" style="margin:12px 0 0;">没有发现本地改动。</p>';
    return;
  }
  html += '<div style="margin-top:12px;display:grid;gap:8px;">';
  changes.forEach(function(item, index) {
    var disabled = item.status !== 'changed' ? ' disabled' : '';
    var detail = item.status === 'unregistered' ? '未登记文章，需先导入元数据' :
      (item.status === 'missing_source' ? '缺少 Markdown 源文件，可从已生成页面恢复' :
      (item.password_protected ? '受保护文章（仅接受有效密文）' : '可同步'));
    html += '<label class="card-meta" style="display:flex;align-items:flex-start;gap:8px;">' +
      '<input type="checkbox" data-local-sync-slug="' + esc(item.slug) + '" data-local-sync-status="' + esc(item.status) + '"' + (!disabled ? ' checked' : '') + disabled + '>' +
      '<span><strong>' + esc(item.title || item.slug) + '</strong> <code>' + esc(item.slug) + '</code><br>' + esc(detail) + '</span></label>';
  });
  html += '</div><div style="display:flex;gap:8px;margin-top:14px;">' +
    '<button class="btn btn-primary" onclick="syncSelectedLocalEssays()"' + (!publishable.length ? ' disabled' : '') + '>同步选中内容</button>' +
    '<button class="btn" onclick="restoreSelectedLocalEssaySources()"' + (!recoverable.length ? ' disabled' : '') + '>恢复缺少的 Markdown</button>' +
    '<button class="btn" onclick="scanLocalEssayChanges()">重新扫描</button></div>';
  panel.innerHTML = html;
}

async function restoreSelectedLocalEssaySources() {
  var slugs = Array.from(document.querySelectorAll('[data-local-sync-status="missing_source"]')).map(function(el) {
    return el.getAttribute('data-local-sync-slug');
  });
  if (!slugs.length) return;
  try {
    var data = await api('POST', '/api/essays/restore-local-source', {slugs: slugs});
    toast('已恢复 ' + data.restored + ' 篇 Markdown 源文件');
    await scanLocalEssayChanges();
  } catch (error) { toast('恢复失败: ' + error.message, true); }
}

async function scanLocalEssayChanges() {
  try {
    var data = await api('GET', '/api/essays/local-changes');
    _renderLocalSyncChanges(data.changes || []);
  } catch (error) { toast('扫描失败: ' + error.message, true); }
}

async function syncSelectedLocalEssays() {
  var slugs = Array.from(document.querySelectorAll('[data-local-sync-slug]:checked')).map(function(el) {
    return el.getAttribute('data-local-sync-slug');
  });
  if (!slugs.length) { toast('请先选择要同步的文章', true); return; }
  try {
    var data = await api('POST', '/api/essays/sync-local', {slugs: slugs});
    var failed = (data.results || []).filter(function(item) { return item.status !== 'synced'; });
    if (failed.length) toast('已同步 ' + data.synced + ' 篇，' + failed.length + ' 篇失败', true);
    else toast('已同步 ' + data.synced + ' 篇文章');
    await loadEssays();
    await scanLocalEssayChanges();
  } catch (error) { toast('同步失败: ' + error.message, true); }
}
