// Canonical theme module — shared by index, admin, and essay pages
// Keep in sync: this is the single source of truth for toggleTheme / applyTheme

function _applyTheme(mode) {
  var html = document.documentElement;
  var btn = document.getElementById('theme-btn');
  if (mode === 'dark') {
    html.classList.add('dark');
    if (btn) btn.textContent = '\u2600';  // ☀
  } else {
    html.classList.remove('dark');
    if (btn) btn.textContent = '\uD83C\uDF19';  // 🌙
  }
}

function _themeMode() {
  var saved = localStorage.getItem('theme');
  if (saved === 'dark' || saved === 'light') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function _notifyThemeChange(mode) {
  window.dispatchEvent(new CustomEvent('themechange', {detail: {mode: mode}}));
}

function toggleTheme() {
  var isDark = document.documentElement.classList.contains('dark');
  var next = isDark ? 'light' : 'dark';
  localStorage.setItem('theme', next);
  _applyTheme(next);
  _notifyThemeChange(next);
}

_applyTheme(_themeMode());

window.addEventListener('storage', function(event) {
  if (event.key !== 'theme') return;
  var mode = event.newValue === 'dark' || event.newValue === 'light'
    ? event.newValue
    : _themeMode();
  _applyTheme(mode);
  _notifyThemeChange(mode);
});

var _themeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
_themeMediaQuery.addEventListener('change', function(event) {
  if (localStorage.getItem('theme')) return;
  var mode = event.matches ? 'dark' : 'light';
  _applyTheme(mode);
  _notifyThemeChange(mode);
});
