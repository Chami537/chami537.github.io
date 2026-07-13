// Main page data-loading entry point.

document.addEventListener('DOMContentLoaded', async function() {
  // Fetch all data in parallel, then render all at once — one layout pass, zero jank
  var sections = ['about','work','essays','photos','contact','friends','music','stack'];
  var results = {};
  try {
    var fetched = await Promise.all(sections.map(function(s) {
      var url = s === 'essays' ? 'data/essays_public.json' : 'data/' + s + '.json';
      return fetch(url + '?v=' + TS).then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; });
    }));
    sections.forEach(function(s, i) { results[s] = fetched[i]; });
  } catch(e) {}

  // About
  try {
    var about = results.about;
    if (about) {
      var paras = about.content.split('\n').filter(Boolean);
      document.getElementById('about-text').innerHTML = paras.map(function(p, i) {
        return '<span class="about-para' + (i === 0 ? ' about-lead' : '') + '">' + htmlEncode(p) + '</span>';
      }).join('');
      if (about.avatar) document.getElementById('portrait-img').src = about.avatar;
      if (about.tags && about.tags.length) {
        document.getElementById('hero-meta').innerHTML = about.tags.map(function(t) { return '<span>' + htmlEncode(t) + '</span>'; }).join('');
      }
    }
  } catch(e) {}
  // Work
  if (results.work) {
    document.getElementById('work-container').innerHTML = renderWork(results.work);
  }
  // Essays
  if (results.essays) {
    var essaysData = Array.isArray(results.essays) ? results.essays : results.essays.essays;
    _allTags = Array.isArray(results.essays) ? [] : (results.essays._tags || []);
    _essayData = essaysData;
    buildEssayFilter();
    renderEssayList();
  }
  // Photos
  if (results.photos) {
    window._photoData = results.photos;
    var total = results.photos.length;
    var cols = total <= 2 ? 2 : total <= 4 ? 3 : total <= 12 ? 4 : 5;
    document.getElementById('photo-masonry').style.columnCount = cols;
    document.getElementById('photo-masonry').innerHTML = renderPhotos(results.photos);

    // Load photo stories from server (pre-computed during build)
    fetch('data/photo_stories.json?v=' + TS).then(function(r) { return r.ok ? r.json() : null; }).then(function(data) {
      if (data) renderPhotoStories(data);
    }).catch(function() {});
    buildPhotoTagFilter();

    // Hide load-more (23 photos fit in one batch)
    var lm = document.getElementById('photo-load-more');
    if (lm) lm.style.display = 'none';

    var gc = results.photos.filter(function(p) { return p.exif && p.exif.gps; }).length;
    var elGc = document.getElementById('gps-count');
    if (gc) {
      elGc.textContent = '· ' + gc + ' location' + (gc > 1 ? 's' : '');
      elGc.style.display = '';
    }
  }
  // Contact
  if (results.contact) document.getElementById('contact-list').innerHTML = renderContact(results.contact);
  // Friends
  if (results.friends) document.getElementById('friends-container').innerHTML = renderFriends(results.friends);
  // Music
  if (results.music) document.getElementById('music-list').innerHTML = renderMusic(results.music);
  // Stack
  if (results.stack) document.getElementById('stack-cloud').innerHTML = renderStack(results.stack);
  // Remove all skeleton classes at once
  document.querySelectorAll('.skeleton-loading').forEach(function(el) { el.classList.remove('skeleton-loading'); });

  initMusicPlayer();
  initLB();

});

// ═══ Dark Mode ═══
// Listen for shared theme changes to sync photo map
window.addEventListener('themechange', function(e) {
  if (_photoMap) {
    _photoMap.invalidateSize();
    _photoMap.getContainer().classList.toggle('dark', e.detail.mode === 'dark');
  }
});
