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

var _essayCodeDependencyLoads = {};
function loadEssayCodeScript(name, src) {
  if (window[name]) return Promise.resolve();
  if (_essayCodeDependencyLoads[name]) return _essayCodeDependencyLoads[name];
  _essayCodeDependencyLoads[name] = new Promise(function(resolve, reject) {
    var script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
  return _essayCodeDependencyLoads[name];
}

function loadEssayKatex() {
  var stylesheet = document.querySelector('link[data-essay-katex]');
  if (!stylesheet) {
    stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.dataset.essayKatex = 'true';
    stylesheet.href = 'https://cdn.staticfile.net/KaTeX/0.16.9/katex.min.css';
    document.head.appendChild(stylesheet);
  }
  return loadEssayCodeScript('katex', 'https://cdn.staticfile.net/KaTeX/0.16.9/katex.min.js');
}

function enhanceEssayCode() {
  var root = document.querySelector('.essay-body');
  if (!root) return;

  var hasMath = root.querySelector('.arithmatex');
  var hasCode = root.querySelector('pre code[class*="language-"]');
  if (hasCode) {
    // Give code an immediate local rendering while the optional CDN loads.
    highlightCodeBlocks(root);
    loadEssayCodeScript('hljs', 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js')
      .then(function() { highlightCodeBlocks(root); })
      .catch(function() {});
  }
  if (hasMath) {
    loadEssayKatex().then(function() { renderKatexIn(root); }).catch(function() {});
  }
}

// This script is loaded after the article body, so enhancement can start
// immediately without waiting for unrelated parser-blocking dependencies.
enhanceEssayCode();
