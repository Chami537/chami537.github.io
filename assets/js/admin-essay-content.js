// Essay content editor lifecycle, drafts, saving, and deletion.

var _autosaveInterval;

async function editEssayContent(slug) {
  var editor = document.getElementById('essay-content-editor');
  if (editor.style.display === 'block' && editor.dataset.slug === slug) {
    editor.style.display = 'none';
    return;
  }
  var oldSlug = editor.dataset.slug;
  if (oldSlug && oldSlug !== slug) {
    var oldMarkdown = document.getElementById('essay-content-md').value;
    if (oldMarkdown.trim()) localStorage.setItem('draft:' + oldSlug, oldMarkdown);
  }
  clearInterval(_autosaveInterval);
  editor.style.display = 'block';
  editor.dataset.slug = slug;
  document.getElementById('essay-content-title').textContent = '— ' + slug;
  try {
    var data = await api('GET', '/api/essays/' + slug + '/content');
    document.getElementById('essay-content-md').value = data.content || '';
    _updateWordCount();
    startAutosave(slug);
    checkDraft(slug);
  } catch (error) {
    document.getElementById('essay-content-md').value = '';
    toast('加载失败: ' + error.message, true);
  }
  editor.scrollIntoView({behavior: 'smooth'});
}

function hideEssayContentEditor() {
  var editor = document.getElementById('essay-content-editor');
  var slug = editor.dataset.slug;
  if (slug) localStorage.setItem('draft-time:' + slug, Date.now());
  clearInterval(_autosaveInterval);
  editor.style.display = 'none';
  document.getElementById('essay-preview').style.display = 'none';
}

function startAutosave(slug) {
  clearInterval(_autosaveInterval);
  _autosaveInterval = setInterval(function() {
    var markdown = document.getElementById('essay-content-md').value;
    if (markdown.trim()) localStorage.setItem('draft:' + slug, markdown);
  }, 10000);
}

function checkDraft(slug) {
  var saved = localStorage.getItem('draft:' + slug);
  if (!saved) return;
  var current = document.getElementById('essay-content-md').value;
  var savedAt = new Date(+localStorage.getItem('draft-time:' + slug) || Date.now()).toLocaleString();
  if (saved !== current && confirm('发现本地草稿（' + savedAt + '），是否恢复？')) {
    document.getElementById('essay-content-md').value = saved;
    clearDraft(slug);
  }
}

function clearDraft(slug) {
  localStorage.removeItem('draft:' + slug);
  localStorage.removeItem('draft-time:' + slug);
}

async function saveEssayContent() {
  try {
    var slug = document.getElementById('essay-content-editor').dataset.slug;
    var markdown = document.getElementById('essay-content-md').value;
    await api('PUT', '/api/essays/' + slug + '/content', {content: markdown});
    markClean();
    clearDraft(slug);
    toast('正文已保存');
  } catch (error) {
    toast(error.message, true);
  }
}

async function deleteEssay(slug) {
  var confirmed = await confirmDialog('确定删除随笔 "' + slug + '"？这将同时删除 HTML 文件。');
  if (!confirmed) return;
  await api('DELETE', '/api/essays/' + slug);
  if (document.getElementById('essay-edit-slug').value === slug) hidePanel('essay-form');
  if (document.getElementById('essay-content-editor').dataset.slug === slug) hideEssayContentEditor();
  clearDraft(slug);
  window['essay' + 'Entry']();
  toast('随笔已删除');
}
