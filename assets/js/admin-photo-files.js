// Photo uploads and deletion.

function handlePhotoDrop(event) {
  if (event.dataTransfer.files.length) handlePhotoFiles(event.dataTransfer.files);
}

function handlePhotoFiles(files) {
  Array.from(files).forEach(function(file) {
    if (!file.type.startsWith('image/')) return;
    var form = new FormData();
    form.append('file', file);
    api('POST', '/api/photos/upload', form).then(function(result) {
      toast('已上传: ' + result.filename);
      loadPhotos();
    }).catch(function(error) {
      toast(error.message, true);
    });
  });
}

async function deletePhoto(filename) {
  var confirmed = await confirmDialog('确定删除照片 "' + filename + '"？');
  if (!confirmed) return;
  await api('DELETE', '/api/photos/' + filename);
  loadPhotos();
  toast('照片已删除');
}
