// Essay Giscus client loader.

(function() {
  var container = document.getElementById('giscus-container');
  if (!container) return;

  var loaded = false;
  function loadGiscus() {
    if (loaded) return;
    loaded = true;
    var gs = document.createElement('script');
    gs.src = 'https://giscus.app/client.js';
    gs.setAttribute('data-repo', 'Chami537/chami537.github.io');
    gs.setAttribute('data-repo-id', 'R_kgDOS6Xqvg');
    gs.setAttribute('data-category', 'General');
    gs.setAttribute('data-category-id', 'DIC_kwDOS6Xqvs4C_7Cz');
    gs.setAttribute('data-mapping', 'pathname');
    gs.setAttribute('data-strict', '0');
    gs.setAttribute('data-reactions-enabled', '1');
    gs.setAttribute('data-emit-metadata', '0');
    gs.setAttribute('data-input-position', 'top');
    gs.setAttribute('data-theme', document.documentElement.classList.contains('dark')
      ? 'https://chami537.github.io/data/giscus-dark.css'
      : 'https://chami537.github.io/data/giscus.css');
    gs.setAttribute('data-lang', 'zh-CN');
    gs.crossOrigin = 'anonymous';
    gs.async = true;
    container.appendChild(gs);
  }

  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function(entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].isIntersecting) {
          observer.disconnect();
          loadGiscus();
          break;
        }
      }
    }, { rootMargin: '200px 0px' });
    observer.observe(container);
  } else if ('requestIdleCallback' in window) {
    requestIdleCallback(loadGiscus, { timeout: 2000 });
  } else {
    setTimeout(loadGiscus, 1500);
  }
})();

