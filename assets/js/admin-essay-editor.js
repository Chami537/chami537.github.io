// Essay metadata and Markdown editor.

function genSlug(title) {
  // Always use essay- prefix + random hex — robust against any title (Chinese, mixed script, emoji, etc.)
  return 'essay-' + Math.random().toString(16).slice(2, 10);
}


function showEssayForm() {
  showEntryForm({ formId: 'essay-form', editId: 'essay-edit-slug', title: '新建文章',
    fields: ['essay-title','essay-date','essay-readtime','essay-epigraph','essay-excerpt','essay-tech-topic','essay-extra-tags'] });
  var now = new Date();
  document.getElementById('essay-date').value = now.getFullYear() + '-' + pad2(now.getMonth()+1) + '-' + pad2(now.getDate());
  document.getElementById('essay-readtime').value = '4';
  let defaultTag = _defaultEssayTagForCurrentFilter();
  renderEssayTaxonomy(defaultTag);
}


async function editEssayMeta(slug) {  const form = document.getElementById('essay-form');
  if (form.style.display === 'block' && document.getElementById('essay-edit-slug').value === slug) {
    form.style.display = 'none'; return;
  }
  const data = await api('GET', '/api/essays');
  const e = data.find(x => x.slug === slug);
  if (!e) return;
  document.getElementById('essay-edit-slug').value = slug;
  document.getElementById('essay-title').value = e.title;
  document.getElementById('essay-tag').value = e.tag || '';
  document.getElementById('essay-date').value = e.date || '';
  document.getElementById('essay-readtime').value = e.readTime || 1;
  document.getElementById('essay-epigraph').value = e.epigraph || '';
  document.getElementById('essay-excerpt').value = e.excerpt || '';
  renderEssayTaxonomy(e.tag || '');
  document.getElementById('essay-form-title').textContent = '编辑元数据';
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
}

async function saveEssay() {
  try {
  var editSlug = document.getElementById('essay-edit-slug').value;
  var slug = editSlug || genSlug('');
  var item = {
    slug: slug,
    title: document.getElementById('essay-title').value,
    tag: syncEssayTagFromTaxonomy(),
    date: document.getElementById('essay-date').value,
    epigraph: document.getElementById('essay-epigraph').value,
    excerpt: document.getElementById('essay-excerpt').value,
  };    if (editSlug) {
      await api('PUT', '/api/essays/' + editSlug, item);
      toast('元数据已更新');
    } else {
      await api('POST', '/api/essays', item);
      toast('随笔已创建，HTML 文件已生成');
    }
    markClean();
    hidePanel('essay-form');
    window['essay' + 'Entry']();
  } catch(e) { toast(e.message, true); }
}

async function editEssayContent(slug) {
  const editor = document.getElementById('essay-content-editor');
  if (editor.style.display === 'block' && editor.dataset.slug === slug) {
    editor.style.display = 'none'; return;
  }
  // Autosave current essay before switching
  var oldSlug = editor.dataset.slug;
  if (oldSlug && oldSlug !== slug) {
    var md = document.getElementById('essay-content-md').value;
    if (md.trim()) localStorage.setItem('draft:' + oldSlug, md);
  }
  clearInterval(_autosaveInterval);
  editor.style.display = 'block';
  document.getElementById('essay-content-title').textContent = '— ' + slug;
  editor.dataset.slug = slug;
  try {
    const data = await api('GET', '/api/essays/' + slug + '/content');
    document.getElementById('essay-content-md').value = data.content || '';
    _updateWordCount();
    startAutosave(slug);
    checkDraft(slug);
  } catch(e) {
    document.getElementById('essay-content-md').value = '';
    toast('加载失败: ' + e.message, true);
  }
  editor.scrollIntoView({ behavior: 'smooth' });
}

function hideEssayContentEditor() {
  var slug = document.getElementById('essay-content-editor').dataset.slug;
  if (slug) localStorage.setItem('draft-time:' + slug, Date.now());
  clearInterval(_autosaveInterval);
  document.getElementById('essay-content-editor').style.display = 'none';
  document.getElementById('essay-preview').style.display = 'none';
}

// ═══ Editor: Tab + Shortcuts + Autosave + Drag-Drop ═══
function _wrapSelection(ta, before, after) {
  var s = ta.selectionStart, e = ta.selectionEnd;
  var sel = ta.value.slice(s, e);
  ta.value = ta.value.slice(0, s) + before + sel + after + ta.value.slice(e);
  var offset = before.length;
  if (sel.length) {
    ta.selectionStart = s + offset;
    ta.selectionEnd = e + offset;
  } else {
    ta.selectionStart = ta.selectionEnd = s + offset;
  }
}

function _prefixLines(ta, prefix) {
  var s = ta.selectionStart, e = ta.selectionEnd;
  var v = ta.value;
  while (s > 0 && v[s - 1] !== '\n') s--;
  while (e < v.length && v[e] !== '\n') e++;
  if (e < v.length) e++;
  var lines = v.slice(s, e).split('\n');
  if (lines.length > 1 && lines[lines.length - 1] === '') lines.pop();
  var result = lines.map(function(l) { return prefix + l; }).join('\n');
  if (v[e - 1] === '\n') result += '\n';
  ta.value = v.slice(0, s) + result + v.slice(e);
  ta.selectionStart = s;
  ta.selectionEnd = s + result.length;
}

function _essayBySlug(slug) {
  return (_essayAllData || []).find(function(e) { return e.slug === slug; }) || null;
}

function _techTemplateForEssay(essay) {
  var tags = _essayTagParts(essay && essay.tag);
  var topic = tags.find(function(t) {
    return t !== '技术' && ESSAY_MAIN_TAGS.indexOf(t) < 0 && ESSAY_TECH_TYPES.indexOf(t) < 0;
  }) || '这个主题';
  var type = tags.find(function(t) { return ESSAY_TECH_TYPES.indexOf(t) >= 0; }) || '学习日志';
  return [
    '## 我在学什么',
    '',
    '今天围绕 ' + topic + ' 解决一个具体问题。',
    '',
    '## 卡在哪里',
    '',
    '- ',
    '',
    '## 今天弄懂了什么',
    '',
    '- ',
    '',
    '## 可复用结论',
    '',
    '- ',
    '',
    '## 下次继续',
    '',
    '- ',
    '',
    '<!-- 技术主题: ' + topic + ' · 类型: ' + type + ' -->',
    ''
  ].join('\n');
}

function insertTechEssayTemplate() {
  var ta = document.getElementById('essay-content-md');
  var slug = document.getElementById('essay-content-editor').dataset.slug;
  var template = _techTemplateForEssay(_essayBySlug(slug));
  if (ta.value.trim() && !confirm('正文里已有内容，要在光标处插入技术模板吗？')) return;
  var start = ta.selectionStart || 0;
  var end = ta.selectionEnd || start;
  var prefix = start > 0 && ta.value[start - 1] !== '\n' ? '\n\n' : '';
  var suffix = end < ta.value.length && ta.value[end] !== '\n' ? '\n\n' : '';
  ta.value = ta.value.slice(0, start) + prefix + template + suffix + ta.value.slice(end);
  ta.focus();
  ta.selectionStart = ta.selectionEnd = start + prefix.length + template.length;
  _updateWordCount();
  markDirty();
}

function _updateWordCount() {
  var ta = document.getElementById('essay-content-md');
  var text = ta.value;
  var chars = text.length;
  var cjk = (text.match(/[\u4e00-\u9fff\u3400-\u4dbf]/g) || []).length;
  var words = (text.match(/[a-zA-Z]+/g) || []).length;
  var el = document.getElementById('essay-word-count');
  el.textContent = chars + ' 字符 · ' + (cjk + words) + ' 词 · ~' + Math.max(1, Math.round((cjk + words * 1.5) / 300)) + ' min';
}

document.addEventListener('keydown', function(e) {
  var ta = document.getElementById('essay-content-md');
  if (document.activeElement !== ta) return;
  // Tab → 2 spaces
  if (e.key === 'Tab') {
    e.preventDefault();
    var s = ta.selectionStart, v = ta.value;
    ta.value = v.slice(0, s) + '  ' + v.slice(ta.selectionEnd);
    ta.selectionStart = ta.selectionEnd = s + 2;
  }
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 's') { e.preventDefault(); saveEssayContent(); }
    if (e.key === 'b') { e.preventDefault(); _wrapSelection(ta, '**', '**'); }
    if (e.key === 'i') { e.preventDefault(); _wrapSelection(ta, '*', '*'); }
    if (e.key === 'k') { e.preventDefault(); _wrapSelection(ta, '[', '](url)'); }
    // Inline code Ctrl+`
    if (e.code === 'Backquote') { e.preventDefault(); _wrapSelection(ta, '`', '`'); }
    // Code block Ctrl+Shift+`
    if (e.code === 'Backquote' && e.shiftKey) {
      e.preventDefault();
      var s = ta.selectionStart, v = ta.value, sel = v.slice(s, ta.selectionEnd);
      var block = '\n```\n' + (sel || 'code') + '\n```\n';
      ta.value = v.slice(0, s) + block + v.slice(ta.selectionEnd);
      var pos = s + 5 + (sel ? 0 : 0);
      ta.selectionStart = ta.selectionEnd = sel ? s + block.length : pos;
    }
    // Ordered list Ctrl+Shift+7
    if (e.key === '7' && e.shiftKey) { e.preventDefault(); _prefixLines(ta, '1. '); }
    // Unordered list Ctrl+Shift+8
    if (e.key === '8' && e.shiftKey) { e.preventDefault(); _prefixLines(ta, '- '); }
  }
});

// Word count on input
document.getElementById('essay-content-md').addEventListener('input', _updateWordCount);

// Drag-and-drop image upload
(function() {
  var ta = document.getElementById('essay-content-md');
  ta.addEventListener('dragover', function(e) {
    if (e.dataTransfer.types && e.dataTransfer.types.indexOf('Files') >= 0) {
      e.preventDefault(); e.stopPropagation();
    }
  });
  ta.addEventListener('drop', async function(e) {
    var file = e.dataTransfer.files[0];
    if (!file || !file.type.startsWith('image/')) return;  // let browser handle text drag
    e.preventDefault(); e.stopPropagation();
    var fd = new FormData();
    var slug = document.getElementById('essay-content-editor').dataset.slug;
    if (slug) fd.append('slug', slug);
    fd.append('file', file);
    try {
      var result = await api('POST', '/api/essays/upload-image', fd);
      var url = result.url || '';
      var md = '![](' + (url.startsWith('/') ? url : '/' + url) + ')';
      var s = ta.selectionStart, end = ta.selectionEnd;
      ta.value = ta.value.slice(0, s) + md + ta.value.slice(end);
      ta.focus();
      ta.selectionStart = ta.selectionEnd = s + md.length;
      toast('图片已插入');
    } catch(ex) { toast(ex.message, true); }
  });
})();

var _autosaveInterval;
function startAutosave(slug) {
  clearInterval(_autosaveInterval);
  _autosaveInterval = setInterval(function() {
    var md = document.getElementById('essay-content-md').value;
    if (md.trim()) localStorage.setItem('draft:' + slug, md);
  }, 10000);
}

function checkDraft(slug) {
  var saved = localStorage.getItem('draft:' + slug);
  if (!saved) return;
  var cur = document.getElementById('essay-content-md').value;
  if (saved !== cur && confirm('发现本地草稿（' + new Date(+localStorage.getItem('draft-time:' + slug) || Date.now()).toLocaleString() + '），是否恢复？')) {
    document.getElementById('essay-content-md').value = saved;
    localStorage.removeItem('draft:' + slug);
    localStorage.removeItem('draft-time:' + slug);
  }
}

function clearDraft(slug) {
  localStorage.removeItem('draft:' + slug);
  localStorage.removeItem('draft-time:' + slug);
}

async function saveEssayContent() {
  try {
  const slug = document.getElementById('essay-content-editor').dataset.slug;
  const md = document.getElementById('essay-content-md').value;    await api('PUT', '/api/essays/' + slug + '/content', { content: md });
    markClean();
    clearDraft(slug);
    toast('正文已保存');
  } catch(e) { toast(e.message, true); }
}

async function uploadEssayImage() {
  try {
  var file = document.getElementById('essay-img-input').files[0];
  if (!file) return;
  var fd = new FormData();
  var slug = document.getElementById('essay-edit-slug').value;
  if (slug) fd.append('slug', slug);
  fd.append('file', file);    var result = await api('POST', '/api/essays/upload-image', fd);
    var url = result.url || '';
    var md = '![](' + (url.startsWith('/') ? url : '/' + url) + ')';
    var ta = document.getElementById('essay-content-md');
    var start = ta.selectionStart, end = ta.selectionEnd;
    ta.value = ta.value.slice(0, start) + md + ta.value.slice(end);
    ta.focus();
    ta.selectionStart = ta.selectionEnd = start + md.length;
    toast('图片已插入');
  } catch(e) { toast(e.message, true); }
  document.getElementById('essay-img-input').value = '';
}

async function previewEssayContent() {
  try {
  var panel = document.getElementById('essay-preview');
  if (panel.style.display === 'block') {
    panel.style.display = 'none';
    return;
  }
  const md = document.getElementById('essay-content-md').value;    const data = await api('POST', '/api/essays/x/html', { md: md });
    panel.innerHTML = data.html;
  window._renderAdminEditor(panel);
    panel.style.display = 'block';
  } catch(e) { toast(e.message, true); }
}

async function deleteEssay(slug) {  const confirmed = await confirmDialog('确定删除随笔 "' + slug + '"？这将同时删除 HTML 文件。');
  if (!confirmed) return;
  await api('DELETE', '/api/essays/' + slug);
  // Close any open panels for this essay
  if (document.getElementById('essay-edit-slug').value === slug) hidePanel('essay-form');
  if (document.getElementById('essay-content-editor').dataset.slug === slug) hideEssayContentEditor();
  clearDraft(slug);
  window['essay' + 'Entry']();
  toast('随笔已删除');
}

