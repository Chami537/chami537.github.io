// ═══════════════════════════════════
// Auth
// ═══════════════════════════════════
async function doLogin() {
  var pw = document.getElementById('login-password').value;
  var r = await fetch('/api/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})});
  if (r.ok) {
    isDirty = false;
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
    html += '<div class="track-row">' +
      '<span>' + esc(t.name) + ' <code class="code-muted">' + esc(t.file) + '</code></span>' +
      '<button class="btn btn-sm btn-danger" onclick="deleteTrack(' + i + ')">删除</button>' +
      '</div>';
  });
  document.getElementById('tracks-list').innerHTML = html || '<p class="text-muted">暂无轨迹</p>';
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
  else clearInterval(window._autosaveInterval);  // stop autosave when leaving editor
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
// Theme
// ═══════════════════════════════════
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
