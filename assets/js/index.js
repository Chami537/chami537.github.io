// Main page data-loading entry point.

// Main page data-loading entry point.

function _clearSkeleton(id) {
  var el = document.getElementById(id);
  if (el) el.classList.remove('skeleton-loading');
  return el;
}

function _photoStoryNameMap() {
  var map = Object.create(null);
  (window._photoStories || []).forEach(function(story) {
    if (!story || !story.name || !Array.isArray(story.photos)) return;
    story.photos.forEach(function(fname) {
      if (!map[fname]) map[fname] = story.name;
    });
  });
  return map;
}

function _photoByFilenameMap() {
  var map = Object.create(null);
  (window._photoData || []).forEach(function(photo) {
    if (photo && photo.filename) map[photo.filename] = photo;
  });
  return map;
}

function _applyPhotoImgAlts(root) {
  if (!root || !window._photoData) return;
  var byFile = _photoByFilenameMap();
  var storyByFile = _photoStoryNameMap();
  root.querySelectorAll('img').forEach(function(img) {
    var src = img.getAttribute('src') || '';
    var rawName = src.split('/').pop().split('?')[0];
    var filename = rawName;
    try { filename = decodeURIComponent(rawName); } catch (_) {}
    var photo = byFile[filename] || byFile[rawName];
    if (photo) {
      img.alt = buildPhotoAlt(photo, storyByFile[photo.filename] || '');
    }
  });
}

function _observePhotoAlts() {
  if (typeof MutationObserver !== 'function') return;
  var masonry = document.getElementById('photo-masonry');
  if (masonry && !masonry._altObserver) {
    masonry._altObserver = new MutationObserver(function() {
      _applyPhotoImgAlts(masonry);
    });
    masonry._altObserver.observe(masonry, { childList: true, subtree: true });
  }
  var mapBox = document.getElementById('photo-map-container');
  if (mapBox && !mapBox._altObserver) {
    mapBox._altObserver = new MutationObserver(function() {
      _applyPhotoImgAlts(mapBox);
    });
    mapBox._altObserver.observe(mapBox, { childList: true, subtree: true });
  }
}

document.addEventListener('DOMContentLoaded', function() {
  // About
  fetchJsonWithTimeout(dataUrl('data/about.json')).then(function(about) {
    if (about) {
      var paras = (about.content || '').split('\n').filter(Boolean);
      if (paras.length) {
        document.getElementById('about-text').innerHTML = paras.map(function(p, i) {
          return '<span class="about-para' + (i === 0 ? ' about-lead' : '') + '">' + htmlEncode(p) + '</span>';
        }).join('');
      }
      if (about.avatar) document.getElementById('portrait-img').src = about.avatar;
      if (about.tags && about.tags.length) {
        document.getElementById('hero-meta').innerHTML = about.tags.map(function(t) { return '<span>' + htmlEncode(t) + '</span>'; }).join('');
      }
    }
  }).catch(function() {
    // Keep static fallback content in #about-text
  }).finally(function() {
    _clearSkeleton('about-text');
    _clearSkeleton('hero-meta');
  });

  // Work
  fetchJsonWithTimeout(dataUrl('data/work.json')).then(function(work) {
    var workContainer = document.getElementById('work-container');
    if (Array.isArray(work)) {
      workContainer.innerHTML = work.length
        ? renderWork(work)
        : '<p class="section-loading">暂无项目</p>';
    } else {
      workContainer.innerHTML = '<p class="section-loading">项目暂时无法加载</p>';
    }
  }).catch(function() {
    var workContainer = document.getElementById('work-container');
    if (workContainer) workContainer.innerHTML = '<p class="section-loading">项目暂时无法加载</p>';
  }).finally(function() {
    var workContainer = _clearSkeleton('work-container');
    if (workContainer) workContainer.setAttribute('aria-busy', 'false');
  });

  // Stack
  fetchJsonWithTimeout(dataUrl('data/stack.json')).then(function(stack) {
    var el = document.getElementById('stack-cloud');
    if (!el) return;
    el.innerHTML = Array.isArray(stack) ? renderStack(stack) : '<p class="section-loading">技术栈暂时无法加载</p>';
  }).catch(function() {
    var el = document.getElementById('stack-cloud');
    if (el) el.innerHTML = '<p class="section-loading">技术栈暂时无法加载</p>';
  });

  // Essays (shared single request with Stories)
  fetchEssaysPublic().then(function(essays) {
    if (!essays) throw new Error('empty essays');
    var essaysData = Array.isArray(essays) ? essays : essays.essays;
    if (!Array.isArray(essaysData)) throw new Error('invalid essays');
    _allTags = Array.isArray(essays) ? [] : (essays._tags || []);
    _essayData = essaysData;
    buildEssayFilter();
    renderEssayList();
  }).catch(function() {
    var el = document.getElementById('essays-list');
    if (el) el.innerHTML = '<p class="section-loading">随笔暂时无法加载</p>';
  }).finally(function() {
    _clearSkeleton('essays-list');
  });

  // Photos
  fetchJsonWithTimeout(dataUrl('data/photos.json')).then(function(photos) {
    if (!Array.isArray(photos)) throw new Error('invalid photos');
    window._photoData = photos;
    var masonry = document.getElementById('photo-masonry');
    var total = photos.length;
    var cols = total <= 2 ? 2 : total <= 4 ? 3 : total <= 12 ? 4 : 5;
    masonry.style.columnCount = cols;
    masonry.innerHTML = renderPhotos(photos);
    _applyPhotoImgAlts(masonry);
    _observePhotoAlts();

    buildPhotoTagFilter();

    var lm = document.getElementById('photo-load-more');
    if (lm) lm.style.display = 'none';

    var gc = photos.filter(function(p) { return p.exif && p.exif.gps; }).length;
    var elGc = document.getElementById('gps-count');
    if (gc && elGc) {
      elGc.textContent = '· ' + gc + ' location' + (gc > 1 ? 's' : '');
      elGc.style.display = '';
    }

    initLB();

    // Load photo stories from server (pre-computed during build)
    fetchJsonWithTimeout(dataUrl('data/photo_stories.json')).then(function(data) {
      if (data) {
        window._photoStories = data;
        renderPhotoStories(data);
        _applyPhotoImgAlts(masonry);
      }
    }).catch(function() {});
  }).catch(function() {
    var masonry = document.getElementById('photo-masonry');
    if (masonry) masonry.innerHTML = '<p class="section-loading">照片暂时无法加载</p>';
  }).finally(function() {
    _clearSkeleton('photo-masonry');
  });

  // Contact
  fetchJsonWithTimeout(dataUrl('data/contact.json')).then(function(contact) {
    if (Array.isArray(contact)) {
      document.getElementById('contact-list').innerHTML = renderContact(contact);
    }
  }).catch(function() {
    // Keep static fallback links in #contact-list
  }).finally(function() {
    _clearSkeleton('contact-list');
  });

  // Friends
  fetchJsonWithTimeout(dataUrl('data/friends.json')).then(function(friends) {
    if (Array.isArray(friends)) {
      document.getElementById('friends-container').innerHTML = renderFriends(friends);
    } else {
      throw new Error('invalid friends');
    }
  }).catch(function() {
    var el = document.getElementById('friends-container');
    if (el) el.innerHTML = '<div class="friends-label">FRIEND</div><span class="section-loading">友链暂时无法加载</span>';
  }).finally(function() {
    _clearSkeleton('friends-container');
  });

  // Music
  fetchJsonWithTimeout(dataUrl('data/music.json')).then(function(music) {
    if (Array.isArray(music)) {
      document.getElementById('music-list').innerHTML = renderMusic(music);
    }
  }).catch(function() {
    // Keep static fallback tracks in #music-list
  }).finally(function() {
    _clearSkeleton('music-list');
    initMusicPlayer();
  });
});

// ═══ Dark Mode ═══
// Listen for shared theme changes to sync photo map
window.addEventListener('themechange', function(e) {
  if (_photoMap) {
    _photoMap.invalidateSize();
    _photoMap.getContainer().classList.toggle('dark', e.detail.mode === 'dark');
  }
});
