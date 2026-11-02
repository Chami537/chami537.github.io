// Main page shared utilities, scroll state, and music player.

const bar = document.querySelector('.progress');
const nlinks = document.querySelectorAll('nav .links a');
const secs = document.querySelectorAll('section[id]:not(#about)');

function getSectionTop(s) {
  return s.getBoundingClientRect().top + scrollY;
}

function updateProgress() {
  var h = document.documentElement.scrollHeight - innerHeight; if (h > 0) {
    var t = scrollY / h;
    bar.style.width = (t * 100) + '%';
  } else {
    bar.style.width = '0';
  }

  var cur = '';
  var visibleSections = Array.from(secs).filter(function(s) { return !s.hidden; });
  var currentSection = visibleSections[0];
  for (var i = 0; i < visibleSections.length; i++) {
    if (scrollY >= getSectionTop(visibleSections[i]) - 200) {
      currentSection = visibleSections[i];
      cur = currentSection.id;
    }
  }
  if (scrollY + innerHeight >= document.documentElement.scrollHeight - 2) {
    currentSection = visibleSections[visibleSections.length - 1];
    cur = currentSection ? currentSection.id : '';
  }
  // Read the actual label color so the progress bar and current section agree.
  var tag = currentSection && currentSection.querySelector('.section-tag');
  if (tag) bar.style.background = getComputedStyle(tag).color;
  for (var i = 0; i < nlinks.length; i++) {
    nlinks[i].classList.toggle('active', nlinks[i].getAttribute('href') === '#' + cur);
  }
}

// Scroll → progress bar + nav highlight
addEventListener('scroll', updateProgress, {passive: true});

// Nav sticky: hide on scroll down, show on scroll up
var _lastScrollY = scrollY;
addEventListener('scroll', function() {
  var nav = document.querySelector('nav');
  var dy = scrollY - _lastScrollY;
  if (scrollY < 100) { nav.classList.remove('hidden'); }
  else if (dy > 8) { nav.classList.add('hidden'); }
  else if (dy < -8) { nav.classList.remove('hidden'); }
  _lastScrollY = scrollY;
}, {passive: true});

// ResizeObserver: re-sync when content size changes (lazy images, load-more, etc.)
if (window.ResizeObserver) {
  new ResizeObserver(function() { updateProgress(); }).observe(document.body);
}

var player, curRow;
var musicTimeHandler, musicEndHandler;

function _fmtTime(sec) {
  if (!sec || !isFinite(sec)) return '0:00';
  var m = Math.floor(sec / 60);
  var s = Math.floor(sec % 60);
  return m + ':' + (s < 10 ? '0' : '') + s;
}

function _resetMusicRow(row) {
  if (!row) return;
  row.classList.remove('playing', 'paused');
  row.style.removeProperty('--progress');
}

function _toggleMusicRow(row) {
  if (player.paused) { player.play(); row.classList.remove('paused'); }
  else { player.pause(); row.classList.add('paused'); }
}

function _playMusicRow(row) {
  if (curRow) _resetMusicRow(curRow);
  curRow = row;
  row.classList.add('playing');
  player.src = encodeURI(row.dataset.src);
  player.play().catch(function() {
    _resetMusicRow(curRow);
    curRow = null;
  });
}

function _bindMusicRows(musicRows) {
  musicRows.forEach(row => row.addEventListener('click', function(e) {
    if (!row.dataset.src) return;
    if (curRow === row && player.duration) {
      var rect = row.getBoundingClientRect();
      player.currentTime = (e.clientX - rect.left) / rect.width * player.duration;
    }
    if (curRow === row) _toggleMusicRow(row);
    else _playMusicRow(row);
  }));
}

function _bindMusicProgress() {
  musicTimeHandler = function() {
    if (curRow && player.duration) {
      var pct = (player.currentTime / player.duration * 100).toFixed(2);
      curRow.style.setProperty('--progress', pct + '%');
      var t = curRow.querySelector('.time');
      if (t) t.textContent = _fmtTime(player.currentTime) + ' / ' + _fmtTime(player.duration);
    }
  };
}

function _bindMusicEnded(musicRows) {
  musicEndHandler = function() {
    if (curRow) { _resetMusicRow(curRow); var t = curRow.querySelector('.time'); if (t) t.textContent = ''; }
    var idx = Array.prototype.indexOf.call(musicRows, curRow);
    curRow = null;
    if (idx >= 0 && idx + 1 < musicRows.length) {
      musicRows[idx + 1].click();
    }
  };
}

function initMusicPlayer() {
  player = document.getElementById('player');
  if (!player) return;
  curRow = null;
  if (musicTimeHandler) player.removeEventListener('timeupdate', musicTimeHandler);
  if (musicEndHandler) player.removeEventListener('ended', musicEndHandler);
  var musicRows = document.querySelectorAll('.music-row');
  _bindMusicRows(musicRows);
  _bindMusicProgress();
  _bindMusicEnded(musicRows);
  player.addEventListener('timeupdate', musicTimeHandler);
  player.addEventListener('ended', musicEndHandler);
}

// ═══════════════════════════════════
// JSON Data Loading (skeleton + cache busting + fallback)
// ═══════════════════════════════════
function htmlEncode(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function inlineJsString(value) {
  return htmlEncode(String(value == null ? '' : value)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'"));
}

function safeExternalUrl(url) {
  var value = String(url || '').trim();
  return /^https?:\/\//i.test(value) ? value : '';
}

function _exifStr(ex, html) {
  var parts = [];
  if (ex.focal) parts.push(String(ex.focal));
  if (ex.aperture) parts.push(String(ex.aperture));
  if (ex.shutter) parts.push(String(ex.shutter));
  if (ex.iso) parts.push('ISO ' + String(ex.iso));
  var str = parts.join(' · ');
  return html ? str.replace(/&/g,'&amp;').replace(/</g,'&lt;') : str;
}

function _exifCamera(ex) { return ex.model || ex.camera || ''; }

function _gpsStr(lat, lng, decimals) {
  decimals = decimals != null ? decimals : 4;
  return Math.abs(lat).toFixed(decimals) + '\u00B0' + (lat >= 0 ? 'N' : 'S') + ', ' + Math.abs(lng).toFixed(decimals) + '\u00B0' + (lng >= 0 ? 'E' : 'W');
}

const TS = Date.now(); // cache busting timestamp, fixed per page load


function renderWork(data) {
  return data.map((w, i) => {
    const num = String(i + 1).padStart(2, '0');
    var url = safeExternalUrl(w.url);
    var tag = url ? 'a' : 'div';
    var linkAttrs = url ? ' href="' + htmlEncode(url) + '" target="_blank" rel="noopener noreferrer"' : '';
    return '<' + tag + ' class="work-card" data-repo="' + htmlEncode(w.repo||'') + '"' + linkAttrs + '>' +
      '<div class="num">' + num + '</div>' +
      '<h3>' + htmlEncode(w.title) + '</h3>' +
      '<p>' + htmlEncode(w.description) + '</p>' +
      '<div class="line-tag">' + htmlEncode((w.tags||[]).join(' · ')) + ' <span class="stars">' + ((w.stars != null) ? w.stars + ' stars' : '') + '</span></div>' +
      '</' + tag + '>';
  }).join('');
}
