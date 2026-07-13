// Admin Stack CRUD and ordering.

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

