// Shared AI suggestions for non-essay admin content. Nothing is persisted on apply.

var _adminAiApplySuggestion = null;
var _adminAiSession = null;

function closeAdminAiDialog() {
  document.getElementById('admin-ai-copy-dialog').close();
  _adminAiApplySuggestion = null;
  _adminAiSession = null;
}

function _renderAdminAiSuggestions(title, response, applySuggestion) {
  var dialog = document.getElementById('admin-ai-copy-dialog');
  var options = document.getElementById('admin-ai-copy-options');
  document.getElementById('admin-ai-copy-title').textContent = title;
  document.getElementById('admin-ai-copy-status').textContent =
    (response.style_profile_used ? '已引用文风画像 · ' : '') + '选择后只会改表单，仍需手动保存';
  options.replaceChildren();
  document.getElementById('admin-ai-copy-feedback').hidden = true;
  _adminAiApplySuggestion = applySuggestion;
  var suggestions = response.result.suggestions || [{title: '继续调整后的候选', content: response.result.content}];
  suggestions.forEach(function(suggestion) {
    var card = document.createElement('article');
    card.className = 'admin-ai-copy-option';
    var heading = document.createElement('strong');
    heading.textContent = suggestion.title;
    var content = document.createElement('p');
    content.textContent = suggestion.content;
    if (_adminAiSession && _adminAiSession.original) {
      var diff = document.createElement('div');
      diff.className = 'admin-ai-diff-wrap';
      AdminAiWorkflow.renderDiff(diff, _adminAiSession.original, suggestion.content);
      card.appendChild(diff);
    }
    var apply = document.createElement('button');
    apply.type = 'button';
    apply.className = 'btn btn-primary btn-sm';
    apply.textContent = '应用这个版本';
    apply.addEventListener('click', function() {
      if (_adminAiSession) _adminAiSession.candidate = suggestion.content;
      if (_adminAiApplySuggestion) _adminAiApplySuggestion(suggestion);
      markDirty();
      closeAdminAiDialog();
      toast('已应用到表单，请检查后手动保存');
    });
    card.append(heading, content, apply);
    options.appendChild(card);
  });
  if (_adminAiSession) {
    document.getElementById('admin-ai-copy-feedback').hidden = false;
    document.getElementById('admin-ai-copy-feedback-input').value = '';
  }
  if (!dialog.open) dialog.showModal();
}

async function refineAdminAiCopy() {
  if (!_adminAiSession) return;
  var feedback = document.getElementById('admin-ai-copy-feedback-input').value.trim();
  if (!feedback) return toast('请先写一句具体调整要求', true);
  if (!_adminAiSession.candidate) return toast('请先选择一个候选版本', true);
  if (!AdminAiWorkflow.isSnapshotCurrent(_adminAiSession)) {
    return toast('当前内容已变化，请重新请求 AI', true);
  }
  var button = document.getElementById('admin-ai-copy-refine');
  button.disabled = true;
  try {
    var response = await api('POST', '/api/ai/admin-assist', {
      task: 'refine',
      context: {
        domain: _adminAiSession.domain,
        source_task: _adminAiSession.task,
        source_content: _adminAiSession.original,
        candidate: _adminAiSession.candidate,
        feedback: feedback
      }
    });
    _adminAiSession.candidate = response.result.content;
    _renderAdminAiSuggestions('AI 继续调整', response, _adminAiApplySuggestion);
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function _requestAdminAiCopy(task, context, title, applySuggestion) {
  var dialog = document.getElementById('admin-ai-copy-dialog');
  document.getElementById('admin-ai-copy-title').textContent = title;
  document.getElementById('admin-ai-copy-status').textContent = 'DeepSeek 正在处理…';
  document.getElementById('admin-ai-copy-options').replaceChildren();
  var original = context.content || context.description || context.caption || '';
  _adminAiSession = AdminAiWorkflow.createSession({
    domain: task,
    task: task,
    recordId: context.id || context.name || '',
    original: original,
    snapshot: original,
    getCurrent: function() {
      if (task === 'about') return document.getElementById('about-content').value;
      if (task === 'project') return document.getElementById('work-desc').value;
      return original;
    }
  });
  document.getElementById('admin-ai-copy-refine').onclick = refineAdminAiCopy;
  if (!dialog.open) dialog.showModal();
  try {
    var response = await api('POST', '/api/ai/admin-assist', {
      task: task,
      context: context
    });
    if (response.result.suggestions && response.result.suggestions[0]) {
      _adminAiSession.candidate = response.result.suggestions[0].content;
    }
    _renderAdminAiSuggestions(title, response, applySuggestion);
  } catch (error) {
    closeAdminAiDialog();
    toast(error.message, true);
  }
}

function aiImproveAbout() {
  var content = document.getElementById('about-content').value.trim();
  if (!content) return toast('请先填写简介', true);
  _requestAdminAiCopy('about', {
    content: content,
    tags: document.getElementById('about-tags').value.split(/[,，]/).map(function(tag) {
      return tag.trim();
    }).filter(Boolean)
  }, 'AI 简介建议', function(suggestion) {
    document.getElementById('about-content').value = suggestion.content;
  });
}

function aiImproveWork() {
  var title = document.getElementById('work-title').value.trim();
  var description = document.getElementById('work-desc').value.trim();
  if (!title && !description) return toast('请先填写项目标题或描述', true);
  _requestAdminAiCopy('project', {
    title: title,
    description: description,
    repo: document.getElementById('work-repo').value.trim(),
    tags: document.getElementById('work-tags').value.split(',').map(function(tag) {
      return tag.trim();
    }).filter(Boolean)
  }, 'AI 项目描述建议', function(suggestion) {
    document.getElementById('work-desc').value = suggestion.content;
  });
}

function aiSuggestPhotoStory(storyIndex) {
  var story = _storyData[storyIndex];
  if (!story) return;
  if (!(story.caption || '').trim()) {
    return toast('请先写一句照片故事简介，AI 看不到照片画面', true);
  }
  var photoContext = (story.photos || []).map(function(filename) {
    var photo = (_photoData || []).find(function(item) { return item.filename === filename; });
    return photo ? {date: photo.date || '', tags: photo.tags || []} : {};
  });
  _requestAdminAiCopy('photo_story', {
    name: story.name || '',
    date: story.date || '',
    caption: story.caption || '',
    photos: photoContext
  }, 'AI 照片故事建议', function(suggestion) {
    story.caption = suggestion.content;
    renderStoryEditor();
  });
}

function _renderAdminAiAudit(findings) {
  var results = document.getElementById('admin-ai-audit-results');
  results.replaceChildren();
  findings.forEach(function(finding) {
    var item = document.createElement('article');
    item.className = 'admin-ai-finding';
    item.dataset.priority = finding.priority;
    var area = document.createElement('strong');
    area.textContent = finding.area + '：';
    var issue = document.createTextNode(finding.issue + ' ');
    var suggestion = document.createElement('span');
    suggestion.textContent = '建议：' + finding.suggestion;
    item.append(area, issue, suggestion);
    if (finding.locator) {
      var open = document.createElement('button');
      open.type = 'button';
      open.className = 'btn btn-sm';
      open.textContent = '去处理';
      open.addEventListener('click', function() { openAdminFinding(finding); });
      item.appendChild(open);
    }
    if (finding.can_suggest) {
      var suggest = document.createElement('button');
      suggest.type = 'button';
      suggest.className = 'btn btn-sm';
      suggest.textContent = '生成候选';
      suggest.addEventListener('click', function() { suggestAdminFinding(finding); });
      item.appendChild(suggest);
    }
    results.appendChild(item);
  });
  if (!findings.length) results.appendChild(_dashboardEmpty('未发现明显的内容问题'));
}

function openAdminFinding(finding) {
  var locator = finding && finding.locator;
  if (!locator) return;
  if (locator.domain === 'project') {
    switchTab('work');
    editWork(Number(locator.record_id));
  } else if (locator.domain === 'essay') {
    switchTab('essays');
    editEssayMeta(locator.record_id);
    setTimeout(function() {
      var field = document.getElementById('essay-' + locator.field);
      if (field) field.focus();
    }, 300);
  } else if (locator.domain === 'about') {
    switchTab('about');
    setTimeout(function() { document.getElementById('about-content').focus(); }, 150);
  }
}

function suggestAdminFinding(finding) {
  var locator = finding && finding.locator;
  if (!locator || !finding.can_suggest) return;
  openAdminFinding(finding);
  setTimeout(function() {
    if (locator.domain === 'project') aiImproveWork();
    if (locator.domain === 'about') aiImproveAbout();
  }, 450);
}

async function runSiteContentAudit() {
  var button = document.getElementById('admin-ai-audit-button');
  button.disabled = true;
  document.getElementById('admin-ai-audit-status').textContent = 'DeepSeek 正在巡检公开内容…';
  document.getElementById('admin-ai-audit-results').replaceChildren();
  try {
    var response = await api('POST', '/api/ai/site-content-audit', {});
    _renderAdminAiAudit(response.result.findings || []);
    document.getElementById('admin-ai-audit-status').textContent =
      '巡检完成 · ' + (response.usage.prompt_tokens || 0) + '输入 / ' +
      (response.usage.completion_tokens || 0) + '输出 tokens';
  } catch (error) {
    document.getElementById('admin-ai-audit-status').textContent = '巡检失败';
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}
