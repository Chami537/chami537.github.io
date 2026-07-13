// Admin Photo Stories editor.

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
    el.innerHTML = '<div class="story-empty">暂无故事线。<button class="btn btn-sm" onclick="addStory()">+ 新建故事</button></div>';
    return;
  }
  var allPhotos = _photoData || [];
  var html = '';
  _storyData.forEach(function(s, si) {
    var cover = s.cover || (s.photos && s.photos[0]) || '';
    var caption = s.caption || '';
    var photos = s.photos || [];
    html += '<div class="story-edit-card">' +
      '<div class="story-edit-head">' +
      '<input class="story-id-input" value="' + esc(s.id) + '" onchange="_storyData[' + si + '].id=this.value" placeholder="故事ID">' +
      '<span class="story-edit-count">' + photos.length + ' photos</span>' +
      '<button class="btn btn-sm btn-danger" onclick="deleteStory(' + si + ')">删除</button>' +
      '</div>' +
      '<div class="story-edit-fields">' +
      '<input value="' + esc(s.name || '') + '" onchange="_storyData[' + si + '].name=this.value" placeholder="故事名称">' +
      '<input value="' + esc(s.date || '') + '" onchange="_storyData[' + si + '].date=this.value" placeholder="日期标签">' +
      '</div>' +
      '<div class="story-edit-help">封面 / 照片：点击图片选封面，点右上角添加或移除。</div>' +
      '<div class="story-cover-picker">';
    allPhotos.forEach(function(p) {
      var fn = p.filename;
      var inStory = photos.indexOf(fn) >= 0;
      var itemClass = 'story-photo-pick' + (fn === cover ? ' is-cover' : '') + (inStory ? ' in-story' : '');
      html += '<div class="' + itemClass + '" title="' + esc(fn) + '">' +
        '<img src="/images/sm/' + encodeURIComponent(fn) + '" data-fn="' + esc(fn) + '" ' +
        'onclick="pickStoryCover(' + si + ', this)" ' +
        'class="story-photo-thumb">' +
        '<span class="story-photo-toggle" onclick="toggleStoryPhoto(' + si + ', \'' + esc(fn) + '\', this)">' + (inStory ? '✓' : '+') + '</span>' +
        '</div>';
    });
    html += '</div>' +
      '<textarea class="story-caption-input" onchange="_storyData[' + si + '].caption=this.value" rows="2" placeholder="简介（留空不显示）">' + esc(caption) + '</textarea>' +
      '</div>';
  });
  html += '<button class="btn btn-sm story-add-btn" onclick="addStory()">+ 新建故事</button>';
  el.innerHTML = html;
}

function _editorMarkerIcon() {
  return L.divIcon({className: 'custom-marker', html: '<div class="marker-dot"></div>', iconSize: [16, 16], iconAnchor: [8, 8]});
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
  container.querySelectorAll('.story-photo-pick').forEach(function(el) { el.classList.remove('is-cover'); });
  img.closest('.story-photo-pick').classList.add('is-cover');
  _storyData[si].cover = img.dataset.fn;
}

function toggleStoryPhoto(si, fn, badge) {
  var photos = _storyData[si].photos || [];
  var idx = photos.indexOf(fn);
  var item = badge.closest('.story-photo-pick');
  if (idx >= 0) {
    photos.splice(idx, 1);
    badge.textContent = '+';
    item.classList.remove('in-story');
    if (_storyData[si].cover === fn) {
      _storyData[si].cover = photos[0] || '';
    }
  } else {
    photos.push(fn);
    badge.textContent = '✓';
    item.classList.add('in-story');
    if (!_storyData[si].cover) {
      _storyData[si].cover = fn;
    }
  }
  _storyData[si].photos = photos;
  var picker = item.closest('.story-cover-picker');
  if (picker) {
    picker.querySelectorAll('.story-photo-pick').forEach(function(el) {
      var img = el.querySelector('img');
      el.classList.toggle('is-cover', img && img.dataset.fn === _storyData[si].cover);
    });
  }
  var card = badge.closest('.story-edit-card');
  var count = card && card.querySelector('.story-edit-count');
  if (count) count.textContent = photos.length + ' photos';
}

async function saveStoryOverrides() {
  try {
    await api('PUT', '/api/photo-stories', _storyData);
    toast('故事线已保存');
  } catch(e) { toast(e.message, true); }
}

