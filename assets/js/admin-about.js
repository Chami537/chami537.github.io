// About profile, avatar, tag library, and editor.

async function loadAbout() {
  try {
    var data = await api('GET', '/api/about');
    document.getElementById('about-content').value = data.content || '';
    document.getElementById('about-avatar-preview').src = data.avatar || '';
    document.getElementById('about-tags').value = (data.tags || []).join(', ');
    renderAboutTagChips();
  } catch (error) {
    toast(error.message, true);
  }
}

async function uploadAvatar() {
  try {
    var file = document.getElementById('about-avatar-file').files[0];
    if (!file) return;
    var form = new FormData();
    form.append('file', file);
    var result = await api('POST', '/api/about/upload-avatar', form);
    document.getElementById('about-avatar-preview').src = result.url;
    document.getElementById('about-avatar-preview').dataset.path = result.url;
    toast('头像已上传');
  } catch (error) {
    toast(error.message, true);
  }
}

async function saveAbout() {
  try {
    var selected = document.getElementById('about-tags').value
      .split(/[,，]/).map(function(tag) { return tag.trim(); }).filter(Boolean);
    await api('PUT', '/api/about', {
      content: document.getElementById('about-content').value,
      tags: getAboutTags().filter(function(tag) { return selected.indexOf(tag) >= 0; }),
      avatar: document.getElementById('about-avatar-preview').dataset.path ||
        document.getElementById('about-avatar-preview').src.split('/').slice(-2).join('/')
    });
    markClean();
    toast('简介已保存');
  } catch (error) {
    toast(error.message, true);
  }
}

window['about' + 'Entry'] = saveAbout;

// ═══ About tag system ═══
function getAboutTags() {
  var stored = _tagLib('about-tags', '["CS STUDENT","PHOTOGRAPHER","SHENZHEN"]');
  var cur = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
  cur.forEach(function(t) { if (stored.indexOf(t) < 0) stored.push(t); });
  return stored;
}
function saveAboutTags(tags) { _saveTagLib('about-tags', tags); }

var _aboutEditingTag = null;

function renderAboutTagChips() {
  var tags = getAboutTags();
  var selected = document.getElementById('about-tags').value;
  var selList = selected ? selected.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean) : [];
  var html = '';
  tags.forEach(function(t, i) {
    var active = selList.indexOf(t) >= 0;
    html += '<span class="tag-chip' + (active ? ' active' : '') + '" data-tag="' + esc(t) + '" data-idx="' + i + '" draggable="true"' +
      ' ondragstart="aboutDragStart(event,' + i + ')" ondragover="aboutDragOver(event)" ondrop="aboutDrop(event,' + i + ')" ondragend="aboutDragEnd(event)">' +
      '<span onclick="editAboutChip(\'' + esc(t) + '\')">' + esc(t) + '</span>' +
      '<span class="tag-del" onclick="event.stopPropagation();deleteAboutTag(\'' + esc(t) + '\')" title="删除标签">×</span>' +
      '</span>';
  });
  document.getElementById('about-tag-chips').innerHTML = html;
}

function editAboutChip(tag) {
  _aboutEditingTag = tag;
  var input = document.getElementById('about-new-tag');
  input.value = tag;
  input.focus();
  input.select();
}

function aboutDragStart(e, idx) { _dragStart(e, idx); }
function aboutDragOver(e) { _dragOver(e); }

function aboutDrop(e, targetIdx) {
  e.preventDefault();
  var fromIdx = _dragState.idx;
  if (fromIdx < 0 || fromIdx === targetIdx) return;
  var tags = getAboutTags();
  var moved = tags.splice(fromIdx, 1)[0];
  tags.splice(targetIdx, 0, moved);
  saveAboutTags(tags);
  _dragState.idx = -1;
  renderAboutTagChips();
  window['about' + 'Entry']();
}

function aboutDragEnd(e) { _dragEnd(e); }

function deleteAboutTag(tag) {
  var tags = getAboutTags();
  var idx_t = tags.indexOf(tag);
  if (idx_t >= 0) { tags.splice(idx_t, 1); saveAboutTags(tags); }
  var cur = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
  var idx_c = cur.indexOf(tag);
  if (idx_c >= 0) { cur.splice(idx_c, 1); document.getElementById('about-tags').value = cur.join(', '); }
  renderAboutTagChips();
}

function toggleAboutTag(tag) {
  var cur = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
  var idx = cur.indexOf(tag);
  if (idx >= 0) { cur.splice(idx, 1); } else { cur.push(tag); }
  document.getElementById('about-tags').value = cur.join(', ');
  renderAboutTagChips();
}

function addAboutCustomTag() {
  var input = document.getElementById('about-new-tag');
  var tag = input.value.trim();
  if (!tag) return;
  var tags = getAboutTags();
  // If editing an existing tag (rename)
  if (_aboutEditingTag && tags.indexOf(_aboutEditingTag) >= 0 && tag !== _aboutEditingTag) {
    var idx = tags.indexOf(_aboutEditingTag);
    tags[idx] = tag;
    // Also update hidden input selection
    var cur = document.getElementById('about-tags').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean);
    var ci = cur.indexOf(_aboutEditingTag);
    if (ci >= 0) { cur[ci] = tag; document.getElementById('about-tags').value = cur.join(', '); }
    saveAboutTags(tags);
    _aboutEditingTag = null;
    input.value = '';
    renderAboutTagChips();
    return;
  }
  _aboutEditingTag = null;
  if (tags.indexOf(tag) < 0) { tags.push(tag); saveAboutTags(tags); }
  input.value = '';
  renderAboutTagChips();
  toggleAboutTag(tag);
}
