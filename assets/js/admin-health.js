function _healthText(value) {
  return value == null ? '' : String(value);
}

function _healthState(state, message) {
  document.getElementById('health-loading').hidden = state !== 'loading';
  document.getElementById('health-error').hidden = state !== 'error';
  document.getElementById('health-content').hidden = state !== 'ready';
  if (state === 'error') document.getElementById('health-error').textContent = message;
}

function _healthSummary(report) {
  var summary = report.summary || {};
  document.getElementById('health-summary').textContent =
    '通过 ' + _healthText(summary.passed) + ' · 警告 ' + _healthText(summary.warnings) +
    ' · 错误 ' + _healthText(summary.errors);
}

function _healthHistory() {
  try { return JSON.parse(localStorage.getItem('site-health-history') || '[]'); }
  catch (_) { return []; }
}

function _saveHealthHistory(report) {
  var history = _healthHistory();
  history.unshift({
    at: new Date().toISOString(), status: report.status,
    passed: report.summary && report.summary.passed || 0,
    warnings: report.summary && report.summary.warnings || 0,
    errors: report.summary && report.summary.errors || 0
  });
  try { localStorage.setItem('site-health-history', JSON.stringify(history.slice(0, 6))); } catch (_) {}
  _renderHealthHistory();
}

function _renderHealthHistory() {
  var box = document.getElementById('health-history-list');
  if (!box) return;
  box.replaceChildren();
  _healthHistory().forEach(function(item) {
    var row = document.createElement('span');
    row.className = 'health-history-item';
    var date = new Date(item.at);
    row.textContent = (isNaN(date) ? '' : date.toLocaleString()) + ' · ' +
      item.passed + '/' + item.warnings + '/' + item.errors;
    box.appendChild(row);
  });
  if (!box.children.length) box.textContent = '暂无历史记录';
}

function _renderHealthChecks(checks) {
  var box = document.getElementById('health-checks');
  box.replaceChildren();
  (checks || []).forEach(function(check) {
    var item = document.createElement('article');
    item.className = 'health-check health-' + check.status;
    var heading = document.createElement('div');
    heading.className = 'health-check-heading';
    var label = document.createElement('strong');
    label.textContent = check.label;
    var status = document.createElement('span');
    status.className = 'health-status';
    status.textContent = check.status === 'passed' ? '正常' : check.status === 'warning' ? '警告' : '错误';
    heading.append(label, status);
    item.appendChild(heading);
    var message = document.createElement('p');
    message.textContent = check.message;
    item.appendChild(message);
    if (check.details && check.details.length) {
      var details = document.createElement('ul');
      check.details.forEach(function(detail) {
        var row = document.createElement('li');
        row.textContent = detail;
        details.appendChild(row);
      });
      item.appendChild(details);
    }
    box.appendChild(item);
  });
}

async function loadHealth() {
  _healthState('loading');
  try {
    var report = await api('GET', '/api/site-health');
    _healthSummary(report);
    _renderHealthChecks(report.checks);
    _saveHealthHistory(report);
    _healthState('ready');
  } catch (e) {
    _healthState('error', '健康检查失败：' + (e.message || '未知错误'));
  }
}

function filterHealthChecks(status, button) {
  document.querySelectorAll('.health-filter button').forEach(function(item) { item.classList.remove('active'); });
  button.classList.add('active');
  document.querySelectorAll('#health-checks .health-check').forEach(function(item) {
    item.hidden = status !== 'all' && !item.classList.contains('health-' + status);
  });
}
