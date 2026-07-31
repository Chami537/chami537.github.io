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
  var scope = '全文';
  if (task === 'polish') {
    if (textarea.selectionEnd > textarea.selectionStart) {
      start = textarea.selectionStart;
      end = textarea.selectionEnd;
      scope = '选中文字';
    } else {
      var cursor = textarea.selectionStart;
      start = markdown.lastIndexOf('\n\n', Math.max(0, cursor - 1));
      start = start < 0 ? 0 : start + 2;
      end = markdown.indexOf('\n\n', cursor);
      end = end < 0 ? markdown.length : end;
      if (!markdown.slice(start, end).trim()) {
        start = 0;
        end = markdown.length;
        scope = '全文';
      } else {
        scope = '光标所在段落';
      }
    }
  }
  return {
    slug: editor.dataset.slug,
    markdown: markdown,
    start: start,
    end: end,
    content: markdown.slice(start, end),
    scope: scope,
    surroundingContext: task === 'polish' ? {
      before: markdown.slice(Math.max(0, start - 1250), start),
      after: markdown.slice(end, Math.min(markdown.length, end + 1250))
    } : null
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

function _renderEssayAiResult(task, suggestion, snapshot) {
  var container = document.getElementById('essay-ai-result');
  container.textContent = '';

  var title = document.createElement('div');
  title.className = 'essay-ai-result-title';
  title.textContent = {
    summary: '摘要建议',
    tags: '标签建议',
    title: '标题建议',
    polish: '润色建议',
    continue: '续写建议',
    review: '检查结果'
  }[task];
  container.appendChild(title);

  if (task === 'title') {
    var choices = document.createElement('div');
    choices.className = 'essay-ai-title-options';
    suggestion.titles.forEach(function(candidate) {
      var choice = document.createElement('button');
      choice.type = 'button';
      choice.className = 'btn essay-ai-title-choice';
      choice.textContent = candidate;
      choice.addEventListener('click', function() {
        applyEssayAiResult(candidate);
      });
      choices.appendChild(choice);
    });
    container.appendChild(choices);
  } else if (task === 'tags') {
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
    if (task === 'polish') {
      var original = document.createElement('details');
      original.className = 'essay-ai-original';
      var originalLabel = document.createElement('summary');
      originalLabel.textContent = '查看润色前原文';
      var originalText = document.createElement('pre');
      originalText.textContent = snapshot.content;
      original.appendChild(originalLabel);
      original.appendChild(originalText);
      container.appendChild(original);
    }
    var text = document.createElement('p');
    text.className = 'essay-ai-result-text';
    text.textContent = task === 'summary' ? suggestion.excerpt : suggestion.content;
    container.appendChild(text);
    if (task === 'polish' && suggestion.changes && suggestion.changes.length) {
      var changes = document.createElement('ul');
      changes.className = 'essay-ai-change-list';
      suggestion.changes.forEach(function(change) {
        var changeItem = document.createElement('li');
        changeItem.textContent = change;
        changes.appendChild(changeItem);
      });
      container.appendChild(changes);
    }
    if (task === 'polish' && suggestion.content === snapshot.content) {
      var unchanged = document.createElement('div');
      unchanged.className = 'essay-ai-unchanged';
      unchanged.textContent = '原文已经够顺，不建议为了润色而改。';
      container.appendChild(unchanged);
    } else {
      _appendEssayAiApply(container, {
        summary: '应用到摘要',
        polish: '替换原文',
        continue: '追加到正文'
      }[task]);
    }
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
    var payload = {
      slug: snapshot.slug,
      task: task,
      content: snapshot.content,
      title: essay.title || '',
      existing_tags: _essayTagParts(essay.tag || '')
    };
    if (task === 'polish') {
      payload.polish_mode = document.getElementById('essay-ai-polish-mode').value;
      payload.instruction = document.getElementById('essay-ai-instruction').value.trim();
      payload.surrounding_context = snapshot.surroundingContext;
    }
    var response = await api(
      'POST', '/api/ai/essay-assist', payload, {signal: controller.signal}
    );
    if (_essayAiController !== controller) return;
    _essayAiSuggestion = {
      task: task,
      result: response.result,
      snapshot: snapshot
    };
    _renderEssayAiResult(task, response.result, snapshot);
    var usage = response.usage || {};
    var styleCount = response.style_reference_count || 0;
    var styleStatus = task !== 'tags' && styleCount
      ? '已参考 ' + styleCount + ' 篇公开随笔'
      : '通用编辑模式';
    var unchangedStatus = task === 'polish' &&
      response.result.content === snapshot.content ? '无需修改 · ' : '';
    var scopeStatus = task === 'polish' ? snapshot.scope + ' · ' : '';
    _setEssayAiBusy(false, unchangedStatus + scopeStatus + styleStatus + ' · ' +
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

function applyEssayAiResult(titleChoice) {
  if (!_essayAiSuggestion) return;
  var task = _essayAiSuggestion.task;
  var suggestion = _essayAiSuggestion.result;
  var snapshot = _essayAiSuggestion.snapshot;
  var editor = document.getElementById('essay-content-editor');

  if (editor.dataset.slug !== snapshot.slug) {
    toast('当前文章已变化，请重新请求 AI', true);
    return;
  }
  if (task === 'summary' || task === 'tags' || task === 'title') {
    if (!_openEssayMetaForAi(snapshot.slug)) {
      toast('找不到文章元数据', true);
      return;
    }
    if (task === 'summary') {
      document.getElementById('essay-excerpt').value = suggestion.excerpt;
    } else {
      if (task === 'tags') {
        renderEssayTaxonomy(suggestion.tags.join(', '));
      } else if (typeof titleChoice === 'string') {
        document.getElementById('essay-title').value = titleChoice;
      } else {
        return;
      }
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
  } else if (task === 'continue') {
    var continueTextarea = document.getElementById('essay-content-md');
    if (continueTextarea.value !== snapshot.markdown) {
      toast('正文已变化，请重新请求 AI', true);
      return;
    }
    var separator = continueTextarea.value.endsWith('\n\n')
      ? ''
      : (continueTextarea.value.endsWith('\n') ? '\n' : '\n\n');
    continueTextarea.value += separator + suggestion.content;
    continueTextarea.focus();
    continueTextarea.selectionStart = continueTextarea.selectionEnd = continueTextarea.value.length;
    _updateWordCount();
  } else {
    return;
  }

  markDirty();
  if (task === 'title') {
    document.querySelectorAll('.essay-ai-title-choice').forEach(function(button) {
      button.disabled = true;
      if (button.textContent === titleChoice) {
        button.textContent = '已应用 · ' + titleChoice;
      }
    });
  } else {
    var applyButton = document.querySelector('.essay-ai-apply');
    if (applyButton) {
      applyButton.disabled = true;
      applyButton.textContent = '已应用，尚未保存';
    }
  }
  document.getElementById('essay-ai-status').textContent = '已应用到编辑器，请检查后手动保存';
}

document.querySelectorAll('[data-ai-task]').forEach(function(button) {
  button.addEventListener('click', function() {
    requestEssayAi(button.dataset.aiTask);
  });
});
