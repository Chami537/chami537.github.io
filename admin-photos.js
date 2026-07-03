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
  } catch(e) { toast(e.message, true); }
}

function renderAdminPhotos() {
  document.getElementById('photo-grid').innerHTML = _photoData.map(function(p, i) {
    var tagCount = (p.tags || []).length;
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
        '<div class="sz">' + (p.size || '') + (p.exif && p.exif.camera ? ' · ' + esc(p.exif.camera) : '') + '</div>' +
        (p.exif && Object.keys(p.exif).length ? '<div class="photo-exif">' + esc(p.exif.aperture||'') + ' ' + esc(p.exif.shutter||'') + ' ISO' + esc(p.exif.iso||'') + '</div>' : '') +
        (p.date ? '<div class="photo-exif" style="color:var(--c3)">📅 ' + esc(p.date) + '</div>' : '') +
        (p.exif && p.exif.gps ? '<div class="photo-exif">📍 ' + p.exif.gps.lat.toFixed(4) + ', ' + p.exif.gps.lng.toFixed(4) + '</div>' : '') +
        tagBtn +
      '</div>' +
      '</div>';
  }).join('');
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
  var curDate = p.date || '';
  if (curDate && curDate.match(/^\w{3} \d{1,2}, \d{4}$/)) {
    var parts = curDate.match(/(\w+) (\d+), (\d+)/);
    if (parts) curDate = parts[3] + '-' + MONTHS_NUM[parts[1]] + '-' + String(parts[2]).padStart(2,'0');
  }
  dateInput.value = curDate;
  // GPS
  var gps = p.exif && p.exif.gps;
  document.getElementById('photo-editor-lat').value = gps ? gps.lat : '';
  document.getElementById('photo-editor-lng').value = gps ? gps.lng : '';
  // Update map marker
  if (_editorMarker && gps) {
    _editorMarker.setLatLng([gps.lat, gps.lng]);
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
    document.head.appendChild(s);
  } else {
    initEditorMap(container);
  }
}

function initEditorMap(container) {
  _editorMap = L.map(container).setView([22.5431, 113.9579], 11);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, subdomains: 'abcd', attribution: '&copy; OSM &copy; CARTO'
  }).addTo(_editorMap);
  // Click to set GPS
  _editorMap.on('click', function(e) {
    var lat = e.latlng.lat.toFixed(6), lng = e.latlng.lng.toFixed(6);
    document.getElementById('photo-editor-lat').value = lat;
    document.getElementById('photo-editor-lng').value = lng;
    if (_editorMarker) _editorMap.removeLayer(_editorMarker);
    _editorMarker = L.marker([lat, lng]).addTo(_editorMap);
  });
  // If selected photo has GPS, show it
  if (_selectedPhotoIdx >= 0) {
    var gps = _photoData[_selectedPhotoIdx].exif && _photoData[_selectedPhotoIdx].exif.gps;
    if (gps) {
      _editorMarker = L.marker([gps.lat, gps.lng]).addTo(_editorMap);
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

// ═══ Story editor ═══

var _storyData = [];

async function loadStories() {
  try {
    _storyData = await api('GET', '/api/photo-stories');
  } catch(e) {
    _storyData = [];
  }
  renderStoryEditor();
}

function renderStoryEditor() {
  var el = document.getElementById('story-editor-list');
  if (!_storyData.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:12px;">暂无故事线。<button class="btn btn-sm" onclick="addStory()" style="margin-left:8px;">+ 新建故事</button></p>';
    return;
  }
  var allPhotos = _photoData || [];
  var html = '';
  _storyData.forEach(function(s, si) {
    var cover = s.cover || (s.photos && s.photos[0]) || '';
    var caption = s.caption || '';
    var photos = s.photos || [];
    html += '<div class="story-edit-card" style="background:var(--card-bg);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:12px;">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
      '<input value="' + esc(s.id) + '" onchange="_storyData[' + si + '].id=this.value" style="width:180px;font-weight:600;font-size:13px;border:1px solid var(--border);border-radius:4px;padding:3px 6px;background:var(--bg);color:var(--fg);" placeholder="故事ID">' +
      '<button class="btn btn-sm btn-danger" onclick="deleteStory(' + si + ')">删除</button>' +
      '</div>' +
      '<div style="display:flex;gap:8px;margin-bottom:6px;">' +
      '<input value="' + esc(s.name || '') + '" onchange="_storyData[' + si + '].name=this.value" style="flex:1;font-size:12px;border:1px solid var(--border);border-radius:4px;padding:3px 6px;background:var(--bg);color:var(--fg);" placeholder="故事名称">' +
      '<input value="' + esc(s.date || '') + '" onchange="_storyData[' + si + '].date=this.value" style="width:140px;font-size:12px;border:1px solid var(--border);border-radius:4px;padding:3px 6px;background:var(--bg);color:var(--fg);" placeholder="日期标签">' +
      '</div>' +
      '<div style="font-size:11px;margin-bottom:4px;">封面 / 照片（点击图选封面，点 ✓/+ 添加/移除）：</div>' +
      '<div style="display:flex;gap:4px;overflow-x:auto;padding-bottom:6px;flex-wrap:wrap;" class="story-cover-picker">';
    allPhotos.forEach(function(p) {
      var fn = p.filename;
      var sel = fn === cover ? 'border:2px solid #0066ff;' : 'border:2px solid transparent;';
      var inStory = photos.indexOf(fn) >= 0;
      html += '<div style="position:relative;flex-shrink:0;" title="' + esc(fn) + '">' +
        '<img src="/images/sm/' + fn + '" data-fn="' + esc(fn) + '" ' +
        'onclick="pickStoryCover(' + si + ', this)" ' +
        'style="width:56px;height:56px;object-fit:cover;border-radius:6px;cursor:pointer;' + sel + 'opacity:' + (inStory ? '1' : '0.35') + '">' +
        '<span onclick="toggleStoryPhoto(' + si + ', \'' + esc(fn) + '\', this)" ' +
        'style="position:absolute;top:2px;right:2px;width:16px;height:16px;border-radius:50%;background:' + (inStory ? '#0066ff' : '#888') + ';color:#fff;font-size:10px;line-height:16px;text-align:center;cursor:pointer;">' + (inStory ? '✓' : '+') + '</span>' +
        '</div>';
    });
    html += '</div>' +
      '<textarea onchange="_storyData[' + si + '].caption=this.value" style="width:100%;box-sizing:border-box;padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--fg);font-size:12px;resize:vertical;margin-top:6px;" rows="2" placeholder="简介（留空不显示）">' + esc(caption) + '</textarea>' +
      '</div>';
  });
  html += '<button class="btn btn-sm" onclick="addStory()" style="margin-top:4px;">+ 新建故事</button>';
  el.innerHTML = html;
}

function addStory() {
  _storyData.push({id: 'new_story_' + Date.now(), name: '', date: '', caption: '', cover: '', photos: []});
  renderStoryEditor();
}

function deleteStory(idx) {
  if (!confirm('删除故事 "' + (_storyData[idx].name || _storyData[idx].id) + '"？')) return;
  _storyData.splice(idx, 1);
  renderStoryEditor();
}

function pickStoryCover(si, img) {
  var container = img.closest('.story-cover-picker');
  container.querySelectorAll('img').forEach(function(el) { el.style.border = '2px solid transparent'; });
  img.style.border = '2px solid #0066ff';
  _storyData[si].cover = img.dataset.fn;
}

function toggleStoryPhoto(si, fn, badge) {
  var photos = _storyData[si].photos || [];
  var idx = photos.indexOf(fn);
  if (idx >= 0) {
    photos.splice(idx, 1);
    badge.style.background = '#888';
    badge.textContent = '+';
    badge.parentElement.querySelector('img').style.opacity = '0.35';
  } else {
    photos.push(fn);
    badge.style.background = '#0066ff';
    badge.textContent = '✓';
    badge.parentElement.querySelector('img').style.opacity = '1';
  }
  _storyData[si].photos = photos;
}

async function saveStoryOverrides() {
  try {
    await api('PUT', '/api/photo-stories', _storyData);
    toast('故事线已保存');
  } catch(e) { toast(e.message, true); }
}

// Auto-load stories when photos tab is active
// Auto-load stories when photos tab is active
var _origLoadPhotos = loadPhotos;
loadPhotos = async function() {
  await _origLoadPhotos();
  loadStories();
};

