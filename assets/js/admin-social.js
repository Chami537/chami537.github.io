// Admin Contact and Friends CRUD.

// Contact
async function loadContact() {
  try {
    const data = await api('GET', '/api/contact');
  document.getElementById('contact-list').innerHTML = data.map(c => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${esc(c.label)} <span style="color:var(--muted);font-weight:400;">${esc(c.handle)}</span></div>
          <div class="card-meta">${c.url ? '🔗 ' + esc(c.url) : '无链接'}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editContact(${c.id})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteContact(${c.id})">删除</button>
        </div>
      </div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function showContactForm() {
  showEntryForm({ formId: 'contact-form', editId: 'contact-edit-id', title: '添加联系方式',
    fields: ['contact-label','contact-handle','contact-url'] });
}


function editContact(id) {
  var form = document.getElementById('contact-form');
  if (form.style.display === 'block' && document.getElementById('contact-edit-id').value == id) {
    form.style.display = 'none'; return;
  }
  api('GET', '/api/contact').then(data => {
    var c = data.find(item => item.id === id);
    if (!c) { toast('未找到条目', true); return; }
    document.getElementById('contact-edit-id').value = id;
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
  var id = document.getElementById('contact-edit-id').value;
  var item = {
    label: document.getElementById('contact-label').value,
    handle: document.getElementById('contact-handle').value,
    url: document.getElementById('contact-url').value,
  };    if (id !== '') { await api('PUT', '/api/contact/' + id, item); }
    else { await api('POST', '/api/contact', item); }
    markClean();
    hidePanel('contact-form');
    loadContact();
    toast('已保存');
  } catch(e) { toast(e.message, true); }
}

async function deleteContact(id) {  var confirmed = await confirmDialog('确定删除？');
  if (!confirmed) return;
  await api('DELETE', '/api/contact/' + id);
  if (document.getElementById('contact-edit-id') && document.getElementById('contact-edit-id').value == id) hidePanel('contact-form');
  loadContact();
  toast('已删除');
}

// Friends
// ═══════════════════════════════════
async function loadFriends() {
  try {
    const data = await api('GET', '/api/friends');
  document.getElementById('friend-list').innerHTML = data.map(f => `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">${esc(f.name)}</div>
          <div class="card-meta">${esc(f.url)}</div>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" onclick="editFriend(${f.id})">编辑</button>
          <button class="btn btn-sm btn-danger" onclick="deleteFriend(${f.id})">删除</button>
        </div>
      </div>
    </div>
  `).join('');
  } catch(e) { toast(e.message, true); }
}

function showFriendForm() {
  showEntryForm({ formId: 'friend-form', editId: 'friend-edit-id', title: '添加友链',
    fields: ['friend-name','friend-url'] });
}


function editFriend(id) {
  var form = document.getElementById('friend-form');
  if (form.style.display === 'block' && document.getElementById('friend-edit-id').value == id) {
    form.style.display = 'none'; return;
  }
  document.getElementById('friend-edit-id').value = id;
  document.getElementById('friend-form-title').textContent = '编辑友链';
  api('GET', '/api/friends').then(data => {
    var f = data.find(item => item.id === id);
    if (!f) { toast('未找到条目', true); return; }
    document.getElementById('friend-name').value = f.name;
    document.getElementById('friend-url').value = f.url;
    form.style.display = 'block';
    form.scrollIntoView({ behavior: 'smooth' });
  }).catch(e => toast(e.message, true));
}

async function saveFriend() {
  try {
  const id = document.getElementById('friend-edit-id').value;
  const item = { name: document.getElementById('friend-name').value, url: document.getElementById('friend-url').value };    if (id !== '') {
      await api('PUT', '/api/friends/' + id, item);
    } else {
      await api('POST', '/api/friends', item);
    }
    markClean();
    hidePanel('friend-form');
    loadFriends();
    toast('友链已保存');
  } catch(e) { toast(e.message, true); }
}

async function deleteFriend(id) {  const confirmed = await confirmDialog('确定删除这个友链？');
  if (!confirmed) return;
  await api('DELETE', '/api/friends/' + id);
  if (document.getElementById('friend-edit-id') && document.getElementById('friend-edit-id').value == id) hidePanel('friend-form');
  loadFriends();
  toast('友链已删除');
}

// ═══════════════════════════════════

