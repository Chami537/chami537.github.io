async function loadTracks() {
  var data = await api('GET', '/api/tracks');
  var html = '';
  data.forEach(function(t, i) {
    html += '<div class="track-row">' +
      '<span>' + esc(t.name) + ' <code class="code-muted">' + esc(t.file) + '</code></span>' +
      '<button class="btn btn-sm btn-danger" onclick="deleteTrack(' + i + ')">删除</button>' +
      '</div>';
  });
  document.getElementById('tracks-list').innerHTML = html || '<p class="text-muted">暂无轨迹</p>';
}

var _lastTrackFile = '';

async function uploadTrackFile(f, autoName) {
  var fd = new FormData(); fd.append('file', f);
  var r = await api('POST', '/api/tracks/upload', fd);
  if (r.file) {
    _lastTrackFile = r.file;
    if (autoName) { var tn = document.getElementById('track-name'); if (tn) tn.value = r.file.replace('.gpx',''); }
    loadTracks();
    toast('已上传: ' + r.file);
  }
}

async function renameLastTrack(name) {
  if (!_lastTrackFile || !name.trim()) return;
  var tracks = await api('GET', '/api/tracks');
  for (var i = tracks.length - 1; i >= 0; i--) {
    if (tracks[i].file === _lastTrackFile) {
      await api('DELETE', '/api/tracks/' + i);
      await api('POST', '/api/tracks', {name: name.trim(), file: _lastTrackFile});
      loadTracks();
      break;
    }
  }
}


function handleTrackDrop(e) {
  var files = e.dataTransfer.files;
  if (files.length) handleTrackFile(files);
}

function handleTrackFile(files) {
  Array.from(files).forEach(function(f) {
    if (f.name.toLowerCase().endsWith('.gpx')) uploadTrackFile(f, true);
  });
}

async function deleteTrack(i) {
  if (!confirm('删除此轨迹？')) return;
  await api('DELETE', '/api/tracks/' + i);
  loadTracks();
}

// Dashboard tab dispatch lives in admin-tabs.js: if (name === 'dashboard') loadDashboard();
// ═══════════════════════════════════
// About
async function loadAbout() {
  try {
    const data = await api('GET', '/api/about');
    document.getElementById('about-content').value = data.content || '';
    document.getElementById('about-avatar-preview').src = data.avatar || '';
    document.getElementById('about-tags').value = (data.tags || []).join(', ');
    renderAboutTagChips();
  } catch(e) { toast(e.message, true); }
}

async function uploadAvatar() {
  try {
  var file = document.getElementById('about-avatar-file').files[0];
  if (!file) return;
  var fd = new FormData();
  fd.append('file', file);    var result = await api('POST', '/api/about/upload-avatar', fd);
    document.getElementById('about-avatar-preview').src = result.url;
    document.getElementById('about-avatar-preview').dataset.path = result.url;
    toast('头像已上传');
  } catch(e) { toast(e.message, true); }
}

async function saveAbout() {
  try {
    await api('PUT', '/api/about', {
      content: document.getElementById('about-content').value,
      tags: (function() { var all = getAboutTags(), sel = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean); return all.filter(function(t){return sel.indexOf(t)>=0;}); })(),
      avatar: document.getElementById('about-avatar-preview').dataset.path || document.getElementById('about-avatar-preview').src.split('/').slice(-2).join('/')
    });
    markClean();
    toast('简介已保存');
  } catch(e) { toast(e.message, true); }
}

window['about' + 'Entry'] = saveAbout;

// README
// ═══════════════════════════════════
async function loadReadme() {
  try {
    var data = await api('GET', '/api/readme');
    document.getElementById('readme-content').value = data.content || '';
  } catch(e) { toast(e.message, true); }
}

async function saveReadme() {
  try {
    await api('PUT', '/api/readme', {
      content: document.getElementById('readme-content').value
    });
    markClean();
    toast('README 已保存');
  } catch(e) { toast(e.message, true); }
}

// ═══════════════════════════════════
// Theme (toggleTheme / _applyTheme defined in shared /theme.js)
// ═══════════════════════════════════
(function() {
  var saved = localStorage.getItem('theme');
  if (saved === 'dark') _applyTheme('dark');
})();

// ═══ KaTeX renderer ═══
function renderKatexIn(el) {
  var els = el.querySelectorAll('.arithmatex');
  els.forEach(function(sp) {
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
  var blocks = el.querySelectorAll ? el.querySelectorAll('pre code[class*="language-"]') : [];
  blocks.forEach(function(code) {
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

window._renderAdminEditor = function(el) {
  renderKatexIn(el);
  highlightCodeBlocks(el);
};
