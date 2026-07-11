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

function initMusicPlayer() {
  player = document.getElementById('player');
  if (!player) return;
  curRow = null;
  if (musicTimeHandler) player.removeEventListener('timeupdate', musicTimeHandler);
  if (musicEndHandler) player.removeEventListener('ended', musicEndHandler);

  var musicRows = document.querySelectorAll('.music-row');
  musicRows.forEach(row => {
    row.addEventListener('click', function(e) {
      var src = row.dataset.src;
      if (!src) return;
      // If clicking on a playing row, seek to position
      if (curRow === row && player.duration) {
        var rect = row.getBoundingClientRect();
        var pct = (e.clientX - rect.left) / rect.width;
        player.currentTime = pct * player.duration;
        if (player.paused) { player.play(); row.classList.remove('paused'); }
        else { player.pause(); row.classList.add('paused'); }
        return;
      }
      if (curRow === row) {
        if (player.paused) { player.play(); row.classList.remove('paused'); }
        else { player.pause(); row.classList.add('paused'); }
        return;
      }
      if (curRow) { curRow.classList.remove('playing', 'paused'); curRow.style.removeProperty('--progress'); }
      curRow = row;
      row.classList.add('playing');
      player.src = encodeURI(src);
      player.play().catch(function() {
        if (curRow) { curRow.classList.remove('playing', 'paused'); curRow.style.removeProperty('--progress'); curRow = null; }
      });
    });
  });

  musicTimeHandler = function() {
    if (curRow && player.duration) {
      var pct = (player.currentTime / player.duration * 100).toFixed(2);
      curRow.style.setProperty('--progress', pct + '%');
      var t = curRow.querySelector('.time');
      if (t) t.textContent = _fmtTime(player.currentTime) + ' / ' + _fmtTime(player.duration);
    }
  };
  musicEndHandler = function() {
    if (curRow) { curRow.classList.remove('playing'); curRow.style.removeProperty('--progress');
      var t = curRow.querySelector('.time'); if (t) t.textContent = ''; }
    var idx = Array.prototype.indexOf.call(musicRows, curRow);
    curRow = null;
    if (idx >= 0 && idx + 1 < musicRows.length) {
      musicRows[idx + 1].click();
    }
  };
  player.addEventListener('timeupdate', musicTimeHandler);
  player.addEventListener('ended', musicEndHandler);
}

// ═══════════════════════════════════
// JSON Data Loading (skeleton + cache busting + fallback)
// ═══════════════════════════════════
function htmlEncode(str) {
  const d = document.createElement('div');
  d.textContent = str != null ? str : '';
  return d.innerHTML.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
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
    return '<a class="work-card" data-repo="' + htmlEncode(w.repo||'') + '" href="' + htmlEncode(w.url) + '" target="_blank" rel="noopener noreferrer">' +
      '<div class="num">' + num + '</div>' +
      '<h3>' + htmlEncode(w.title) + '</h3>' +
      '<p>' + htmlEncode(w.description) + '</p>' +
      '<div class="line-tag">' + htmlEncode((w.tags||[]).join(' · ')) + ' <span class="stars">' + ((w.stars != null) ? w.stars + ' stars' : '') + '</span></div>' +
      '</a>';
  }).join('');
}

var _essayData = [];
var _allTags = [];
var _essayPrimaryFilter = '';
var _essayTopicFilter = '';
var _essayTypeFilter = '';
var _essayPrimaryTags = ['技术', '生活', '摄影', '阅读', '感悟', '随笔'];
var _essayTechTopics = ['Obsidian', 'Kotlin', 'Shell', 'Git', 'LeetCode', 'Python', 'Flask', '前端', '安全'];
var _essayTechTypes = ['学习日志', '教程', '踩坑', '速查', '题解', '项目复盘'];

function _essayTagsFor(item) {
  return (item.tag || '').split(/[,，]/).map(function(t) { return t.trim(); }).filter(Boolean);
}

function _orderedEssayTags(tags, preferred) {
  var known = [];
  var rest = [];
  preferred.forEach(function(t) {
    if (tags.indexOf(t) >= 0) known.push(t);
  });
  tags.forEach(function(t) {
    if (known.indexOf(t) < 0) rest.push(t);
  });
  return known.concat(rest.sort(function(a, b) { return a.localeCompare(b, 'zh-CN'); }));
}

function _restartContentMotion(el) {
  if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  el.classList.remove('content-swap');
  void el.offsetWidth;
  el.classList.add('content-swap');
}

function buildEssayFilter() {
  var tags = new Set(_allTags);
  var techTopicSet = new Set();
  var techTypeSet = new Set();
  _essayData.forEach(function(e) {
    var essayTags = _essayTagsFor(e);
    if (essayTags.indexOf('技术') < 0) return;
    essayTags.forEach(function(t) {
      if (_essayTechTypes.indexOf(t) >= 0) techTypeSet.add(t);
      else if (t !== '技术' && _essayPrimaryTags.indexOf(t) < 0) techTopicSet.add(t);
    });
  });
  if (!tags.size) {
    _essayData.forEach(function(e) {
      _essayTagsFor(e).forEach(function(t) { tags.add(t); });
    });
  }
  var primary = [];
  _essayPrimaryTags.forEach(function(t) {
    if (tags.has(t)) primary.push(t);
  });
  tags.forEach(function(t) {
    if (primary.indexOf(t) < 0 && !techTopicSet.has(t) && !techTypeSet.has(t)) primary.push(t);
  });
  var html = '<button type="button" class="ef-chip' + (!_essayPrimaryFilter ? ' active' : '') + '" onclick="filterEssayPrimary(\'\')">置顶</button>';
  primary.forEach(function(t) {
    html += '<button type="button" class="ef-chip' + (_essayPrimaryFilter === t ? ' active' : '') + '" data-tag="' + htmlEncode(t) + '" onclick="filterEssayPrimary(this.getAttribute(\'data-tag\'))">' + htmlEncode(t) + '</button>';
  });
  var primaryEl = document.getElementById('essay-tag-filter');
  primaryEl.innerHTML = html;

  var topicEl = document.getElementById('essay-topic-filter');
  var typeEl = document.getElementById('essay-type-filter');
  if (!topicEl || !typeEl) return;
  if (_essayPrimaryFilter !== '技术') {
    _essayTopicFilter = '';
    _essayTypeFilter = '';
    topicEl.style.display = 'none';
    topicEl.innerHTML = '';
    typeEl.style.display = 'none';
    typeEl.innerHTML = '';
    return;
  }
  var techTopics = _orderedEssayTags(Array.from(techTopicSet), _essayTechTopics);
  var techTypes = _orderedEssayTags(Array.from(techTypeSet), _essayTechTypes);
  if (techTopics.length) {
    var topicHtml = '<span class="ef-label">主题</span><span class="ef-options"><button type="button" class="ef-chip' + (!_essayTopicFilter ? ' active' : '') + '" onclick="filterEssayTopic(\'\')">全部</button>';
    techTopics.forEach(function(t) {
      topicHtml += '<button type="button" class="ef-chip' + (_essayTopicFilter === t ? ' active' : '') + '" data-tag="' + htmlEncode(t) + '" onclick="filterEssayTopic(this.getAttribute(\'data-tag\'))">' + htmlEncode(t) + '</button>';
    });
    topicHtml += '</span>';
    topicEl.innerHTML = topicHtml;
    topicEl.style.display = 'flex';
  } else {
    topicEl.style.display = 'none';
    topicEl.innerHTML = '';
  }
  if (techTypes.length) {
    var typeHtml = '<span class="ef-label">类型</span><span class="ef-options"><button type="button" class="ef-chip' + (!_essayTypeFilter ? ' active' : '') + '" onclick="filterEssayType(\'\')">全部</button>';
    techTypes.forEach(function(t) {
      typeHtml += '<button type="button" class="ef-chip' + (_essayTypeFilter === t ? ' active' : '') + '" data-tag="' + htmlEncode(t) + '" onclick="filterEssayType(this.getAttribute(\'data-tag\'))">' + htmlEncode(t) + '</button>';
    });
    typeHtml += '</span>';
    typeEl.innerHTML = typeHtml;
    typeEl.style.display = 'flex';
  } else {
    typeEl.style.display = 'none';
    typeEl.innerHTML = '';
  }
}

function filterEssayPrimary(tag) {
  _essayPrimaryFilter = tag;
  _essayTopicFilter = '';
  _essayTypeFilter = '';
  buildEssayFilter();
  renderEssayList();
}

function filterEssayTopic(tag) {
  _essayTopicFilter = tag;
  buildEssayFilter();
  renderEssayList();
}

function filterEssayType(tag) {
  _essayTypeFilter = tag;
  buildEssayFilter();
  renderEssayList();
}

function renderEssayList() {
  var filtered = _essayData;
  if (_essayPrimaryFilter) {
    filtered = _essayData.filter(function(e) {
      var tags = _essayTagsFor(e);
      if (tags.indexOf(_essayPrimaryFilter) < 0) return false;
      if (_essayTopicFilter && tags.indexOf(_essayTopicFilter) < 0) return false;
      if (_essayTypeFilter && tags.indexOf(_essayTypeFilter) < 0) return false;
      return true;
    });
  } else {
    // Show pinned articles (default "置顶" view)
    filtered = _essayData.filter(function(e) {
      return e.pinned === true;
    });
  }
  var MAX = 5;
  var html = '';
  var shown = filtered.slice(0, MAX);
  var hidden = filtered.length - MAX;
  shown.forEach(function(e) {
    var tagParam = '?tag=' + encodeURIComponent(_essayTopicFilter || _essayTypeFilter || _essayPrimaryFilter || '置顶');
    var tagText = _essayTagDisplay(e);
    html += '<a class="essay-row" href="essays/' + htmlEncode(e.slug) + '.html' + tagParam + '">' +
      '<div class="essay-left">' +
      '<span class="essay-title">' + htmlEncode(e.title) + '</span>' +
      (e.excerpt ? '<span class="essay-excerpt">' + htmlEncode(e.excerpt) + '</span>' : '') +
      '</div>' +
      '<div class="essay-right">' +
      '<span class="essay-tag">' + htmlEncode(tagText) + '</span>' +
      '<span class="essay-meta">' + (e.date_display || '') + ' · ' + (e.readTime || 1) + ' min read</span>' +
      '<span class="essay-arr">→</span>' +
      '</div>' +
      '</a>';
  });
  if (hidden > 0) {
    html += '<a class="essay-row" href="archive.html" style="justify-content:center;color:var(--muted);font-size:13px;text-decoration:none;">查看全部（' + hidden + ' 篇）→</a>';
  }
  var listEl = document.getElementById('essays-list');
  listEl.innerHTML = html;
  listEl.classList.remove('skeleton-loading');
  _restartContentMotion(listEl);
}

function _essayTagDisplay(e) {
  var tags = _essayTagsFor(e);
  if (tags.indexOf('技术') < 0) return (e.tag || '').replace(/, ?/g, ' · ');
  var topic = tags.find(function(t) {
    return t !== '技术' && _essayPrimaryTags.indexOf(t) < 0 && _essayTechTypes.indexOf(t) < 0;
  });
  var type = tags.find(function(t) { return _essayTechTypes.indexOf(t) >= 0; });
  var left = topic ? '技术 · ' + topic : '技术';
  return type ? left + '    ' + type : left;
}

function renderPhotos(data) {
  if (!data || !data.length) {
    return '<div class="photo-empty">这一组暂时没有匹配的照片。</div>';
  }
  return data.map(function(p) {
    var fn = encodeURIComponent(p.filename);
    var srcset = 'images/sm/' + fn + ' 400w, images/md/' + fn + ' 800w, images/lg/' + fn + ' 1920w';
    var ex = p.exif || {};
    var exifStr = (_exifCamera(ex) + ' ' + _exifStr(ex)).trim();
    var gpsText2 = '', gpsText4 = '';
    if (ex.gps) {
      gpsText2 = _gpsStr(ex.gps.lat, ex.gps.lng, 2);
      gpsText4 = _gpsStr(ex.gps.lat, ex.gps.lng, 4);
    }
    var gpsHtml = gpsText2 ? ' · <span style="cursor:pointer;text-decoration:underline" class="gps-link" onclick="event.stopPropagation();flyToPhoto(\'' + encodeURIComponent(p.filename) + '\',' + ex.gps.lat + ',' + ex.gps.lng + ')">' + gpsText2 + '</span>' : '';
    var dateHtml = p.date ? '<span class="photo-date">' + p.date + '</span>' : '';
    var infoHtml = (exifStr || gpsHtml) ? '<div class="photo-info">' + exifStr + gpsHtml + '</div>' : '';
    var tagStr = (p.tags || []).join(',');
    return '<div class="photo-item" data-tags="' + htmlEncode(tagStr) + '">' +
      '<img src="images/sm/' + fn + '" srcset="' + srcset + '" sizes="(max-width: 768px) 50vw, 33vw" alt="Photo" loading="lazy" data-exif="' + htmlEncode(exifStr + (gpsText4 ? ' · ' + gpsText4 : '') + (p.date ? ' · ' + p.date : '')) + '">' +
      dateHtml +
      infoHtml +
      '</div>';
  }).join('');
}

var _photoMap = null;
var _photoMapLoaded = false;
var _markerGroup = null;
var _currentPhotoTag = '';
var _photoStories = [];
var _currentStory = -1;

function renderPhotoStories(data) {
  _photoStories = data || [];
  var el = document.getElementById('photo-stories');
  if (!el || !_photoStories.length) { if (el) el.style.display = 'none'; return; }
  el.style.display = 'flex';
  var html = '';
  _photoStories.forEach(function(story, i) {
    var loc = story.gps ? _gpsStr(story.gps.lat, story.gps.lng, 2) : '';
    var active = _currentStory === i;
    var photoCount = story.photos ? story.photos.length : 0;
    var countText = photoCount + ' photo' + (photoCount === 1 ? '' : 's');
    var cover = story.cover ? encodeURIComponent(story.cover) : '';
    html += '<button type="button" class="story-card' + (active ? ' active' : '') + '" aria-pressed="' + (active ? 'true' : 'false') + '" aria-label="' + htmlEncode(story.name || 'Photo story') + ', ' + countText + '" onclick="filterByStory(' + i + ')">' +
      '<span class="story-cover">' + (cover ? '<img src="images/sm/' + cover + '" alt="" loading="lazy">' : '') + '<span class="story-count">' + countText + '</span></span>' +
      '<div class="story-info">' +
      '<span class="story-name">' + htmlEncode(story.name) + '</span>' +
      (story.caption ? '<span class="story-caption">' + htmlEncode(story.caption) + '</span>' : '') +
      '<span class="story-meta">' + (story.date ? story.date : 'Untitled story') + '</span>' +
      (loc ? '<span class="story-loc">' + loc + '</span>' : '') +
      '</div></button>';
  });
  el.innerHTML = html;
}

function filterByStory(idx) {
  var wasActive = _currentStory === idx;
  _currentStory = wasActive ? -1 : idx;
  document.querySelectorAll('.story-card').forEach(function(c, i) {
    var active = i === _currentStory;
    c.classList.toggle('active', active);
    c.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  _renderAllPhotos();
  _syncMapMarkers();
  _syncPhotoLocationCount();
  _syncStoryNote();
}

function clearStoryFilter() {
  _currentStory = -1;
  document.querySelectorAll('.story-card').forEach(function(c) {
    c.classList.remove('active');
    c.setAttribute('aria-pressed', 'false');
  });
  _renderAllPhotos();
  _syncMapMarkers();
  _syncPhotoLocationCount();
  _syncStoryNote();
}

function buildPhotoTagFilter() {
  var tags = new Set();
  (window._photoData || []).forEach(function(p) {
    (p.tags || []).forEach(function(t) { tags.add(t); });
  });
  var el = document.getElementById('photo-tag-filter');
  if (tags.size === 0) { el.style.display = 'none'; return; }
  el.style.display = 'flex';
  var html = '<span tabindex="0" role="button" class="ef-chip' + (!_currentPhotoTag ? ' active' : '') + '" onclick="filterPhotosByTag(\'\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();filterPhotosByTag(\'\')}">全部</span>';
  tags.forEach(function(t) {
    html += '<span tabindex="0" role="button" class="ef-chip' + (_currentPhotoTag === t ? ' active' : '') + '" onclick="filterPhotosByTag(\'' + htmlEncode(t) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();filterPhotosByTag(\'' + htmlEncode(t) + '\')}">' + htmlEncode(t) + '</span>';
  });
  el.innerHTML = html;
}

function openMapPhotoLB(filename) {
  var pool = _getFilteredPhotos().filter(function(p) { return p.exif && p.exif.gps; });
  lbPhotos = pool.map(function(p) {
    var ex = p.exif || {};
    var parts = [_exifCamera(ex), _exifStr(ex, true), _gpsStr(ex.gps.lat, ex.gps.lng, 4), p.date].filter(Boolean);
    return { src: 'images/lg/' + p.filename, alt: '', exif: parts.join(' · ') };
  });
  lbIndex = lbPhotos.findIndex(function(p) { return p.src.endsWith('/' + filename); });
  if (lbIndex < 0) lbIndex = 0;
  openLB();
}

function _syncMapMarkers() {
  if (!_markerGroup || !window._photoData) return;
  _markerGroup.clearLayers();
  var pool = _getFilteredPhotos();
  var gpsPhotos = pool.filter(function(p) { return p.exif && p.exif.gps; });
  gpsPhotos.forEach(function(p) {
    var g = p.exif.gps;
    var ex = p.exif || {};
    var camera = (ex.model || ex.camera || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    var exifHtml = _exifStr(ex, true);
    var gpsHtml = _gpsStr(g.lat, g.lng);
    var html = '<img src=\"images/sm/' + encodeURIComponent(p.filename) + '\" onclick=\"openMapPhotoLB(\'' + encodeURIComponent(p.filename) + '\')\" style=\"cursor:zoom-in\" title=\"点击查看大图\">';
    if (camera) html += '<b>' + camera + '</b>';
    if (exifHtml) html += '<br><span class=\"popup-exif\">' + exifHtml + '</span>';
    html += '<br><span class=\"popup-exif\">' + gpsHtml + '</span>';
    var icon = L.divIcon({className: 'custom-marker', html: '<div class="marker-dot"></div>', iconSize: [16, 16], iconAnchor: [8, 8]});
    var mw = Math.min(260, window.innerWidth - 48);
    var popup = L.popup({maxWidth: mw, minWidth: 100}).setContent(html);
    L.marker([g.lat, g.lng], {icon: icon}).addTo(_markerGroup).bindPopup(popup);
  });
  if (_markerGroup.getLayers().length > 0) {
    _photoMap.fitBounds(_markerGroup.getBounds(), {padding: [50, 50], maxZoom: 14});
  }
}

function filterPhotosByTag(tag) {
  _currentPhotoTag = tag;
  document.querySelectorAll('#photo-tag-filter .ef-chip').forEach(function(c) {
    c.classList.toggle('active', c.textContent === (tag || '全部'));
  });
  _renderAllPhotos();
  _syncMapMarkers();
  _syncPhotoLocationCount();
  _syncStoryNote();
}
var _photoMapLoading = false;
var _photoMapCallbacks = [];

function loadLeaflet(cb) {
  if (_photoMapLoaded) { if (cb) cb(); return; }
  if (_photoMapLoading) { if (cb) _photoMapCallbacks.push(cb); return; }
  _photoMapLoading = true;
  if (cb) _photoMapCallbacks.push(cb);

  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css';
  document.head.appendChild(link);

  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js';
  s.onload = function() {
    setTimeout(function() {
      if (!_photoMap) initPhotoMap();
      _photoMapLoaded = true;
      _photoMapLoading = false;
      var cbs = _photoMapCallbacks;
      _photoMapCallbacks = [];
      cbs.forEach(function(f) { f(); });
    }, 100);
  };
  s.onerror = function() {
    _photoMapLoading = false;
    _photoMapCallbacks = [];
  };
  document.head.appendChild(s);
}

function initPhotoMap() {
  var container = document.getElementById('photo-map-container');
  _photoMap = L.map(container).setView([22.5431, 113.9579], 11);
  _markerGroup = L.featureGroup().addTo(_photoMap);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, subdomains: 'abcd',
    attribution: '&copy; OSM &copy; CARTO'
  }).addTo(_photoMap);

  // Add markers from photo data (shared with _syncMapMarkers)
  if (window._photoData) {
    _syncMapMarkers();
  }

  // Load GPX tracks (always load, independent of photo data)
  loadGpxTracks();

  // Sync dark mode
  if (document.documentElement.classList.contains('dark')) {
    _photoMap.getContainer().classList.add('dark');
  }
}

function _haversine(lat1, lon1, lat2, lon2) {
  var R = 6371000; // meters
  var dLat = (lat2 - lat1) * Math.PI / 180;
  var dLon = (lon2 - lon1) * Math.PI / 180;
  var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return R * 2 * Math.atan2(Math.sqrt(Math.min(a, 1)), Math.sqrt(Math.max(1 - a, 0)));
}

function _fmtDist(m) {
  if (m < 1000) return Math.round(m) + ' m';
  return (m / 1000).toFixed(1) + ' km';
}

function loadGpxTracks() {
  var trackColors = ['#0066ff', '#ff4d4d', '#00c853', '#ffb800', '#9c27b0'];
  var colorIdx = 0;
  fetch('/data/tracks.json?v=' + TS).then(function(r) {
    if (!r.ok) return;
    return r.json();
  }).then(function(tracks) {
    if (!tracks || !tracks.length) return;
    tracks.forEach(function(t) {
      fetch('/tracks/' + t.file).then(function(r) { return r.text(); }).then(function(xml) {
        var parser = new DOMParser();
        var doc = parser.parseFromString(xml, 'text/xml');
        var points = [];
        var dist = 0, gain = 0, prevEle = null;
        doc.querySelectorAll('trkpt').forEach(function(pt) {
          var lat = parseFloat(pt.getAttribute('lat'));
          var lon = parseFloat(pt.getAttribute('lon'));
          var eleEl = pt.querySelector('ele');
          var ele = eleEl ? parseFloat(eleEl.textContent) : null;
          if (points.length > 0) {
            var prev = points[points.length - 1];
            dist += _haversine(prev[0], prev[1], lat, lon);
            if (ele !== null && prevEle !== null && ele > prevEle) gain += ele - prevEle;
          }
          points.push([lat, lon]);
          prevEle = ele;
        });
        if (points.length > 1) {
          var color = trackColors[colorIdx % trackColors.length];
          var name = t.name || t.file.replace('.gpx', '');
          var stats = [name];
          stats.push(_fmtDist(dist));
          if (gain > 0) stats.push('↑' + Math.round(gain) + ' m');
          var line = L.polyline(points, {color: color, weight: 3, opacity: 0.7, smoothFactor: 1}).addTo(_photoMap);
          line.bindPopup('<b>' + stats.join('</b> · <b>') + '</b>');
          colorIdx++;
        }
      }).catch(function() {});
    });
  }).catch(function() {});
}

function switchView(view, cb) {
  var masonry = document.getElementById('photo-masonry');
  var mapContainer = document.getElementById('photo-map-container');
  var btnGrid = document.getElementById('btn-grid');
  var btnMap = document.getElementById('btn-map');
  var lm = document.getElementById('photo-load-more');

  if (view === 'map') {
    masonry.style.display = 'none';
    mapContainer.style.display = 'block';
    btnGrid.className = 'inactive';
    btnMap.className = 'active';
    lm.style.display = 'none';

    loadLeaflet(function() {
      setTimeout(function() { _photoMap.invalidateSize(); }, 50);
      _syncMapMarkers();  // re-apply current filter on map
      if (cb) cb();
    });
  } else {
    masonry.style.display = ''; mapContainer.style.display = 'none';
    btnGrid.className = 'active';
    btnMap.className = 'inactive';
    lm.style.display = 'none';
    if (cb) cb();
  }
}

function _getFilteredPhotos() {
  if (!window._photoData) return [];
  return window._photoData.filter(function(p) {
    var story = _photoStories[_currentStory];
    if (story && story.photos && story.photos.indexOf(p.filename) < 0) return false;
    return !_currentPhotoTag || (p.tags || []).indexOf(_currentPhotoTag) >= 0;
  });
}

function _syncPhotoLocationCount() {
  var pool = _getFilteredPhotos();
  var count = pool.filter(function(p){ return p.exif && p.exif.gps; }).length;
  var el = document.getElementById('gps-count');
  if (!el) return;
  if (count) {
    el.textContent = '· ' + count + ' location' + (count > 1 ? 's' : '');
    el.style.display = '';
  } else {
    el.style.display = 'none';
  }
}

function _syncStoryNote() {
  var el = document.getElementById('photo-story-note');
  if (!el) return;
  var story = _photoStories[_currentStory];
  if (!story) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }
  var count = _getFilteredPhotos().length;
  var meta = [];
  if (story.date) meta.push(htmlEncode(story.date));
  meta.push(count + ' photo' + (count === 1 ? '' : 's'));
  if (_currentPhotoTag) meta.push(htmlEncode(_currentPhotoTag));
  el.innerHTML =
    '<span class="story-note-kicker">Story</span>' +
    '<strong>' + htmlEncode(story.name || story.id || 'Untitled story') + '</strong>' +
    (story.caption ? '<span>' + htmlEncode(story.caption) + '</span>' : '') +
    '<em>' + meta.join(' · ') + '</em>' +
    '<button type="button" onclick="clearStoryFilter()" aria-label="清除故事筛选">×</button>';
  el.style.display = 'flex';
}

function _renderAllPhotos() {
  var pool = _getFilteredPhotos();
  var masonry = document.getElementById('photo-masonry');
  masonry.classList.toggle('is-empty', pool.length === 0);
  masonry.innerHTML = renderPhotos(pool);
  _restartContentMotion(masonry);
  initLB();
}

function flyToPhoto(filename, lat, lng) {
  switchView('map', function() {
    if (_photoMap) {
      _photoMap.flyTo([lat, lng], 15, {animate: true, duration: 1.5});
      // Open the corresponding marker popup
      _photoMap.eachLayer(function(layer) {
        if (layer.getLatLng && layer.getLatLng().lat === lat && layer.getLatLng().lng === lng) {
          layer.openPopup();
        }
      });
    }
  });
}

function renderFriends(data) {
  var html = '<div class="friends-label">FRIEND</div>';
  data.forEach((f, i) => {
    var href = htmlEncode(f.url);
    if (/^https?:\/\//i.test(f.url)) { html += '<a href="' + href + '">' + htmlEncode(f.name) + '</a>'; }
    else { html += '<span>' + htmlEncode(f.name) + '</span>'; }
  });
  return html;
}

function renderMusic(data) {
  const themes = [
    ['rgba(255,77,77,0.10)', '#ff4d4d'],
    ['rgba(0,102,255,0.10)', '#0066ff'],
    ['rgba(255,184,0,0.10)', '#ffb800'],
    ['rgba(0,200,83,0.10)', '#00c853'],
    ['rgba(156,39,176,0.10)', '#9c27b0'],
  ];
  return data.map((m, i) => {
    var num = String(i + 1).padStart(2, '0');
    var t = themes[i % themes.length];
    return '<div class="music-row" data-src="music/' + htmlEncode(m.filename) + '" style="--theme:' + t[0] + ';--idx-color:' + t[1] + '">' +
      '<span class="idx">' + num + '</span>' +
      '<span class="info"><span class="title">' + htmlEncode(m.title) + '</span>' +
      '<span class="artist">' + htmlEncode(m.artist) + '</span></span>' +
      '<span class="time"></span>' +
      '</div>';
  }).join('');
}

function renderContact(data) {
  return data.map(c => {
    var inner = '<span class="value">' + htmlEncode(c.label) + ' <span style="color:#999;font-weight:400;">' + htmlEncode(c.handle) + '</span></span>';
    if (c.url) {
      return '<a href="' + htmlEncode(c.url) + '" target="_blank" rel="noopener noreferrer" class="contact-row">' + inner + '<span class="arr">→</span></a>';
    }
    return '<div class="contact-row">' + inner + '</div>';
  }).join('');
}

function renderStack(data) {
  var colors = ['#ff4d4d','#ff6d00','#ffb800','#0066ff','#00c853','#9c27b0'];
  return data.map(function(c, i) {
    return '<span class="stack-chip" style="--chip-color:' + colors[i % 6] + '">' + htmlEncode(c) + '</span>';
  }).join('');
}

document.addEventListener('DOMContentLoaded', async function() {
  // Fetch all data in parallel, then render all at once — one layout pass, zero jank
  var sections = ['about','work','essays','photos','contact','friends','music','stack'];
  var results = {};
  try {
    var fetched = await Promise.all(sections.map(function(s) {
      var url = s === 'essays' ? 'data/essays_public.json' : 'data/' + s + '.json';
      return fetch(url + '?v=' + TS).then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; });
    }));
    sections.forEach(function(s, i) { results[s] = fetched[i]; });
  } catch(e) {}

  // About
  try {
    var about = results.about;
    if (about) {
      var paras = about.content.split('\n').filter(Boolean);
      document.getElementById('about-text').innerHTML = paras.map(function(p, i) {
        return '<span class="about-para' + (i === 0 ? ' about-lead' : '') + '">' + htmlEncode(p) + '</span>';
      }).join('');
      if (about.avatar) document.getElementById('portrait-img').src = about.avatar;
      if (about.tags && about.tags.length) {
        document.getElementById('hero-meta').innerHTML = about.tags.map(function(t) { return '<span>' + htmlEncode(t) + '</span>'; }).join('');
      }
    }
  } catch(e) {}
  // Work
  if (results.work) {
    document.getElementById('work-container').innerHTML = renderWork(results.work);
  }
  // Essays
  if (results.essays) {
    var essaysData = Array.isArray(results.essays) ? results.essays : results.essays.essays;
    _allTags = Array.isArray(results.essays) ? [] : (results.essays._tags || []);
    _essayData = essaysData;
    buildEssayFilter();
    renderEssayList();
  }
  // Photos
  if (results.photos) {
    window._photoData = results.photos;
    var total = results.photos.length;
    var cols = total <= 2 ? 2 : total <= 4 ? 3 : total <= 12 ? 4 : 5;
    document.getElementById('photo-masonry').style.columnCount = cols;
    document.getElementById('photo-masonry').innerHTML = renderPhotos(results.photos);

    // Load photo stories from server (pre-computed during build)
    fetch('data/photo_stories.json?v=' + TS).then(function(r) { return r.ok ? r.json() : null; }).then(function(data) {
      if (data) renderPhotoStories(data);
    }).catch(function() {});
    buildPhotoTagFilter();

    // Hide load-more (23 photos fit in one batch)
    var lm = document.getElementById('photo-load-more');
    if (lm) lm.style.display = 'none';

    var gc = results.photos.filter(function(p) { return p.exif && p.exif.gps; }).length;
    var elGc = document.getElementById('gps-count');
    if (gc) {
      elGc.textContent = '· ' + gc + ' location' + (gc > 1 ? 's' : '');
      elGc.style.display = '';
    }
  }
  // Contact
  if (results.contact) document.getElementById('contact-list').innerHTML = renderContact(results.contact);
  // Friends
  if (results.friends) document.getElementById('friends-container').innerHTML = renderFriends(results.friends);
  // Music
  if (results.music) document.getElementById('music-list').innerHTML = renderMusic(results.music);
  // Stack
  if (results.stack) document.getElementById('stack-cloud').innerHTML = renderStack(results.stack);
  // Remove all skeleton classes at once
  document.querySelectorAll('.skeleton-loading').forEach(function(el) { el.classList.remove('skeleton-loading'); });

  initMusicPlayer();
  initThemeBtn();
  initLB();

});

// ═══ Dark Mode ═══
// Priority: manual toggle > system preference > default (light)
function initThemeBtn() {
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  var saved = localStorage.getItem('theme');
  if (saved === 'dark' || (!saved && mq.matches)) {
    _applyTheme('dark');
  }
  mq.addEventListener('change', function(e) {
    if (localStorage.getItem('theme')) return;
    _applyTheme(e.matches ? 'dark' : 'light');
  });
}
// Listen for theme changes to sync photo map
window.addEventListener('themechange', function(e) {
  if (_photoMap) {
    _photoMap.invalidateSize();
    _photoMap.getContainer().classList.toggle('dark', e.detail.mode === 'dark');
  }
});

// ═══ Lightbox ═══
var lbPhotos = [];
var lbIndex = 0;
var _lbInited = false;
var _lbPreload = {};
function initLB() {
  if (_lbInited) return;
  _lbInited = true;
  var masonry = document.querySelector('#photo-masonry');
  if (!masonry) return;
  masonry.addEventListener('click', function(e) {
    var img = e.target.closest('.photo-item')?.querySelector('img');
    if (!img) return;
    lbPhotos = Array.from(document.querySelectorAll('#photo-masonry img')).map(function(el) {
      var filename = el.src.split('/').pop().split('?')[0];
      return { src: 'images/lg/' + filename, alt: el.alt, exif: el.dataset.exif || '' };
    });
    var clickedFile = img.src.split('/').pop().split('?')[0];
    lbIndex = lbPhotos.findIndex(function(p) { return p.src.endsWith('/' + clickedFile); });
    openLB();
  });
  document.addEventListener('keydown', function(e) {
    if (!document.getElementById('lightbox').classList.contains('show')) return;
    if (e.key === 'Escape') closeLB();
    if (e.key === 'ArrowLeft') navLB(-1);
    if (e.key === 'ArrowRight') navLB(1);
  });
  // Touch swipe
  var touchX = 0;
  var lb = document.getElementById('lightbox');
  lb.addEventListener('touchstart', function(e) { touchX = e.touches[0].clientX; }, {passive: true});
  lb.addEventListener('touchend', function(e) {
    var dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 50) navLB(dx < 0 ? 1 : -1);
  }, {passive: true});
}
function openLB() {
  var lb = document.getElementById('lightbox');
  lb.classList.add('show');
  updateLB();
  preloadAdjacent();
  document.body.style.overflow = 'hidden';
}
function closeLB() {
  document.getElementById('lightbox').classList.remove('show');
  document.body.style.overflow = '';
}
function navLB(dir) {
  lbIndex = (lbIndex + dir + lbPhotos.length) % lbPhotos.length;
  updateLB();
  preloadAdjacent();
}
function preloadAdjacent() {
  [-1, 1].forEach(function(offset) {
    var i = (lbIndex + offset + lbPhotos.length) % lbPhotos.length;
    if (i === lbIndex) return;
    var src = lbPhotos[i].src;
    if (_lbPreload[src]) return;
    var img = new Image();
    img.onload = function() { _lbPreload[src] = true; };
    img.src = src;
  });
}
function updateLB() {
  var p = lbPhotos[lbIndex];
  if (!p) return;
  var img = document.getElementById('lb-img');
  if (img.src === p.src) return;
  img.onload = function() { img.classList.remove('loading'); };
  img.classList.add('loading');
  img.src = p.src;
  img.alt = p.alt;
  document.getElementById('lb-exif').textContent = p.exif || '';
  document.getElementById('lb-counter').textContent = (lbIndex + 1) + ' / ' + lbPhotos.length;
}
