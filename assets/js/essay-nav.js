// Essay navigation sticky behavior.

// Nav sticky: hide on scroll down, show on scroll up
var _lastScrollY = scrollY;
addEventListener('scroll', function() {
  var nav = document.querySelector('nav');
  var dy = scrollY - _lastScrollY;
  if (scrollY < 100) nav.classList.remove('hidden');
  else if (dy > 8) nav.classList.add('hidden');
  else if (dy < -8) nav.classList.remove('hidden');
  _lastScrollY = scrollY;
}, { passive: true });

