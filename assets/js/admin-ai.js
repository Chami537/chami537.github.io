// DeepSeek editorial suggestions. Results only change local form state after approval.

var _essayAiController = null;
var _essayAiSuggestion = null;
var _essayAiProtected = false;

function _essayAiButtons() {
  return document.querySelectorAll('#essay-ai-actions button');
}

function _essayAiFindEssay(slug) {
  return (_essayAllData || []).find(function(essay) { return essay.slug === slug; });
}

function _resetEssayAiResult() {
  _essayAiSuggestion = null;
  var result = document.getElementById('essay-ai-result');
  result.textContent = '';
  result.hidden = true;
}

function _setEssayAiBusy(busy, message) {
  _essayAiButtons().forEach(function(button) {
    button.disabled = busy || _essayAiProtected;
  });
  if (message) document.getElementById('essay-ai-status').textContent = message;
}

function updateEssayAiAvailability(slug) {
  var panel = document.getElementById('essay-ai-panel');
  if (!panel) return;
  if (panel.dataset.slug !== slug) {
    if (_essayAiController) _essayAiController.abort();
    _essayAiController = null;
    panel.dataset.slug = slug;
    _resetEssayAiResult();
  }
  var essay = slug && _essayAiFindEssay(slug);
  _essayAiProtected = Boolean(essay && essay.password_set);
  _setEssayAiBusy(false, _essayAiProtected
    ? '密码保护文章不会发送给 AI'
    : '选择一项操作，结果不会自动保存');
}

function _essayAiSnapshot(task) {
  var editor = document.getElementById('essay-content-editor');
  var textarea = document.getElementById('essay-content-md');
  var markdown = textarea.value;
  var start = 0;
  var end = markdown.length;
  if (task === 'polish' && textarea.selectionEnd > textarea.selectionStart) {
    start = textarea.selectionStart;
    end = textarea.selectionEnd;
  }
  return {
    slug: editor.dataset.slug,
    markdown: markdown,
    start: start,
    end: end,
    content: markdown.slice(start, end)
  };
}

function _appendEssayAiApply(result, label) {
  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'btn btn-primary btn-sm essay-ai-apply';
  button.textContent = label;
  button.addEventListener('click', applyEssayAiResult);
  result.appendChild(button);
}

function _renderEssayAiResult(task, suggestion) {
  var container = document.getElementById('essay-ai-result');
  container.textContent = '';

  var title = document.createElement('div');
  title.className = 'essay-ai-result-title';
  title.textContent = {
    summary: '摘要建议',
    tags: '标签建议',
    polish: '润色建议',
    review: '检查结果'
  }[task];
  container.appendChild(title);

  if (task === 'tags') {
    var tags = document.createElement('div');
    tags.className = 'essay-ai-tags';
    suggestion.tags.forEach(function(tag) {
      var chip = document.createElement('span');
      chip.className = 'tag';
      chip.textContent = tag;
      tags.appendChild(chip);
    });
    container.appendChild(tags);
    _appendEssayAiApply(container, '应用到标签');
  } else if (task === 'review') {
    var list = document.createElement('ul');
    list.className = 'essay-ai-issue-list';
    if (!suggestion.issues.length) {
      var empty = document.createElement('li');
      empty.textContent = '未发现明显问题';
      list.appendChild(empty);
    }
    suggestion.issues.forEach(function(issue) {
      var item = document.createElement('li');
      var type = document.createElement('strong');
      type.textContent = issue.type + '：';
      item.appendChild(type);
      item.appendChild(document.createTextNode(issue.message + '；建议：' + issue.suggestion));
      list.appendChild(item);
    });
    container.appendChild(list);
  } else {
    var text = document.createElement('p');
    text.className = 'essay-ai-result-text';
    text.textContent = task === 'summary' ? suggestion.excerpt : suggestion.content;
    container.appendChild(text);
    _appendEssayAiApply(container, task === 'summary' ? '应用到摘要' : '替换原文');
  }
  container.hidden = false;
}

async function requestEssayAi(task) {
  if (_essayAiProtected) {
    toast('密码保护文章不能发送给 AI', true);
    return;
  }
  var snapshot = _essayAiSnapshot(task);
  if (!snapshot.slug || !snapshot.content.trim()) {
    toast('请先打开并填写随笔正文', true);
    return;
  }
  var essay = _essayAiFindEssay(snapshot.slug) || {};
  if (_essayAiController) _essayAiController.abort();
  var controller = new AbortController();
  _essayAiController = controller;
  _resetEssayAiResult();
  _setEssayAiBusy(true, 'DeepSeek 正在处理…');

  try {
    var response = await api('POST', '/api/ai/essay-assist', {
      slug: snapshot.slug,
      task: task,
      content: snapshot.content,
      title: essay.title || '',
      existing_tags: _essayTagParts(essay.tag || '')
    }, {signal: controller.signal});
    if (_essayAiController !== controller) return;
    _essayAiSuggestion = {
      task: task,
      result: response.result,
      snapshot: snapshot
    };
    _renderEssayAiResult(task, response.result);
    var usage = response.usage || {};
    _setEssayAiBusy(false, '建议已生成 · ' +
      (usage.prompt_tokens || 0) + ' 输入 / ' +
      (usage.completion_tokens || 0) + ' 输出 tokens');
  } catch (error) {
    if (error.name === 'AbortError') return;
    if (_essayAiController === controller) {
      _setEssayAiBusy(false, '请求失败，可修改内容后重试');
      toast(error.message, true);
    }
  } finally {
    if (_essayAiController === controller) _essayAiController = null;
  }
}

function _openEssayMetaForAi(slug) {
  var essay = _essayAiFindEssay(slug);
  if (!essay) return false;
  _fillEssayMetaForm(essay);
  return true;
}

function applyEssayAiResult() {
  if (!_essayAiSuggestion) return;
  var task = _essayAiSuggestion.task;
  var suggestion = _essayAiSuggestion.result;
  var snapshot = _essayAiSuggestion.snapshot;
  var editor = document.getElementById('essay-content-editor');

  if (editor.dataset.slug !== snapshot.slug) {
    toast('当前文章已变化，请重新请求 AI', true);
    return;
  }
  if (task === 'summary' || task === 'tags') {
    if (!_openEssayMetaForAi(snapshot.slug)) {
      toast('找不到文章元数据', true);
      return;
    }
    if (task === 'summary') {
      document.getElementById('essay-excerpt').value = suggestion.excerpt;
    } else {
      renderEssayTaxonomy(suggestion.tags.join(', '));
    }
  } else if (task === 'polish') {
    var textarea = document.getElementById('essay-content-md');
    if (textarea.value !== snapshot.markdown) {
      toast('正文已变化，请重新请求 AI', true);
      return;
    }
    textarea.value = snapshot.markdown.slice(0, snapshot.start) +
      suggestion.content + snapshot.markdown.slice(snapshot.end);
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = snapshot.start + suggestion.content.length;
    _updateWordCount();
  } else {
    return;
  }

  markDirty();
  var applyButton = document.querySelector('.essay-ai-apply');
  if (applyButton) {
    applyButton.disabled = true;
    applyButton.textContent = '已应用，尚未保存';
  }
  document.getElementById('essay-ai-status').textContent = '已应用到编辑器，请检查后手动保存';
}

document.querySelectorAll('[data-ai-task]').forEach(function(button) {
  button.addEventListener('click', function() {
    requestEssayAi(button.dataset.aiTask);
  });
});
