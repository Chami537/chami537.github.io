// Essay metadata form and persistence.

function genSlug() {
  return 'essay-' + Math.random().toString(16).slice(2, 10);
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
  document.getElementById('essay-edit-slug').value = slug;
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
