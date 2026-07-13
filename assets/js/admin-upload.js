// Cross-tab drag-and-drop upload coordination.
document.addEventListener('dragover', function(e) {
  var ta = document.getElementById('essay-content-md');
  if (ta && (e.target === ta || (e.target.closest && e.target.closest('#essay-content-md')))) return;
  e.preventDefault();
});

document.addEventListener('drop', function(e) {
  var ta = document.getElementById('essay-content-md');
  if (ta && (e.target === ta || (e.target.closest && e.target.closest('#essay-content-md')))) return;
  e.preventDefault();
  var files = e.dataTransfer.files;
  if (!files.length) return;
  var tab = document.querySelector('.tab-btn.active');
  var tabName = tab ? tab.textContent.trim() : '';
  if (tabName === 'Photos') {
    var photoCount = 0;
    Array.from(files).forEach(function(f) {
      if (!f.type.startsWith('image/')) return;
      var fd = new FormData(); fd.append('file', f); fd.append('size', 'sm');
      api('POST', '/api/photos/upload', fd).then(function() { loadPhotos(); }).catch(function(err) {
        toast('上传失败: ' + (err.message || '未知错误'), true);
      });
      photoCount++;
    });
    if (photoCount > 0) toast('已上传 ' + photoCount + ' 张照片');
  } else if (document.getElementById('essay-content-editor').style.display === 'block') {
    var essayCount = 0;
    Array.from(files).forEach(function(f) {
      if (!f.type.startsWith('image/')) return;
      var fd = new FormData(); fd.append('file', f);
      var slug = document.getElementById('essay-edit-slug').value;
      if (slug) fd.append('slug', slug);
      api('POST', '/api/essays/upload-image', fd).then(function(r) {
        var editor = document.getElementById('essay-content-md');
        var cursor = editor.selectionStart;
        var md = '![](' + (r.url || '') + ')\n';
        editor.value = editor.value.slice(0, cursor) + md + editor.value.slice(editor.selectionEnd);
        editor.selectionStart = editor.selectionEnd = cursor + md.length;
      }).catch(function(err) {
        toast('插图上传失败: ' + (err.message || '未知错误'), true);
      });
      essayCount++;
    });
    if (essayCount > 0) toast('已插入 ' + essayCount + ' 张图片');
  }
});
