// Admin Markdown preview rendering and math handling.

(function() {
  var saved = localStorage.getItem('theme');
  if (saved === 'dark') _applyTheme('dark');
})();

function renderKatexIn(el) {
  if (typeof katex === 'undefined') return;
  var elements = el.querySelectorAll('.arithmatex');
  elements.forEach(function(element) {
    var text = element.textContent || element.innerText;
    var isBlock = text.indexOf('\\[') !== -1;
    var startDelimiter = isBlock ? '\\[' : '\\(';
    var endDelimiter = isBlock ? '\\]' : '\\)';
    var startIndex = text.indexOf(startDelimiter);
    var endIndex = text.lastIndexOf(endDelimiter);
    if (startIndex === -1 || endIndex <= startIndex) return;
    try {
      katex.render(text.substring(startIndex + 2, endIndex), element, {
        displayMode: isBlock, throwOnError: false, output: 'htmlAndMathml'
      });
    } catch (error) {
      console.error('KaTeX:', error);
    }
  });
}

var _adminKatexLoading = null;
function _loadAdminKatex() {
  if (typeof katex !== 'undefined') return Promise.resolve();
  if (_adminKatexLoading) return _adminKatexLoading;
  var stylesheet = document.createElement('link');
  stylesheet.rel = 'stylesheet';
  stylesheet.href = 'https://cdn.staticfile.net/KaTeX/0.16.9/katex.min.css';
  document.head.appendChild(stylesheet);
  _adminKatexLoading = new Promise(function(resolve, reject) {
    var script = document.createElement('script');
    script.src = 'https://cdn.staticfile.net/KaTeX/0.16.9/katex.min.js';
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
  return _adminKatexLoading;
}

window._renderAdminEditor = function(el) {
  var math = el.querySelector('.arithmatex');
  if (math && typeof katex === 'undefined') {
    _loadAdminKatex().then(function() { renderKatexIn(el); }).catch(function() {
      console.warn('KaTeX failed to load');
    });
  } else {
    renderKatexIn(el);
  }
  highlightCodeBlocks(el);
};
