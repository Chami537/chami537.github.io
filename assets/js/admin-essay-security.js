// Essay pinning and password controls.

// ═══ Pin system ═══
function pinBtn(e) {
  var pinned = e.pinned || false;
  var totalPinned = (_essayAllData || []).filter(function(x) { return x.pinned; }).length;
  var atLimit = totalPinned >= 5;
  if (pinned) {
    return '<button class="pin-btn pinned" onclick="togglePin(\'' + esc(e.slug) + '\')" title="取消置顶">置顶</button>';
  }
  if (atLimit) {
    return '<button class="pin-btn" disabled title="已满5篇">置顶</button>';
  }
  return '<button class="pin-btn" onclick="togglePin(\'' + esc(e.slug) + '\')" title="置顶">置顶</button>';
}

var _essayAllData = [];
async function togglePin(slug) {
  try {
    var r = await api('POST', '/api/essays/' + slug + '/pin');
    toast(r.pinned ? '已置顶 (' + r.count + '/5)' : '已取消置顶 (' + r.count + '/5)');
    // Update local state
    var e = _essayAllData.find(function(x) { return x.slug === slug; });
    if (e) e.pinned = r.pinned;
    window['essay' + 'Entry']();
  } catch(e) { toast(e.message, true); }
}

function passwordBtn(e) {
  var hasPwd = e.password_set || false;
  var label = hasPwd ? '密码' : '设密码';
  var title = hasPwd ? '点击修改或清除密码' : '设置密码保护';
  return '<button class="password-btn' + (hasPwd ? ' active' : '') + '" onclick="setPassword(\'' + esc(e.slug) + '\', ' + hasPwd + ')" title="' + title + '">' + label + '</button>';
}

function togglePwdVis(inputId, btn) {
  var input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '\u{1F576}';
    btn.title = '隐藏密码';
  } else {
    input.type = 'password';
    btn.textContent = '\u{1F441}';
    btn.title = '显示密码';
  }
}

function _resetPasswordDialog(hasPwd) {
  document.getElementById('pwd-current').textContent = hasPwd ? '(已设置)' : '(未设置)';
  var pwdNew = document.getElementById('pwd-new');
  var pwdConfirm = document.getElementById('pwd-confirm');
  pwdNew.value = '';
  pwdNew.type = 'password';
  pwdConfirm.value = '';
  pwdConfirm.type = 'password';
  document.getElementById('pwd-error').style.display = 'none';
  // Reset eye icons
  document.querySelectorAll('.pwd-toggle').forEach(function(b) { b.textContent = '\u{1F441}'; b.title = '显示密码'; });

}

function _passwordFormState() {
  return {
    newPassword: document.getElementById('pwd-new'),
    confirmation: document.getElementById('pwd-confirm'),
    error: document.getElementById('pwd-error'),
    saveButton: document.getElementById('pwd-save'),
  };
}

function _validatePasswordChange(pwd, confirm, hasPwd, error) {
  if (pwd && pwd !== confirm) {
    error.textContent = '两次输入的密码不一致';
    error.style.display = 'block';
    return false;
  }
  if (!pwd && hasPwd && !window.confirm('确定清除密码？文章将变为公开可见。')) return false;
  return true;
}

function setPassword(slug, hasPwd) {
  _resetPasswordDialog(hasPwd);
  var state = _passwordFormState();
  var pwdNew = state.newPassword;
  var pwdConfirm = state.confirmation;
  var pwdError = state.error;
  var saveBtn = state.saveButton;
  var dialog = document.getElementById('password-dialog');
  var form = document.getElementById('password-form');
  var saving = false;

  // Auto-clear error on input
  var clearError = function() { pwdError.style.display = 'none'; };
  pwdNew.oninput = clearError;
  pwdConfirm.oninput = clearError;

  form.onsubmit = async function(e) {
    e.preventDefault();
    if (saving) return false;
    var pwd = pwdNew.value;
    var confirm = pwdConfirm.value;

    if (!_validatePasswordChange(pwd, confirm, hasPwd, pwdError)) return false;

    saving = true;
    saveBtn.disabled = true;
    saveBtn.textContent = '保存中…';

    try {
      var r = await api('POST', '/api/essays/' + slug + '/password', { password: pwd });
      toast(r.password_set ? '密码已设置' : '密码已清除');
      dialog.close();
      window['essay' + 'Entry']();
    } catch(e) {
      toast(e.message, true);
      // Keep dialog open for retry
      saveBtn.disabled = false;
      saveBtn.textContent = '保存';
      saving = false;
    }
    return false;
  };
  dialog.showModal();
  pwdNew.focus();
}

function closePwdDialog() {
  document.getElementById('password-dialog').close();
}

function updatePinCount(data) {
  _essayAllData = data || [];
  var c = data.filter(function(e) { return e.pinned; }).length;
  document.getElementById('pin-count').textContent = c > 0 ? '\u{1F4CC} \u5DF2\u7F6E\u9876 ' + c + '/5' : '';
}
