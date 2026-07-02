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

function initMusicPlayer() {
  player = document.getElementById('player');
  if (!player) return;
  curRow = null;
  if (musicTimeHandler) player.removeEventListener('timeupdate', musicTimeHandler);
  if (musicEndHandler) player.removeEventListener('ended', musicEndHandler);

  document.querySelectorAll('.music-row').forEach(row => {
    row.addEventListener('click', () => {
      const src = row.dataset.src;
      if (!src) return;
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

  musicTimeHandler = () => {
    if (curRow && player.duration) {
      curRow.style.setProperty('--progress', (player.currentTime / player.duration * 100).toFixed(2) + '%');
    }
  };
  musicEndHandler = () => {
    if (curRow) { curRow.classList.remove('playing'); curRow.style.removeProperty('--progress'); }
    // Auto-play next track
    var rows = document.querySelectorAll('.music-row');
    var idx = Array.prototype.indexOf.call(rows, curRow);
    curRow = null;
    if (idx >= 0 && idx + 1 < rows.length) {
      rows[idx + 1].click();
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
  d.textContent = str;
  return d.innerHTML.replace(/"/g, '&quot;');
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
var _essayFilter = '';

function buildEssayFilter() {
  var tags = new Set();
  _essayData.forEach(function(e) {
    (e.tag || '').split(/[,，]/).forEach(function(t) { t = t.trim(); if (t) tags.add(t); });
  });
  var html = '<span class="ef-chip' + (!_essayFilter ? ' active' : '') + '" onclick="filterEssays(\'\')">置顶</span>';
  tags.forEach(function(t) {
    html += '<span class="ef-chip' + (_essayFilter === t ? ' active' : '') + '" data-tag="' + htmlEncode(t) + '" onclick="filterEssays(this.getAttribute(\'data-tag\'))">' + htmlEncode(t) + '</span>';
  });
  document.getElementById('essay-tag-filter').innerHTML = html;
}

function filterEssays(tag) {
  _essayFilter = tag;
  buildEssayFilter();
  renderEssayList();
}

function renderEssayList() {
  var filtered = _essayData;
  if (_essayFilter) {
    filtered = _essayData.filter(function(e) {
      return (e.tag || '').split(/[,，]/).some(function(t) { return t.trim() === _essayFilter; });
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
    var tagParam = '?tag=' + encodeURIComponent(_essayFilter || '置顶');
    html += '<a class="essay-row" href="essays/' + htmlEncode(e.slug) + '.html' + tagParam + '">' +
      '<div class="essay-left">' +
      '<span class="essay-title">' + htmlEncode(e.title) + '</span>' +
      (e.excerpt ? '<span class="essay-excerpt">' + htmlEncode(e.excerpt) + '</span>' : '') +
      '</div>' +
      '<div class="essay-right">' +
      '<span class="essay-tag">' + htmlEncode((e.tag || '').replace(/, ?/g, ' · ')) + '</span>' +
      '<span class="essay-meta">' + (e.date_display || '') + ' · ' + (e.readTime || 1) + ' min</span>' +
      '<span class="essay-arr">→</span>' +
      '</div>' +
      '</a>';
  });
  if (hidden > 0) {
    html += '<a class="essay-row" href="archive.html" style="justify-content:center;color:var(--muted);font-size:13px;text-decoration:none;">查看全部（' + hidden + ' 篇）→</a>';
  }
  document.getElementById('essays-list').innerHTML = html;
  document.getElementById('essays-list').classList.remove('skeleton-loading');
}

function renderPhotos(data) {
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

function filterPhotosByTag(tag) {
  _currentPhotoTag = tag;
  // Grid: toggle display
  document.querySelectorAll('.photo-item').forEach(function(el) {
    var itemTags = (el.dataset.tags || '').split(',').filter(Boolean);
    el.style.display = (!tag || itemTags.indexOf(tag) >= 0) ? '' : 'none';
  });
  // Reset paging + re-render initial batch from filtered pool
  _photoPage = 0; _photoExpanded = false;
  document.querySelectorAll('.photo-batch').forEach(function(el) { el.remove(); });
  var pool = _getFilteredPhotos();
  var masonry = document.getElementById('photo-masonry');
  var shown = pool.slice(0, _photoPageSize);
  masonry.innerHTML = renderPhotos(shown);
  var hidden = pool.length - _photoPageSize;
  var lm = document.getElementById('photo-load-more');
  if (hidden > 0) {
    lm.innerHTML = '<button class="load-more-btn" onclick="loadMorePhotos()">Load (' + hidden + ' more)</button>';
    lm.style.display = 'block';
  } else { lm.style.display = 'none'; }
  // Update filter chip active state
  document.querySelectorAll('#photo-tag-filter .ef-chip').forEach(function(c) {
    c.classList.toggle('active', c.textContent === (tag || '全部'));
  });
  // Map: rebuild markers
  if (_markerGroup && window._photoData) {
    _markerGroup.clearLayers();
    var filtered = window._photoData.filter(function(p) {
      return !tag || (p.tags || []).indexOf(tag) >= 0;
    });
    filtered.forEach(function(p) {
      var gps = p.exif && p.exif.gps;
      if (!gps) return;
      var icon = L.divIcon({className: 'custom-marker', html: '<div class="marker-dot"></div>', iconSize: [16, 16], iconAnchor: [8, 8]});
      var html = '<img src="images/lg/' + encodeURIComponent(p.filename) + '"><b>' + (p.exif.model || p.exif.camera || 'Photo') + '</b>';
      L.marker([gps.lat, gps.lng], {icon: icon}).addTo(_markerGroup).bindPopup(html);
    });
    if (filtered.length > 0) {
      _photoMap.fitBounds(_markerGroup.getBounds(), {padding: [50, 50], maxZoom: 14});
    }
  }
  // Sync GPS count to filtered pool
  var gc2 = pool.filter(function(p){return p.exif&&p.exif.gps;}).length;
  var elGc = document.getElementById('gps-count');
  if (gc2) { elGc.textContent = '· ' + gc2 + ' location' + (gc2>1?'s':''); elGc.style.display = ''; }
  else { elGc.style.display = 'none'; }
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

  // Add markers from photo data
  if (window._photoData) {
    window._photoData.forEach(function(p) {
      var gps = p.exif && p.exif.gps;
      if (!gps) return;
      var ex = p.exif || {};
      var camera = _exifCamera(ex);
      var html = '<img src="images/lg/' + encodeURIComponent(p.filename) + '">' +
        '<b>' + (camera || 'Photo').replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</b>';
      var exifHtml = _exifStr(ex, true);
      if (exifHtml) html += '<br><span class="popup-exif">' + exifHtml + '</span>';
      html += '<br><span class="popup-exif">' + _gpsStr(gps.lat, gps.lng) + '</span>';
      var icon = L.divIcon({className: 'custom-marker', html: '<div class="marker-dot"></div>', iconSize: [16, 16], iconAnchor: [8, 8]});
      L.marker([gps.lat, gps.lng], {icon: icon}).addTo(_markerGroup).bindPopup(html);
    });

    if (_markerGroup.getLayers().length > 0) {
      _photoMap.fitBounds(_markerGroup.getBounds(), {padding: [50, 50], maxZoom: 14});
  }

  // Load GPX tracks
  loadGpxTracks();
    }

  // Sync dark mode
  if (document.documentElement.classList.contains('dark')) {
    _photoMap.getContainer().classList.add('dark');
  }
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
        doc.querySelectorAll('trkpt').forEach(function(pt) {
          points.push([parseFloat(pt.getAttribute('lat')), parseFloat(pt.getAttribute('lon'))]);
        });
        if (points.length > 1) {
          var color = trackColors[colorIdx % trackColors.length];
          L.polyline(points, {color: color, weight: 3, opacity: 0.7, smoothFactor: 1}).addTo(_photoMap);
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
      if (_currentPhotoTag) filterPhotosByTag(_currentPhotoTag);  // re-apply filter on map
      if (cb) cb();
    });
  } else {
    masonry.style.display = ''; mapContainer.style.display = 'none';
    btnGrid.className = 'active';
    btnMap.className = 'inactive';
    // Restore load-more visibility: show if expanded or more photos remain
    var pool = _getFilteredPhotos();
    var hidden = pool.length - _photoPageSize;
    lm.style.display = (_photoExpanded || hidden > 0) ? 'block' : 'none';
    if (cb) cb();
  }
}

var _photoPage = 0;
var _photoPageSize = 12;
var _photoExpanded = false;

function _getFilteredPhotos() {
  if (!window._photoData) return [];
  if (!_currentPhotoTag) return window._photoData;
  return window._photoData.filter(function(p) {
    return (p.tags || []).indexOf(_currentPhotoTag) >= 0;
  });
}

function loadMorePhotos() {
  var lm = document.getElementById('photo-load-more');
  var masonry = document.getElementById('photo-masonry');
  var pool = _getFilteredPhotos();
  if (_photoExpanded) {
    _photoExpanded = false; _photoPage = 0;
    document.querySelectorAll('.photo-batch').forEach(function(el) { el.remove(); });
    var hidden = pool.length - _photoPageSize;
    if (hidden > 0) {
      lm.innerHTML = '<button class="load-more-btn" onclick="loadMorePhotos()">Load (' + hidden + ' more)</button>';
      lm.style.display = 'block';
    } else { lm.style.display = 'none'; }
    return;
  }
  _photoPage++;
  var start = _photoPage * _photoPageSize;
  var end = start + _photoPageSize;
  var batch = pool.slice(start, end);
  var more = pool.length - end;
  var wrapper = document.createElement('div');
  wrapper.className = 'photo-batch';
  wrapper.innerHTML = renderPhotos(batch);
  masonry.appendChild(wrapper);
  if (more > 0) {
    lm.innerHTML = '<button class="load-more-btn" onclick="loadMorePhotos()">Load (' + more + ' more)</button>';
    lm.style.display = 'block';
  } else {
    _photoExpanded = true;
    lm.innerHTML = '<button class="load-more-btn" onclick="loadMorePhotos()">Collapse</button>';
    lm.style.display = 'block';
  }
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
      '<span class="title">' + htmlEncode(m.title) + '</span>' +
      '<span class="artist">' + htmlEncode(m.artist) + '</span>' +
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
    _essayData = results.essays;
    buildEssayFilter();
    renderEssayList();
  }
  // Photos
  if (results.photos) {
    window._photoData = results.photos;
    var total = results.photos.length;
    var cols = total <= 2 ? 2 : total <= 4 ? 3 : total <= 12 ? 4 : 5;
    document.getElementById('photo-masonry').style.columnCount = cols;
    var shown = results.photos.slice(0, _photoPageSize);
    document.getElementById('photo-masonry').innerHTML = renderPhotos(shown);
    var hidden = total - _photoPageSize;

    buildPhotoTagFilter();

    var lm = document.getElementById('photo-load-more');
    if (hidden > 0) {
      lm.style.display = 'block';
      lm.innerHTML = '<button class="load-more-btn" onclick="loadMorePhotos()">Load (' + hidden + ' more)</button>';
    } else {
      lm.style.display = 'none';
    }

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
function _applyTheme(mode) {
  var html = document.documentElement, btn = document.getElementById('theme-btn');
  if (mode === 'dark') { html.classList.add('dark'); btn.textContent = '☀'; }
  else { html.classList.remove('dark'); btn.textContent = '🌙'; }
}
function initThemeBtn() {
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  var saved = localStorage.getItem('theme');
  if (saved === 'dark' || (!saved && mq.matches)) {
    _applyTheme('dark');
  }
  mq.addEventListener('change', function(e) {
    if (localStorage.getItem('theme')) return;  // manual override wins
    _applyTheme(e.matches ? 'dark' : 'light');
  });
}
// [shared] Keep in sync with templates/includes/theme.js::toggleTheme()
function toggleTheme() {
  if (document.documentElement.classList.contains('dark')) {
    localStorage.setItem('theme', 'light');
    _applyTheme('light');
  } else {
    localStorage.setItem('theme', 'dark');
    _applyTheme('dark');
  }
  if (_photoMap) _photoMap.invalidateSize();
}

// ═══ Lightbox ═══
var lbPhotos = [];
var lbIndex = 0;
var _lbInited = false;
function initLB() {
  if (_lbInited) return;
  _lbInited = true;
  document.querySelector('#photo-masonry').addEventListener('click', function(e) {
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
  document.body.style.overflow = 'hidden';
}
function closeLB() {
  document.getElementById('lightbox').classList.remove('show');
  document.body.style.overflow = '';
}
function navLB(dir) {
  lbIndex = (lbIndex + dir + lbPhotos.length) % lbPhotos.length;
  updateLB();
}
function updateLB() {
  var p = lbPhotos[lbIndex];
  document.getElementById('lb-img').src = p.src;
  document.getElementById('lb-img').alt = p.alt;
  document.getElementById('lb-exif').textContent = p.exif || '';
  document.getElementById('lb-counter').textContent = (lbIndex + 1) + ' / ' + lbPhotos.length;
}
