// Essay math and code block rendering.

function renderKatexIn(el) {
  (el.querySelectorAll ? el.querySelectorAll('.arithmatex') : []).forEach(function(sp) {
    var t = sp.textContent || sp.innerText;
    var isBlock = t.indexOf('\\[') !== -1;
    var startDelim = isBlock ? '\\[' : '\\(';
    var endDelim = isBlock ? '\\]' : '\\)';
    var startIdx = t.indexOf(startDelim);
    var endIdx = t.lastIndexOf(endDelim);
    if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
      var math = t.substring(startIdx + 2, endIdx);
      try {
        katex.render(math, sp, {displayMode: isBlock, throwOnError: false, output: 'htmlAndMathml'});
      } catch(e) { console.error('KaTeX:', e); }
    }
  });
}
function highlightCodeBlocks(el) {
  (el.querySelectorAll ? el.querySelectorAll('pre code[class*="language-"]') : []).forEach(function(code) {
    var langClass = Array.prototype.find.call(code.classList, function(cls) {
      return cls.indexOf('language-') === 0;
    });
    var lang = '';
    if (langClass && code.parentElement) {
      lang = langClass.replace('language-', '');
      code.parentElement.dataset.language = lang ? lang.charAt(0).toUpperCase() + lang.slice(1) : '';
      attachCodeLanguageButton(code, code.parentElement.dataset.language);
    }
    if (window.hljs) hljs.highlightElement(code);
    if (!code.querySelector('.hljs-keyword, .hljs-string, .hljs-meta, .hljs-built_in, .hljs-title')) {
      fallbackHighlightCodeBlock(code, lang);
    }
  });
}
function attachCodeLanguageButton(code, label) {
  var pre = code.parentElement;
  if (!pre || pre.querySelector('.code-language')) return;
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'code-language';
  btn.setAttribute('aria-label', 'Copy ' + label + ' code');
  btn.dataset.action = 'COPY';
  btn.textContent = label;
  btn.addEventListener('click', function() {
    var text = code.textContent || '';
    var done = function() {
      btn.dataset.action = 'COPIED';
      window.setTimeout(function() { btn.dataset.action = 'COPY'; }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function() {});
    } else {
      done();
    }
  });
  pre.appendChild(btn);
}
function escapeCodeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function fallbackHighlightCodeBlock(code, lang) {
  var text = code.textContent || '';
  var escaped = '';
  if (lang === 'c' || lang === 'cpp') {
    escaped = highlightPlainCode(text, /^(#\s*include\b.*)$/gm,
      /\b(int|void|return|char|float|double|if|else|for|while|struct|typedef|const|static)\b/g,
      /\b(printf|scanf|main)\b/g);
  } else if (lang === 'python' || lang === 'py') {
    escaped = highlightPlainCode(text, null,
      /\b(def|return|if|elif|else|for|while|import|from|class|in|with|as|try|except|pass|None|True|False)\b/g,
      /\b(print|len|range|str|int|float|list|dict|set)\b/g);
  } else {
    escaped = escapeCodeHtml(text);
  }
  code.innerHTML = escaped;
  code.classList.add('hljs');
}
function highlightPlainCode(text, metaRe, keywordRe, builtinRe) {
  return text.split('\n').map(function(line) {
    if (metaRe) {
      metaRe.lastIndex = 0;
      if (metaRe.test(line)) {
        return escapeCodeHtml(line).replace(/^(#\s*include\b)(.*)$/g, '<span class="hljs-meta">$1</span><span class="hljs-property">$2</span>');
      }
    }
    return line.split(/("[^"\n]*"|'[^'\n]*')/g).map(function(part) {
      if (/^("[^"\n]*"|'[^'\n]*')$/.test(part)) {
        return '<span class="hljs-string">' + escapeCodeHtml(part) + '</span>';
      }
      return escapeCodeHtml(part)
        .replace(keywordRe, '<span class="hljs-keyword">$1</span>')
        .replace(builtinRe, '<span class="hljs-built_in">$1</span>')
        .replace(/\b(\d+)\b/g, '<span class="hljs-number">$1</span>');
    }).join('');
  }).join('\n');
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
document.addEventListener("DOMContentLoaded", function() {
  renderKatexIn(document);
  highlightCodeBlocks(document);
});

