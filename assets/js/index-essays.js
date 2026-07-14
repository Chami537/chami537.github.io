// Main page essay filters and rendering.

var _essayData = [];
var _allTags = [];
var _essayPrimaryFilter = '';
var _essayTopicFilter = '';
var _essayTypeFilter = '';
var _essayPrimaryTags = ['技术', '生活', '摄影', '阅读', '感悟', '随笔'];
var _essayTechTopics = ['Obsidian', 'Kotlin', 'Shell', 'Git', 'LeetCode', 'Python', 'Flask', '前端', '安全'];
var _essayTechTypes = ['学习日志', '教程', '踩坑', '速查', '题解', '项目复盘'];

function _essayTagsFor(item) {
  return (item.tag || '').split(/[,，]/).map(function(t) { return t.trim(); }).filter(Boolean);
}

function _orderedEssayTags(tags, preferred) {
  var known = [];
  var rest = [];
  preferred.forEach(function(t) {
    if (tags.indexOf(t) >= 0) known.push(t);
  });
  tags.forEach(function(t) {
    if (known.indexOf(t) < 0) rest.push(t);
  });
  return known.concat(rest.sort(function(a, b) { return a.localeCompare(b, 'zh-CN'); }));
}

function _restartContentMotion(el) {
  if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  el.classList.remove('content-swap');
  void el.offsetWidth;
  el.classList.add('content-swap');
}

function _essayFilterSets() {
  var tags = new Set(_allTags);
  var techTopicSet = new Set();
  var techTypeSet = new Set();
  _essayData.forEach(function(e) {
    var essayTags = _essayTagsFor(e);
    if (essayTags.indexOf('技术') < 0) return;
    essayTags.forEach(function(t) {
      if (_essayTechTypes.indexOf(t) >= 0) techTypeSet.add(t);
      else if (t !== '技术' && _essayPrimaryTags.indexOf(t) < 0) techTopicSet.add(t);
    });
  });
  if (!tags.size) {
    _essayData.forEach(function(e) {
      _essayTagsFor(e).forEach(function(t) { tags.add(t); });
    });
  }
  var primary = [];
  _essayPrimaryTags.forEach(function(t) {
    if (tags.has(t)) primary.push(t);
  });
  tags.forEach(function(t) {
    if (primary.indexOf(t) < 0 && !techTopicSet.has(t) && !techTypeSet.has(t)) primary.push(t);
  });
  return {primary: primary, topics: techTopicSet, types: techTypeSet};
}

function _renderEssayPrimaryFilter(primary) {
  var html = '<button type="button" class="ef-chip' + (!_essayPrimaryFilter ? ' active' : '') + '" onclick="filterEssayPrimary(\'\')">置顶</button>';
  primary.forEach(function(t) {
    html += '<button type="button" class="ef-chip' + (_essayPrimaryFilter === t ? ' active' : '') + '" data-tag="' + htmlEncode(t) + '" onclick="filterEssayPrimary(this.getAttribute(\'data-tag\'))">' + htmlEncode(t) + '</button>';
  });
  document.getElementById('essay-tag-filter').innerHTML = html;
}

function _renderEssayTechFilter(techTopicSet, techTypeSet) {
  var topicEl = document.getElementById('essay-topic-filter');
  var typeEl = document.getElementById('essay-type-filter');
  if (!topicEl || !typeEl) return;
  if (_essayPrimaryFilter !== '技术') {
    _clearEssayTechFilters(topicEl, typeEl);
    return;
  }
  var techTopics = _orderedEssayTags(Array.from(techTopicSet), _essayTechTopics);
  var techTypes = _orderedEssayTags(Array.from(techTypeSet), _essayTechTypes);
  _renderEssayFilterGroup(topicEl, techTopics, '主题', _essayTopicFilter, 'filterEssayTopic');
  _renderEssayFilterGroup(typeEl, techTypes, '类型', _essayTypeFilter, 'filterEssayType');
}

function _clearEssayTechFilters(topicEl, typeEl) {
  _essayTopicFilter = '';
  _essayTypeFilter = '';
  [topicEl, typeEl].forEach(function(el) {
    el.style.display = 'none';
    el.innerHTML = '';
  });
}

function _renderEssayFilterGroup(el, tags, label, selected, handler) {
  if (!tags.length) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }
  var html = '<span class="ef-label">' + label + '</span><span class="ef-options"><button type="button" class="ef-chip' + (!selected ? ' active' : '') + '" onclick="' + handler + '(\'\')">全部</button>';
  tags.forEach(function(t) {
    html += '<button type="button" class="ef-chip' + (selected === t ? ' active' : '') + '" data-tag="' + htmlEncode(t) + '" onclick="' + handler + '(this.getAttribute(\'data-tag\'))">' + htmlEncode(t) + '</button>';
  });
  el.innerHTML = html + '</span>';
  el.style.display = 'flex';
}

function buildEssayFilter() {
  var sets = _essayFilterSets();
  _renderEssayPrimaryFilter(sets.primary);
  _renderEssayTechFilter(sets.topics, sets.types);
}

function filterEssayPrimary(tag) {
  _essayPrimaryFilter = tag;
  _essayTopicFilter = '';
  _essayTypeFilter = '';
  buildEssayFilter();
  renderEssayList();
}

function filterEssayTopic(tag) {
  _essayTopicFilter = tag;
  buildEssayFilter();
  renderEssayList();
}

function filterEssayType(tag) {
  _essayTypeFilter = tag;
  buildEssayFilter();
  renderEssayList();
}

function _filteredEssayData() {
  if (!_essayPrimaryFilter) return _essayData.filter(function(e) { return e.pinned === true; });
  return _essayData.filter(function(e) {
    var tags = _essayTagsFor(e);
    return tags.indexOf(_essayPrimaryFilter) >= 0 &&
      (!_essayTopicFilter || tags.indexOf(_essayTopicFilter) >= 0) &&
      (!_essayTypeFilter || tags.indexOf(_essayTypeFilter) >= 0);
  });
}

function _essayRowHtml(e) {
  var tagParam = '?tag=' + encodeURIComponent(_essayTopicFilter || _essayTypeFilter || _essayPrimaryFilter || '置顶');
  return '<a class="essay-row" href="essays/' + htmlEncode(e.slug) + '.html' + tagParam + '">' +
    '<div class="essay-left"><span class="essay-title">' + htmlEncode(e.title) +
    (e.password_protected ? ' <span class="essay-lock" title="需要密码">🔒</span>' : '') + '</span>' +
    (e.excerpt ? '<span class="essay-excerpt">' + htmlEncode(e.excerpt) + '</span>' : '') +
    '</div><div class="essay-right"><span class="essay-tag">' + htmlEncode(_essayTagDisplay(e)) +
    '</span><span class="essay-meta">' + (e.date_display || '') + ' · ' + (e.readTime || 1) + ' min</span>' +
    '<span class="essay-arr">→</span></div></a>';
}

function _essayOverflowHtml(hidden) {
  return hidden > 0 ? '<a class="essay-row" href="archive.html" style="justify-content:center;color:var(--muted);font-size:13px;text-decoration:none;">查看全部（' + hidden + ' 篇）→</a>' : '';
}

function renderEssayList() {
  var filtered = _filteredEssayData();
  var MAX = 5;
  var shown = filtered.slice(0, MAX);
  var html = shown.map(_essayRowHtml).join('') + _essayOverflowHtml(filtered.length - MAX);
  var listEl = document.getElementById('essays-list');
  listEl.innerHTML = html;
  listEl.classList.remove('skeleton-loading');
  _restartContentMotion(listEl);
}

function _essayTagDisplay(e) {
  var tags = _essayTagsFor(e);
  if (tags.indexOf('技术') < 0) return (e.tag || '').replace(/, ?/g, ' · ');
  var topic = tags.find(function(t) {
    return t !== '技术' && _essayPrimaryTags.indexOf(t) < 0 && _essayTechTypes.indexOf(t) < 0;
  });
  var type = tags.find(function(t) { return _essayTechTypes.indexOf(t) >= 0; });
  var left = topic ? '技术 · ' + topic : '技术';
  return type ? left + '    ' + type : left;
}
