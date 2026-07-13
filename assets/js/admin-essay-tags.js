// Essay taxonomy and tag navigation state.

// ═══ Tag system ═══
// 全局状态：记录当前激活的标签
let currentEssayTag = null;
let currentEssayChildTag = null;
let currentEssayTypeTag = null;
let essayDeleteTagMode = false;
var _essayTagOrder = [];

// 初始化标签库
function getTags() { return _tagLib('essay-tags', '["随笔","摄影","剪辑","骑行","投资"]'); }
function saveTags(tags) { _saveTagLib('essay-tags', tags); }

var ESSAY_MAIN_TAGS = ['随笔', '生活', '摄影', '阅读', '感悟', '技术'];
var ESSAY_TECH_TOPICS = ['Obsidian', 'Kotlin', 'Shell', 'Git', 'LeetCode', 'Python', 'Flask', '前端', '安全'];
var ESSAY_TECH_TYPES = ['学习日志', '教程', '踩坑', '速查', '题解', '项目复盘'];

function _essayTagParts(value) {
  return (value || '').split(/[,，]/).map(function(s) { return s.trim(); }).filter(Boolean);
}

function _uniqueEssayTags(tags) {
  var out = [];
  tags.forEach(function(t) {
    if (t && out.indexOf(t) < 0) out.push(t);
  });
  return out;
}

function _orderedEssayTags(tags, preferred) {
  var known = [];
  var rest = [];
  (preferred || ESSAY_TECH_TOPICS.concat(ESSAY_TECH_TYPES)).forEach(function(t) {
    if (tags.indexOf(t) >= 0) known.push(t);
  });
  tags.forEach(function(t) {
    if (known.indexOf(t) < 0) rest.push(t);
  });
  return known.concat(rest.sort(function(a, b) { return a.localeCompare(b, 'zh-CN'); }));
}

function _setSelectValue(id, value, fallback) {
  var el = document.getElementById(id);
  var has = Array.prototype.some.call(el.options, function(o) { return o.value === value; });
  el.value = has ? value : fallback;
}

function _essayTechGroups(data) {
  var topicSet = new Set();
  var typeSet = new Set();
  (data || []).forEach(function(e) {
    var tags = _essayTagParts(e.tag);
    if (tags.indexOf('技术') < 0) return;
    tags.forEach(function(t) {
      if (ESSAY_TECH_TYPES.indexOf(t) >= 0) typeSet.add(t);
      else if (t !== '技术' && ESSAY_MAIN_TAGS.indexOf(t) < 0) topicSet.add(t);
    });
  });
  return {topicSet: topicSet, typeSet: typeSet};
}

function _essayAdminPrimaryTags(ordered, techTopicSet, techTypeSet) {
  var allTags = new Set(ordered);
  var primary = [];
  ESSAY_MAIN_TAGS.forEach(function(t) {
    if (allTags.has(t)) primary.push(t);
  });
  ordered.forEach(function(t) {
    if (primary.indexOf(t) < 0 && !techTopicSet.has(t) && !techTypeSet.has(t)) primary.push(t);
  });
  return primary;
}

function renderEssayTaxonomy(tagValue) {
  var tags = _essayTagParts(tagValue);
  var mainTag = tags.find(function(t) { return ESSAY_MAIN_TAGS.indexOf(t) >= 0; });
  var category = tags.indexOf('技术') >= 0 ? '技术' : (mainTag || '随笔');
  _setSelectValue('essay-category', category, '随笔');

  var topic = '';
  var type = '';
  var extras = [];
  if (category === '技术') {
    type = tags.find(function(t) { return ESSAY_TECH_TYPES.indexOf(t) >= 0; }) || '';
    topic = tags.find(function(t) {
      return t !== '技术' && t !== type && ESSAY_MAIN_TAGS.indexOf(t) < 0 && ESSAY_TECH_TYPES.indexOf(t) < 0;
    }) || '';
    extras = tags.filter(function(t) {
      return t !== '技术' && t !== topic && t !== type;
    });
  } else {
    extras = tags.filter(function(t) { return t !== category; });
  }
  document.getElementById('essay-tech-topic').value = topic;
  document.getElementById('essay-tech-type').value = type;
  document.getElementById('essay-extra-tags').value = extras.join(', ');
  syncEssayTagFromTaxonomy();
}

function _defaultEssayTagForFilter(tag) {
  if (!tag) return '随笔';
  if (ESSAY_MAIN_TAGS.indexOf(tag) >= 0) return tag;
  var isKnownTechTag = ESSAY_TECH_TOPICS.indexOf(tag) >= 0 || ESSAY_TECH_TYPES.indexOf(tag) >= 0;
  var isExistingTechTag = (_essayAllData || []).some(function(e) {
    var tags = _essayTagParts(e.tag);
    return tags.indexOf('技术') >= 0 && tags.indexOf(tag) >= 0;
  });
  if (isKnownTechTag || isExistingTechTag) return '技术, ' + tag;
  return '随笔, ' + tag;
}

function _defaultEssayTagForCurrentFilter() {
  if (currentEssayTag === '技术') {
    return _uniqueEssayTags(['技术', currentEssayChildTag, currentEssayTypeTag]).join(', ');
  }
  return _defaultEssayTagForFilter(currentEssayTag);
}

function syncEssayTagFromTaxonomy() {
  var category = document.getElementById('essay-category').value || '随笔';
  var topic = document.getElementById('essay-tech-topic').value.trim();
  var type = document.getElementById('essay-tech-type').value;
  var extras = _essayTagParts(document.getElementById('essay-extra-tags').value);
  var tags = [category];
  if (category === '技术') {
    if (topic) tags.push(topic);
    if (type) tags.push(type);
  }
  tags = _uniqueEssayTags(tags.concat(extras));
  var value = tags.join(', ');
  document.getElementById('essay-tag').value = value;
  document.querySelector('#essay-form .taxonomy-grid').classList.toggle('is-tech', category === '技术');
  document.getElementById('essay-tag-display').textContent = value ? '将保存为: ' + value : '';
  return value;
}

function handleEssayCategoryChange() {
  var category = document.getElementById('essay-category').value || '随笔';
  if (category !== '技术') {
    document.getElementById('essay-tech-topic').value = '';
    document.getElementById('essay-tech-type').value = '';
  }
  syncEssayTagFromTaxonomy();
}

// ── Tag drag-to-reorder ──

var _tagDragSrc = null;
var _tagJustDragged = false;

function tagDragStart(e) {
  _tagDragSrc = e.currentTarget;
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', e.currentTarget.getAttribute('data-tag'));
}

function tagDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
}

async function tagDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  _tagJustDragged = true;
  setTimeout(function() { _tagJustDragged = false; }, 200);
  var src = _tagDragSrc;
  var dst = e.currentTarget;
  if (!src || !dst || src === dst) return;
  var srcTag = src.getAttribute('data-tag');
  var dstTag = dst.getAttribute('data-tag');
  if (!srcTag && !dstTag) return;
  var row = dst.closest('.essay-tag-row') || document;
  var chips = row.querySelectorAll('.tag-tab-btn');
  var ordered = [];
  chips.forEach(function(c) {
    var t = c.getAttribute('data-tag');
    if (t) ordered.push(t);
  });
  var srcIdx = ordered.indexOf(srcTag);
  var dstIdx = ordered.indexOf(dstTag);
  if (srcIdx < 0 || dstIdx < 0) return;
  ordered.splice(srcIdx, 1);
  ordered.splice(dstIdx, 0, srcTag);
  await saveTagOrder(_mergeVisibleTagOrder(ordered));
  if (row.id === 'essay-type-tabs') currentEssayTypeTag = ordered[Math.min(dstIdx, ordered.length - 1)] || currentEssayTypeTag;
  else if (row.id === 'essay-subtag-tabs') currentEssayChildTag = ordered[Math.min(dstIdx, ordered.length - 1)] || currentEssayChildTag;
  else currentEssayTag = ordered[Math.min(dstIdx, ordered.length - 1)] || currentEssayTag;
  window['essay' + 'Entry']();
}

async function saveTagOrder(order) {
  try { await api('PUT', '/api/tags/order', { order: order }); } catch(e) { toast('保存标签顺序失败', true); }
}

function _mergeVisibleTagOrder(visibleOrder) {
  var visibleSet = new Set(visibleOrder);
  var merged = [];
  var inserted = false;
  _essayTagOrder.forEach(function(t) {
    if (visibleSet.has(t)) {
      if (!inserted) {
        merged = merged.concat(visibleOrder);
        inserted = true;
      }
      return;
    }
    merged.push(t);
  });
  if (!inserted) merged = merged.concat(visibleOrder);
  return _uniqueEssayTags(merged);
}

function switchEssayTag(tag) {
  hidePanel('essay-form');
  hideEssayContentEditor();
  currentEssayTag = tag;
  currentEssayChildTag = null;
  currentEssayTypeTag = null;
  window['essay' + 'Entry']();
}

function switchEssayChildTag(tag) {
  hidePanel('essay-form');
  hideEssayContentEditor();
  currentEssayTag = '技术';
  currentEssayChildTag = tag || null;
  window['essay' + 'Entry']();
}

function switchEssayTypeTag(tag) {
  hidePanel('essay-form');
  hideEssayContentEditor();
  currentEssayTag = '技术';
  currentEssayTypeTag = tag || null;
  window['essay' + 'Entry']();
}

function promptNewTag() {
  _promptTag('essay-tags', '["随笔","摄影","剪辑","骑行","投资"]', switchEssayTag);
}

function toggleDeleteTagMode() {
  essayDeleteTagMode = _toggleDeleteTagMode('delete-tag-btn', essayDeleteTagMode, loadEssays);
}

function deleteTagFromTabs(tag) {
  if (!confirm('确定永久删除标签 "' + tag + '"？')) return;
  // Strip this tag from all essays that reference it, then remove from library
  var affected = (_essayAllData || []).filter(function(e) {
    var essayTags = (e.tag || '').split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
    return essayTags.indexOf(tag) >= 0;
  });
  var updates = affected.map(function(e) {
    var newTags = (e.tag || '').split(/[,，]/).map(function(s){return s.trim();}).filter(function(t) { return t !== tag; });
    if (newTags.length === 0) newTags = ['随笔'];
    return api('PUT', '/api/essays/' + e.slug, {
      slug: e.slug, title: e.title, tag: newTags.join(', '),
      date: e.date, epigraph: e.epigraph || '', excerpt: e.excerpt || ''
    });
  });
  Promise.all(updates).then(function() {
    var tags = getTags();
    var idx = tags.indexOf(tag);
    if (idx >= 0) { tags.splice(idx, 1); saveTags(tags); }
    if (currentEssayTag === tag) { currentEssayTag = null; }
    if (currentEssayChildTag === tag) { currentEssayChildTag = null; }
    if (currentEssayTypeTag === tag) { currentEssayTypeTag = null; }
    window['essay' + 'Entry']();
  }).catch(function(err) {
    toast('删除失败: ' + (err.message || '未知错误'), true);
    window['essay' + 'Entry']();
  });
}

function renderTagChips(selected) {
  var tags = getTags();
  var html = '';
  tags.forEach(function(t) {
    var active = (selected || '').split(/[,，]/).map(function(s){return s.trim();}).indexOf(t) >= 0;
    html += '<span class="tag-chip' + (active ? ' active' : '') + '" data-tag="' + esc(t) + '">' +
      '<span onclick="toggleTag(\'' + esc(t) + '\')">' + esc(t) + '</span>' +
      '</span>';
  });
  document.getElementById('tag-chips').innerHTML = html;
  document.getElementById('essay-tag-display').textContent = selected ? '已选: ' + selected : '';
}



function toggleTag(tag) {
  var cur = document.getElementById('essay-tag').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
  var idx = cur.indexOf(tag);
  if (idx >= 0) {
    if (cur.length <= 1) return; // must have at least one tag
    cur.splice(idx, 1);
  } else { cur.push(tag); }
  var val = cur.join(', ');
  document.getElementById('essay-tag').value = val;
  renderTagChips(val);
}

