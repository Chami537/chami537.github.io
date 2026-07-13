// Essay Giscus client loader.

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
    document.getElementById('giscus-container').appendChild(gs);

