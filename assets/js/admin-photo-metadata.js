// Selected photo metadata form and Leaflet map.

var _selectedPhotoIdx = -1;
var _editorMap = null;
var _editorMarker = null;

function selectPhoto(index) {
  _selectedPhotoIdx = index;
  showPhotoEditor(index);
  renderAdminPhotos();
  loadEditorMap();
}

function showPhotoEditor(index) {
  var photo = _photoData[index];
  var editor = document.getElementById('photo-editor');
  editor.style.display = 'block';
  document.getElementById('photo-editor-fn').textContent = photo.filename;
  var currentDate = photo.date || (photo.exif && photo.exif.date) || '';
  if (/^\d{4}-\d{1,2}-\d{1,2}/.test(currentDate)) {
    currentDate = currentDate.slice(0, 10);
  } else {
    var parts = currentDate.match(/(\w+) (\d+), (\d+)/);
    if (parts) currentDate = parts[3] + '-' + MONTHS_NUM[parts[1]] + '-' + String(parts[2]).padStart(2, '0');
  }
  document.getElementById('photo-editor-date').value = currentDate;
  var gps = photo.exif && photo.exif.gps;
  document.getElementById('photo-editor-lat').value = gps ? gps.lat : '';
  document.getElementById('photo-editor-lng').value = gps ? gps.lng : '';
  if (_editorMarker) {
    _editorMap.removeLayer(_editorMarker);
    _editorMarker = null;
  }
  if (_editorMap && gps) {
    _editorMarker = L.marker([gps.lat, gps.lng], {icon: _editorMarkerIcon()}).addTo(_editorMap);
    _editorMap.setView([gps.lat, gps.lng], 14);
  }
  editor.scrollIntoView({behavior: 'smooth'});
}

function clearPhotoEditor() {
  _selectedPhotoIdx = -1;
  document.getElementById('photo-editor').style.display = 'none';
  renderAdminPhotos();
}

async function savePhotoEditor() {
  if (_selectedPhotoIdx < 0) return;
  var filename = _photoData[_selectedPhotoIdx].filename;
  var date = document.getElementById('photo-editor-date').value;
  if (date) {
    var parts = date.split('-');
    if (parts.length === 3) date = MONTHS_ARR[+parts[1] - 1] + ' ' + (+parts[2]) + ', ' + parts[0];
  }
  await api('PUT', '/api/photo-date', {filename: filename, date: date});
  var latitude = document.getElementById('photo-editor-lat').value.trim();
  var longitude = document.getElementById('photo-editor-lng').value.trim();
  if (latitude && longitude && !isNaN(parseFloat(latitude)) && !isNaN(parseFloat(longitude))) {
    await api('PUT', '/api/photo-gps', {filename: filename, lat: parseFloat(latitude), lng: parseFloat(longitude)});
  }
  _selectedPhotoIdx = -1;
  document.getElementById('photo-editor').style.display = 'none';
  loadPhotos();
  toast('已保存');
}

function loadEditorMap() {
  if (_editorMap) return;
  var container = document.getElementById('photo-editor-map');
  container.style.display = 'block';
  if (typeof L !== 'undefined') {
    initEditorMap(container);
    return;
  }
  var stylesheet = document.createElement('link');
  stylesheet.rel = 'stylesheet';
  stylesheet.href = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css';
  document.head.appendChild(stylesheet);
  var script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js';
  script.onload = function() { initEditorMap(container); };
  script.onerror = function() {
    container.style.display = 'none';
    toast('Leaflet 地图加载失败，请检查网络', true);
  };
  document.head.appendChild(script);
}

function initEditorMap(container) {
  _editorMap = L.map(container, {attributionControl: false}).setView([22.5431, 113.9579], 11);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, subdomains: 'abcd', attribution: '&copy; OSM &copy; CARTO'
  }).addTo(_editorMap);
  _editorMap.on('click', function(event) {
    var latitude = event.latlng.lat.toFixed(6);
    var longitude = event.latlng.lng.toFixed(6);
    document.getElementById('photo-editor-lat').value = latitude;
    document.getElementById('photo-editor-lng').value = longitude;
    if (_editorMarker) _editorMap.removeLayer(_editorMarker);
    _editorMarker = L.marker([latitude, longitude], {icon: _editorMarkerIcon()}).addTo(_editorMap);
  });
  if (_selectedPhotoIdx >= 0) {
    var gps = _photoData[_selectedPhotoIdx].exif && _photoData[_selectedPhotoIdx].exif.gps;
    if (gps) {
      _editorMarker = L.marker([gps.lat, gps.lng], {icon: _editorMarkerIcon()}).addTo(_editorMap);
      _editorMap.setView([gps.lat, gps.lng], 14);
    }
  }
  setTimeout(function() { _editorMap.invalidateSize(); }, 200);
}
