// Admin photo list, editor, uploads, and map.

// ═══════════════════════════════════
// Photos
// ═══════════════════════════════════
// Photo tag library (localStorage, like essay tags)
var _currentPhotoTag = '';
var _photoDeleteTagMode = false;
function getPhotoTags() { return _tagLib('photo-tags', '["Shenzhen","Night","Street"]'); }
function savePhotoTags(tags) { _saveTagLib('photo-tags', tags); }

function switchPhotoTabTag(tag) {
  _currentPhotoTag = tag;
  loadPhotos();
}
function promptNewPhotoTag() {
  _promptTag('photo-tags', '["Shenzhen","Night","Street"]', function(t) { _currentPhotoTag = t; loadPhotos(); });
}
function toggleDeletePhotoTagMode() {
  _photoDeleteTagMode = _toggleDeleteTagMode('delete-photo-tag-btn', _photoDeleteTagMode, loadPhotos);
}
async function deletePhotoTagGlobal(tag) {
  if (!confirm('确定永久删除标签 "' + tag + '"？这将从所有照片中移除该标签。')) return;
  var tags = getPhotoTags();
  tags = tags.filter(function(t) { return t !== tag; });
  savePhotoTags(tags);
  // Strip from all photos
  for (var p of _photoData) {
    if (!p.tags) continue;
    var before = p.tags.length;
    p.tags = p.tags.filter(function(t) { return t !== tag; });
    if (p.tags.length !== before) {
      await api('PUT', '/api/photo-tags', {filename: p.filename, tags: p.tags});
    }
  }
  if (_currentPhotoTag === tag) _currentPhotoTag = '';
  loadPhotos();
}

var _photoData = [];
onAdminDataReset(loadPhotos);
var _selectedPhotoIdx = -1;
var _editorMap = null;
var _editorMarker = null;

function _renderPhotoTagTabs() {
  var tags = getPhotoTags();
  var html = '<span tabindex="0" role="button" class="tag-tab-btn-sm' + (!_currentPhotoTag ? ' active' : '') + '" onclick="switchPhotoTabTag(\'\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();switchPhotoTabTag(\'\')}">全部</span>';
  tags.forEach(function(t) {
    var del = _photoDeleteTagMode ? '<span onclick="event.stopPropagation();deletePhotoTagGlobal(\'' + esc(t) + '\')" class="tag-tab-del">×</span>' : '';
    var active = _currentPhotoTag === t;
    html += '<span tabindex="0" role="button" class="tag-tab-btn-sm' + (active ? ' active' : '') + '" onclick="switchPhotoTabTag(\'' + esc(t) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();switchPhotoTabTag(\'' + esc(t) + '\')}">' + esc(t) + del + '</span>';
  });
  document.getElementById('photo-tag-tabs').innerHTML = html;
}

async function loadPhotos() {
  try {
    _photoData = await api('GET', '/api/photos');
    _renderPhotoTagTabs();
    if (_currentPhotoTag) {
      _photoData = _photoData.filter(function(p) {
        return (p.tags || []).indexOf(_currentPhotoTag) >= 0;
      });
    }
    renderAdminPhotos();
    await loadStories();
  } catch(e) { toast(e.message, true); }
}

function _photoDisplayDate(p) {
  var displayDate = p.date || (p.exif && p.exif.date) || '';
  if (!p.date && displayDate) {
    var dateMatch = displayDate.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (dateMatch) displayDate = MONTHS_ARR[+dateMatch[2] - 1] + ' ' + (+dateMatch[3]) + ', ' + dateMatch[1];
  }
  return displayDate;
}

function _photoCardHtml(p, i) {
    var tagCount = (p.tags || []).length;
    var displayDate = _photoDisplayDate(p);
    var tagBtn = '<button class="btn btn-sm" onclick="event.stopPropagation();openPhotoTagModal(' + i + ')" style="font-size:10px;padding:1px 6px;margin-top:4px;">' +
      '🏷 ' + (tagCount > 0 ? tagCount + ' 标签' : '加标签') + '</button>';
    return '<div class="photo-card' + (_selectedPhotoIdx === i ? ' selected' : '') + '" draggable="true" data-index="' + i + '"' +
      ' onclick="selectPhoto(' + i + ')"' +
      ' ondragstart="photoDragStart(event,' + i + ')"' +
      ' ondragover="photoDragOver(event)"' +
      ' ondragend="photoDragEnd(event)"' +
      ' ondrop="photoDrop(event,' + i + ')"' +
      '>' +
      '<img src="/images/sm/' + encodeURIComponent(p.filename) + '" alt="' + esc(p.filename) + '" loading="lazy">' +
      '<button class="del-btn" data-filename="' + esc(p.filename) + '" onclick="deletePhoto(this.dataset.filename)">×</button>' +
      '<div class="photo-info">' +
        '<div class="fn">' + esc(p.filename) + '</div>' +
        '<div class="sz">' + (p.size || '') + '</div>' +
        (p.exif && Object.keys(p.exif).length ? '<div class="photo-exif">' + esc(p.exif.aperture||'') + ' ' + esc(p.exif.shutter||'') + ' ISO' + esc(p.exif.iso||'') + '</div>' : '') +
        (displayDate ? '<div class="photo-exif" style="color:var(--c3)">📅 ' + esc(displayDate) + '</div>' : '') +
        (p.exif && p.exif.gps ? '<div class="photo-exif">📍 ' + p.exif.gps.lat.toFixed(4) + ', ' + p.exif.gps.lng.toFixed(4) + '</div>' : '') +
        tagBtn +
      '</div>' +
      '</div>';
}

function renderAdminPhotos() {
  document.getElementById('photo-grid').innerHTML = _photoData.map(_photoCardHtml).join('');
}

var _tagModalIdx = -1;
function openPhotoTagModal(idx) {
  _tagModalIdx = idx;
  _refreshTagModalContent();
  document.getElementById('tag-modal').showModal();
}
function _refreshTagModalContent() {
  var tags = getPhotoTags();
  var myTags = _photoData[_tagModalIdx].tags || [];
  var html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">';
  tags.forEach(function(t) {
    var active = myTags.indexOf(t) >= 0;
    html += '<span tabindex="0" role="button" onclick="toggleModalTag(\'' + esc(t) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();toggleModalTag(\'' + esc(t) + '\')}" class="tag-tab-btn-sm' + (active ? ' active' : '') + '">' + esc(t) + '</span>';
  });
  html += '</div>';
  document.getElementById('tag-modal-body').innerHTML = html;
}
function closeTagModal() { document.getElementById('tag-modal').close(); }
async function toggleModalTag(tag) {
  var p = _photoData[_tagModalIdx];
  var tags = (p.tags || []).slice();
  var pos = tags.indexOf(tag);
  if (pos >= 0) tags.splice(pos, 1); else tags.push(tag);
  await api('PUT', '/api/photo-tags', {filename: p.filename, tags: tags});
  p.tags = tags;
  _refreshTagModalContent();  // refresh without re-showModal
  renderAdminPhotos();
}

function selectPhoto(idx) {
  _selectedPhotoIdx = idx;
  showPhotoEditor(idx);
  renderAdminPhotos();
  loadEditorMap();
}

function showPhotoEditor(idx) {
  var p = _photoData[idx];
  var ed = document.getElementById('photo-editor');
  ed.style.display = 'block';
  document.getElementById('photo-editor-fn').textContent = p.filename;
  // Date
  var dateInput = document.getElementById('photo-editor-date');
  var curDate = p.date || (p.exif && p.exif.date) || '';
  if (curDate && curDate.match(/^\d{4}-\d{1,2}-\d{1,2}/)) {
    curDate = curDate.slice(0, 10);
  } else if (curDate && curDate.match(/^\w{3} \d{1,2}, \d{4}$/)) {
    var parts = curDate.match(/(\w+) (\d+), (\d+)/);
    if (parts) curDate = parts[3] + '-' + MONTHS_NUM[parts[1]] + '-' + String(parts[2]).padStart(2,'0');
  }
  dateInput.value = curDate;
  // GPS
  var gps = p.exif && p.exif.gps;
  document.getElementById('photo-editor-lat').value = gps ? gps.lat : '';
  document.getElementById('photo-editor-lng').value = gps ? gps.lng : '';
  // Update map marker
  if (_editorMarker) {
    _editorMap.removeLayer(_editorMarker);
    _editorMarker = null;
  }
  if (_editorMap && gps) {
    _editorMarker = L.marker([gps.lat, gps.lng], {icon: _editorMarkerIcon()}).addTo(_editorMap);
    _editorMap.setView([gps.lat, gps.lng], 14);
  }
  ed.scrollIntoView({behavior:'smooth'});
}

function clearPhotoEditor() {
  _selectedPhotoIdx = -1;
  document.getElementById('photo-editor').style.display = 'none';
  renderAdminPhotos();
}

async function savePhotoEditor() {
  if (_selectedPhotoIdx < 0) return;
  var fn = _photoData[_selectedPhotoIdx].filename;
  // Save date
  var dateVal = document.getElementById('photo-editor-date').value;
  if (dateVal) {
    var dp = dateVal.split('-');
    if (dp.length === 3) {
      dateVal = MONTHS_ARR[+dp[1]-1] + ' ' + (+dp[2]) + ', ' + dp[0];
    }
  }
  await api('PUT', '/api/photo-date', {filename: fn, date: dateVal});
  // Save GPS
  var latStr = document.getElementById('photo-editor-lat').value.trim();
  var lngStr = document.getElementById('photo-editor-lng').value.trim();
  if (latStr && lngStr) {
    var lat = parseFloat(latStr), lng = parseFloat(lngStr);
    if (!isNaN(lat) && !isNaN(lng)) {
      await api('PUT', '/api/photo-gps', {filename: fn, lat: lat, lng: lng});
    }
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
  if (typeof L === 'undefined') {
    var css = document.createElement('link'); css.rel='stylesheet';
    css.href='https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(css);
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js';
    s.onload = function() { initEditorMap(container); };
    s.onerror = function() { container.style.display = 'none'; toast('Leaflet 地图加载失败，请检查网络', true); };
    document.head.appendChild(s);
  } else {
    initEditorMap(container);
  }
}

function initEditorMap(container) {
  _editorMap = L.map(container, {attributionControl: false}).setView([22.5431, 113.9579], 11);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, subdomains: 'abcd', attribution: '&copy; OSM &copy; CARTO'
  }).addTo(_editorMap);
  // Click to set GPS
  _editorMap.on('click', function(e) {
    var lat = e.latlng.lat.toFixed(6), lng = e.latlng.lng.toFixed(6);
    document.getElementById('photo-editor-lat').value = lat;
    document.getElementById('photo-editor-lng').value = lng;
    if (_editorMarker) _editorMap.removeLayer(_editorMarker);
    _editorMarker = L.marker([lat, lng], {icon: _editorMarkerIcon()}).addTo(_editorMap);
  });
  // If selected photo has GPS, show it
  if (_selectedPhotoIdx >= 0) {
    var gps = _photoData[_selectedPhotoIdx].exif && _photoData[_selectedPhotoIdx].exif.gps;
    if (gps) {
      _editorMarker = L.marker([gps.lat, gps.lng], {icon: _editorMarkerIcon()}).addTo(_editorMap);
      _editorMap.setView([gps.lat, gps.lng], 14);
    }
  }
  setTimeout(function() { _editorMap.invalidateSize(); }, 200);
}

// Update card click to select
// remove old prompt-based functions (editPhotoDate, editPhotoGps) — replaced by panel above

function photoDragStart(e, idx) { _dragStart(e, idx); e.target.style.transform = 'scale(0.95)'; }
function photoDragOver(e) { _dragOver(e); }
function photoDragEnd(e) { e.target.style.transform = ''; _dragEnd(e); }

async function photoDrop(e, toIdx) {
  e.preventDefault();
  e.stopPropagation();
  var fromIdx = _dragState.idx;
  _dragEnd(e);
  if (fromIdx < 0 || fromIdx === toIdx) return;
  var item = _photoData.splice(fromIdx, 1)[0];
  _photoData.splice(toIdx, 0, item);
  renderAdminPhotos();
  await api('PUT', '/api/photos', _photoData);
  toast('顺序已保存');
}

function handlePhotoDrop(e) {
  if (!e.dataTransfer.files.length) return;  // internal drag, skip
  handlePhotoFiles(e.dataTransfer.files);
}

function handlePhotoFiles(files) {
  Array.from(files).forEach(function(f) {
    if (!f.type.startsWith('image/')) return;
    var fd = new FormData(); fd.append('file', f);
    api('POST', '/api/photos/upload', fd).then(function(r) {
      toast('已上传: ' + r.filename);
      loadPhotos();
    }).catch(function(e) { toast(e.message, true); });
  });
}

async function deletePhoto(filename) {  const confirmed = await confirmDialog('确定删除照片 "' + filename + '"？');
  if (!confirmed) return;
  await api('DELETE', '/api/photos/' + filename);
  loadPhotos();
  toast('照片已删除');
}
