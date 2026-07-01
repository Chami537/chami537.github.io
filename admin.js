// ═══════════════════════════════════
// Auth
// ═══════════════════════════════════
async function doLogin() {
  var pw = document.getElementById('login-password').value;
  var r = await fetch('/api/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})});
  if (r.ok) {
    document.getElementById('login-overlay').style.display = 'none';
    document.getElementById('login-error').style.display = 'none';
    location.reload();
  } else {
    document.getElementById('login-error').style.display = 'block';
  }
}

async function doLogout() {
  await fetch('/api/logout', {method:'POST'});
  location.reload();
}

async function checkAuth() {
  var r = await fetch('/api/about');
  if (r.status === 401) {
    document.getElementById('login-overlay').style.display = 'flex';
  }
}

checkAuth();

// ═══════════════════════════════════
// Globals
// ═══════════════════════════════════
let isDirty = false;
document.addEventListener('input', (e) => {
  if (e.target.matches('input:not(#commit-msg), textarea:not(#commit-msg)')) isDirty = true;
});
window.addEventListener('beforeunload', (e) => {
  if (isDirty) { e.preventDefault(); e.returnValue = ''; }
});

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body && !(body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  } else if (body instanceof FormData) {
    opts.body = body;
  }
  const r = await fetch(path, opts);
  if (r.status === 401) {
    document.getElementById('login-overlay').style.display = 'flex';
    throw new Error('Unauthorized — please login');
  }
  if (!r.ok) {
    const err = await r.json().catch(() => ({ error: r.statusText }));
    throw new Error(err.error || r.statusText);
  }
  return r.json();
}

function toast(msg, err) {
  const t = document.createElement('div');
  t.className = 'toast ' + (err ? 'toast-err' : 'toast-ok');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

function markClean() { isDirty = false; }
function hidePanel(id) { document.getElementById(id).style.display = 'none'; }

// Shared drag-and-drop reorder helpers
var _dragState = { idx: -1 };
function _dragStart(e, idx) {
  _dragState.idx = idx;
  e.dataTransfer.effectAllowed = 'move';
  e.target.style.opacity = '0.5';
}
function _dragOver(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }
function _dragEnd(e) { e.target.style.opacity = '1'; _dragState.idx = -1; }

var MONTHS_NUM = {Jan:'01',Feb:'02',Mar:'03',Apr:'04',May:'05',Jun:'06',Jul:'07',Aug:'08',Sep:'09',Oct:'10',Nov:'11',Dec:'12'};
var MONTHS_ARR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function showEntryForm(cfg) {
  var form = document.getElementById(cfg.formId);
  if (form.style.display === 'block') { form.style.display = 'none'; return; }
  document.getElementById(cfg.editId).value = '';
  cfg.fields.forEach(function(id) { document.getElementById(id).value = ''; });
  if (cfg.defaults) {
    Object.keys(cfg.defaults).forEach(function(id) {
      document.getElementById(id).value = cfg.defaults[id];
    });
  }
  document.getElementById(cfg.formId + '-title').textContent = cfg.title;
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
}

// ═══════════════════════════════════
// Tabs
// ═══════════════════════════════════
async function loadTracks() {
  var data = await api('GET', '/api/tracks');
  var html = '';
  data.forEach(function(t, i) {
    html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--line);">' +
      '<span>' + esc(t.name) + ' <code style="color:#999">' + esc(t.file) + '</code></span>' +
      '<button class="btn btn-sm" style="color:#c00" onclick="deleteTrack(' + i + ')">删除</button>' +
      '</div>';
  });
  document.getElementById('tracks-list').innerHTML = html || '<p style="color:#999">暂无轨迹</p>';
}

var _lastTrackFile = '';

async function uploadTrackFile(f, autoName) {
  var fd = new FormData(); fd.append('file', f);
  var r = await api('POST', '/api/tracks/upload', fd);
  if (r.file) {
    _lastTrackFile = r.file;
    if (autoName) { var tn = document.getElementById('track-name'); if (tn) tn.value = r.file.replace('.gpx',''); }
    loadTracks();
    toast('已上传: ' + r.file);
  }
}

async function renameLastTrack(name) {
  if (!_lastTrackFile || !name.trim()) return;
  var tracks = await api('GET', '/api/tracks');
  for (var i = tracks.length - 1; i >= 0; i--) {
    if (tracks[i].file === _lastTrackFile) {
      await api('DELETE', '/api/tracks/' + i);
      await api('POST', '/api/tracks', {name: name.trim(), file: _lastTrackFile});
      loadTracks();
      break;
    }
  }
}


function handleTrackDrop(e) {
  var files = e.dataTransfer.files;
  if (files.length) handleTrackFile(files);
}

function handleTrackFile(files) {
  Array.from(files).forEach(function(f) {
    if (f.name.toLowerCase().endsWith('.gpx')) uploadTrackFile(f, true);
  });
}

async function deleteTrack(i) {
  if (!confirm('删除此轨迹？')) return;
  await api('DELETE', '/api/tracks/' + i);
  loadTracks();
}

function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  var tabBtn = document.querySelector('.tab-btn[onclick="switchTab(\'' + name + '\')"]');
  if (tabBtn) tabBtn.classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
  if (name === 'work') loadWork();
  if (name === 'essays') loadEssays();
  if (name === 'photos') loadPhotos();
  if (name === 'about') loadAbout();
  if (name === 'contact') loadContact();
  if (name === 'friends') loadFriends();
  if (name === 'tracks') loadTracks();
    if (name === 'music') loadMusic();
  if (name === 'stack') loadStack();
  if (name === 'git') refreshGitStatus();
  if (name === 'readme') loadReadme();
}

// ═══════════════════════════════════
// About
async function loadAbout() {
  try {
    const data = await api('GET', '/api/about');
    document.getElementById('about-content').value = data.content || '';
    document.getElementById('about-avatar-preview').src = data.avatar || '';
    document.getElementById('about-tags').value = (data.tags || []).join(', ');
    renderAboutTagChips();
  } catch(e) { toast(e.message, true); }
}

async function uploadAvatar() {
  try {
  var file = document.getElementById('about-avatar-file').files[0];
  if (!file) return;
  var fd = new FormData();
  fd.append('file', file);    var result = await api('POST', '/api/about/upload-avatar', fd);
    document.getElementById('about-avatar-preview').src = result.url;
    document.getElementById('about-avatar-preview').dataset.path = result.url;
    toast('头像已上传');
  } catch(e) { toast(e.message, true); }
}

async function saveAbout() {
  try {
    await api('PUT', '/api/about', {
      content: document.getElementById('about-content').value,
      tags: (function() { var all = getAboutTags(), sel = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean); return all.filter(function(t){return sel.indexOf(t)>=0;}); })(),
      avatar: document.getElementById('about-avatar-preview').dataset.path || document.getElementById('about-avatar-preview').src.split('/').slice(-2).join('/')
    });
    markClean();
    toast('简介已保存');
  } catch(e) { toast(e.message, true); }
}

// README
// ═══════════════════════════════════
async function loadReadme() {
  try {
    var data = await api('GET', '/api/readme');
    document.getElementById('readme-content').value = data.content || '';
  } catch(e) { toast(e.message, true); }
}

async function saveReadme() {
  try {
    await api('PUT', '/api/readme', {
      content: document.getElementById('readme-content').value
    });
    markClean();
    toast('README 已保存');
  } catch(e) { toast(e.message, true); }
}

// Work
// ═══════════════════════════════════
async function loadWork() {
  try {
    const data = await api('GET', '/api/work');
    document.getElementById('work-list').innerHTML = data.map(w => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${pad2(w.id)} ${esc(w.title)}</div>
          <div class="card-meta">${esc(w.description)}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editWork(${w.id})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteWork(${w.id})">删除</button>
        </div>
      </div>
      <div class="tags">${(w.tags||[]).map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>
      <div class="card-meta" style="margin-top:6px;">🔗 ${esc(w.url)} ${w.repo ? '· ⭐ '+esc(w.repo) : ''}</div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function pad2(n) { return n.toString().padStart(2, '0'); }
function esc(s) { const d = document.createElement('div'); d.textContent = s != null ? s : ''; return d.innerHTML; }

async function editWork(id) {  const form = document.getElementById('work-form');
  if (form.style.display === 'block' && document.getElementById('work-edit-id').value == id) {
    form.style.display = 'none'; return;
  }
  const data = await api('GET', '/api/work');
  const w = data.find(x => x.id === id);
  if (!w) return;
  document.getElementById('work-edit-id').value = id;
  document.getElementById('work-title').value = w.title;
  document.getElementById('work-desc').value = w.description;
  document.getElementById('work-url').value = w.url;
  document.getElementById('work-repo').value = w.repo || '';
  document.getElementById('work-tags').value = (w.tags||[]).join(', ');
  document.getElementById('work-form-title').textContent = '编辑项目';
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
}

function showWorkForm() {
  showEntryForm({ formId: 'work-form', editId: 'work-edit-id', title: '新建项目',
    fields: ['work-title','work-desc','work-url','work-repo','work-tags'] });
}


async function saveWork() {
  try {
  const id = document.getElementById('work-edit-id').value;
  const item = {
    title: document.getElementById('work-title').value,
    description: document.getElementById('work-desc').value,
    url: document.getElementById('work-url').value,
    repo: document.getElementById('work-repo').value,
    tags: document.getElementById('work-tags').value.split(',').map(s => s.trim()).filter(Boolean),
  };    if (id) {
      await api('PUT', '/api/work/' + id, item);
    } else {
      await api('POST', '/api/work', item);
    }
    markClean();
    hidePanel('work-form');
    loadWork();
    toast(id ? '项目已更新' : '项目已创建');
  } catch(e) { toast(e.message, true); }
}

async function deleteWork(id) {  const confirmed = await confirmDialog('确定删除这个项目？');
  if (!confirmed) return;
  await api('DELETE', '/api/work/' + id);
  if (document.getElementById('work-edit-id').value == id) hidePanel('work-form');
  loadWork();
  toast('项目已删除');
}

// ═══════════════════════════════════
// Essays
// ═══════════════════════════════════
async function loadEssays() {
  try {
    const data = await api('GET', '/api/essays');
    _essayAllData = data;
    let tags = getTags();

    data.forEach(e => {
      if (e.tag) {
        e.tag.split(/[,，]/).map(function(s) { return s.trim(); }).filter(Boolean).forEach(function(pt) {
          if (!tags.includes(pt)) tags.push(pt);
        });
      }
    });
    saveTags(tags);

    if (!currentEssayTag && tags.length > 0) {
      currentEssayTag = tags[0];
    }

    let tabsHtml = '';
    tags.forEach(tag => {
      let isActive = tag === currentEssayTag;
      let btnStyle = isActive
        ? 'padding: 6px 16px; border: none; background: var(--accent); color: #fff; border-radius: 20px; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap;'
        : 'padding: 6px 16px; border: 1px solid var(--border); background: var(--card-bg); color: var(--muted); border-radius: 20px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all .2s; white-space: nowrap;';

      let hoverAttr = !isActive ? 'onmouseover="this.style.borderColor=\'var(--accent)\'; this.style.color=\'var(--accent)\'" onmouseout="this.style.borderColor=\'var(--border)\'; this.style.color=\'var(--muted)\'"' : '';

      if (essayDeleteTagMode) {
        tabsHtml += '<span style="display:inline-flex;align-items:center;gap:4px;' + btnStyle + '">' +
          '<span onclick="switchEssayTag(\'' + esc(tag) + '\')" style="cursor:pointer;">' + esc(tag) + '</span>' +
          '<span onclick="event.stopPropagation();deleteTagFromTabs(\'' + esc(tag) + '\')" style="cursor:pointer;font-size:14px;opacity:0.5;line-height:1;" title="删除标签">\u00D7</span>' +
          '</span>';
      } else {
        tabsHtml += '<button style="' + btnStyle + '" ' + hoverAttr + ' onclick="switchEssayTag(\'' + esc(tag) + '\')">' + esc(tag) + '</button>';
      }
    });
    document.getElementById('essay-tag-tabs').innerHTML = tabsHtml;

    const filteredData = data.filter(e => {
       if (!e.tag) return currentEssayTag === '随笔';
       let essayTags = e.tag.split(/[,，]/).map(function(s) { return s.trim(); }).filter(Boolean);
       return essayTags.includes(currentEssayTag);
    });

    if (filteredData.length === 0) {
       document.getElementById('essay-list').innerHTML = '<div style="text-align:center; padding: 60px; color: var(--muted); font-size: 13px; border: 1px dashed var(--border); border-radius: 8px; background: var(--card-bg);">该标签下暂无文章，点击右上角新建</div>';
       return;
    }

    document.getElementById('essay-list').innerHTML = filteredData.map(e => `
    <div class="card">
      <div class="card-header">
        <div style="display:flex;align-items:center;gap:10px;">
          ${pinBtn(e)}
          <div>
            <div class="card-title">${esc(e.title)}</div>
            <div class="card-meta">${esc(e.date)} · ${e.readTime} min · slug: ${esc(e.slug)}</div>
            <div class="card-meta" style="font-style:italic;">${esc(e.epigraph||'')}</div>
          </div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editEssayMeta('${esc(e.slug)}')">元数据</button>
          <button class="btn btn-sm" onclick="editEssayContent('${esc(e.slug)}')">编辑正文</button>
          <button class="btn btn-sm btn-danger" onclick="deleteEssay('${esc(e.slug)}')">删除</button>
        </div>
      </div>
      <div class="card-meta" style="margin-top:4px;"><a href="https://github.com/Chami537/chami537.github.io/discussions?discussions_q=${esc(e.slug)}" target="_blank" rel="noopener" style="color:var(--muted);text-decoration:none;font-size:11px;">💬 查看讨论 →</a></div>
    </div>
  `).join('');
  updatePinCount(data);
  } catch(e) { toast(e.message, true); }
}

// ═══ Tag system ═══
// 全局状态：记录当前激活的标签
let currentEssayTag = null;
let essayDeleteTagMode = false;

// 标签库 helpers
function _tagLib(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key) || fallback); }
  catch(e) { return JSON.parse(fallback); }
}
function _saveTagLib(key, tags) { localStorage.setItem(key, JSON.stringify(tags)); }
function _promptTag(key, fallback, onAdd) {
  var t = prompt('请输入新标签名称：');
  if (!t || !t.trim()) return;
  var tags = _tagLib(key, fallback);
  if (tags.indexOf(t.trim()) < 0) { tags.push(t.trim()); _saveTagLib(key, tags); }
  onAdd(t.trim());
}
function _toggleDeleteTagMode(btnId, flag, onDone) {
  var btn = document.getElementById(btnId);
  var on = !flag;
  btn.textContent = on ? '完成' : '删除标签';
  btn.style.color = on ? 'var(--danger)' : '';
  btn.style.borderColor = on ? 'var(--danger)' : '';
  onDone();
  return on;
}

// 初始化标签库
function getTags() { return _tagLib('essay-tags', '["随笔","摄影","剪辑","骑行","投资"]'); }
function saveTags(tags) { _saveTagLib('essay-tags', tags); }

function switchEssayTag(tag) {
  hidePanel('essay-form');
  hideEssayContentEditor();
  currentEssayTag = tag;
  loadEssays();
}

function promptNewTag() {
  _promptTag('essay-tags', '["随笔","摄影","剪辑","骑行","投资"]', switchEssayTag);
}

function toggleDeleteTagMode() {
  essayDeleteTagMode = _toggleDeleteTagMode('delete-tag-btn', essayDeleteTagMode, loadEssays);
}

function deleteTagFromTabs(tag) {
  if (!confirm('确定永久删除标签 "' + tag + '"？')) return;
  // Strip this tag from all essays that reference it, then remove from library
  var affected = (_essayAllData || []).filter(function(e) {
    var essayTags = (e.tag || '').split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
    return essayTags.indexOf(tag) >= 0;
  });
  var updates = affected.map(function(e) {
    var newTags = (e.tag || '').split(/[,，]/).map(function(s){return s.trim();}).filter(function(t) { return t !== tag; });
    if (newTags.length === 0) newTags = ['随笔'];
    return api('PUT', '/api/essays/' + e.slug, {
      slug: e.slug, title: e.title, tag: newTags.join(', '),
      date: e.date, epigraph: e.epigraph || '', excerpt: e.excerpt || ''
    });
  });
  Promise.all(updates).then(function() {
    var tags = getTags();
    var idx = tags.indexOf(tag);
    if (idx >= 0) { tags.splice(idx, 1); saveTags(tags); }
    if (currentEssayTag === tag) { currentEssayTag = null; }
    loadEssays();
  }).catch(function(err) {
    toast('删除失败: ' + (err.message || '未知错误'), true);
    loadEssays();
  });
}

// ═══ Pin system ═══
function pinBtn(e) {
  var pinned = e.pinned || false;
  var totalPinned = (_essayAllData || []).filter(function(x) { return x.pinned; }).length;
  var atLimit = totalPinned >= 5;
  if (pinned) {
    return '<button class="pin-toggle pinned" onclick="togglePin(\'' + esc(e.slug) + '\')" title="取消置顶" style="width:32px;height:32px;border:1px solid #ffb800;background:#fff8e0;border-radius:6px;cursor:pointer;font-size:16px;line-height:1;color:#ffb800;flex-shrink:0;">📍</button>';
  }
  if (atLimit) {
    return '<button disabled style="width:32px;height:32px;border:1px solid #eee;background:#f5f5f5;border-radius:6px;font-size:16px;line-height:1;color:#ccc;flex-shrink:0;cursor:not-allowed;" title="已满5篇">📌</button>';
  }
  return '<button class="pin-toggle" onclick="togglePin(\'' + esc(e.slug) + '\')" title="置顶" style="width:32px;height:32px;border:1px solid var(--border);background:var(--card-bg);border-radius:6px;cursor:pointer;font-size:16px;line-height:1;color:var(--muted);flex-shrink:0;transition:all .15s;" onmouseover="this.style.borderColor=\'#ffb800\';this.style.color=\'#ffb800\'" onmouseout="this.style.borderColor=\'var(--border)\';this.style.color=\'var(--muted)\'">📌</button>';
}

var _essayAllData = [];
async function togglePin(slug) {
  try {
    var r = await api('POST', '/api/essays/' + slug + '/pin');
    toast(r.pinned ? '已置顶 (' + r.count + '/5)' : '已取消置顶 (' + r.count + '/5)');
    // Update local state
    var e = _essayAllData.find(function(x) { return x.slug === slug; });
    if (e) e.pinned = r.pinned;
    loadEssays();
  } catch(e) { toast(e.message, true); }
}

function updatePinCount(data) {
  _essayAllData = data || [];
  var c = data.filter(function(e) { return e.pinned; }).length;
  document.getElementById('pin-count').textContent = c > 0 ? '\u{1F4CC} \u5DF2\u7F6E\u9876 ' + c + '/5' : '';
}

function renderTagChips(selected) {
  var tags = getTags();
  var html = '';
  tags.forEach(function(t) {
    var active = (selected || '').split(/[,，]/).map(function(s){return s.trim();}).indexOf(t) >= 0;
    html += '<span class="tag-chip' + (active ? ' active' : '') + '" data-tag="' + esc(t) + '">' +
      '<span onclick="toggleTag(\'' + esc(t) + '\')">' + esc(t) + '</span>' +
      '</span>';
  });
  document.getElementById('tag-chips').innerHTML = html;
  document.getElementById('essay-tag-display').textContent = selected ? '已选: ' + selected : '';
}



function toggleTag(tag) {
  var cur = document.getElementById('essay-tag').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
  var idx = cur.indexOf(tag);
  if (idx >= 0) {
    if (cur.length <= 1) return; // must have at least one tag
    cur.splice(idx, 1);
  } else { cur.push(tag); }
  var val = cur.join(', ');
  document.getElementById('essay-tag').value = val;
  renderTagChips(val);
}


// ═══ About tag system ═══
function getAboutTags() {
  var stored = _tagLib('about-tags', '["CS STUDENT","PHOTOGRAPHER","SHENZHEN"]');
  var cur = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
  cur.forEach(function(t) { if (stored.indexOf(t) < 0) stored.push(t); });
  return stored;
}
function saveAboutTags(tags) { _saveTagLib('about-tags', tags); }

var _aboutEditingTag = null;

function renderAboutTagChips() {
  var tags = getAboutTags();
  var selected = document.getElementById('about-tags').value;
  var selList = selected ? selected.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean) : [];
  var html = '';
  tags.forEach(function(t, i) {
    var active = selList.indexOf(t) >= 0;
    html += '<span class="tag-chip' + (active ? ' active' : '') + '" data-tag="' + esc(t) + '" data-idx="' + i + '" draggable="true"' +
      ' ondragstart="aboutDragStart(event,' + i + ')" ondragover="aboutDragOver(event)" ondrop="aboutDrop(event,' + i + ')" ondragend="aboutDragEnd(event)">' +
      '<span onclick="editAboutChip(\'' + esc(t) + '\')">' + esc(t) + '</span>' +
      '<span class="tag-del" onclick="event.stopPropagation();deleteAboutTag(\'' + esc(t) + '\')" title="删除标签">×</span>' +
      '</span>';
  });
  document.getElementById('about-tag-chips').innerHTML = html;
}

function editAboutChip(tag) {
  _aboutEditingTag = tag;
  var input = document.getElementById('about-new-tag');
  input.value = tag;
  input.focus();
  input.select();
}

function aboutDragStart(e, idx) { _dragStart(e, idx); }
function aboutDragOver(e) { _dragOver(e); }

function aboutDrop(e, targetIdx) {
  e.preventDefault();
  var fromIdx = _dragState.idx;
  if (fromIdx < 0 || fromIdx === targetIdx) return;
  var tags = getAboutTags();
  var moved = tags.splice(fromIdx, 1)[0];
  tags.splice(targetIdx, 0, moved);
  saveAboutTags(tags);
  _dragState.idx = -1;
  renderAboutTagChips();
  saveAbout();
}

function aboutDragEnd(e) { _dragEnd(e); }

function deleteAboutTag(tag) {
  var tags = getAboutTags();
  var idx_t = tags.indexOf(tag);
  if (idx_t >= 0) { tags.splice(idx_t, 1); saveAboutTags(tags); }
  var cur = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
  var idx_c = cur.indexOf(tag);
  if (idx_c >= 0) { cur.splice(idx_c, 1); document.getElementById('about-tags').value = cur.join(', '); }
  renderAboutTagChips();
}

function toggleAboutTag(tag) {
  var cur = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
  var idx = cur.indexOf(tag);
  if (idx >= 0) { cur.splice(idx, 1); } else { cur.push(tag); }
  document.getElementById('about-tags').value = cur.join(', ');
  renderAboutTagChips();
}

function addAboutCustomTag() {
  var input = document.getElementById('about-new-tag');
  var tag = input.value.trim();
  if (!tag) return;
  var tags = getAboutTags();
  // If editing an existing tag (rename)
  if (_aboutEditingTag && tags.indexOf(_aboutEditingTag) >= 0 && tag !== _aboutEditingTag) {
    var idx = tags.indexOf(_aboutEditingTag);
    tags[idx] = tag;
    // Also update hidden input selection
    var cur = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
    var ci = cur.indexOf(_aboutEditingTag);
    if (ci >= 0) { cur[ci] = tag; document.getElementById('about-tags').value = cur.join(', '); }
    saveAboutTags(tags);
    _aboutEditingTag = null;
    input.value = '';
    renderAboutTagChips();
    return;
  }
  _aboutEditingTag = null;
  if (tags.indexOf(tag) < 0) { tags.push(tag); saveAboutTags(tags); }
  input.value = '';
  renderAboutTagChips();
  toggleAboutTag(tag);
}

function genSlug(title) {
  // Always use essay- prefix + random hex — robust against any title (Chinese, mixed script, emoji, etc.)
  return 'essay-' + Math.random().toString(16).slice(2, 10);
}


function showEssayForm() {
  showEntryForm({ formId: 'essay-form', editId: 'essay-edit-slug', title: '新建文章',
    fields: ['essay-title','essay-date','essay-readtime','essay-epigraph','essay-excerpt'] });
  var now = new Date();
  document.getElementById('essay-date').value = now.getFullYear() + '-' + pad2(now.getMonth()+1) + '-' + pad2(now.getDate());
  document.getElementById('essay-readtime').value = '4';
  let defaultTag = currentEssayTag || '随笔';
  document.getElementById('essay-tag').value = defaultTag;
  renderTagChips(defaultTag);
}


async function editEssayMeta(slug) {  const form = document.getElementById('essay-form');
  if (form.style.display === 'block' && document.getElementById('essay-edit-slug').value === slug) {
    form.style.display = 'none'; return;
  }
  const data = await api('GET', '/api/essays');
  const e = data.find(x => x.slug === slug);
  if (!e) return;
  document.getElementById('essay-edit-slug').value = slug;
  document.getElementById('essay-title').value = e.title;
  document.getElementById('essay-tag').value = e.tag || '';
  document.getElementById('essay-date').value = e.date || '';
  document.getElementById('essay-readtime').value = e.readTime || 1;
  document.getElementById('essay-epigraph').value = e.epigraph || '';
  document.getElementById('essay-excerpt').value = e.excerpt || '';
  renderTagChips(e.tag || '');
  document.getElementById('essay-form-title').textContent = '编辑元数据';
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
}

async function saveEssay() {
  try {
  var editSlug = document.getElementById('essay-edit-slug').value;
  var slug = editSlug || genSlug('');
  var item = {
    slug: slug,
    title: document.getElementById('essay-title').value,
    tag: document.getElementById('essay-tag').value,
    date: document.getElementById('essay-date').value,
    epigraph: document.getElementById('essay-epigraph').value,
    excerpt: document.getElementById('essay-excerpt').value,
  };    if (editSlug) {
      await api('PUT', '/api/essays/' + editSlug, item);
      toast('元数据已更新');
    } else {
      await api('POST', '/api/essays', item);
      toast('随笔已创建，HTML 文件已生成');
    }
    markClean();
    hidePanel('essay-form');
    loadEssays();
  } catch(e) { toast(e.message, true); }
}

async function editEssayContent(slug) {
  const editor = document.getElementById('essay-content-editor');
  if (editor.style.display === 'block' && editor.dataset.slug === slug) {
    editor.style.display = 'none'; return;
  }
  // Autosave current essay before switching
  var oldSlug = editor.dataset.slug;
  if (oldSlug && oldSlug !== slug) {
    var md = document.getElementById('essay-content-md').value;
    if (md.trim()) localStorage.setItem('draft:' + oldSlug, md);
  }
  clearInterval(_autosaveInterval);
  editor.style.display = 'block';
  document.getElementById('essay-content-title').textContent = '— ' + slug;
  editor.dataset.slug = slug;
  try {
    const data = await api('GET', '/api/essays/' + slug + '/content');
    document.getElementById('essay-content-md').value = data.content || '';
    _updateWordCount();
    startAutosave(slug);
    checkDraft(slug);
  } catch(e) {
    document.getElementById('essay-content-md').value = '';
    toast('加载失败: ' + e.message, true);
  }
  editor.scrollIntoView({ behavior: 'smooth' });
}

function hideEssayContentEditor() {
  var slug = document.getElementById('essay-content-editor').dataset.slug;
  if (slug) localStorage.setItem('draft-time:' + slug, Date.now());
  clearInterval(_autosaveInterval);
  document.getElementById('essay-content-editor').style.display = 'none';
  document.getElementById('essay-preview').style.display = 'none';
}

// ═══ Editor: Tab + Shortcuts + Autosave + Drag-Drop ═══
function _wrapSelection(ta, before, after) {
  var s = ta.selectionStart, e = ta.selectionEnd;
  var sel = ta.value.slice(s, e);
  ta.value = ta.value.slice(0, s) + before + sel + after + ta.value.slice(e);
  var offset = before.length;
  if (sel.length) {
    ta.selectionStart = s + offset;
    ta.selectionEnd = e + offset;
  } else {
    ta.selectionStart = ta.selectionEnd = s + offset;
  }
}

function _updateWordCount() {
  var ta = document.getElementById('essay-content-md');
  var text = ta.value;
  var chars = text.length;
  var cjk = (text.match(/[\u4e00-\u9fff\u3400-\u4dbf]/g) || []).length;
  var words = (text.match(/[a-zA-Z]+/g) || []).length;
  var el = document.getElementById('essay-word-count');
  el.textContent = chars + ' 字符 · ' + (cjk + words) + ' 词 · ~' + Math.max(1, Math.round((cjk + words * 1.5) / 300)) + ' min';
}

document.addEventListener('keydown', function(e) {
  var ta = document.getElementById('essay-content-md');
  if (document.activeElement !== ta) return;
  // Tab → 2 spaces
  if (e.key === 'Tab') {
    e.preventDefault();
    var s = ta.selectionStart, v = ta.value;
    ta.value = v.slice(0, s) + '  ' + v.slice(ta.selectionEnd);
    ta.selectionStart = ta.selectionEnd = s + 2;
  }
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 's') { e.preventDefault(); saveEssayContent(); }
    if (e.key === 'b') { e.preventDefault(); _wrapSelection(ta, '**', '**'); }
    if (e.key === 'i') { e.preventDefault(); _wrapSelection(ta, '*', '*'); }
    if (e.key === 'k') { e.preventDefault(); _wrapSelection(ta, '[', '](url)'); }
  }
});

// Word count on input
document.getElementById('essay-content-md').addEventListener('input', _updateWordCount);

// Drag-and-drop image upload
(function() {
  var ta = document.getElementById('essay-content-md');
  ta.addEventListener('dragover', function(e) {
    if (e.dataTransfer.types && e.dataTransfer.types.indexOf('Files') >= 0) {
      e.preventDefault(); e.stopPropagation();
    }
  });
  ta.addEventListener('drop', async function(e) {
    var file = e.dataTransfer.files[0];
    if (!file || !file.type.startsWith('image/')) return;  // let browser handle text drag
    e.preventDefault(); e.stopPropagation();
    var fd = new FormData();
    var slug = document.getElementById('essay-content-editor').dataset.slug;
    if (slug) fd.append('slug', slug);
    fd.append('file', file);
    try {
      var result = await api('POST', '/api/essays/upload-image', fd);
      var url = result.url || '';
      var md = '![](' + (url.startsWith('/') ? url : '/' + url) + ')';
      var s = ta.selectionStart, end = ta.selectionEnd;
      ta.value = ta.value.slice(0, s) + md + ta.value.slice(end);
      ta.focus();
      ta.selectionStart = ta.selectionEnd = s + md.length;
      toast('图片已插入');
    } catch(ex) { toast(ex.message, true); }
  });
})();

var _autosaveInterval;
function startAutosave(slug) {
  clearInterval(_autosaveInterval);
  _autosaveInterval = setInterval(function() {
    var md = document.getElementById('essay-content-md').value;
    if (md.trim()) localStorage.setItem('draft:' + slug, md);
  }, 10000);
}

function checkDraft(slug) {
  var saved = localStorage.getItem('draft:' + slug);
  if (!saved) return;
  var cur = document.getElementById('essay-content-md').value;
  if (saved !== cur && confirm('发现本地草稿（' + new Date(+localStorage.getItem('draft-time:' + slug) || Date.now()).toLocaleString() + '），是否恢复？')) {
    document.getElementById('essay-content-md').value = saved;
    localStorage.removeItem('draft:' + slug);
    localStorage.removeItem('draft-time:' + slug);
  }
}

function clearDraft(slug) {
  localStorage.removeItem('draft:' + slug);
  localStorage.removeItem('draft-time:' + slug);
}

async function saveEssayContent() {
  try {
  const slug = document.getElementById('essay-content-editor').dataset.slug;
  const md = document.getElementById('essay-content-md').value;    await api('PUT', '/api/essays/' + slug + '/content', { content: md });
    markClean();
    clearDraft(slug);
    toast('正文已保存');
  } catch(e) { toast(e.message, true); }
}

async function uploadEssayImage() {
  try {
  var file = document.getElementById('essay-img-input').files[0];
  if (!file) return;
  var fd = new FormData();
  var slug = document.getElementById('essay-edit-slug').value;
  if (slug) fd.append('slug', slug);
  fd.append('file', file);    var result = await api('POST', '/api/essays/upload-image', fd);
    var url = result.url || '';
    var md = '![](' + (url.startsWith('/') ? url : '/' + url) + ')';
    var ta = document.getElementById('essay-content-md');
    var start = ta.selectionStart, end = ta.selectionEnd;
    ta.value = ta.value.slice(0, start) + md + ta.value.slice(end);
    ta.focus();
    ta.selectionStart = ta.selectionEnd = start + md.length;
    toast('图片已插入');
  } catch(e) { toast(e.message, true); }
  document.getElementById('essay-img-input').value = '';
}

async function previewEssayContent() {
  try {
  var panel = document.getElementById('essay-preview');
  if (panel.style.display === 'block') {
    panel.style.display = 'none';
    return;
  }
  const md = document.getElementById('essay-content-md').value;    const data = await api('POST', '/api/essays/x/html', { md: md });
    panel.innerHTML = data.html;
    renderKatexIn(panel);
    panel.style.display = 'block';
  } catch(e) { toast(e.message, true); }
}

async function deleteEssay(slug) {  const confirmed = await confirmDialog('确定删除随笔 "' + slug + '"？这将同时删除 HTML 文件。');
  if (!confirmed) return;
  await api('DELETE', '/api/essays/' + slug);
  // Close any open panels for this essay
  if (document.getElementById('essay-edit-slug').value === slug) hidePanel('essay-form');
  if (document.getElementById('essay-content-editor').dataset.slug === slug) hideEssayContentEditor();
  clearDraft(slug);
  loadEssays();
  toast('随笔已删除');
}

// ═══════════════════════════════════
// Photos
// ═══════════════════════════════════
// Photo tag library (localStorage, like essay tags)
var _currentPhotoTag = '';
var _photoDeleteTagMode = false;
function getPhotoTags() { return _tagLib('photo-tags', '["Shenzhen","Night","Street"]'); }
function savePhotoTags(tags) { _saveTagLib('photo-tags', tags); }

function switchPhotoTabTag(tag) {
  _currentPhotoTag = tag;
  loadPhotos();
}
function promptNewPhotoTag() {
  _promptTag('photo-tags', '["Shenzhen","Night","Street"]', function(t) { _currentPhotoTag = t; loadPhotos(); });
}
function toggleDeletePhotoTagMode() {
  _photoDeleteTagMode = _toggleDeleteTagMode('delete-photo-tag-btn', _photoDeleteTagMode, loadPhotos);
}
async function deletePhotoTagGlobal(tag) {
  if (!confirm('确定永久删除标签 "' + tag + '"？这将从所有照片中移除该标签。')) return;
  var tags = getPhotoTags();
  tags = tags.filter(function(t) { return t !== tag; });
  savePhotoTags(tags);
  // Strip from all photos
  for (var p of _photoData) {
    if (!p.tags) continue;
    var before = p.tags.length;
    p.tags = p.tags.filter(function(t) { return t !== tag; });
    if (p.tags.length !== before) {
      await api('PUT', '/api/photo-tags', {filename: p.filename, tags: p.tags});
    }
  }
  if (_currentPhotoTag === tag) _currentPhotoTag = '';
  loadPhotos();
}

var _photoData = [];
var _selectedPhotoIdx = -1;
var _editorMap = null;
var _editorMarker = null;

function _renderPhotoTagTabs() {
  var tags = getPhotoTags();
  var btnStyle = 'padding:3px 12px;border-radius:20px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid var(--border);color:var(--muted);transition:all .15s;user-select:none;background:var(--card-bg);';
  var html = '<span tabindex="0" role="button" style="' + btnStyle + (!_currentPhotoTag ? 'background:var(--c2);color:#fff;border-color:var(--c2);' : '') + '" onclick="switchPhotoTabTag(\'\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();switchPhotoTabTag(\'\')}">全部</span>';
  tags.forEach(function(t) {
    var del = _photoDeleteTagMode ? '<span onclick="event.stopPropagation();deletePhotoTagGlobal(\'' + esc(t) + '\')" style="margin-left:2px;color:var(--danger);cursor:pointer;font-weight:700;">×</span>' : '';
    var active = _currentPhotoTag === t;
    html += '<span tabindex="0" role="button" style="' + btnStyle + (active ? 'background:var(--c2);color:#fff;border-color:var(--c2);' : '') + '" onclick="switchPhotoTabTag(\'' + esc(t) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();switchPhotoTabTag(\'' + esc(t) + '\')}">' + esc(t) + del + '</span>';
  });
  document.getElementById('photo-tag-tabs').innerHTML = html;
}

async function loadPhotos() {
  try {
    _photoData = await api('GET', '/api/photos');
    _renderPhotoTagTabs();
    if (_currentPhotoTag) {
      _photoData = _photoData.filter(function(p) {
        return (p.tags || []).indexOf(_currentPhotoTag) >= 0;
      });
    }
    renderAdminPhotos();
  } catch(e) { toast(e.message, true); }
}

function renderAdminPhotos() {
  document.getElementById('photo-grid').innerHTML = _photoData.map(function(p, i) {
    var tagCount = (p.tags || []).length;
    var tagBtn = '<button class="btn btn-sm" onclick="event.stopPropagation();openPhotoTagModal(' + i + ')" style="font-size:10px;padding:1px 6px;margin-top:4px;">' +
      '🏷 ' + (tagCount > 0 ? tagCount + ' 标签' : '加标签') + '</button>';
    return '<div class="photo-card' + (_selectedPhotoIdx === i ? ' selected' : '') + '" draggable="true" data-index="' + i + '"' +
      ' onclick="selectPhoto(' + i + ')"' +
      ' ondragstart="photoDragStart(event,' + i + ')"' +
      ' ondragover="photoDragOver(event)"' +
      ' ondragend="photoDragEnd(event)"' +
      ' ondrop="photoDrop(event,' + i + ')"' +
      '>' +
      '<img src="/images/sm/' + encodeURIComponent(p.filename) + '" alt="' + esc(p.filename) + '" loading="lazy">' +
      '<button class="del-btn" data-filename="' + esc(p.filename) + '" onclick="deletePhoto(this.dataset.filename)">×</button>' +
      '<div class="photo-info">' +
        '<div class="fn">' + esc(p.filename) + '</div>' +
        '<div class="sz">' + (p.size || '') + (p.exif && p.exif.camera ? ' · ' + esc(p.exif.camera) : '') + '</div>' +
        (p.exif && Object.keys(p.exif).length ? '<div class="photo-exif">' + esc(p.exif.aperture||'') + ' ' + esc(p.exif.shutter||'') + ' ISO' + esc(p.exif.iso||'') + '</div>' : '') +
        (p.date ? '<div class="photo-exif" style="color:var(--c3)">📅 ' + esc(p.date) + '</div>' : '') +
        (p.exif && p.exif.gps ? '<div class="photo-exif">📍 ' + p.exif.gps.lat.toFixed(4) + ', ' + p.exif.gps.lng.toFixed(4) + '</div>' : '') +
        tagBtn +
      '</div>' +
      '</div>';
  }).join('');
}

var _tagModalIdx = -1;
function openPhotoTagModal(idx) {
  _tagModalIdx = idx;
  _refreshTagModalContent();
  document.getElementById('tag-modal').showModal();
}
function _refreshTagModalContent() {
  var tags = getPhotoTags();
  var myTags = _photoData[_tagModalIdx].tags || [];
  var html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">';
  tags.forEach(function(t) {
    var active = myTags.indexOf(t) >= 0;
    html += '<span tabindex="0" role="button" onclick="toggleModalTag(\'' + esc(t) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();toggleModalTag(\'' + esc(t) + '\')}" style="display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;' +
      (active ? 'background:var(--c2);color:#fff;' : 'background:var(--border);color:var(--muted);') + '">' + esc(t) + '</span>';
  });
  html += '</div>';
  document.getElementById('tag-modal-body').innerHTML = html;
}
function closeTagModal() { document.getElementById('tag-modal').close(); }
async function toggleModalTag(tag) {
  var p = _photoData[_tagModalIdx];
  var tags = (p.tags || []).slice();
  var pos = tags.indexOf(tag);
  if (pos >= 0) tags.splice(pos, 1); else tags.push(tag);
  await api('PUT', '/api/photo-tags', {filename: p.filename, tags: tags});
  p.tags = tags;
  _refreshTagModalContent();  // refresh without re-showModal
  renderAdminPhotos();
}

function selectPhoto(idx) {
  _selectedPhotoIdx = idx;
  showPhotoEditor(idx);
  renderAdminPhotos();
  loadEditorMap();
}

function showPhotoEditor(idx) {
  var p = _photoData[idx];
  var ed = document.getElementById('photo-editor');
  ed.style.display = 'block';
  document.getElementById('photo-editor-fn').textContent = p.filename;
  // Date
  var dateInput = document.getElementById('photo-editor-date');
  var curDate = p.date || '';
  if (curDate && curDate.match(/^\w{3} \d{1,2}, \d{4}$/)) {
    var parts = curDate.match(/(\w+) (\d+), (\d+)/);
    if (parts) curDate = parts[3] + '-' + MONTHS_NUM[parts[1]] + '-' + String(parts[2]).padStart(2,'0');
  }
  dateInput.value = curDate;
  // GPS
  var gps = p.exif && p.exif.gps;
  document.getElementById('photo-editor-lat').value = gps ? gps.lat : '';
  document.getElementById('photo-editor-lng').value = gps ? gps.lng : '';
  // Update map marker
  if (_editorMarker && gps) {
    _editorMarker.setLatLng([gps.lat, gps.lng]);
    _editorMap.setView([gps.lat, gps.lng], 14);
  }
  ed.scrollIntoView({behavior:'smooth'});
}

function clearPhotoEditor() {
  _selectedPhotoIdx = -1;
  document.getElementById('photo-editor').style.display = 'none';
  renderAdminPhotos();
}

async function savePhotoEditor() {
  if (_selectedPhotoIdx < 0) return;
  var fn = _photoData[_selectedPhotoIdx].filename;
  // Save date
  var dateVal = document.getElementById('photo-editor-date').value;
  if (dateVal) {
    var dp = dateVal.split('-');
    if (dp.length === 3) {
      dateVal = MONTHS_ARR[+dp[1]-1] + ' ' + (+dp[2]) + ', ' + dp[0];
    }
  }
  await api('PUT', '/api/photo-date', {filename: fn, date: dateVal});
  // Save GPS
  var latStr = document.getElementById('photo-editor-lat').value.trim();
  var lngStr = document.getElementById('photo-editor-lng').value.trim();
  if (latStr && lngStr) {
    var lat = parseFloat(latStr), lng = parseFloat(lngStr);
    if (!isNaN(lat) && !isNaN(lng)) {
      await api('PUT', '/api/photo-gps', {filename: fn, lat: lat, lng: lng});
    }
  }
  _selectedPhotoIdx = -1;
  document.getElementById('photo-editor').style.display = 'none';
  loadPhotos();
  toast('已保存');
}

function loadEditorMap() {
  if (_editorMap) return;
  var container = document.getElementById('photo-editor-map');
  container.style.display = 'block';
  if (typeof L === 'undefined') {
    var css = document.createElement('link'); css.rel='stylesheet';
    css.href='https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(css);
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js';
    s.onload = function() { initEditorMap(container); };
    document.head.appendChild(s);
  } else {
    initEditorMap(container);
  }
}

function initEditorMap(container) {
  _editorMap = L.map(container).setView([22.5431, 113.9579], 11);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, subdomains: 'abcd', attribution: '&copy; OSM &copy; CARTO'
  }).addTo(_editorMap);
  // Click to set GPS
  _editorMap.on('click', function(e) {
    var lat = e.latlng.lat.toFixed(6), lng = e.latlng.lng.toFixed(6);
    document.getElementById('photo-editor-lat').value = lat;
    document.getElementById('photo-editor-lng').value = lng;
    if (_editorMarker) _editorMap.removeLayer(_editorMarker);
    _editorMarker = L.marker([lat, lng]).addTo(_editorMap);
  });
  // If selected photo has GPS, show it
  if (_selectedPhotoIdx >= 0) {
    var gps = _photoData[_selectedPhotoIdx].exif && _photoData[_selectedPhotoIdx].exif.gps;
    if (gps) {
      _editorMarker = L.marker([gps.lat, gps.lng]).addTo(_editorMap);
      _editorMap.setView([gps.lat, gps.lng], 14);
    }
  }
  setTimeout(function() { _editorMap.invalidateSize(); }, 200);
}

// Update card click to select
// remove old prompt-based functions (editPhotoDate, editPhotoGps) — replaced by panel above

function photoDragStart(e, idx) { _dragStart(e, idx); e.target.style.transform = 'scale(0.95)'; }
function photoDragOver(e) { _dragOver(e); }
function photoDragEnd(e) { e.target.style.transform = ''; _dragEnd(e); }

async function photoDrop(e, toIdx) {
  e.preventDefault();
  e.stopPropagation();
  var fromIdx = _dragState.idx;
  _dragEnd(e);
  if (fromIdx < 0 || fromIdx === toIdx) return;
  var item = _photoData.splice(fromIdx, 1)[0];
  _photoData.splice(toIdx, 0, item);
  renderAdminPhotos();
  await api('PUT', '/api/photos', _photoData);
  toast('顺序已保存');
}

function handlePhotoDrop(e) {
  if (!e.dataTransfer.files.length) return;  // internal drag, skip
  handlePhotoFiles(e.dataTransfer.files);
}

function handlePhotoFiles(files) {
  Array.from(files).forEach(function(f) {
    if (!f.type.startsWith('image/')) return;
    var fd = new FormData(); fd.append('file', f);
    api('POST', '/api/photos/upload', fd).then(function(r) {
      toast('已上传: ' + r.filename);
      loadPhotos();
    }).catch(function(e) { toast(e.message, true); });
  });
}

async function deletePhoto(filename) {  const confirmed = await confirmDialog('确定删除照片 "' + filename + '"？');
  if (!confirmed) return;
  await api('DELETE', '/api/photos/' + filename);
  loadPhotos();
  toast('照片已删除');
}

// ═══════════════════════════════════
// Contact
async function loadContact() {
  try {
    const data = await api('GET', '/api/contact');
  document.getElementById('contact-list').innerHTML = data.map((c, i) => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${esc(c.label)} <span style="color:var(--muted);font-weight:400;">${esc(c.handle)}</span></div>
          <div class="card-meta">${c.url ? '🔗 ' + esc(c.url) : '无链接'}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editContact(${i})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteContact(${i})">删除</button>
        </div>
      </div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function showContactForm() {
  showEntryForm({ formId: 'contact-form', editId: 'contact-edit-index', title: '添加联系方式',
    fields: ['contact-label','contact-handle','contact-url'] });
}


function editContact(i) {
  var form = document.getElementById('contact-form');
  if (form.style.display === 'block' && document.getElementById('contact-edit-index').value == i) {
    form.style.display = 'none'; return;
  }
  api('GET', '/api/contact').then(data => {
    var c = data[i];
    document.getElementById('contact-edit-index').value = i;
    document.getElementById('contact-label').value = c.label;
    document.getElementById('contact-handle').value = c.handle;
    document.getElementById('contact-url').value = c.url || '';
    document.getElementById('contact-form-title').textContent = '编辑联系方式';
    form.style.display = 'block';
    form.scrollIntoView({ behavior: 'smooth' });
  }).catch(e => toast(e.message, true));
}

async function saveContact() {
  try {
  var idx = document.getElementById('contact-edit-index').value;
  var item = {
    label: document.getElementById('contact-label').value,
    handle: document.getElementById('contact-handle').value,
    url: document.getElementById('contact-url').value,
  };    if (idx !== '') { await api('PUT', '/api/contact/' + idx, item); }
    else { await api('POST', '/api/contact', item); }
    markClean();
    hidePanel('contact-form');
    loadContact();
    toast('已保存');
  } catch(e) { toast(e.message, true); }
}

async function deleteContact(i) {  var confirmed = await confirmDialog('确定删除？');
  if (!confirmed) return;
  await api('DELETE', '/api/contact/' + i);
  if (document.getElementById('contact-edit-index').value == i) hidePanel('contact-form');
  loadContact();
  toast('已删除');
}

// Friends
// ═══════════════════════════════════
async function loadFriends() {
  try {
    const data = await api('GET', '/api/friends');
  document.getElementById('friend-list').innerHTML = data.map((f, i) => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${esc(f.name)}</div>
          <div class="card-meta">${esc(f.url)}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editFriend(${i})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteFriend(${i})">删除</button>
        </div>
      </div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function showFriendForm() {
  showEntryForm({ formId: 'friend-form', editId: 'friend-edit-index', title: '添加友链',
    fields: ['friend-name','friend-url'] });
}


function editFriend(i) {
  var form = document.getElementById('friend-form');
  if (form.style.display === 'block' && document.getElementById('friend-edit-index').value == i) {
    form.style.display = 'none'; return;
  }
  document.getElementById('friend-edit-index').value = i;
  document.getElementById('friend-form-title').textContent = '编辑友链';
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
  api('GET', '/api/friends').then(data => {
    document.getElementById('friend-name').value = data[i].name;
    document.getElementById('friend-url').value = data[i].url;
  }).catch(e => toast(e.message, true));
}

async function saveFriend() {
  try {
  const idx = document.getElementById('friend-edit-index').value;
  const item = { name: document.getElementById('friend-name').value, url: document.getElementById('friend-url').value };    if (idx !== '') {
      await api('PUT', '/api/friends/' + idx, item);
    } else {
      await api('POST', '/api/friends', item);
    }
    markClean();
    hidePanel('friend-form');
    loadFriends();
    toast('友链已保存');
  } catch(e) { toast(e.message, true); }
}

async function deleteFriend(i) {  const confirmed = await confirmDialog('确定删除这个友链？');
  if (!confirmed) return;
  await api('DELETE', '/api/friends/' + i);
  if (document.getElementById('friend-edit-index').value == i) hidePanel('friend-form');
  loadFriends();
  toast('友链已删除');
}

// ═══════════════════════════════════
// Music
// ═══════════════════════════════════
async function loadMusic() {
  try {
    const data = await api('GET', '/api/music');
  document.getElementById('music-list').innerHTML = data.map(m => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${pad2(m.id)} ${esc(m.title)}</div>
          <div class="card-meta">${esc(m.artist)} · ${esc(m.filename)}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editMusic(${m.id})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteMusic(${m.id})">删除</button>
        </div>
      </div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function autoFillMusic() {
  var file = document.getElementById('music-file').files[0];
  if (!file) return;
  document.getElementById('music-filename').value = file.name;
  var name = file.name.replace(/\.mp3$/i, '');
  var parts = name.split(' - ');
  if (parts.length >= 2) {
    document.getElementById('music-artist').value = parts[0].trim();
    document.getElementById('music-title').value = parts.slice(1).join(' - ').trim();
  } else {
    document.getElementById('music-title').value = name;
  }
}

function showMusicForm() {
  showEntryForm({ formId: 'music-form', editId: 'music-edit-id', title: '添加曲目',
    fields: ['music-file','music-title','music-artist','music-filename'] });
}


async function editMusic(id) {  var form = document.getElementById('music-form');
  if (form.style.display === 'block' && document.getElementById('music-edit-id').value == id) {
    form.style.display = 'none'; return;
  }
  const data = await api('GET', '/api/music');
  const m = data.find(x => x.id === id);
  if (!m) return;
  document.getElementById('music-edit-id').value = id;
  document.getElementById('music-title').value = m.title;
  document.getElementById('music-artist').value = m.artist;
  document.getElementById('music-filename').value = m.filename;
  document.getElementById('music-form-title').textContent = '编辑曲目';
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
}

async function saveMusic() {
  try {
  var fileInput = document.getElementById('music-file');
  var file = fileInput.files[0];
  // Upload file if present
  if (file) {
    var fd = new FormData();
    fd.append('file', file);
    try { var uploadResult = await api('POST', '/api/music/upload', fd); }
    catch(e) { toast('上传失败: ' + e.message, true); return; }
  }
  var id = document.getElementById('music-edit-id').value;
  var item = {
    title: document.getElementById('music-title').value,
    artist: document.getElementById('music-artist').value,
    filename: uploadResult ? uploadResult.filename : document.getElementById('music-filename').value,
  };    if (id) { await api('PUT', '/api/music/' + id, item); }
    else { await api('POST', '/api/music', item); }
    markClean();
    hidePanel('music-form');
    loadMusic();
    toast(id ? '曲目已更新' : '曲目已添加');
  } catch(e) { toast(e.message, true); }
}

async function deleteMusic(id) {  const confirmed = await confirmDialog('确定删除这个曲目？');
  if (!confirmed) return;
  await api('DELETE', '/api/music/' + id);
  if (document.getElementById('music-edit-id').value == id) hidePanel('music-form');
  loadMusic();
  toast('曲目已删除');
}

// ═══════════════════════════════════
// Git
// ═══════════════════════════════════
// ═══════════════════════════════════
// Stack — drag-to-reorder chips


function renderStackChips(data) {
  var colors = ['#ff4d4d','#ff6d00','#ffb800','#0066ff','#00c853','#9c27b0'];
  return data.map(function(c, i) {
    var color = colors[i % 6];
    return '<span class="stack-chip" draggable="true"' +
      ' style="--chip-color:' + color + ';display:inline-flex;align-items:center;gap:6px;padding:4px 8px 4px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid ' + color + '40;color:' + color + ';cursor:grab;transition:opacity .2s;"' +
      ' ondragstart="stackDragStart(event,' + i + ')"' +
      ' ondragover="stackDragOver(event)"' +
      ' ondragend="stackDragEnd(event)"' +
      ' ondrop="stackDrop(event,' + i + ')"' +
      '>' + esc(c) +
      '<button onclick="deleteStackChip(' + i + ')" style="background:none;border:none;color:inherit;opacity:0.5;cursor:pointer;font-size:14px;line-height:1;padding:0 2px;" title="删除">\u00d7</button>' +
      '</span>';
  }).join('');
}

async function loadStack() {
  try {
    var data = await api('GET', '/api/stack');
    window._stackData = data;
    document.getElementById('stack-chips').innerHTML = renderStackChips(data) || '<span style="color:var(--muted);font-size:12px;">还没有添加技术栈</span>';
  } catch(e) { toast(e.message, true); }
}

async function addStackItem() {
  var input = document.getElementById('stack-new-name');
  var name = input.value.trim();
  if (!name) return;
  var data;
  try { data = await api('GET', '/api/stack'); } catch(e) { data = []; }
  data.push(name);
  await api('PUT', '/api/stack', data);
  input.value = '';
  loadStack();
}

async function deleteStackChip(idx) {
  var data = await api('GET', '/api/stack');
  data.splice(idx, 1);
  await api('PUT', '/api/stack', data);
  loadStack();
}

function stackDragStart(e, idx) { _dragStart(e, idx); }
function stackDragOver(e) { _dragOver(e); }
function stackDragEnd(e) { _dragEnd(e); }

async function stackDrop(e, toIdx) {
  e.preventDefault();
  var fromIdx = _dragState.idx;
  if (fromIdx < 0 || fromIdx === toIdx) return;
  var data = await api('GET', '/api/stack');
  var item = data.splice(fromIdx, 1)[0];
  data.splice(toIdx, 0, item);
  await api('PUT', '/api/stack', data);
  _dragState.idx = -1;
  loadStack();
}

async function refreshGitStatus() {
  try {
    const data = await api('GET', '/api/git/status');
    document.getElementById('git-badge').textContent = data.branch + (data.clean ? '  ✓' : '  ✗');
    var html = '<div class="card">';
    html += '<div style="font-size:16px;font-weight:700;margin-bottom:4px;">' + esc(data.branch) + '</div>';
    html += '<div style="font-size:13px;color:' + (data.clean ? '#28a745' : 'var(--danger)') + ';margin-bottom:12px;">' + (data.clean ? '工作区干净' : '有未提交的改动') + '</div>';
    if (data.files && data.files.length > 0) {
      html += '<div style="font-size:12px;color:var(--muted);margin-bottom:6px;">变更文件:</div>';
      data.files.forEach(function(f) {
        var color = f.startsWith('??') ? '#e36209' : f.startsWith(' M') || f.startsWith('M ') ? '#0366d6' : '#28a745';
        html += '<div style="font-family:monospace;font-size:12px;padding:2px 0;color:' + color + ';">' + esc(f) + '</div>';
      });
    }
    if (data.diffStat) {
      html += '<div style="font-size:12px;color:var(--muted);margin-top:8px;font-family:monospace;white-space:pre-wrap;">' + esc(data.diffStat) + '</div>';
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
  await api('POST', '/api/git/revert');
  toast('已撤销');
  refreshGitStatus();
  loadWork(); loadEssays(); loadPhotos(); loadFriends(); loadContact(); loadMusic();
}

async function showGitDiff() {
  try {
    var data = await api('GET', '/api/git/diff');
    var el = document.getElementById('diff-content');
    // Simple color: + lines green, - lines red
    var html = (data.diff || '(no changes)').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    html = html.replace(/^(\+.*)$/gm, '<span style="color:#22863a;">$1</span>');
    html = html.replace(/^(-.*)$/gm, '<span style="color:#cb2431;">$1</span>');
    html = html.replace(/^(@@.*@@)$/gm, '<span style="color:#0366d6;">$1</span>');
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

// ═══════════════════════════════════
// Confirm Dialog
// ═══════════════════════════════════
function confirmDialog(msg) {
  return new Promise((resolve) => {
    document.getElementById('confirm-msg').textContent = msg;
    const dialog = document.getElementById('confirm-dialog');
    const form = dialog.querySelector('form');
    var done = false;
    form.onsubmit = () => { if (!done) { done = true; dialog.close(); resolve(true); } return false; };
    dialog.querySelector('[value="cancel"]').onclick = () => { if (!done) { done = true; dialog.close(); resolve(false); } };
    dialog.showModal();
  });
}

// ═══════════════════════════════════
// Init
// ═══════════════════════════════════
refreshGitStatus();
loadWork();
// [shared] Keep in sync with index.js::toggleTheme()
function _applyTheme(mode) {
  var btn = document.getElementById('theme-btn');
  if (mode === 'dark') { document.body.classList.add('dark'); btn.textContent = '☀'; }
  else { document.body.classList.remove('dark'); btn.textContent = '🌙'; }
}
(function() {
  var saved = localStorage.getItem('theme');
  if (saved === 'dark') _applyTheme('dark');
})();
function toggleTheme() {
  if (document.body.classList.contains('dark')) {
    localStorage.setItem('theme', 'light');
    _applyTheme('light');
  } else {
    localStorage.setItem('theme', 'dark');
    _applyTheme('dark');
  }
}

// ═══ Drag & Drop upload ═══
document.addEventListener('dragover', function(e) {
  // Don't intercept text dragging inside the essay editor textarea
  var ta = document.getElementById('essay-content-md');
  if (ta && (e.target === ta || (e.target.closest && e.target.closest('#essay-content-md')))) return;
  e.preventDefault();
});
document.addEventListener('drop', function(e) {
  // Don't intercept text dropping inside the essay editor textarea
  var ta = document.getElementById('essay-content-md');
  if (ta && (e.target === ta || (e.target.closest && e.target.closest('#essay-content-md')))) return;
  e.preventDefault();
  var files = e.dataTransfer.files;
  if (!files.length) return;
  var tab = document.querySelector('.tab-btn.active');
  var tabName = tab ? tab.textContent.trim() : '';
  if (tabName === 'Photos') {
    var count = 0;
    Array.from(files).forEach(function(f) {
      if (!f.type.startsWith('image/')) return;
      var fd = new FormData(); fd.append('file', f); fd.append('size', 'sm');
      api('POST', '/api/photos/upload', fd).then(function() { loadPhotos(); }).catch(function(e) { toast('上传失败: ' + (e.message || '未知错误'), true); });
      count++;
    });
    if (count > 0) toast('已上传 ' + count + ' 张照片');
  } else if (document.getElementById('essay-content-editor').style.display === 'block') {
    var count = 0;
    Array.from(files).forEach(function(f) {
      if (!f.type.startsWith('image/')) return;
      var fd = new FormData(); fd.append('file', f);
      var s = document.getElementById('essay-edit-slug').value;
      if (s) fd.append('slug', s);
      api('POST', '/api/essays/upload-image', fd).then(function(r) {
        var ta = document.getElementById('essay-content-md');
        var s = ta.selectionStart;
        var md = '![](' + (r.url||'') + ')\n';
        ta.value = ta.value.slice(0, s) + md + ta.value.slice(ta.selectionEnd);
        ta.selectionStart = ta.selectionEnd = s + md.length;
      }).catch(function(e) { toast('插图上传失败: ' + (e.message || '未知错误'), true); });
      count++;
    });
    if (count > 0) toast('已插入 ' + count + ' 张图片');
  }
});

// ═══ KaTeX renderer ═══
function renderKatexIn(el) {
  var els = el.querySelectorAll('.arithmatex');
  els.forEach(function(sp) {
    var t = sp.textContent || sp.innerText;
    var isBlock = t.indexOf('\\[') !== -1;
    var startDelim = isBlock ? '\\[' : '\\(';
    var endDelim = isBlock ? '\\]' : '\\)';
    var startIdx = t.indexOf(startDelim);
    var endIdx = t.lastIndexOf(endDelim);
    if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
      var math = t.substring(startIdx + 2, endIdx);
      try {
        katex.render(math, sp, {displayMode: isBlock, throwOnError: false, output: 'htmlAndMathml'});
      } catch(e) { console.error('KaTeX:', e); }
    }
  });
}
