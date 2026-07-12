// Canonical theme module — shared by index, admin, and essay pages
// Keep in sync: this is the single source of truth for toggleTheme / applyTheme

function _applyTheme(mode, preference) {
  var html = document.documentElement;
  var btn = document.getElementById('theme-btn');
  if (mode === 'dark') {
    html.classList.add('dark');
  } else {
    html.classList.remove('dark');
  }
  if (btn) {
    if (preference === 'system') {
      btn.textContent = '\u25D0'; // ◐
      btn.title = '跟随系统（当前' + (mode === 'dark' ? '深色' : '浅色') + '）';
      btn.setAttribute('aria-label', btn.title);
    } else if (mode === 'dark') {
      btn.textContent = '\u2600'; // ☀
      btn.title = '手动深色';
      btn.setAttribute('aria-label', btn.title);
    } else {
      btn.textContent = '\uD83C\uDF19'; // 🌙
      btn.title = '手动浅色';
      btn.setAttribute('aria-label', btn.title);
    }
  }
}

function _themePreference() {
  var saved = localStorage.getItem('theme');
  return saved === 'dark' || saved === 'light' || saved === 'system' ? saved : 'system';
}

function _themeMode() {
  var preference = _themePreference();
  if (preference !== 'system') return preference;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function _notifyThemeChange(mode, preference) {
  window.dispatchEvent(new CustomEvent('themechange', {detail: {mode: mode, preference: preference}}));
}

function toggleTheme() {
  var preference = _themePreference();
  var mode = _themeMode();
  var next = preference === 'system'
    ? (mode === 'dark' ? 'light' : 'dark')
    : (preference === 'dark' ? 'light' : 'system');
  localStorage.setItem('theme', next);
  var nextMode = _themeMode();
  _applyTheme(nextMode, next);
  _notifyThemeChange(nextMode, next);
}

var _initialThemePreference = _themePreference();
_applyTheme(_themeMode(), _initialThemePreference);

window.addEventListener('storage', function(event) {
  if (event.key !== 'theme') return;
  var preference = _themePreference();
  var mode = _themeMode();
  _applyTheme(mode, preference);
  _notifyThemeChange(mode, preference);
});

var _themeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
_themeMediaQuery.addEventListener('change', function(event) {
  if (_themePreference() !== 'system') return;
  var mode = event.matches ? 'dark' : 'light';
  _applyTheme(mode, 'system');
  _notifyThemeChange(mode, 'system');
});
