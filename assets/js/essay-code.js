// Essay math rendering and Markdown preparation.

function renderKatexIn(el) {
  (el.querySelectorAll ? el.querySelectorAll('.arithmatex') : []).forEach(function(sp) {
    var text = sp.textContent || sp.innerText;
    var isBlock = text.indexOf('\\[') !== -1;
    var startDelimiter = isBlock ? '\\[' : '\\(';
    var endDelimiter = isBlock ? '\\]' : '\\)';
    var startIndex = text.indexOf(startDelimiter);
    var endIndex = text.lastIndexOf(endDelimiter);
    if (startIndex !== -1 && endIndex !== -1 && endIndex > startIndex) {
      var math = text.substring(startIndex + 2, endIndex);
      try {
        katex.render(math, sp, {displayMode: isBlock, throwOnError: false, output: 'htmlAndMathml'});
      } catch (error) {
        console.error('KaTeX:', error);
      }
    }
  });
}

function escapeHtmlOutsideCode(md) {
  return md.split(/(```[\s\S]*?```)/g).map(function(part) {
    if (part.indexOf('```') === 0 && part.lastIndexOf('```') === part.length - 3) return part;
    return part.split(/(`+[^`\n]+?`+)/g).map(function(inline) {
      return inline.indexOf('`') === 0 && inline.lastIndexOf('`') === inline.length - 1
        ? inline
        : inline.replace(/</g, '&lt;');
    }).join('');
  }).join('');
}

function markMathForKatex(md) {
  return md.replace(/\$\$([\s\S]+?)\$\$/g, function(_, math) {
    return '<div class="arithmatex">\\[' + math.trim() + '\\]</div>';
  }).replace(/(^|[^$])\$([^$\n]+?)\$/g, function(_, prefix, math) {
    return prefix + '<span class="arithmatex">\\(' + math.trim() + '\\)</span>';
  });
}

document.addEventListener('DOMContentLoaded', function() {
  renderKatexIn(document);
  highlightCodeBlocks(document);
});
