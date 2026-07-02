// ═══════════════════════════════════
// Essays
// ═══════════════════════════════════
async function loadEssays() {
  try {
    const data = await api('GET', '/api/essays');
    _essayAllData = data;

    // Load saved tag order from server; merge any new essay tags at end
    let ordered = [];
    try { ordered = await api('GET', '/api/tags/order'); } catch(e) {}
    data.forEach(e => {
      if (e.tag) {
        e.tag.split(/[,，]/).map(function(s) { return s.trim(); }).filter(Boolean).forEach(function(pt) {
          if (!ordered.includes(pt)) ordered.push(pt);
        });
      }
    });

    if (!currentEssayTag && ordered.length > 0) {
      currentEssayTag = ordered[0];
    }

    let tabsHtml = '';
    ordered.forEach(tag => {
      let isActive = tag === currentEssayTag;
      if (essayDeleteTagMode) {
        tabsHtml += '<span class="tag-tab-btn' + (isActive ? ' active' : '') + '" style="display:inline-flex;align-items:center;gap:4px">' +
          '<span onclick="switchEssayTag(\'' + esc(tag) + '\')" style="cursor:pointer;">' + esc(tag) + '</span>' +
          '<span onclick="event.stopPropagation();deleteTagFromTabs(\'' + esc(tag) + '\')" class="tag-tab-del" title="删除标签">\u00D7</span>' +
          '</span>';
      } else {
        tabsHtml += '<span class="tag-tab-btn' + (isActive ? ' active' : '') + '" draggable="true" ' +
          'ondragstart="tagDragStart(event)" ondragover="event.preventDefault()" ondrop="tagDrop(event)" ' +
          'onclick="switchEssayTag(\'' + esc(tag) + '\')" data-tag="' + esc(tag) + '">' + esc(tag) + '</span>';
      }
    });
    document.getElementById('essay-tag-tabs').innerHTML = tabsHtml;

    var filteredData = data.filter(e => {
       if (!e.tag) return currentEssayTag === ordered[0] || ordered.indexOf('随笔') >= 0;
       let essayTags = e.tag.split(/[,，]/).map(function(s) { return s.trim(); }).filter(Boolean);
       return essayTags.includes(currentEssayTag);
    });

    if (filteredData.length === 0) {
       document.getElementById('essay-list').innerHTML = '<div class="empty-state">该标签下暂无文章，点击右上角新建</div>';
       return;
    }

    document.getElementById('essay-list').innerHTML = filteredData.map(e => `
    <div class="card${e.password_set ? ' card-password' : ''}">
      <div class="card-header">
        <div class="essay-header-row">
          ${pinBtn(e)}
          <div>
            <div class="card-title">${esc(e.title)}</div>
            <div class="card-meta">${esc(e.date)} · ${e.readTime} min · slug: ${esc(e.slug)}</div>
            <div class="card-meta epigraph">${esc(e.epigraph||'')}</div>
          </div>
        </div>
        <div class="card-actions">
          ${passwordBtn(e)}
          <button class="btn btn-sm" onclick="editEssayMeta('${esc(e.slug)}')">元数据</button>
          <button class="btn btn-sm" onclick="editEssayContent('${esc(e.slug)}')">编辑正文</button>
          <button class="btn btn-sm btn-danger" onclick="deleteEssay('${esc(e.slug)}')">删除</button>
        </div>
      </div>
      <div class="card-meta"><a class="essay-discuss-link" href="https://github.com/Chami537/chami537.github.io/discussions?discussions_q=${esc(e.slug)}" target="_blank" rel="noopener">💬 查看讨论 →</a></div>
    </div>
  `).join('');
  updatePinCount(data);
  } catch(e) { toast(e.message, true); }
}

// ═══ Tag system ═══
// 全局状态：记录当前激活的标签
let currentEssayTag = null;
let essayDeleteTagMode = false;

// 标签库 helpers
function _tagLib(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key) || fallback); }
  catch(e) { return JSON.parse(fallback); }
}
function _saveTagLib(key, tags) { localStorage.setItem(key, JSON.stringify(tags)); }
function _promptTag(key, fallback, onAdd) {
  var t = prompt('请输入新标签名称：');
  if (!t || !t.trim()) return;
  var tags = _tagLib(key, fallback);
  if (tags.indexOf(t.trim()) < 0) { tags.push(t.trim()); _saveTagLib(key, tags); }
  onAdd(t.trim());
}
function _toggleDeleteTagMode(btnId, flag, onDone) {
  var btn = document.getElementById(btnId);
  var on = !flag;
  btn.textContent = on ? '完成' : '删除标签';
  btn.classList.toggle('btn-danger', on);
  onDone();
  return on;
}

// 初始化标签库
function getTags() { return _tagLib('essay-tags', '["随笔","摄影","剪辑","骑行","投资"]'); }
function saveTags(tags) { _saveTagLib('essay-tags', tags); }

// ── Tag drag-to-reorder ──

var _tagDragSrc = null;

function tagDragStart(e) {
  _tagDragSrc = e.currentTarget;
  e.dataTransfer.effectAllowed = 'move';
}

function tagDrop(e) {
  e.preventDefault();
  var src = _tagDragSrc;
  var dst = e.currentTarget;
  if (!src || !dst || src === dst) return;
  var srcTag = src.getAttribute('data-tag');
  var dstTag = dst.getAttribute('data-tag');
  // Read all visible tag chips in order (the displayed order)
  var chips = document.querySelectorAll('#essay-tag-tabs .tag-tab-btn');
  var ordered = [];
  chips.forEach(function(c) { var t = c.getAttribute('data-tag'); if (t) ordered.push(t); });
  var srcIdx = ordered.indexOf(srcTag);
  var dstIdx = ordered.indexOf(dstTag);
  if (srcIdx < 0 || dstIdx < 0) return;
  ordered.splice(srcIdx, 1);
  ordered.splice(dstIdx, 0, srcTag);
  saveTagOrder(ordered);
  // Update current tag to maintain active state
  currentEssayTag = ordered[Math.min(dstIdx, ordered.length - 1)] || currentEssayTag;
  loadEssays();
}

async function saveTagOrder(order) {
  try { await api('PUT', '/api/tags/order', { order: order }); } catch(e) {}
}

function switchEssayTag(tag) {
  hidePanel('essay-form');
  hideEssayContentEditor();
  currentEssayTag = tag;
  loadEssays();
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
    loadEssays();
  }).catch(function(err) {
    toast('删除失败: ' + (err.message || '未知错误'), true);
    loadEssays();
  });
}

// ═══ Pin system ═══
function pinBtn(e) {
  var pinned = e.pinned || false;
  var totalPinned = (_essayAllData || []).filter(function(x) { return x.pinned; }).length;
  var atLimit = totalPinned >= 5;
  if (pinned) {
    return '<button class="pin-btn pinned" onclick="togglePin(\'' + esc(e.slug) + '\')" title="取消置顶">📍</button>';
  }
  if (atLimit) {
    return '<button class="pin-btn" disabled title="已满5篇">📌</button>';
  }
  return '<button class="pin-btn" onclick="togglePin(\'' + esc(e.slug) + '\')" title="置顶">📌</button>';
}

var _essayAllData = [];
async function togglePin(slug) {
  try {
    var r = await api('POST', '/api/essays/' + slug + '/pin');
    toast(r.pinned ? '已置顶 (' + r.count + '/5)' : '已取消置顶 (' + r.count + '/5)');
    // Update local state
    var e = _essayAllData.find(function(x) { return x.slug === slug; });
    if (e) e.pinned = r.pinned;
    loadEssays();
  } catch(e) { toast(e.message, true); }
}

function passwordBtn(e) {
  var hasPwd = e.password_set || false;
  var current = e.password || '';
  var label = hasPwd ? '&#x1F512; 密码' : '&#x1F511; 设密码';
  var title = hasPwd ? '点击修改或清除密码' : '设置密码保护';
  return '<button class="password-btn' + (hasPwd ? ' active' : '') + '" onclick="setPassword(\'' + esc(e.slug) + '\', \'' + esc(current) + '\')" title="' + title + '">' + label + '</button>';
}

function setPassword(slug, current) {
  document.getElementById('pwd-current').textContent = current || '(未设置)';
  document.getElementById('pwd-new').value = '';
  document.getElementById('pwd-confirm').value = '';
  document.getElementById('pwd-error').style.display = 'none';
  var dialog = document.getElementById('password-dialog');
  var form = document.getElementById('password-form');
  var done = false;
  form.onsubmit = async function(e) {
    e.preventDefault();
    if (done) return false; done = true;
    var pwd = document.getElementById('pwd-new').value;
    var confirm = document.getElementById('pwd-confirm').value;
    if (pwd && pwd !== confirm) {
      document.getElementById('pwd-error').textContent = '两次输入的密码不一致';
      document.getElementById('pwd-error').style.display = 'block';
      done = false;
      return false;
    }
    try {
      var r = await api('POST', '/api/essays/' + slug + '/password', { password: pwd });
      toast(r.password_set ? '密码已设置' : '密码已清除');
      dialog.close();
      loadEssays();
    } catch(e) { toast(e.message, true); dialog.close(); }
    return false;
  };
  dialog.showModal();
}

function closePwdDialog() {
  document.getElementById('password-dialog').close();
}

function updatePinCount(data) {
  _essayAllData = data || [];
  var c = data.filter(function(e) { return e.pinned; }).length;
  document.getElementById('pin-count').textContent = c > 0 ? '\u{1F4CC} \u5DF2\u7F6E\u9876 ' + c + '/5' : '';
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
  saveAbout();
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

function genSlug(title) {
  // Always use essay- prefix + random hex — robust against any title (Chinese, mixed script, emoji, etc.)
  return 'essay-' + Math.random().toString(16).slice(2, 10);
}


function showEssayForm() {
  showEntryForm({ formId: 'essay-form', editId: 'essay-edit-slug', title: '新建文章',
    fields: ['essay-title','essay-date','essay-readtime','essay-epigraph','essay-excerpt'] });
  var now = new Date();
  document.getElementById('essay-date').value = now.getFullYear() + '-' + pad2(now.getMonth()+1) + '-' + pad2(now.getDate());
  document.getElementById('essay-readtime').value = '4';
  let defaultTag = currentEssayTag || '随笔';
  document.getElementById('essay-tag').value = defaultTag;
  renderTagChips(defaultTag);
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
  renderTagChips(e.tag || '');
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
    tag: document.getElementById('essay-tag').value,
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
    loadEssays();
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
    renderKatexIn(panel);
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
  loadEssays();
  toast('随笔已删除');
}

