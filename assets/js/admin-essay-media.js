// Essay image insertion and HTML preview.

function _insertEssayImage(markdown) {
  var textarea = document.getElementById('essay-content-md');
  var start = textarea.selectionStart;
  textarea.value = textarea.value.slice(0, start) + markdown + textarea.value.slice(textarea.selectionEnd);
  textarea.focus();
  textarea.selectionStart = textarea.selectionEnd = start + markdown.length;
}

async function _uploadEssayImageFile(file, slug) {
  var form = new FormData();
  if (slug) form.append('slug', slug);
  form.append('file', file);
  var result = await api('POST', '/api/essays/upload-image', form);
  var url = result.url || '';
  _insertEssayImage('![](' + (url.startsWith('/') ? url : '/' + url) + ')');
  toast('图片已插入');
}

async function uploadEssayImage() {
  var input = document.getElementById('essay-img-input');
  try {
    var file = input.files[0];
    if (!file) return;
    await _uploadEssayImageFile(file, document.getElementById('essay-content-editor').dataset.slug);
  } catch (error) {
    toast(error.message, true);
  } finally {
    input.value = '';
  }
}

async function previewEssayContent() {
  try {
    var panel = document.getElementById('essay-preview');
    if (panel.style.display === 'block') {
      panel.style.display = 'none';
      return;
    }
    var markdown = document.getElementById('essay-content-md').value;
    var data = await api('POST', '/api/essays/x/html', {md: markdown});
    panel.innerHTML = data.html;
    window._renderAdminEditor(panel);
    panel.style.display = 'block';
  } catch (error) {
    toast(error.message, true);
  }
}

(function() {
  var textarea = document.getElementById('essay-content-md');
  textarea.addEventListener('dragover', function(event) {
    if (event.dataTransfer.types && event.dataTransfer.types.indexOf('Files') >= 0) {
      event.preventDefault();
      event.stopPropagation();
    }
  });
  textarea.addEventListener('drop', async function(event) {
    var file = event.dataTransfer.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    event.preventDefault();
    event.stopPropagation();
    try {
      await _uploadEssayImageFile(file, document.getElementById('essay-content-editor').dataset.slug);
    } catch (error) {
      toast(error.message, true);
    }
  });
})();
