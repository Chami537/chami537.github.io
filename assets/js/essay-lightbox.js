// Essay image lightbox.

// Lightbox
var lbImgs = [];
var lbIdx = 0;
var essayBody = document.querySelector('.essay-body');
if (essayBody) essayBody.addEventListener('click', function(e) {
  if (e.target.tagName !== 'IMG') return;
  lbImgs = Array.from(document.querySelectorAll('.essay-body img'));
  lbIdx = lbImgs.indexOf(e.target);
  document.getElementById('lb').classList.add('show');
  document.getElementById('lb-img').src = e.target.src;
  document.getElementById('lb-counter').textContent = (lbIdx + 1) + ' / ' + lbImgs.length;
  document.body.style.overflow = 'hidden';
});
function lbClose() {
  document.getElementById('lb').classList.remove('show');
  document.body.style.overflow = '';
}
function lbNav(d) {
  lbIdx = (lbIdx + d + lbImgs.length) % lbImgs.length;
  document.getElementById('lb-img').src = lbImgs[lbIdx].src;
  document.getElementById('lb-counter').textContent = (lbIdx + 1) + ' / ' + lbImgs.length;
}
document.addEventListener('keydown', function(e) {
  if (!document.getElementById('lb').classList.contains('show')) return;
  if (e.key === 'Escape') lbClose();
  if (e.key === 'ArrowLeft') lbNav(-1);
  if (e.key === 'ArrowRight') lbNav(1);
});
// Touch swipe
var _lbTouchX = 0;
var lbEl = document.getElementById('lb');
if (lbEl) {
  lbEl.addEventListener('touchstart', function(e) { _lbTouchX = e.touches[0].clientX; }, {passive: true});
  lbEl.addEventListener('touchend', function(e) {
    var dx = e.changedTouches[0].clientX - _lbTouchX;
    if (Math.abs(dx) > 50) lbNav(dx < 0 ? 1 : -1);
  }, {passive: true});
}

