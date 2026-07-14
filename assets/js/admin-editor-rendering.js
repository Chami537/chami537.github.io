// Admin Markdown preview rendering and code highlighting.

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

function highlightCodeBlocks(el) {
  var blocks = el.querySelectorAll ? el.querySelectorAll('pre code[class*="language-"]') : [];
  blocks.forEach(function(code) {
    var languageClass = Array.prototype.find.call(code.classList, function(name) {
      return name.indexOf('language-') === 0;
    });
    var language = '';
    if (languageClass && code.parentElement) {
      language = languageClass.replace('language-', '');
      code.parentElement.dataset.language = language ? language.charAt(0).toUpperCase() + language.slice(1) : '';
      attachCodeLanguageButton(code, code.parentElement.dataset.language);
    }
    if (window.hljs) hljs.highlightElement(code);
    if (!code.querySelector('.hljs-keyword, .hljs-string, .hljs-meta, .hljs-built_in, .hljs-title')) {
      fallbackHighlightCodeBlock(code, language);
    }
  });
}

function attachCodeLanguageButton(code, label) {
  var pre = code.parentElement;
  if (!pre || pre.querySelector('.code-language')) return;
  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'code-language';
  button.setAttribute('aria-label', 'Copy ' + label + ' code');
  button.dataset.action = 'COPY';
  button.textContent = label;
  button.addEventListener('click', function() {
    var done = function() {
      button.dataset.action = 'COPIED';
      window.setTimeout(function() { button.dataset.action = 'COPY'; }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code.textContent || '').then(done).catch(function() {});
    } else {
      done();
    }
  });
  pre.appendChild(button);
}

function escapeCodeHtml(value) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function fallbackHighlightCodeBlock(code, language) {
  var text = code.textContent || '';
  var escaped;
  if (language === 'c' || language === 'cpp') {
    escaped = highlightPlainCode(text, /^(#\s*include\b.*)$/gm,
      /\b(int|void|return|char|float|double|if|else|for|while|struct|typedef|const|static)\b/g,
      /\b(printf|scanf|main)\b/g);
  } else if (language === 'python' || language === 'py') {
    escaped = highlightPlainCode(text, null,
      /\b(def|return|if|elif|else|for|while|import|from|class|in|with|as|try|except|pass|None|True|False)\b/g,
      /\b(print|len|range|str|int|float|list|dict|set)\b/g);
  } else {
    escaped = escapeCodeHtml(text);
  }
  code.innerHTML = escaped;
  code.classList.add('hljs');
}

function highlightPlainCode(text, metaPattern, keywordPattern, builtinPattern) {
  return text.split('\n').map(function(line) {
    if (metaPattern) {
      metaPattern.lastIndex = 0;
      if (metaPattern.test(line)) {
        return escapeCodeHtml(line).replace(/^(#\s*include\b)(.*)$/g,
          '<span class="hljs-meta">$1</span><span class="hljs-property">$2</span>');
      }
    }
    return line.split(/("[^"\n]*"|'[^'\n]*')/g).map(function(part) {
      if (/^("[^"\n]*"|'[^'\n]*')$/.test(part)) {
        return '<span class="hljs-string">' + escapeCodeHtml(part) + '</span>';
      }
      return escapeCodeHtml(part)
        .replace(keywordPattern, '<span class="hljs-keyword">$1</span>')
        .replace(builtinPattern, '<span class="hljs-built_in">$1</span>')
        .replace(/\b(\d+)\b/g, '<span class="hljs-number">$1</span>');
    }).join('');
  }).join('\n');
}

window._renderAdminEditor = function(el) {
  renderKatexIn(el);
  highlightCodeBlocks(el);
};
