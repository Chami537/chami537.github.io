// Shared admin infrastructure: auth, API transport, UI state, and helpers.

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
function onAdminDataReset(handler) { document.addEventListener('admin:data-reset', handler); }
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s != null ? s : '';
  return d.innerHTML.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}
function confirmDialog(msg) {
  return new Promise((resolve) => {
    document.getElementById('confirm-msg').textContent = msg;
    const dialog = document.getElementById('confirm-dialog');
    const form = dialog.querySelector('form');
    const cancelBtn = dialog.querySelector('[value="cancel"]');
    var done = false;
    function handleSubmit(e) {
      e.preventDefault();
      if (!done) { done = true; dialog.close(); cleanup(); resolve(true); }
    }
    function handleCancel() {
      if (!done) { done = true; dialog.close(); cleanup(); resolve(false); }
    }
    function cleanup() {
      form.removeEventListener('submit', handleSubmit);
      cancelBtn.removeEventListener('click', handleCancel);
    }
    form.addEventListener('submit', handleSubmit);
    cancelBtn.addEventListener('click', handleCancel);
    dialog.showModal();
  });
}

var _dragState = { idx: -1 };
function _dragStart(e, idx) {
  _dragState.idx = idx;
  e.dataTransfer.effectAllowed = 'move';
  e.target.style.opacity = '0.5';
}
function _dragOver(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }
function _dragEnd(e) { e.target.style.opacity = '1'; _dragState.idx = -1; }

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
  btn.classList.toggle('btn-danger', on);
  onDone();
  return on;
}

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

checkAuth();
