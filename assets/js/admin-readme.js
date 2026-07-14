// README editor.

async function loadReadme() {
  try {
    var data = await api('GET', '/api/readme');
    document.getElementById('readme-content').value = data.content || '';
  } catch (error) {
    toast(error.message, true);
  }
}

async function saveReadme() {
  try {
    await api('PUT', '/api/readme', {
      content: document.getElementById('readme-content').value
    });
    markClean();
    toast('README 已保存');
  } catch (error) {
    toast(error.message, true);
  }
}
