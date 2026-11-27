// Essay image lightbox.

// Lightbox
var lbImgs = [];
var lbIdx = 0;
function _getLbCaptionEl() {
  var caption = document.getElementById('lb-caption');
  if (caption) return caption;
  var lbEl = document.getElementById('lb');
  if (!lbEl) return null;
  caption = document.createElement('div');
  caption.id = 'lb-caption';
  caption.className = 'lb-caption';
  caption.hidden = true;
  caption.style.display = 'none';
  var counter = document.getElementById('lb-counter');
  if (counter && counter.parentNode === lbEl) {
    lbEl.insertBefore(caption, counter);
  } else {
    lbEl.appendChild(caption);
  }
  return caption;
}
function _isFilenameAlt(alt) {
  if (!alt) return false;
  if (/\.(jpe?g|png|gif|webp|avif)$/i.test(alt)) return true;
  return /^(img|dsc|dscf|pxl|mvimg|pasted[-_ ]?image|image|photo|screenshot|wechatimg|mmexport|微信图片|屏幕截图)[-_ ]?[0-9][0-9_\- ]*$/i.test(alt);
}
function _updateLbDisplay(imgEl) {
  if (!imgEl) return;
  var lbImg = document.getElementById('lb-img');
  var alt = (imgEl.getAttribute('alt') || '').trim();
  lbImg.src = imgEl.src;
  lbImg.alt = alt;
  var captionText = _isFilenameAlt(alt) ? '' : alt;
  var caption = _getLbCaptionEl();
  if (caption) {
    caption.textContent = captionText;
    caption.hidden = !captionText;
    caption.style.display = captionText ? '' : 'none';
  }
  document.getElementById('lb-counter').textContent = (lbIdx + 1) + ' / ' + lbImgs.length;
}
function lbClose() {
  document.getElementById('lb').classList.remove('show');
  document.body.style.overflow = '';
}
function lbNav(d) {
  if (!lbImgs.length) return;
  lbIdx = (lbIdx + d + lbImgs.length) % lbImgs.length;
  _updateLbDisplay(lbImgs[lbIdx]);
}
document.addEventListener('keydown', function(e) {
  var lbEl = document.getElementById('lb');
  if (!lbEl || !lbEl.classList.contains('show')) return;
  if (e.key === 'Escape') lbClose();
  if (e.key === 'ArrowLeft') lbNav(-1);
  if (e.key === 'ArrowRight') lbNav(1);
});

function initLightbox() {
  var essayBody = document.querySelector('.essay-body');
  if (essayBody) essayBody.addEventListener('click', function(e) {
    if (e.target.tagName !== 'IMG') return;
    lbImgs = Array.from(document.querySelectorAll('.essay-body img'));
    lbIdx = lbImgs.indexOf(e.target);
    document.getElementById('lb').classList.add('show');
    _updateLbDisplay(e.target);
    document.body.style.overflow = 'hidden';
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
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initLightbox);
} else {
  initLightbox();
}

