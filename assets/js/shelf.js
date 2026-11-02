// Complete public shelf: type filters, retry and stable fragment navigation.
(function() {
  'use strict';
  var items = [], essays = [], current = '';
  var list = document.getElementById('shelf-list');
  var status = document.getElementById('shelf-status');
  var retry = document.getElementById('shelf-retry');
  var filters = document.querySelectorAll('[data-shelf-type]');
  function locate() {
    if (!/^#story-\d+$/.test(location.hash)) return;
    var target = document.getElementById(location.hash.slice(1));
    if (target) {
      target.scrollIntoView({block: 'start'});
      target.classList.remove('shelf-highlight');
      void target.offsetWidth;
      target.classList.add('shelf-highlight');
    }
  }
  function render() {
    var selected = items.filter(function(s) { return !current || s.type === current; });
    StoriesShelf.render(list, selected, essays);
    status.textContent = selected.length ? '共 ' + selected.length + ' 部作品' :
      (current ? '这个分类还没有收录。' : '还在整理，慢慢把喜欢的故事放进来。');
    filters.forEach(function(b) { b.setAttribute('aria-pressed', String(b.dataset.shelfType === current)); });
  }
  async function load() {
    retry.hidden = true;
    list.setAttribute('aria-busy', 'true');
    status.textContent = '书架加载中…';
    try {
      items = await StoriesShelf.load();
      // An unavailable essay list suppresses links without hiding the shelf.
      essays = await fetch('data/essays_public.json?v=' + Date.now()).then(function(r) {
        return r.ok ? r.json() : null;
      }).then(function(data) { return data ? (Array.isArray(data) ? data : data.essays || []) : []; }).catch(function() { return []; });
      render();
      locate();
    } catch (_) {
      list.replaceChildren();
      status.textContent = '书架暂时无法加载，请稍后重试。';
      retry.hidden = false;
    } finally { list.setAttribute('aria-busy', 'false'); }
  }
  filters.forEach(function(button) {
    button.addEventListener('click', function() { current = button.dataset.shelfType; render(); });
  });
  window.addEventListener('hashchange', function() {
    current = '';
    render();
    locate();
  });
  retry.addEventListener('click', load);
  load();
})();
