// Shared admin UI primitives used by domain modules.

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
