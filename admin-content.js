// Work
// ═══════════════════════════════════
async function loadWork() {
  try {
    const data = await api('GET', '/api/work');
    document.getElementById('work-list').innerHTML = data.map(w => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${pad2(w.id)} ${esc(w.title)}</div>
          <div class="card-meta">${esc(w.description)}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editWork(${w.id})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteWork(${w.id})">删除</button>
        </div>
      </div>
      <div class="tags">${(w.tags||[]).map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>
      <div class="card-meta" style="margin-top:6px;">🔗 ${esc(w.url)} ${w.repo ? '· ⭐ '+esc(w.repo) : ''}</div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function pad2(n) { return n.toString().padStart(2, '0'); }
function esc(s) { const d = document.createElement('div'); d.textContent = s != null ? s : ''; return d.innerHTML; }

async function editWork(id) {  const form = document.getElementById('work-form');
  if (form.style.display === 'block' && document.getElementById('work-edit-id').value == id) {
    form.style.display = 'none'; return;
  }
  const data = await api('GET', '/api/work');
  const w = data.find(x => x.id === id);
  if (!w) return;
  document.getElementById('work-edit-id').value = id;
  document.getElementById('work-title').value = w.title;
  document.getElementById('work-desc').value = w.description;
  document.getElementById('work-url').value = w.url;
  document.getElementById('work-repo').value = w.repo || '';
  document.getElementById('work-tags').value = (w.tags||[]).join(', ');
  document.getElementById('work-form-title').textContent = '编辑项目';
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
}

function showWorkForm() {
  showEntryForm({ formId: 'work-form', editId: 'work-edit-id', title: '新建项目',
    fields: ['work-title','work-desc','work-url','work-repo','work-tags'] });
}


async function saveWork() {
  try {
  const id = document.getElementById('work-edit-id').value;
  const item = {
    title: document.getElementById('work-title').value,
    description: document.getElementById('work-desc').value,
    url: document.getElementById('work-url').value,
    repo: document.getElementById('work-repo').value,
    tags: document.getElementById('work-tags').value.split(',').map(s => s.trim()).filter(Boolean),
  };    if (id) {
      await api('PUT', '/api/work/' + id, item);
    } else {
      await api('POST', '/api/work', item);
    }
    markClean();
    hidePanel('work-form');
    loadWork();
    toast(id ? '项目已更新' : '项目已创建');
  } catch(e) { toast(e.message, true); }
}

async function deleteWork(id) {  const confirmed = await confirmDialog('确定删除这个项目？');
  if (!confirmed) return;
  await api('DELETE', '/api/work/' + id);
  if (document.getElementById('work-edit-id').value == id) hidePanel('work-form');
  loadWork();
  toast('项目已删除');
}

// ═══════════════════════════════════
// ═══════════════════════════════════
// Contact
async function loadContact() {
  try {
    const data = await api('GET', '/api/contact');
  document.getElementById('contact-list').innerHTML = data.map((c, i) => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${esc(c.label)} <span style="color:var(--muted);font-weight:400;">${esc(c.handle)}</span></div>
          <div class="card-meta">${c.url ? '🔗 ' + esc(c.url) : '无链接'}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editContact(${i})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteContact(${i})">删除</button>
        </div>
      </div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function showContactForm() {
  showEntryForm({ formId: 'contact-form', editId: 'contact-edit-index', title: '添加联系方式',
    fields: ['contact-label','contact-handle','contact-url'] });
}


function editContact(i) {
  var form = document.getElementById('contact-form');
  if (form.style.display === 'block' && document.getElementById('contact-edit-index').value == i) {
    form.style.display = 'none'; return;
  }
  api('GET', '/api/contact').then(data => {
    var c = data[i];
    document.getElementById('contact-edit-index').value = i;
    document.getElementById('contact-label').value = c.label;
    document.getElementById('contact-handle').value = c.handle;
    document.getElementById('contact-url').value = c.url || '';
    document.getElementById('contact-form-title').textContent = '编辑联系方式';
    form.style.display = 'block';
    form.scrollIntoView({ behavior: 'smooth' });
  }).catch(e => toast(e.message, true));
}

async function saveContact() {
  try {
  var idx = document.getElementById('contact-edit-index').value;
  var item = {
    label: document.getElementById('contact-label').value,
    handle: document.getElementById('contact-handle').value,
    url: document.getElementById('contact-url').value,
  };    if (idx !== '') { await api('PUT', '/api/contact/' + idx, item); }
    else { await api('POST', '/api/contact', item); }
    markClean();
    hidePanel('contact-form');
    loadContact();
    toast('已保存');
  } catch(e) { toast(e.message, true); }
}

async function deleteContact(i) {  var confirmed = await confirmDialog('确定删除？');
  if (!confirmed) return;
  await api('DELETE', '/api/contact/' + i);
  if (document.getElementById('contact-edit-index').value == i) hidePanel('contact-form');
  loadContact();
  toast('已删除');
}

// Friends
// ═══════════════════════════════════
async function loadFriends() {
  try {
    const data = await api('GET', '/api/friends');
  document.getElementById('friend-list').innerHTML = data.map((f, i) => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${esc(f.name)}</div>
          <div class="card-meta">${esc(f.url)}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editFriend(${i})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteFriend(${i})">删除</button>
        </div>
      </div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function showFriendForm() {
  showEntryForm({ formId: 'friend-form', editId: 'friend-edit-index', title: '添加友链',
    fields: ['friend-name','friend-url'] });
}


function editFriend(i) {
  var form = document.getElementById('friend-form');
  if (form.style.display === 'block' && document.getElementById('friend-edit-index').value == i) {
    form.style.display = 'none'; return;
  }
  document.getElementById('friend-edit-index').value = i;
  document.getElementById('friend-form-title').textContent = '编辑友链';
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
  api('GET', '/api/friends').then(data => {
    document.getElementById('friend-name').value = data[i].name;
    document.getElementById('friend-url').value = data[i].url;
  }).catch(e => toast(e.message, true));
}

async function saveFriend() {
  try {
  const idx = document.getElementById('friend-edit-index').value;
  const item = { name: document.getElementById('friend-name').value, url: document.getElementById('friend-url').value };    if (idx !== '') {
      await api('PUT', '/api/friends/' + idx, item);
    } else {
      await api('POST', '/api/friends', item);
    }
    markClean();
    hidePanel('friend-form');
    loadFriends();
    toast('友链已保存');
  } catch(e) { toast(e.message, true); }
}

async function deleteFriend(i) {  const confirmed = await confirmDialog('确定删除这个友链？');
  if (!confirmed) return;
  await api('DELETE', '/api/friends/' + i);
  if (document.getElementById('friend-edit-index').value == i) hidePanel('friend-form');
  loadFriends();
  toast('友链已删除');
}

// ═══════════════════════════════════
// Music
// ═══════════════════════════════════
async function loadMusic() {
  try {
    const data = await api('GET', '/api/music');
  document.getElementById('music-list').innerHTML = data.map(m => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${pad2(m.id)} ${esc(m.title)}</div>
          <div class="card-meta">${esc(m.artist)} · ${esc(m.filename)}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editMusic(${m.id})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteMusic(${m.id})">删除</button>
        </div>
      </div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function autoFillMusic() {
  var file = document.getElementById('music-file').files[0];
  if (!file) return;
  document.getElementById('music-filename').value = file.name;
  var name = file.name.replace(/\.mp3$/i, '');
  var parts = name.split(' - ');
  if (parts.length >= 2) {
    document.getElementById('music-artist').value = parts[0].trim();
    document.getElementById('music-title').value = parts.slice(1).join(' - ').trim();
  } else {
    document.getElementById('music-title').value = name;
  }
}

function showMusicForm() {
  showEntryForm({ formId: 'music-form', editId: 'music-edit-id', title: '添加曲目',
    fields: ['music-file','music-title','music-artist','music-filename'] });
}


async function editMusic(id) {  var form = document.getElementById('music-form');
  if (form.style.display === 'block' && document.getElementById('music-edit-id').value == id) {
    form.style.display = 'none'; return;
  }
  const data = await api('GET', '/api/music');
  const m = data.find(x => x.id === id);
  if (!m) return;
  document.getElementById('music-edit-id').value = id;
  document.getElementById('music-title').value = m.title;
  document.getElementById('music-artist').value = m.artist;
  document.getElementById('music-filename').value = m.filename;
  document.getElementById('music-form-title').textContent = '编辑曲目';
  form.style.display = 'block';
  form.scrollIntoView({ behavior: 'smooth' });
}

async function saveMusic() {
  try {
  var fileInput = document.getElementById('music-file');
  var file = fileInput.files[0];
  // Upload file if present
  if (file) {
    var fd = new FormData();
    fd.append('file', file);
    try { var uploadResult = await api('POST', '/api/music/upload', fd); }
    catch(e) { toast('上传失败: ' + e.message, true); return; }
  }
  var id = document.getElementById('music-edit-id').value;
  var item = {
    title: document.getElementById('music-title').value,
    artist: document.getElementById('music-artist').value,
    filename: uploadResult ? uploadResult.filename : document.getElementById('music-filename').value,
  };    if (id) { await api('PUT', '/api/music/' + id, item); }
    else { await api('POST', '/api/music', item); }
    markClean();
    hidePanel('music-form');
    loadMusic();
    toast(id ? '曲目已更新' : '曲目已添加');
  } catch(e) { toast(e.message, true); }
}

async function deleteMusic(id) {  const confirmed = await confirmDialog('确定删除这个曲目？');
  if (!confirmed) return;
  await api('DELETE', '/api/music/' + id);
  if (document.getElementById('music-edit-id').value == id) hidePanel('music-form');
  loadMusic();
  toast('曲目已删除');
}

// ═══════════════════════════════════
// Git
// ═══════════════════════════════════
// ═══════════════════════════════════
// Stack — drag-to-reorder chips


function renderStackChips(data) {
  var colors = ['#ff4d4d','#ff6d00','#ffb800','#0066ff','#00c853','#9c27b0'];
  return data.map(function(c, i) {
    var color = colors[i % 6];
    return '<span class="stack-chip" draggable="true"' +
      ' style="--chip-color:' + color + '"' +
      ' ondragstart="stackDragStart(event,' + i + ')"' +
      ' ondragover="stackDragOver(event)"' +
      ' ondragend="stackDragEnd(event)"' +
      ' ondrop="stackDrop(event,' + i + ')"' +
      '>' + esc(c) +
      '<button onclick="deleteStackChip(' + i + ')" class="stack-chip-del" title="删除">\u00d7</button>' +
      '</span>';
  }).join('');
}

async function loadStack() {
  try {
    var data = await api('GET', '/api/stack');
    window._stackData = data;
    document.getElementById('stack-chips').innerHTML = renderStackChips(data) || '<span style="color:var(--muted);font-size:12px;">还没有添加技术栈</span>';
  } catch(e) { toast(e.message, true); }
}

async function addStackItem() {
  var input = document.getElementById('stack-new-name');
  var name = input.value.trim();
  if (!name) return;
  var data;
  try { data = await api('GET', '/api/stack'); } catch(e) { data = []; }
  data.push(name);
  await api('PUT', '/api/stack', data);
  input.value = '';
  loadStack();
}

async function deleteStackChip(idx) {
  var data = await api('GET', '/api/stack');
  data.splice(idx, 1);
  await api('PUT', '/api/stack', data);
  loadStack();
}

function stackDragStart(e, idx) { _dragStart(e, idx); }
function stackDragOver(e) { _dragOver(e); }
function stackDragEnd(e) { _dragEnd(e); }

async function stackDrop(e, toIdx) {
  e.preventDefault();
  var fromIdx = _dragState.idx;
  if (fromIdx < 0 || fromIdx === toIdx) return;
  var data = await api('GET', '/api/stack');
  var item = data.splice(fromIdx, 1)[0];
  data.splice(toIdx, 0, item);
  await api('PUT', '/api/stack', data);
  _dragState.idx = -1;
  loadStack();
}

async function refreshGitStatus() {
  try {
    const data = await api('GET', '/api/git/status');
    document.getElementById('git-badge').textContent = data.branch + (data.clean ? '  ✓' : '  ✗');
    var html = '<div class="card">';
    html += '<div class="git-branch">' + esc(data.branch) + '</div>';
    html += '<div class="git-clean' + (data.clean ? ' clean' : ' dirty') + '">' + (data.clean ? '工作区干净' : '有未提交的改动') + '</div>';
    if (data.files && data.files.length > 0) {
      html += '<div class="git-files-label">变更文件:</div>';
      data.files.forEach(function(f) {
        var cls = f.startsWith('??') ? ' untracked' : f.startsWith(' M') || f.startsWith('M ') ? ' modified' : ' added';
        html += '<div class="git-file-row' + cls + '">' + esc(f) + '</div>';
      });
    }
    if (data.diffStat) {
      html += '<div class="git-diff-stat">' + esc(data.diffStat) + '</div>';
    }
    html += '</div>';
    document.getElementById('git-status-cards').innerHTML = html;
  } catch(e) {
    document.getElementById('git-status-cards').innerHTML = '<div class="card" style="color:var(--danger);">错误: ' + esc(e.message) + '</div>';
  }
}

function showCommitDialog() {
  document.getElementById('commit-dialog').showModal();
}

document.getElementById('commit-form').addEventListener('submit', async (e) => {
  const msg = document.getElementById('commit-msg').value;
  try {
    const result = await api('POST', '/api/git/commit', { message: msg });
    toast('Committed: ' + (result.output || ''));
    document.getElementById('commit-dialog').close();
    document.getElementById('commit-msg').value = '';
    refreshGitStatus();
  } catch(e) { toast(e.message, true); }
});

async function confirmRevert() {  const confirmed = await confirmDialog('确定撤销所有未提交的改动？此操作不可恢复。');
  if (!confirmed) return;
  await api('POST', '/api/git/revert');
  toast('已撤销');
  refreshGitStatus();
  loadWork(); loadEssays(); loadPhotos(); loadFriends(); loadContact(); loadMusic();
}

async function showGitDiff() {
  try {
    var data = await api('GET', '/api/git/diff');
    var el = document.getElementById('diff-content');
    // Simple color: + lines green, - lines red
    var html = (data.diff || '(no changes)').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    html = html.replace(/^(\+.*)$/gm, '<span class="diff-added">$1</span>');
    html = html.replace(/^(-.*)$/gm, '<span class="diff-removed">$1</span>');
    html = html.replace(/^(@@.*@@)$/gm, '<span class="diff-hunk">$1</span>');
    el.innerHTML = html;
    document.getElementById('diff-dialog').showModal();
  } catch(e) { toast(e.message, true); }
}

async function handlePush() {
  try {
  const confirmed = await confirmDialog('确定推送到远程仓库？');
  if (!confirmed) return;    await api('POST', '/api/git/push');
    toast('Push 成功');
    refreshGitStatus();
  } catch(e) { toast(e.message, true); }
}

