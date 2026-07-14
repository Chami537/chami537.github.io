// Admin Music CRUD.

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
    var file = document.getElementById('music-file').files[0];
    var uploadResult = await _uploadMusicFile(file);
    if (file && !uploadResult) return;
    var id = document.getElementById('music-edit-id').value;
    await _saveMusicItem(id, _musicFormItem(uploadResult));
    markClean();
    hidePanel('music-form');
    loadMusic();
    toast(id ? '曲目已更新' : '曲目已添加');
  } catch(e) { toast(e.message, true); }
}

async function _uploadMusicFile(file) {
  if (!file) return null;
  var fd = new FormData();
  fd.append('file', file);
  try {
    return await api('POST', '/api/music/upload', fd);
  } catch(e) {
    toast('上传失败: ' + e.message, true);
    return null;
  }
}

function _musicFormItem(uploadResult) {
  return {
    title: document.getElementById('music-title').value,
    artist: document.getElementById('music-artist').value,
    filename: uploadResult ? uploadResult.filename : document.getElementById('music-filename').value,
  };
}

async function _saveMusicItem(id, item) {
  if (id) {
    await api('PUT', '/api/music/' + id, item);
  } else {
    await api('POST', '/api/music', item);
  }
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
