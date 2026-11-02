// Stories CRUD uses the existing admin transport, confirmation and dirty-state helpers.
var _stories = [];
var _storyEssays = [];
var _storyBusy = false;
var _storyCoverPreviewURL = null;

function storyField(name) { return document.getElementById('story-' + name); }
function storyText(tag, text) { var el = document.createElement(tag); el.textContent = text; return el; }
function storyPublicEssay(e) { return !e.hidden && !e.password_set && !e.password_protected && !e.password; }

async function loadStories() {
  try {
    var data = await Promise.all([api('GET', '/api/stories'), api('GET', '/api/essays')]);
    _stories = data[0];
    _storyEssays = data[1].filter(storyPublicEssay);
    renderAdminStories();
  } catch (e) { toast(e.message, true); }
}
function renderAdminStories() {
  var list = document.getElementById('stories-admin-list');
  list.replaceChildren();
  if (!_stories.length) list.appendChild(storyText('p', '还没有收录作品，添加第一部喜欢的故事吧。'));
  _stories.forEach(function(item, index) {
    var card = document.createElement('div'); card.className = 'card stories-admin-card';
    var cover = document.createElement('div'); cover.className = 'stories-admin-cover';
    if (/^images\/stories\/[a-zA-Z0-9_-]+\.(jpg|jpeg|png|webp|gif)$/i.test(item.cover || '')) {
      var img = document.createElement('img'); img.src = item.cover; img.alt = item.title; cover.appendChild(img);
    } else cover.textContent = item.title;
    card.appendChild(cover);
    var content = document.createElement('div'); content.className = 'stories-admin-content';
    content.appendChild(storyText('h3', item.title));
    var type = {movie:'电影', series:'电视剧', novel:'小说'}[item.type];
    content.appendChild(storyText('p', type + (item.favorite ? ' · ★ 最喜欢' : '')));
    var summary = storyText('p', item.recommendation); summary.className = 'stories-admin-summary'; content.appendChild(summary);
    if (item.essay_slug && !_storyEssays.some(function(e) { return e.slug === item.essay_slug; })) {
      var warning = storyText('p', '关联随笔已不可公开访问，公开书架将不显示链接；请编辑重新选择。');
      warning.className = 'stories-warning'; content.appendChild(warning);
    }
    var actions = document.createElement('div'); actions.className = 'card-actions';
    [['上移', function() { moveStory(index, -1); }, index === 0],
      ['下移', function() { moveStory(index, 1); }, index === _stories.length - 1],
      ['编辑', function() { editStory(item.id); }, false],
      ['删除', function() { deleteStory(item.id); }, false]].forEach(function(action) {
      var button = storyText('button', action[0]); button.type = 'button';
      button.className = 'btn btn-sm' + (action[0] === '删除' ? ' btn-danger' : '');
      button.disabled = action[2]; button.setAttribute('aria-label', action[0] + ' ' + item.title);
      button.addEventListener('click', action[1]); actions.appendChild(button);
    });
    content.appendChild(actions); card.appendChild(content); list.appendChild(card);
  });
}
function fillStoryEssays(selected) {
  var select = storyField('essay_slug');
  select.replaceChildren(new Option('不关联随笔', ''));
  _storyEssays.forEach(function(e) { select.add(new Option(e.title, e.slug)); });
  select.value = _storyEssays.some(function(e) { return e.slug === selected; }) ? selected : '';
}
function openStoryForm(item) {
  if (_storyBusy) return;
  var form = document.getElementById('story-form');
  form.reset();
  ['id','title','creator','cover','recommendation','rating','finished_on'].forEach(function(key) {
    storyField(key).value = item[key] == null ? '' : item[key];
  });
  storyField('type').value = item.type || 'movie';
  ['favorite'].forEach(function(key) { storyField(key).checked = !!item[key]; });
  fillStoryEssays(item.essay_slug);
  document.getElementById('story-form-title').textContent = item.id ? '编辑作品' : '添加作品';
  form.style.display = 'block';
  previewStoryCover();
  form.scrollIntoView({behavior:'smooth', block:'start'});
  storyField('title').focus({preventScroll:true});
}
function showStoryForm() { openStoryForm({}); }
function editStory(id) { var item = _stories.find(function(s) { return s.id === id; }); if (item) openStoryForm(item); }
function previewStoryCover() {
  if (_storyCoverPreviewURL) { URL.revokeObjectURL(_storyCoverPreviewURL); _storyCoverPreviewURL = null; }
  var preview = storyField('cover-preview');
  preview.hidden = !storyField('cover').value;
  if (!preview.hidden) preview.src = storyField('cover').value;
  else preview.removeAttribute('src');
}
function previewSelectedStoryCover() {
  previewStoryCover();
  var file = storyField('file').files[0];
  if (!file) return;
  _storyCoverPreviewURL = URL.createObjectURL(file);
  storyField('cover-preview').src = _storyCoverPreviewURL;
  storyField('cover-preview').hidden = false;
}
async function saveStory(event) {
  event.preventDefault();
  if (_storyBusy) return;
  _storyBusy = true;
  var form = document.getElementById('story-form');
  var saveButton = document.getElementById('story-save'); saveButton.disabled = true;
  // Prevent edits or switching records while an upload/save is in flight.
  var controls = Array.from(form.querySelectorAll('input,textarea,select,button'));
  controls.forEach(function(el) { el.disabled = true; });
  try {
    var file = storyField('file').files[0];
    if (file) {
      var fd = new FormData(); fd.append('file', file);
      var uploaded = await api('POST', '/api/stories/upload-cover', fd);
      storyField('cover').value = uploaded.cover;
      storyField('file').value = '';
      previewStoryCover();
    }
    var item = {};
    ['title','creator','cover','recommendation','type','finished_on','essay_slug'].forEach(function(key) { item[key] = storyField(key).value; });
    ['favorite'].forEach(function(key) { item[key] = storyField(key).checked; });
    item.rating = storyField('rating').value === '' ? null : Number(storyField('rating').value);
    var id = storyField('id').value;
    var previous = _stories.find(function(s) { return String(s.id) === id; });
    item.featured = previous ? !!previous.featured : false; // Preserve legacy metadata; all stories are displayed.
    await api(id ? 'PUT' : 'POST', '/api/stories' + (id ? '/' + id : ''), item);
    markClean(); hidePanel('story-form'); await loadStories(); toast('作品已保存');
  } catch (e) { toast(e.message, true); }
  finally { _storyBusy = false; controls.forEach(function(el) { el.disabled = false; }); }
}
async function moveStory(index, offset) {
  if (_storyBusy) return;
  _storyBusy = true;
  try {
    var ids = _stories.map(function(s) { return s.id; });
    var moved = ids[index]; ids[index] = ids[index + offset]; ids[index + offset] = moved;
    await api('PUT', '/api/stories/order', {order:ids}); await loadStories();
  } catch (e) { toast(e.message, true); }
  finally { _storyBusy = false; }
}
async function deleteStory(id) {
  if (_storyBusy || !await confirmDialog('确定删除这部作品？封面文件将保留。')) return;
  _storyBusy = true;
  try {
    await api('DELETE', '/api/stories/' + id);
    if (String(id) === storyField('id').value) hidePanel('story-form');
    await loadStories(); toast('作品已删除');
  } catch (e) { toast(e.message, true); }
  finally { _storyBusy = false; }
}
onAdminDataReset(function() { _stories = []; _storyEssays = []; hidePanel('story-form'); });
