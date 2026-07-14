// Structured essay category form and tag serialization.

function renderEssayTaxonomy(tagValue) {
  var tags = _essayTagParts(tagValue);
  var mainTag = tags.find(function(tag) { return ESSAY_MAIN_TAGS.indexOf(tag) >= 0; });
  var category = tags.indexOf('技术') >= 0 ? '技术' : (mainTag || '随笔');
  _setSelectValue('essay-category', category, '随笔');

  var topic = '';
  var type = '';
  var extras = [];
  if (category === '技术') {
    type = tags.find(function(tag) { return ESSAY_TECH_TYPES.indexOf(tag) >= 0; }) || '';
    topic = tags.find(function(tag) {
      return tag !== '技术' && tag !== type && ESSAY_MAIN_TAGS.indexOf(tag) < 0 && ESSAY_TECH_TYPES.indexOf(tag) < 0;
    }) || '';
    extras = tags.filter(function(tag) {
      return tag !== '技术' && tag !== topic && tag !== type;
    });
  } else {
    extras = tags.filter(function(tag) { return tag !== category; });
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
  var isExistingTechTag = (_essayAllData || []).some(function(essay) {
    var tags = _essayTagParts(essay.tag);
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
