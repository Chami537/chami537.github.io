// Photo loading, cards, selection, and drag ordering.

var _photoData = [];
onAdminDataReset(loadPhotos);

async function loadPhotos() {
  try {
    _photoData = await api('GET', '/api/photos');
    _renderPhotoTagTabs();
    if (_currentPhotoTag) {
      _photoData = _photoData.filter(function(photo) {
        return (photo.tags || []).indexOf(_currentPhotoTag) >= 0;
      });
    }
    renderAdminPhotos();
    await loadStories();
  } catch (error) {
    toast(error.message, true);
  }
}

function _photoDisplayDate(photo) {
  var displayDate = photo.date || (photo.exif && photo.exif.date) || '';
  if (!photo.date && displayDate) {
    var match = displayDate.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (match) displayDate = MONTHS_ARR[+match[2] - 1] + ' ' + (+match[3]) + ', ' + match[1];
  }
  return displayDate;
}

function _photoCardHtml(photo, index) {
  var tagCount = (photo.tags || []).length;
  var displayDate = _photoDisplayDate(photo);
  var tagButton = '<button class="btn btn-sm" onclick="event.stopPropagation();openPhotoTagModal(' + index + ')" style="font-size:10px;padding:1px 6px;margin-top:4px;">' +
    '🏷 ' + (tagCount > 0 ? tagCount + ' 标签' : '加标签') + '</button>';
  var exif = photo.exif || {};
  return '<div class="photo-card' + (_selectedPhotoIdx === index ? ' selected' : '') + '" draggable="true" data-index="' + index + '"' +
    ' onclick="selectPhoto(' + index + ')" ondragstart="photoDragStart(event,' + index + ')"' +
    ' ondragover="photoDragOver(event)" ondragend="photoDragEnd(event)" ondrop="photoDrop(event,' + index + ')">' +
    '<img src="/images/sm/' + encodeURIComponent(photo.filename) + '" alt="' + esc(photo.filename) + '" loading="lazy">' +
    '<button class="del-btn" data-filename="' + esc(photo.filename) + '" onclick="deletePhoto(this.dataset.filename)">×</button>' +
    '<div class="photo-info"><div class="fn">' + esc(photo.filename) + '</div><div class="sz">' + (photo.size || '') + '</div>' +
    (Object.keys(exif).length ? '<div class="photo-exif">' + esc(exif.aperture || '') + ' ' + esc(exif.shutter || '') + ' ISO' + esc(exif.iso || '') + '</div>' : '') +
    (displayDate ? '<div class="photo-exif" style="color:var(--c3)">📅 ' + esc(displayDate) + '</div>' : '') +
    (exif.gps ? '<div class="photo-exif">📍 ' + exif.gps.lat.toFixed(4) + ', ' + exif.gps.lng.toFixed(4) + '</div>' : '') +
    tagButton + '</div></div>';
}

function renderAdminPhotos() {
  document.getElementById('photo-grid').innerHTML = _photoData.map(_photoCardHtml).join('');
}

function photoDragStart(event, index) {
  _dragStart(event, index);
  event.target.style.transform = 'scale(0.95)';
}

function photoDragOver(event) { _dragOver(event); }

function photoDragEnd(event) {
  event.target.style.transform = '';
  _dragEnd(event);
}

async function photoDrop(event, targetIndex) {
  event.preventDefault();
  event.stopPropagation();
  var sourceIndex = _dragState.idx;
  _dragEnd(event);
  if (sourceIndex < 0 || sourceIndex === targetIndex) return;
  var item = _photoData.splice(sourceIndex, 1)[0];
  _photoData.splice(targetIndex, 0, item);
  renderAdminPhotos();
  await api('PUT', '/api/photos', _photoData);
  toast('顺序已保存');
}
