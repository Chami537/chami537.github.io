// Essay page data, navigation, progress, and reveal behavior.

// Essay image lightbox.

const pageRoot = document.querySelector('main.reading');
const buildTs = pageRoot ? pageRoot.dataset.buildTs : '';
const currentSlug = pageRoot ? pageRoot.dataset.slug : '';
const bar = document.querySelector('.progress');
var pageHeight = document.documentElement.scrollHeight - innerHeight;

window.addEventListener('resize', () => {
  pageHeight = document.documentElement.scrollHeight - innerHeight;
});

addEventListener('scroll', () => {
  if (pageHeight > 0) bar.style.width = (scrollY / pageHeight * 100) + '%';
});

// Render friends
(async () => {
  try {
    const friends = await fetch('/data/friends.json?v=' + encodeURIComponent(buildTs)).then(r => r.json());
    const container = document.getElementById('friends-container');
    let html = '<div class="friends-label">FRIEND</div>';
    friends.forEach((f, i) => {
      var escUrl = f.url.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      var escName = f.name.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      if (/^https?:\/\//i.test(f.url)) {
        html += '<a href="' + escUrl + '">' + escName + '</a>';
      } else {
        html += '<span>' + escName + '</span>';
      }
    });
    container.innerHTML = html;
    pageHeight = document.documentElement.scrollHeight - innerHeight;
  } catch(e) {}
})();

// Context-aware previous/next links. When opened from a filtered essay list,
// keep navigation inside that same list; otherwise keep the build-time fallback.
(async () => {
  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, function(c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function essayTags(e) {
    var tags = (e.tag || '').split(/[,，]/).map(function(t) { return t.trim(); }).filter(Boolean);
    if (e.pinned && tags.indexOf('置顶') < 0) tags.push('置顶');
    return tags;
  }
  function navLink(e, dir) {
    if (!e) return '<div></div>';
    var label = dir < 0 ? '上一篇' : '下一篇';
    var cls = dir < 0 ? 'prev-link' : 'next-link';
    var titleCls = dir < 0 ? 'prev-title' : 'next-title';
    var arrCls = dir < 0 ? 'prev-arr' : 'next-arr';
    var href = esc(e.slug) + '.html' + location.search;
    if (dir < 0) {
      return '<a href="' + href + '" class="' + cls + '"><span class="prev-label">' + label + '</span><div class="' + titleCls + '"><span class="' + arrCls + '">←</span><span>' + esc(e.title) + '</span></div></a>';
    }
    return '<a href="' + href + '" class="' + cls + '"><span class="next-label">' + label + '</span><div class="' + titleCls + '"><span>' + esc(e.title) + '</span><span class="' + arrCls + '">→</span></div></a>';
  }

  var tag = new URLSearchParams(location.search).get('tag');
  if (!tag) return;
  try {
    var payload = await fetch('/data/essays_public.json?v=' + encodeURIComponent(buildTs)).then(function(r) { return r.ok ? r.json() : null; });
    var essays = payload && (payload.essays || payload);
    if (!Array.isArray(essays)) return;
    var list = essays.filter(function(e) { return essayTags(e).indexOf(tag) >= 0; });
    var idx = list.findIndex(function(e) { return e.slug === currentSlug; });
    if (idx < 0) return;
    document.getElementById('nav-row').innerHTML = navLink(list[idx - 1], -1) + navLink(list[idx + 1], 1);
  } catch(e) {}
})();

// Scroll reveal
(function() {
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        observer.unobserve(e.target);
      }
    });
  }, { threshold: 0.15 });
  document.querySelectorAll('.essay-body p, .essay-body h2, .essay-body img, .essay-body blockquote').forEach(function(el) {
    el.classList.add('reveal');
    observer.observe(el);
  });
})();

