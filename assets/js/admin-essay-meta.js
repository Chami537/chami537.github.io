// Essay metadata form and persistence.

function genSlug() {
  return 'essay-' + Math.random().toString(16).slice(2, 10);
}

function _markdownMeta(markdown, filename) {
  var front = {};
  var match = markdown.match(/^---\s*\n([\s\S]*?)\n---\s*\n?/);
  if (match) {
    match[1].split('\n').forEach(function(line) {
      var pair = line.match(/^([\w-]+):\s*(.*?)\s*$/);
      if (pair) front[pair[1].toLowerCase()] = pair[2].replace(/^['"]|['"]$/g, '');
    });
    markdown = markdown.slice(match[0].length);
  }
  var heading = markdown.match(/^#\s+(.+)$/m);
  var title = front.title || (heading && heading[1].trim()) || filename.replace(/\.md$/i, '');
  var plain = markdown.replace(/^```[\s\S]*?```/gm, '').replace(/^#{1,6}\s+/gm, '').replace(/[*_>`\[\]]/g, '').trim();
  var excerpt = (plain.split(/\n\s*\n/).find(function(p) { return p.trim(); }) || '').replace(/\s+/g, ' ').slice(0, 140);
  return {markdown: markdown, title: title.slice(0, 120), date: front.date || '', tag: front.tags || front.tag || '随笔', excerpt: front.excerpt || excerpt};
}

function _fileTimestamp(file) {
  var date = new Date(file.lastModified || Date.now());
  function pad(value) { return String(value).padStart(2, '0'); }
  return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()) + ' ' + pad(date.getHours()) + ':' + pad(date.getMinutes());
}

async function importEssayMarkdown(input) {
  var file = input.files && input.files[0];
  input.value = '';
  if (!file) return;
  try {
    var markdown = await file.text();
    var meta = _markdownMeta(markdown, file.name);
    var basename = file.name.replace(/\.md$/i, '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '');
    var slug = basename && /^[a-z0-9-]+$/.test(basename) ? (basename.indexOf('essay-') === 0 ? basename : 'essay-' + basename) : genSlug();
    await api('POST', '/api/essays', {slug: slug, title: meta.title, tag: meta.tag, date: meta.date || _fileTimestamp(file), epigraph: '', excerpt: meta.excerpt, body: meta.markdown});
    toast('Markdown 已导入并发布');
    window['essay' + 'Entry']();
  } catch (error) {
    toast('导入失败: ' + error.message, true);
  }
}

function showEssayForm() {
  showEntryForm({
    formId: 'essay-form', editId: 'essay-edit-slug', title: '新建文章',
    fields: ['essay-title', 'essay-date', 'essay-readtime', 'essay-epigraph', 'essay-excerpt', 'essay-tech-topic', 'essay-extra-tags']
  });
  var now = new Date();
  document.getElementById('essay-date').value = now.getFullYear() + '-' + pad2(now.getMonth() + 1) + '-' + pad2(now.getDate());
  document.getElementById('essay-readtime').value = '4';
  renderEssayTaxonomy(_defaultEssayTagForCurrentFilter());
}

async function editEssayMeta(slug) {
  var form = document.getElementById('essay-form');
  if (form.style.display === 'block' && document.getElementById('essay-edit-slug').value === slug) {
    form.style.display = 'none';
    return;
  }
  var data = await api('GET', '/api/essays');
  var essay = data.find(function(item) { return item.slug === slug; });
  if (!essay) return;
  _fillEssayMetaForm(essay);
}

function _fillEssayMetaForm(essay) {
  var form = document.getElementById('essay-form');
  document.getElementById('essay-edit-slug').value = essay.slug;
  document.getElementById('essay-title').value = essay.title;
  document.getElementById('essay-tag').value = essay.tag || '';
  document.getElementById('essay-date').value = essay.date || '';
  document.getElementById('essay-readtime').value = essay.readTime || 1;
  document.getElementById('essay-epigraph').value = essay.epigraph || '';
  document.getElementById('essay-excerpt').value = essay.excerpt || '';
  renderEssayTaxonomy(essay.tag || '');
  document.getElementById('essay-form-title').textContent = '编辑元数据';
  form.style.display = 'block';
  form.scrollIntoView({behavior: 'smooth'});
}

async function saveEssay() {
  try {
    var editSlug = document.getElementById('essay-edit-slug').value;
    var item = {
      slug: editSlug || genSlug(),
      title: document.getElementById('essay-title').value,
      tag: syncEssayTagFromTaxonomy(),
      date: document.getElementById('essay-date').value,
      epigraph: document.getElementById('essay-epigraph').value,
      excerpt: document.getElementById('essay-excerpt').value
    };
    if (editSlug) {
      await api('PUT', '/api/essays/' + editSlug, item);
      toast('元数据已更新');
    } else {
      await api('POST', '/api/essays', item);
      toast('随笔已创建，HTML 文件已生成');
    }
    markClean();
    hidePanel('essay-form');
    window['essay' + 'Entry']();
  } catch (error) {
    toast(error.message, true);
  }
}
