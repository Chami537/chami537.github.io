// Main page photo gallery, stories, and filters.

function renderPhotos(data) {
  if (!data || !data.length) {
    return '<div class="photo-empty">这一组暂时没有匹配的照片。</div>';
  }
  return data.map(_photoItemHtml).join('');
}

function _photoItemHtml(photo) {
  var filename = encodeURIComponent(photo.filename);
  var exif = photo.exif || {};
  var meta = _photoMeta(photo, exif);
  var dateHtml = meta.date ? '<span class="photo-date">' + htmlEncode(meta.date) + '</span>' : '';
  var infoHtml = (meta.exifText || meta.gpsHtml) ? '<div class="photo-info">' + meta.exifText + meta.gpsHtml + '</div>' : '';
  var tagStr = (photo.tags || []).join(',');
  return '<div class="photo-item" data-tags="' + htmlEncode(tagStr) + '">' +
    '<img src="images/sm/' + filename + '" srcset="' + _photoSrcset(filename) + '" sizes="(max-width: 768px) 50vw, 33vw" alt="Photo" loading="lazy" data-exif="' + htmlEncode(meta.exifText + (meta.gpsText ? ' · ' + meta.gpsText : '') + (meta.date ? ' · ' + meta.date : '')) + '">' +
    dateHtml + infoHtml + '</div>';
}

function _photoSrcset(filename) {
  return 'images/sm/' + filename + ' 400w, images/md/' + filename + ' 800w, images/lg/' + filename + ' 1920w';
}

function _photoMeta(photo, exif) {
  var exifText = (_exifCamera(exif) + ' ' + _exifStr(exif)).trim();
  var gpsText = exif.gps ? _gpsStr(exif.gps.lat, exif.gps.lng, 4) : '';
  var gpsShort = exif.gps ? _gpsStr(exif.gps.lat, exif.gps.lng, 2) : '';
  var gpsHtml = gpsShort ? ' · <span style="cursor:pointer;text-decoration:underline" class="gps-link" onclick="event.stopPropagation();flyToPhoto(\'' + encodeURIComponent(photo.filename) + '\',' + exif.gps.lat + ',' + exif.gps.lng + ')">' + gpsShort + '</span>' : '';
  return {exifText: exifText, gpsText: gpsText, gpsHtml: gpsHtml, date: _photoDate(photo, exif)};
}

function _photoDate(photo, exif) {
  var date = photo.date || exif.date || '';
  if (photo.date || !date) return date;
  var match = date.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (!match) return date;
  var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return months[+match[2] - 1] + ' ' + (+match[3]) + ', ' + match[1];
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
      '<span class="story-meta">' + htmlEncode(story.date ? story.date : 'Untitled story') + '</span>' +
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
    html += '<span tabindex="0" role="button" class="ef-chip' + (_currentPhotoTag === t ? ' active' : '') + '" onclick="filterPhotosByTag(\'' + inlineJsString(t) + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();filterPhotosByTag(\'' + inlineJsString(t) + '\')}">' + htmlEncode(t) + '</span>';
  });
  el.innerHTML = html;
}
