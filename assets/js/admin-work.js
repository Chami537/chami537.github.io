// Admin Work CRUD.

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

