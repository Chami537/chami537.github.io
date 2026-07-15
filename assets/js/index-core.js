// Main page shared utilities, scroll state, and music player.

const bar = document.querySelector('.progress');
const nlinks = document.querySelectorAll('nav .links a');
const secs = document.querySelectorAll('section[id]:not(#about)');

function getSectionTop(s) {
  return s.getBoundingClientRect().top + scrollY;
}

function progressColor(t, h) {
  var colors = ['#ff4d4d', '#ff6d00', '#ffb800', '#0066ff', '#00c853', '#9c27b0'];
  if (h <= 0 || secs.length < 2) return colors[0];
  var stops = Array.from(secs).map(function(s) { return (getSectionTop(s) - 200) / h; });
  if (t < stops[0]) return colors[0];
  for (var i = 0; i < stops.length - 1; i++) {
    if (t >= stops[i] && t < stops[i+1]) {
      var seg = (t - stops[i]) / (stops[i+1] - stops[i]);
      return lerpColor(colors[i], colors[Math.min(i+1, colors.length-1)], seg);
    }
  }
  return colors[colors.length - 1];
}

function lerpColor(a, b, t) {
  var ah = parseInt(a.slice(1), 16), bh = parseInt(b.slice(1), 16);
  var ar = (ah >> 16) & 0xff, ag = (ah >> 8) & 0xff, ab = ah & 0xff;
  var br = (bh >> 16) & 0xff, bg = (bh >> 8) & 0xff, bb = bh & 0xff;
  return 'rgb(' + Math.round(ar + (br - ar) * t) + ',' + Math.round(ag + (bg - ag) * t) + ',' + Math.round(ab + (bb - ab) * t) + ')';
}

function updateProgress() {
  var h = document.documentElement.scrollHeight - innerHeight; if (h > 0) {
    var t = scrollY / h;
    bar.style.width = (t * 100) + '%';
    bar.style.background = progressColor(t, h);
  } else {
    bar.style.width = '0';
  }

  var cur = '';
  for (var i = 0; i < secs.length; i++) {
    if (scrollY >= getSectionTop(secs[i]) - 200) cur = secs[i].id;
  }
  if (scrollY + innerHeight >= document.documentElement.scrollHeight - 2) {
    cur = secs[secs.length - 1].id;
  }
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
    const num = String(w.id || i + 1).padStart(2, '0');
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
