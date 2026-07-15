// Admin Markdown preview rendering and math handling.

(function() {
  var saved = localStorage.getItem('theme');
  if (saved === 'dark') _applyTheme('dark');
})();

function renderKatexIn(el) {
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

window._renderAdminEditor = function(el) {
  renderKatexIn(el);
  highlightCodeBlocks(el);
};
