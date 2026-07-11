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

function toggleTheme() {
  var isDark = document.documentElement.classList.contains('dark');
  var next = isDark ? 'light' : 'dark';
  localStorage.setItem('theme', next);
  _applyTheme(next);
  // Dispatch for page-specific listeners (e.g. map invalidation)
  window.dispatchEvent(new CustomEvent('themechange', {detail: {mode: next}}));
}
