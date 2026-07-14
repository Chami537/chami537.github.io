// Photo tag library, filters, and tag modal.

var _currentPhotoTag = '';
var _photoDeleteTagMode = false;
var _tagModalIdx = -1;

function getPhotoTags() { return _tagLib('photo-tags', '["Shenzhen","Night","Street"]'); }
function savePhotoTags(tags) { _saveTagLib('photo-tags', tags); }

function switchPhotoTabTag(tag) {
  _currentPhotoTag = tag;
  loadPhotos();
}

function promptNewPhotoTag() {
  _promptTag('photo-tags', '["Shenzhen","Night","Street"]', function(tag) {
    _currentPhotoTag = tag;
    loadPhotos();
  });
}

function toggleDeletePhotoTagMode() {
  _photoDeleteTagMode = _toggleDeleteTagMode('delete-photo-tag-btn', _photoDeleteTagMode, loadPhotos);
}

async function deletePhotoTagGlobal(tag) {
  if (!confirm('确定永久删除标签 "' + tag + '"？这将从所有照片中移除该标签。')) return;
  savePhotoTags(getPhotoTags().filter(function(item) { return item !== tag; }));
  for (var photo of _photoData) {
    if (!photo.tags) continue;
    var tags = photo.tags.filter(function(item) { return item !== tag; });
    if (tags.length !== photo.tags.length) {
      photo.tags = tags;
      await api('PUT', '/api/photo-tags', {filename: photo.filename, tags: tags});
    }
  }
  if (_currentPhotoTag === tag) _currentPhotoTag = '';
  loadPhotos();
}

function _renderPhotoTagTabs() {
  var html = '<span tabindex="0" role="button" class="tag-tab-btn-sm' + (!_currentPhotoTag ? ' active' : '') +
    '" onclick="switchPhotoTabTag(\'\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();switchPhotoTabTag(\'\')}">全部</span>';
  getPhotoTags().forEach(function(tag) {
    var deletion = _photoDeleteTagMode ? '<span onclick="event.stopPropagation();deletePhotoTagGlobal(\'' + esc(tag) + '\')" class="tag-tab-del">×</span>' : '';
    html += '<span tabindex="0" role="button" class="tag-tab-btn-sm' + (_currentPhotoTag === tag ? ' active' : '') +
      '" onclick="switchPhotoTabTag(\'' + esc(tag) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();switchPhotoTabTag(\'' + esc(tag) + '\')}">' + esc(tag) + deletion + '</span>';
  });
  document.getElementById('photo-tag-tabs').innerHTML = html;
}

function openPhotoTagModal(index) {
  _tagModalIdx = index;
  _refreshTagModalContent();
  document.getElementById('tag-modal').showModal();
}

function _refreshTagModalContent() {
  var selected = _photoData[_tagModalIdx].tags || [];
  var html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">';
  getPhotoTags().forEach(function(tag) {
    html += '<span tabindex="0" role="button" onclick="toggleModalTag(\'' + esc(tag) + '\')" class="tag-tab-btn-sm' +
      (selected.indexOf(tag) >= 0 ? ' active' : '') + '" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();toggleModalTag(\'' + esc(tag) + '\')}">' + esc(tag) + '</span>';
  });
  document.getElementById('tag-modal-body').innerHTML = html + '</div>';
}

function closeTagModal() { document.getElementById('tag-modal').close(); }

async function toggleModalTag(tag) {
  var photo = _photoData[_tagModalIdx];
  var tags = (photo.tags || []).slice();
  var index = tags.indexOf(tag);
  if (index >= 0) tags.splice(index, 1); else tags.push(tag);
  await api('PUT', '/api/photo-tags', {filename: photo.filename, tags: tags});
  photo.tags = tags;
  _refreshTagModalContent();
  renderAdminPhotos();
}
