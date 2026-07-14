// Essay tag filters, deletion, and editor chips.

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
  var affected = (_essayAllData || []).filter(function(essay) {
    return _essayTagParts(essay.tag).indexOf(tag) >= 0;
  });
  var updates = affected.map(function(essay) {
    var newTags = _essayTagParts(essay.tag).filter(function(item) { return item !== tag; });
    if (newTags.length === 0) newTags = ['随笔'];
    return api('PUT', '/api/essays/' + essay.slug, {
      slug: essay.slug,
      title: essay.title,
      tag: newTags.join(', '),
      date: essay.date,
      epigraph: essay.epigraph || '',
      excerpt: essay.excerpt || ''
    });
  });
  Promise.all(updates).then(function() {
    var tags = getTags();
    var index = tags.indexOf(tag);
    if (index >= 0) {
      tags.splice(index, 1);
      saveTags(tags);
    }
    if (currentEssayTag === tag) currentEssayTag = null;
    if (currentEssayChildTag === tag) currentEssayChildTag = null;
    if (currentEssayTypeTag === tag) currentEssayTypeTag = null;
    window['essay' + 'Entry']();
  }).catch(function(error) {
    toast('删除失败: ' + (error.message || '未知错误'), true);
    window['essay' + 'Entry']();
  });
}

function renderTagChips(selected) {
  var html = '';
  getTags().forEach(function(tag) {
    var active = _essayTagParts(selected).indexOf(tag) >= 0;
    html += '<span class="tag-chip' + (active ? ' active' : '') + '" data-tag="' + esc(tag) + '">' +
      '<span onclick="toggleTag(\'' + esc(tag) + '\')">' + esc(tag) + '</span>' +
      '</span>';
  });
  document.getElementById('tag-chips').innerHTML = html;
  document.getElementById('essay-tag-display').textContent = selected ? '已选: ' + selected : '';
}

function toggleTag(tag) {
  var current = _essayTagParts(document.getElementById('essay-tag').value);
  var index = current.indexOf(tag);
  if (index >= 0) {
    if (current.length <= 1) return;
    current.splice(index, 1);
  } else {
    current.push(tag);
  }
  var value = current.join(', ');
  document.getElementById('essay-tag').value = value;
  renderTagChips(value);
}
