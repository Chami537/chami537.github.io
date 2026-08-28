// Donation/support card. Payment providers stay configuration-driven.
(function () {
  var dialog = document.getElementById('support-dialog');
  var trigger = document.getElementById('support-trigger');
  var methodsEl = document.getElementById('support-methods');
  var statusEl = document.getElementById('support-status');
  if (!dialog || !trigger) return;

  var methods = [];

  function renderMethods() {
    if (!methods.length) {
      methodsEl.innerHTML = '<div class="support-empty">收款方式准备中</div>';
    } else {
      methodsEl.innerHTML = methods.map(function (method) {
      if (method.type === 'qr' && method.image) {
        return '<div class="support-qr-stage"><button type="button" class="support-qr-card" data-qr-image="' + htmlEncode(method.image) + '"><img src="' + htmlEncode(method.image) + '" alt="' + htmlEncode(method.label || '收款二维码') + '"><strong>' + htmlEncode(method.label || '微信支付') + '</strong><small>' + htmlEncode(method.description || '扫码支持') + '</small></button></div>';
      }
      var url = safeExternalUrl(method.url);
      var label = htmlEncode(method.label || '支持');
      var description = htmlEncode(method.description || '');
      if (!url) return '<button type="button" class="support-method disabled" disabled><span><strong>' + label + '</strong><small>' + description + '</small></span><em>待接入</em></button>';
      return '<a class="support-method" href="' + htmlEncode(url) + '" target="_blank" rel="noopener noreferrer"><span><strong>' + label + '</strong><small>' + description + '</small></span><em>打开 ↗</em></a>';
      }).join('');
      methodsEl.querySelectorAll('[data-qr-image]').forEach(function (button) {
        button.addEventListener('click', function () { openQr(button.dataset.qrImage); });
      });
    }
  }

  function openQr(image) {
    var layer = document.createElement('div');
    layer.className = 'support-qr-lightbox';
    layer.innerHTML = '<button type="button" aria-label="关闭二维码">×</button><img src="' + htmlEncode(image) + '" alt="微信收款二维码"><small>微信扫一扫</small>';
    layer.addEventListener('click', function (event) { if (event.target === layer || event.target.tagName === 'BUTTON') layer.remove(); });
    document.body.appendChild(layer);
  }

  function open() {
    dialog.hidden = false;
    requestAnimationFrame(function () { dialog.classList.add('show'); });
    document.body.classList.add('support-dialog-open');
    statusEl.textContent = '微信扫一扫';
    trigger.setAttribute('aria-expanded', 'true');
    dialog.querySelector('.support-dialog-close').focus();
  }
  function close() {
    dialog.classList.remove('show');
    document.body.classList.remove('support-dialog-open');
    trigger.setAttribute('aria-expanded', 'false');
    setTimeout(function () { dialog.hidden = true; }, 180);
    trigger.focus();
  }

  trigger.addEventListener('click', open);
  dialog.querySelectorAll('[data-support-close]').forEach(function (el) { el.addEventListener('click', close); });
  document.addEventListener('keydown', function (event) { if (event.key === 'Escape' && !dialog.hidden) close(); });
  fetch('data/support.json?v=' + (window.TS || Date.now())).then(function (response) {
    return response.ok ? response.json() : null;
  }).then(function (data) {
    if (!data) return;
    if (data.title) document.getElementById('support-dialog-title').textContent = data.title;
    if (data.description) document.getElementById('support-description').textContent = data.description;
    methods = Array.isArray(data.methods) ? data.methods : [];
    renderMethods();
  }).catch(function () { renderMethods(); });
  renderMethods();
}());
