// Build an interactive table of contents from Markdown h1/h2 headings.

(function() {
  function headingId(text, index) {
    var slug = String(text || '').trim().toLowerCase()
      .replace(/[^\w\u3400-\u9fff\s-]/g, '')
      .trim().replace(/[\s_-]+/g, '-');
    return slug ? 'heading-' + slug : 'heading-' + (index + 1);
  }

  function setGroupState(button, list, expanded, animate) {
    if (!animate) {
      list.hidden = !expanded;
      list.style.maxHeight = expanded ? 'none' : '0px';
      list.style.opacity = expanded ? '1' : '0';
    } else if (expanded) {
      list.hidden = false;
      list.style.maxHeight = '0px';
      list.style.opacity = '0';
      void list.offsetHeight;
      requestAnimationFrame(function() {
        list.style.maxHeight = list.scrollHeight + 'px';
        list.style.opacity = '1';
      });
    } else {
      list.style.maxHeight = list.scrollHeight + 'px';
      list.hidden = true;
      void list.offsetHeight;
      requestAnimationFrame(function() {
        list.style.maxHeight = '0px';
        list.style.opacity = '0';
      });
    }
    button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    button.setAttribute('aria-label', expanded ? '收缩此章节' : '展开此章节');
    button.textContent = expanded ? '−' : '+';
  }

  function makeLink(heading) {
    var link = document.createElement('a');
    link.href = '#' + heading.id;
    link.textContent = heading.textContent.trim();
    link.addEventListener('click', function(event) {
      event.preventDefault();
      history.replaceState(null, '', '#' + heading.id);
      heading.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
    return link;
  }

  function watchActiveHeading(root, linksByHeading) {
    if (root._essayTocObserver) root._essayTocObserver.disconnect();
    var headings = Array.from(linksByHeading.keys());
    if (!headings.length) return;
    function activate(heading) {
      linksByHeading.forEach(function(link) { link.classList.remove('is-active'); });
      var link = linksByHeading.get(heading);
      if (link) link.classList.add('is-active');
    }
    activate(headings[0]);
    root._essayTocObserver = new IntersectionObserver(function(entries) {
      var visible = entries.filter(function(entry) { return entry.isIntersecting; });
      if (visible.length) activate(visible.sort(function(a, b) {
        return a.boundingClientRect.top - b.boundingClientRect.top;
      })[0].target);
    }, { rootMargin: '-112px 0px -65% 0px', threshold: 0 });
    headings.forEach(function(heading) { root._essayTocObserver.observe(heading); });
  }

  function buildEssayToc(root) {
    root = root || document.querySelector('.essay-body');
    var toc = document.getElementById('essay-toc');
    var list = document.getElementById('essay-toc-list');
    if (!root || !toc || !list) return;

    var headings = Array.from(root.querySelectorAll('h1, h2'));
    list.replaceChildren();
    var usedIds = new Set();
    var currentGroup = null;
    var groupLists = [];
    var linksByHeading = new Map();

    headings.forEach(function(heading, index) {
      var baseId = heading.id || headingId(heading.textContent, index);
      var id = baseId;
      var suffix = 2;
      while (usedIds.has(id) || (document.getElementById(id) && document.getElementById(id) !== heading)) {
        id = baseId + '-' + suffix++;
      }
      heading.id = id;
      heading.classList.add('essay-toc-heading');
      usedIds.add(id);

      if (heading.tagName.toLowerCase() === 'h1') {
        var item = document.createElement('li');
        item.className = 'essay-toc-item essay-toc-h1';
        var row = document.createElement('div');
        row.className = 'essay-toc-row';
        var sublist = document.createElement('ul');
        sublist.className = 'essay-toc-sublist';
        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'essay-toc-toggle';
        toggle.setAttribute('aria-label', '收缩此章节');
        toggle.addEventListener('click', function() {
          var expanded = list.hidden ? true : sublist.hidden;
          setGroupState(toggle, sublist, expanded, true);
        });
        var h1Link = makeLink(heading);
        linksByHeading.set(heading, h1Link);
        row.append(toggle, h1Link);
        item.appendChild(row);
        item.appendChild(sublist);
        list.appendChild(item);
        currentGroup = sublist;
        groupLists.push({button: toggle, list: sublist});
      } else {
        var target = currentGroup || list;
        var item = document.createElement('li');
        item.className = 'essay-toc-item essay-toc-h2';
        var h2Link = makeLink(heading);
        linksByHeading.set(heading, h2Link);
        item.appendChild(h2Link);
        target.appendChild(item);
      }
    });

    toc.hidden = headings.length === 0;
    if (!headings.length) return;
    groupLists.forEach(function(group) { setGroupState(group.button, group.list, true, false); });
    watchActiveHeading(root, linksByHeading);

    if (!toc._essayTocToggleReady) {
      var summary = toc.querySelector('summary');
      var nav = toc.querySelector('nav');
      summary.addEventListener('click', function(event) {
        event.preventDefault();
        if (toc._essayTocAnimating) return;
        toc._essayTocAnimating = true;
        if (toc.open) {
          nav.style.maxHeight = nav.scrollHeight + 'px';
          nav.style.opacity = '1';
          void nav.offsetHeight;
          requestAnimationFrame(function() {
            nav.style.maxHeight = '0px';
            nav.style.opacity = '0';
          });
          nav.addEventListener('transitionend', function close(event) {
            if (event.propertyName !== 'max-height') return;
            toc.open = false;
            nav.style.maxHeight = '0px';
            nav.style.opacity = '0';
            toc._essayTocAnimating = false;
            nav.removeEventListener('transitionend', close);
          });
        } else {
          toc.open = true;
          nav.style.maxHeight = '0px';
          nav.style.opacity = '0';
          void nav.offsetHeight;
          requestAnimationFrame(function() {
            nav.style.maxHeight = nav.scrollHeight + 'px';
            nav.style.opacity = '1';
          });
          nav.addEventListener('transitionend', function open(event) {
            if (event.propertyName !== 'max-height') return;
            nav.style.maxHeight = '';
            nav.style.opacity = '';
            toc._essayTocAnimating = false;
            nav.removeEventListener('transitionend', open);
          });
        }
      });
      toc._essayTocToggleReady = true;
    }

  }

  window.buildEssayToc = buildEssayToc;
  // This script is loaded after the article and TOC markup. Build immediately
  // instead of waiting for parser-blocking CDN scripts at the end of the page.
  buildEssayToc();
})();
