// Essay Giscus theme synchronization.

// Sync Giscus theme with dark mode
function syncGiscusTheme() {
  var isDark = document.documentElement.classList.contains('dark');
  var theme = isDark ? 'https://chami537.github.io/data/giscus-dark.css' : 'https://chami537.github.io/data/giscus.css';
  var frame = document.querySelector('.giscus-frame');
  if (frame) {
    frame.contentWindow.postMessage(
      { giscus: { setConfig: { theme: theme } } },
      'https://giscus.app'
    );
  }
}
window.addEventListener('themechange', syncGiscusTheme);
// Listen for Giscus load
window.addEventListener('message', function(e) {
  if (e.origin !== 'https://giscus.app' || !e.data || !e.data.giscus) return;
  if (e.data.giscus.discussion) {
    syncGiscusTheme();
  }
});

