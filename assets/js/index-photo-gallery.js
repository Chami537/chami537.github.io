// Main page photo gallery, stories, and filters.

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
    var photoDate = p.date || ex.date || '';
    if (!p.date && photoDate) {
      var dateMatch = photoDate.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
      if (dateMatch) {
        var dateMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        photoDate = dateMonths[+dateMatch[2] - 1] + ' ' + (+dateMatch[3]) + ', ' + dateMatch[1];
      }
    }
    var dateHtml = photoDate ? '<span class="photo-date">' + photoDate + '</span>' : '';
    var infoHtml = (exifStr || gpsHtml) ? '<div class="photo-info">' + exifStr + gpsHtml + '</div>' : '';
    var tagStr = (p.tags || []).join(',');
    return '<div class="photo-item" data-tags="' + htmlEncode(tagStr) + '">' +
      '<img src="images/sm/' + fn + '" srcset="' + srcset + '" sizes="(max-width: 768px) 50vw, 33vw" alt="Photo" loading="lazy" data-exif="' + htmlEncode(exifStr + (gpsText4 ? ' · ' + gpsText4 : '') + (photoDate ? ' · ' + photoDate : '')) + '">' +
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

