// Markdown formatting shortcuts, templates, and word count.

function _wrapSelection(textarea, before, after) {
  var start = textarea.selectionStart;
  var end = textarea.selectionEnd;
  var selected = textarea.value.slice(start, end);
  textarea.value = textarea.value.slice(0, start) + before + selected + after + textarea.value.slice(end);
  var offset = before.length;
  textarea.selectionStart = start + offset;
  textarea.selectionEnd = selected.length ? end + offset : start + offset;
}

function _prefixLines(textarea, prefix) {
  var start = textarea.selectionStart;
  var end = textarea.selectionEnd;
  var value = textarea.value;
  while (start > 0 && value[start - 1] !== '\n') start--;
  while (end < value.length && value[end] !== '\n') end++;
  if (end < value.length) end++;
  var lines = value.slice(start, end).split('\n');
  if (lines.length > 1 && lines[lines.length - 1] === '') lines.pop();
  var result = lines.map(function(line) { return prefix + line; }).join('\n');
  if (value[end - 1] === '\n') result += '\n';
  textarea.value = value.slice(0, start) + result + value.slice(end);
  textarea.selectionStart = start;
  textarea.selectionEnd = start + result.length;
}

function _essayBySlug(slug) {
  return (_essayAllData || []).find(function(essay) { return essay.slug === slug; }) || null;
}

function _techTemplateForEssay(essay) {
  var tags = _essayTagParts(essay && essay.tag);
  var topic = tags.find(function(tag) {
    return tag !== '技术' && ESSAY_MAIN_TAGS.indexOf(tag) < 0 && ESSAY_TECH_TYPES.indexOf(tag) < 0;
  }) || '这个主题';
  var type = tags.find(function(tag) { return ESSAY_TECH_TYPES.indexOf(tag) >= 0; }) || '学习日志';
  return [
    '## 我在学什么', '', '今天围绕 ' + topic + ' 解决一个具体问题。', '',
    '## 卡在哪里', '', '- ', '', '## 今天弄懂了什么', '', '- ', '',
    '## 可复用结论', '', '- ', '', '## 下次继续', '', '- ', '',
    '<!-- 技术主题: ' + topic + ' · 类型: ' + type + ' -->', ''
  ].join('\n');
}

function insertTechEssayTemplate() {
  var textarea = document.getElementById('essay-content-md');
  var slug = document.getElementById('essay-content-editor').dataset.slug;
  var template = _techTemplateForEssay(_essayBySlug(slug));
  if (textarea.value.trim() && !confirm('正文里已有内容，要在光标处插入技术模板吗？')) return;
  var start = textarea.selectionStart || 0;
  var end = textarea.selectionEnd || start;
  var prefix = start > 0 && textarea.value[start - 1] !== '\n' ? '\n\n' : '';
  var suffix = end < textarea.value.length && textarea.value[end] !== '\n' ? '\n\n' : '';
  textarea.value = textarea.value.slice(0, start) + prefix + template + suffix + textarea.value.slice(end);
  textarea.focus();
  textarea.selectionStart = textarea.selectionEnd = start + prefix.length + template.length;
  _updateWordCount();
  markDirty();
}

function _updateWordCount() {
  var text = document.getElementById('essay-content-md').value;
  var cjk = (text.match(/[\u4e00-\u9fff\u3400-\u4dbf]/g) || []).length;
  var words = (text.match(/[a-zA-Z]+/g) || []).length;
  document.getElementById('essay-word-count').textContent = text.length + ' 字符 · ' +
    (cjk + words) + ' 词 · ~' + Math.max(1, Math.round((cjk + words * 1.5) / 300)) + ' min';
}

document.addEventListener('keydown', function(event) {
  var textarea = document.getElementById('essay-content-md');
  if (document.activeElement !== textarea) return;
  if (event.key === 'Tab') {
    event.preventDefault();
    var start = textarea.selectionStart;
    textarea.value = textarea.value.slice(0, start) + '  ' + textarea.value.slice(textarea.selectionEnd);
    textarea.selectionStart = textarea.selectionEnd = start + 2;
  }
  if (!(event.ctrlKey || event.metaKey)) return;
  if (event.key === 's') { event.preventDefault(); saveEssayContent(); }
  if (event.key === 'b') { event.preventDefault(); _wrapSelection(textarea, '**', '**'); }
  if (event.key === 'i') { event.preventDefault(); _wrapSelection(textarea, '*', '*'); }
  if (event.key === 'k') { event.preventDefault(); _wrapSelection(textarea, '[', '](url)'); }
  if (event.code === 'Backquote' && event.shiftKey) {
    event.preventDefault();
    var position = textarea.selectionStart;
    var selected = textarea.value.slice(position, textarea.selectionEnd);
    var block = '\n```\n' + (selected || 'code') + '\n```\n';
    textarea.value = textarea.value.slice(0, position) + block + textarea.value.slice(textarea.selectionEnd);
    textarea.selectionStart = textarea.selectionEnd = selected ? position + block.length : position + 5;
  } else if (event.code === 'Backquote') {
    event.preventDefault();
    _wrapSelection(textarea, '`', '`');
  }
  if (event.key === '7' && event.shiftKey) { event.preventDefault(); _prefixLines(textarea, '1. '); }
  if (event.key === '8' && event.shiftKey) { event.preventDefault(); _prefixLines(textarea, '- '); }
});

document.getElementById('essay-content-md').addEventListener('input', _updateWordCount);
