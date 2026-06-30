(function initThemeBtn() {
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  var btn = document.getElementById('theme-btn');
  if (localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && mq.matches)) {
    btn.textContent = '☀';
  }
  mq.addEventListener('change', function(e) {
    if (localStorage.getItem('theme')) return;
    btn.textContent = e.matches ? '☀' : '🌙';
  });
})();
// [shared] Keep in sync with index.js::toggleTheme()
function toggleTheme() {
  var html = document.documentElement;
  var btn = document.getElementById('theme-btn');
  if (html.classList.toggle('dark')) {
    localStorage.setItem('theme', 'dark');
    btn.textContent = '☀';
  } else {
    localStorage.setItem('theme', 'light');
    btn.textContent = '🌙';
  }
}
