// Shared AI suggestions for non-essay admin content. Nothing is persisted on apply.

var _adminAiApplySuggestion = null;

function closeAdminAiDialog() {
  document.getElementById('admin-ai-copy-dialog').close();
  _adminAiApplySuggestion = null;
}

function _renderAdminAiSuggestions(title, response, applySuggestion) {
  var dialog = document.getElementById('admin-ai-copy-dialog');
  var options = document.getElementById('admin-ai-copy-options');
  document.getElementById('admin-ai-copy-title').textContent = title;
  document.getElementById('admin-ai-copy-status').textContent =
    (response.style_profile_used ? '已引用文风画像 · ' : '') + '选择后只会改表单，仍需手动保存';
  options.replaceChildren();
  _adminAiApplySuggestion = applySuggestion;
  response.result.suggestions.forEach(function(suggestion) {
    var card = document.createElement('article');
    card.className = 'admin-ai-copy-option';
    var heading = document.createElement('strong');
    heading.textContent = suggestion.title;
    var content = document.createElement('p');
    content.textContent = suggestion.content;
    var apply = document.createElement('button');
    apply.type = 'button';
    apply.className = 'btn btn-primary btn-sm';
    apply.textContent = '应用这个版本';
    apply.addEventListener('click', function() {
      if (_adminAiApplySuggestion) _adminAiApplySuggestion(suggestion);
      markDirty();
      closeAdminAiDialog();
      toast('已应用到表单，请检查后手动保存');
    });
    card.append(heading, content, apply);
    options.appendChild(card);
  });
  if (!dialog.open) dialog.showModal();
}

async function _requestAdminAiCopy(task, context, title, applySuggestion) {
  var dialog = document.getElementById('admin-ai-copy-dialog');
  document.getElementById('admin-ai-copy-title').textContent = title;
  document.getElementById('admin-ai-copy-status').textContent = 'DeepSeek 正在处理…';
  document.getElementById('admin-ai-copy-options').replaceChildren();
  if (!dialog.open) dialog.showModal();
  try {
    var response = await api('POST', '/api/ai/admin-assist', {
      task: task,
      context: context
    });
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
    results.appendChild(item);
  });
  if (!findings.length) results.appendChild(_dashboardEmpty('未发现明显的内容问题'));
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
