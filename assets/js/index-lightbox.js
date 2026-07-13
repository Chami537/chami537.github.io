// Main page photo lightbox.

// ═══ Lightbox ═══
var lbPhotos = [];
var lbIndex = 0;
var _lbInited = false;
var _lbPreload = {};
function initLB() {
  if (_lbInited) return;
  _lbInited = true;
  var masonry = document.querySelector('#photo-masonry');
  if (!masonry) return;
  masonry.addEventListener('click', function(e) {
    var img = e.target.closest('.photo-item')?.querySelector('img');
    if (!img) return;
    lbPhotos = Array.from(document.querySelectorAll('#photo-masonry img')).map(function(el) {
      var filename = el.src.split('/').pop().split('?')[0];
      return { src: 'images/lg/' + filename, alt: el.alt, exif: el.dataset.exif || '' };
    });
    var clickedFile = img.src.split('/').pop().split('?')[0];
    lbIndex = lbPhotos.findIndex(function(p) { return p.src.endsWith('/' + clickedFile); });
    openLB();
  });
  document.addEventListener('keydown', function(e) {
    if (!document.getElementById('lightbox').classList.contains('show')) return;
    if (e.key === 'Escape') closeLB();
    if (e.key === 'ArrowLeft') navLB(-1);
    if (e.key === 'ArrowRight') navLB(1);
  });
  // Touch swipe
  var touchX = 0;
  var lb = document.getElementById('lightbox');
  lb.addEventListener('touchstart', function(e) { touchX = e.touches[0].clientX; }, {passive: true});
  lb.addEventListener('touchend', function(e) {
    var dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 50) navLB(dx < 0 ? 1 : -1);
  }, {passive: true});
}
function openLB() {
  var lb = document.getElementById('lightbox');
  lb.classList.add('show');
  updateLB();
  preloadAdjacent();
  document.body.style.overflow = 'hidden';
}
function closeLB() {
  document.getElementById('lightbox').classList.remove('show');
  document.body.style.overflow = '';
}
function navLB(dir) {
  lbIndex = (lbIndex + dir + lbPhotos.length) % lbPhotos.length;
  updateLB();
  preloadAdjacent();
}
function preloadAdjacent() {
  [-1, 1].forEach(function(offset) {
    var i = (lbIndex + offset + lbPhotos.length) % lbPhotos.length;
    if (i === lbIndex) return;
    var src = lbPhotos[i].src;
    if (_lbPreload[src]) return;
    var img = new Image();
    img.onload = function() { _lbPreload[src] = true; };
    img.src = src;
  });
}
function updateLB() {
  var p = lbPhotos[lbIndex];
  if (!p) return;
  var img = document.getElementById('lb-img');
  if (img.src === p.src) return;
  img.onload = function() { img.classList.remove('loading'); };
  img.classList.add('loading');
  img.src = p.src;
  img.alt = p.alt;
  document.getElementById('lb-exif').textContent = p.exif || '';
  document.getElementById('lb-counter').textContent = (lbIndex + 1) + ' / ' + lbPhotos.length;
}

