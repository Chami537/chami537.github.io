// Shared shelf cards; all personal text is inserted using textContent.
window.StoriesShelf = (function() {
  'use strict';
  var types = {movie: '电影', series: '电视剧', novel: '小说'};
  function node(tag, className, text) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    if (text != null) el.textContent = text;
    return el;
  }
  function validCover(path) {
    return typeof path === 'string' && /^images\/stories\/[a-zA-Z0-9_-]+\.(jpg|jpeg|png|webp|gif)$/i.test(path);
  }
  function cover(item) {
    var box = node('span', 'shelf-cover');
    box.appendChild(node('span', 'shelf-cover-placeholder', item.title));
    if (validCover(item.cover)) {
      var img = node('img');
      img.alt = item.title + '封面';
      img.loading = 'lazy';
      img.decoding = 'async';
      img.addEventListener('error', function() { img.remove(); });
      img.src = item.cover;
      box.appendChild(img);
    }
    return box;
  }
  function card(item) {
    var el = node('article', 'shelf-card');
    el.id = 'story-' + item.id;
    var button = node('button', 'shelf-card-button');
    button.type = 'button';
    button.id = 'story-button-' + item.id;
    button.setAttribute('aria-label', item.title + '，展开感想');
    button.setAttribute('aria-expanded', 'false');
    button.appendChild(cover(item));
    var title = node('span', 'shelf-title', item.title);
    button.appendChild(title);
    button.appendChild(node('span', 'shelf-excerpt', (item.recommendation || '').trim().split(/\n\s*\n|\n/)[0]));
    el.appendChild(button);
    return el;
  }
  function render(container, items, essays) {
    if (container._storiesObserver) container._storiesObserver.disconnect();
    container.getAnimations({subtree: true}).forEach(function(animation) { animation.cancel(); });
    container.replaceChildren();
    var cards = items.map(function(item, index) {
      var el = card(item);
      el.style.order = index * 2;
      container.appendChild(el);
      return el;
    });
    var panel = node('section', 'shelf-expanded');
    panel.id = container.id + '-detail';
    panel.setAttribute('role', 'region');
    panel.hidden = true;
    container.appendChild(panel);
    var active = -1;
    var motion = null;
    function panelState() {
      var style = getComputedStyle(panel);
      return {
        height: panel.getBoundingClientRect().height + 'px',
        opacity: style.opacity,
        paddingTop: style.paddingTop,
        paddingBottom: style.paddingBottom,
        borderTopWidth: style.borderTopWidth,
        marginBottom: style.marginBottom
      };
    }
    function animatePanel(previous, opening) {
      panel.inert = !opening;
      panel.setAttribute('aria-hidden', String(!opening));
      if (matchMedia('(prefers-reduced-motion: reduce)').matches || !panel.animate) {
        panel.hidden = !opening;
        return;
      }
      var collapsed = {
        height: '0px', opacity: 0, paddingTop: '0px', paddingBottom: '0px',
        borderTopWidth: '0px', marginBottom: '-' + getComputedStyle(container).rowGap
      };
      var target = opening ? panelState() : collapsed;
      panel.classList.add('is-animating');
      var animation = panel.animate([previous || collapsed, target], {
        duration: opening ? 320 : 220,
        easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'both'
      });
      motion = animation;
      animation.onfinish = function() {
        if (motion !== animation) return;
        panel.hidden = !opening;
        panel.classList.remove('is-animating');
        animation.cancel();
        motion = null;
      };
    }
    function placePanel() {
      if (active < 0) return;
      var columns = getComputedStyle(container).gridTemplateColumns.split(' ').length;
      var rowEnd = Math.min(items.length - 1, (Math.floor(active / columns) + 1) * columns - 1);
      panel.style.order = rowEnd * 2 + 1;
    }
    function select(index, returnFocus) {
      var previous = panel.hidden ? null : panelState();
      if (motion) { motion.cancel(); motion = null; }
      panel.classList.remove('is-animating');
      var switching = active >= 0 && active !== index;
      active = active === index ? -1 : index;
      cards.forEach(function(el, i) {
        var button = el.querySelector('button');
        button.setAttribute('aria-expanded', String(i === active));
        button.setAttribute('aria-label', items[i].title + (i === active ? '，收起感想' : '，展开感想'));
      });
      if (active < 0) {
        animatePanel(previous, false);
        if (returnFocus) cards[index].querySelector('button').focus({preventScroll: true});
        return;
      }
      panel.hidden = false;
      var item = items[active];
      panel.replaceChildren();
      panel.setAttribute('aria-labelledby', 'story-button-' + item.id);
      var heading = node('div', 'shelf-expanded-heading');
      heading.appendChild(node('h3', '', item.title));
      var close = node('button', 'shelf-close', '收起感想');
      close.type = 'button';
      close.addEventListener('click', function() { select(index, true); });
      heading.appendChild(close);
      panel.appendChild(heading);
      var recommendation = node('div', 'shelf-recommendation');
      (item.recommendation || '').split(/\r?\n\s*\r?\n/).forEach(function(paragraph) {
        recommendation.appendChild(node('p', '', paragraph));
      });
      panel.appendChild(recommendation);
      var details = [types[item.type] || ''];
      if (item.creator) details.push(item.creator);
      if (item.rating != null) details.push('我的评分 ' + item.rating + ' / 5');
      if (item.finished_on) details.push('看完于 ' + item.finished_on);
      panel.appendChild(node('p', 'shelf-meta', details.join(' · ')));
      var essay = (essays || []).find(function(e) {
        return e.slug === item.essay_slug && !e.hidden && !e.password_protected && !e.password;
      });
      if (essay && /^[a-z0-9-]+$/.test(essay.slug)) {
        var link = node('a', 'shelf-essay', '读我的感想 →');
        link.href = 'essays/' + essay.slug + '.html';
        panel.appendChild(link);
      }
      placePanel();
      if (previous && switching) previous.opacity = 0;
      animatePanel(previous, true);
    }
    cards.forEach(function(el, index) {
      var button = el.querySelector('button');
      button.setAttribute('aria-controls', panel.id);
      button.addEventListener('click', function() { select(index, false); });
    });
    container._storiesObserver = new ResizeObserver(placePanel);
    container._storiesObserver.observe(container);
  }
  async function load() {
    var response = await fetch('data/stories.json?v=' + Date.now());
    if (!response.ok) throw new Error('书架暂时无法加载');
    var items = await response.json();
    if (!Array.isArray(items)) throw new Error('书架数据格式异常');
    return items.filter(function(item) { return item && Number.isSafeInteger(item.id) && item.id > 0; });
  }
  async function initHome() {
    var section = document.getElementById('stories');
    if (!section) return;
    try {
      var items = await load();
      var essays = [];
      if (items.some(function(item) { return item.essay_slug; })) {
        essays = await fetch('data/essays_public.json?v=' + Date.now()).then(function(r) {
          return r.ok ? r.json() : null;
        }).then(function(data) { return data ? (Array.isArray(data) ? data : data.essays || []) : []; }).catch(function() { return []; });
      }
      render(document.getElementById('stories-list'), items, essays);
      section.hidden = items.length === 0;
      document.getElementById('stories-nav').hidden = items.length === 0;
    } catch (_) {
      section.hidden = true;
      document.getElementById('stories-nav').hidden = true;
    }
  }
  document.addEventListener('DOMContentLoaded', initHome);
  return {types: types, node: node, cover: cover, render: render, load: load};
})();
