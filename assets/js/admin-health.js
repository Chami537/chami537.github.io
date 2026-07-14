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
    _healthState('ready');
  } catch (e) {
    _healthState('error', '健康检查失败：' + (e.message || '未知错误'));
  }
}
