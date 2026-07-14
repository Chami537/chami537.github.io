// Essay tag navigation state and shared taxonomy helpers.

let currentEssayTag = null;
let currentEssayChildTag = null;
let currentEssayTypeTag = null;
let essayDeleteTagMode = false;
var _essayTagOrder = [];

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
  tags.forEach(function(tag) {
    if (tag && out.indexOf(tag) < 0) out.push(tag);
  });
  return out;
}

function _orderedEssayTags(tags, preferred) {
  var known = [];
  var rest = [];
  (preferred || ESSAY_TECH_TOPICS.concat(ESSAY_TECH_TYPES)).forEach(function(tag) {
    if (tags.indexOf(tag) >= 0) known.push(tag);
  });
  tags.forEach(function(tag) {
    if (known.indexOf(tag) < 0) rest.push(tag);
  });
  return known.concat(rest.sort(function(a, b) { return a.localeCompare(b, 'zh-CN'); }));
}

function _setSelectValue(id, value, fallback) {
  var element = document.getElementById(id);
  var hasValue = Array.prototype.some.call(element.options, function(option) { return option.value === value; });
  element.value = hasValue ? value : fallback;
}

function _essayTechGroups(data) {
  var topicSet = new Set();
  var typeSet = new Set();
  (data || []).forEach(function(essay) {
    var tags = _essayTagParts(essay.tag);
    if (tags.indexOf('技术') < 0) return;
    tags.forEach(function(tag) {
      if (ESSAY_TECH_TYPES.indexOf(tag) >= 0) typeSet.add(tag);
      else if (tag !== '技术' && ESSAY_MAIN_TAGS.indexOf(tag) < 0) topicSet.add(tag);
    });
  });
  return {topicSet: topicSet, typeSet: typeSet};
}

function _essayAdminPrimaryTags(ordered, techTopicSet, techTypeSet) {
  var allTags = new Set(ordered);
  var primary = [];
  ESSAY_MAIN_TAGS.forEach(function(tag) {
    if (allTags.has(tag)) primary.push(tag);
  });
  ordered.forEach(function(tag) {
    if (primary.indexOf(tag) < 0 && !techTopicSet.has(tag) && !techTypeSet.has(tag)) primary.push(tag);
  });
  return primary;
}
