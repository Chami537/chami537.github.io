// Main page photo map, markers, and GPX tracks.

function openMapPhotoLB(filename) {
  var pool = _getFilteredPhotos().filter(function(p) { return p.exif && p.exif.gps; });
  lbPhotos = pool.map(function(p) {
    var ex = p.exif || {};
    var parts = [_exifCamera(ex), _exifStr(ex, true), _gpsStr(ex.gps.lat, ex.gps.lng, 4), p.date || ex.date].filter(Boolean);
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
  _photoMap = L.map(container, {attributionControl: false}).setView([22.5431, 113.9579], 11);
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
  fetch('/data/tracks.json?v=' + TS).then(function(r) {
    if (!r.ok) return;
    return r.json();
  }).then(function(tracks) {
    if (!tracks || !tracks.length) return;
    tracks.forEach(function(track, index) {
      _loadGpxTrack(track, trackColors[index % trackColors.length]);
    });
  }).catch(function() {});
}

function _loadGpxTrack(track, color) {
  fetch('/tracks/' + track.file).then(function(r) {
    return r.text();
  }).then(function(xml) {
    var summary = _parseGpxTrack(xml);
    if (summary) _drawGpxTrack(track, color, summary);
  }).catch(function() {});
}

function _parseGpxTrack(xml) {
  var parser = new DOMParser();
  var doc = parser.parseFromString(xml, 'text/xml');
  var points = [];
  var distance = 0;
  var gain = 0;
  var previousElevation = null;
  doc.querySelectorAll('trkpt').forEach(function(pt) {
    var lat = parseFloat(pt.getAttribute('lat'));
    var lon = parseFloat(pt.getAttribute('lon'));
    var eleEl = pt.querySelector('ele');
    var elevation = eleEl ? parseFloat(eleEl.textContent) : null;
    if (points.length > 0) {
      var previous = points[points.length - 1];
      distance += _haversine(previous[0], previous[1], lat, lon);
      if (elevation !== null && previousElevation !== null && elevation > previousElevation) {
        gain += elevation - previousElevation;
      }
    }
    points.push([lat, lon]);
    previousElevation = elevation;
  });
  return points.length > 1 ? {points: points, distance: distance, gain: gain} : null;
}

function _drawGpxTrack(track, color, summary) {
  var name = track.name || track.file.replace('.gpx', '');
  var stats = [name, _fmtDist(summary.distance)];
  if (summary.gain > 0) stats.push('↑' + Math.round(summary.gain) + ' m');
  var line = L.polyline(summary.points, {color: color, weight: 3, opacity: 0.7, smoothFactor: 1}).addTo(_photoMap);
  line.bindPopup('<b>' + stats.join('</b> · <b>') + '</b>');
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
  var mapContainer = document.getElementById('photo-map-container');
  switchView('map', function() {
    mapContainer.scrollIntoView({behavior:'smooth', block:'start'});
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
