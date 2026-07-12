function _dashboardSetState(state, message) {
  document.getElementById('dashboard-loading').hidden = state !== 'loading';
  document.getElementById('dashboard-error').hidden = state !== 'error';
  document.getElementById('dashboard-content').hidden = state !== 'ready';
  if (state === 'error') document.getElementById('dashboard-error').textContent = message;
}

function _dashboardText(value) {
  return value == null ? '' : String(value);
}

function _dashboardCount(label, value) {
  var item = document.createElement('div');
  item.className = 'dashboard-count-item';
  var number = document.createElement('strong');
  number.textContent = _dashboardText(value);
  var caption = document.createElement('span');
  caption.textContent = label;
  item.append(number, caption);
  return item;
}

function _dashboardRow(label, value) {
  var row = document.createElement('div');
  row.className = 'dashboard-stat-row';
  var name = document.createElement('span');
  name.textContent = label;
  var count = document.createElement('strong');
  count.textContent = _dashboardText(value);
  row.append(name, count);
  return row;
}

function _dashboardEmpty(message) {
  var empty = document.createElement('p');
  empty.className = 'text-muted dashboard-empty';
  empty.textContent = message;
  return empty;
}

function _renderDashboard(data) {
  var counts = data.counts || {};
  var essays = counts.essays || {};
  var countItems = [
    ['随笔', essays.total], ['照片', counts.photos], ['照片故事', counts.photo_stories],
    ['地点', counts.places], ['项目', counts.work], ['音乐', counts.music],
    ['朋友', counts.friends], ['技术栈', counts.stack]
  ];
  var countBox = document.getElementById('dashboard-counts');
  countBox.replaceChildren();
  countItems.forEach(function(item) { countBox.appendChild(_dashboardCount(item[0], item[1])); });

  var statusBox = document.getElementById('dashboard-essay-status');
  statusBox.replaceChildren();
  [['公开', essays.public], ['加密', essays.encrypted]].forEach(function(item) {
    statusBox.appendChild(_dashboardRow(item[0], item[1]));
  });

  function renderTagList(id, tags) {
    var tagBox = document.getElementById(id);
    tagBox.replaceChildren();
    (tags || []).forEach(function(tag) {
      var row = document.createElement('div');
      row.className = 'dashboard-tag-row';
      var name = document.createElement('span');
      name.textContent = tag.name;
      var count = document.createElement('strong');
      count.textContent = tag.count;
      row.append(name, count);
      tagBox.appendChild(row);
    });
    if (!tagBox.children.length) tagBox.appendChild(_dashboardEmpty('暂无标签'));
  }
  var tags = data.tags || {};
  renderTagList('dashboard-primary-tags', tags.primary);
  renderTagList('dashboard-secondary-tags', tags.secondary);

  var recentBox = document.getElementById('dashboard-recent');
  recentBox.replaceChildren();
  (data.recent || []).forEach(function(item) {
    var link = document.createElement('a');
    link.className = 'dashboard-recent-item';
    link.href = item.url || '#';
    var title = document.createElement('strong');
    title.textContent = item.title || '未命名';
    var meta = document.createElement('span');
    meta.textContent = (item.type === 'photo_story' ? '照片故事' : '随笔') + ' · ' + _dashboardText(item.date);
    link.append(title, meta);
    recentBox.appendChild(link);
  });
  if (!recentBox.children.length) recentBox.appendChild(_dashboardEmpty('暂无更新'));
}

async function loadDashboard() {
  _dashboardSetState('loading');
  try {
    var data = await api('GET', '/api/dashboard-stats');
    _renderDashboard(data);
    _dashboardSetState('ready');
  } catch (e) {
    _dashboardSetState('error', '统计加载失败：' + (e.message || '未知错误'));
  }
}
