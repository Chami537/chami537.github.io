// Tracks list, GPX upload, rename, and deletion.

async function loadTracks() {
  var data = await api('GET', '/api/tracks');
  var html = '';
  data.forEach(function(t, i) {
    html += '<div class="track-row">' +
      '<span>' + esc(t.name) + ' <code class="code-muted">' + esc(t.file) + '</code></span>' +
      '<button class="btn btn-sm btn-danger" onclick="deleteTrack(' + i + ')">删除</button>' +
      '</div>';
  });
  document.getElementById('tracks-list').innerHTML = html || '<p class="text-muted">暂无轨迹</p>';
}

async function uploadTrackFile(file) {
  var form = new FormData();
  form.append('file', file);
  var result = await api('POST', '/api/tracks/upload', form);
  if (!result.file) return;
  loadTracks();
  toast('已上传: ' + result.file);
}

function handleTrackDrop(event) {
  if (event.dataTransfer.files.length) handleTrackFile(event.dataTransfer.files);
}

function handleTrackFile(files) {
  Array.from(files).forEach(function(file) {
    if (file.name.toLowerCase().endsWith('.gpx')) uploadTrackFile(file);
  });
}

async function deleteTrack(index) {
  if (!confirm('删除此轨迹？')) return;
  await api('DELETE', '/api/tracks/' + index);
  loadTracks();
}
