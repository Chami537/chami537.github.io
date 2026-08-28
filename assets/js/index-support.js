// Donation/support card. Payment providers stay configuration-driven.
(function () {
  var dialog = document.getElementById('support-dialog');
  var trigger = document.getElementById('support-trigger');
  var methodsEl = document.getElementById('support-methods');
  var statusEl = document.getElementById('support-status');
  if (!dialog || !trigger) return;

  var selectedAmount = 10;
  var methods = [];
  var paymentDemo = null;

  function renderMethods() {
    if (!methods.length) {
      methodsEl.innerHTML = '<div class="support-empty">收款方式准备中</div>';
    } else {
      methodsEl.innerHTML = methods.map(function (method) {
      if (method.type === 'qr' && method.image) {
        return '<button type="button" class="support-method support-qr-method" data-qr-image="' + htmlEncode(method.image) + '"><img src="' + htmlEncode(method.image) + '" alt="' + htmlEncode(method.label || '收款二维码') + '"><span><strong>' + htmlEncode(method.label || '微信支付') + '</strong><small>' + htmlEncode(method.description || '扫码支持') + '</small></span><em>查看</em></button>';
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
    if (paymentDemo && paymentDemo.enabled) {
      methodsEl.insertAdjacentHTML('afterbegin', '<button type="button" class="support-method support-pay-button" id="support-pay-button"><span><strong><i aria-hidden="true">⊹</i> 支持</strong><small>确认金额</small></span><em class="support-pay-action">继续</em></button>');
      var payButton = document.getElementById('support-pay-button');
      payButton.addEventListener('click', runSupportAnimation);
    }
  }

  function openQr(image) {
    var layer = document.createElement('div');
    layer.className = 'support-qr-lightbox';
    layer.innerHTML = '<button type="button" aria-label="关闭二维码">×</button><img src="' + htmlEncode(image) + '" alt="微信收款二维码"><small>微信扫一扫</small>';
    layer.addEventListener('click', function (event) { if (event.target === layer || event.target.tagName === 'BUTTON') layer.remove(); });
    document.body.appendChild(layer);
  }

  function runSupportAnimation() {
    var button = document.getElementById('support-pay-button');
    if (!button || button.classList.contains('is-processing')) return;
    button.classList.add('is-processing');
    statusEl.textContent = '确认 ¥' + selectedAmount + '…';
    setTimeout(function () { statusEl.textContent = '处理中…'; }, 520);
    setTimeout(function () { button.classList.remove('is-processing'); statusEl.textContent = '演示完成'; }, 1250);
  }

  function open() {
    dialog.hidden = false;
    requestAnimationFrame(function () { dialog.classList.add('show'); });
    document.body.classList.add('support-dialog-open');
    statusEl.textContent = '选择金额';
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
  dialog.querySelectorAll('[data-support-amount]').forEach(function (button) {
    button.addEventListener('click', function () {
      selectedAmount = Number(button.dataset.supportAmount) || 10;
      dialog.querySelectorAll('[data-support-amount]').forEach(function (item) { item.classList.toggle('active', item === button); });
      statusEl.textContent = '已选 ¥' + selectedAmount;
    });
  });

  fetch('data/support.json?v=' + (window.TS || Date.now())).then(function (response) {
    return response.ok ? response.json() : null;
  }).then(function (data) {
    if (!data) return;
    if (data.title) document.getElementById('support-dialog-title').textContent = data.title;
    if (data.description) document.getElementById('support-description').textContent = data.description;
    methods = Array.isArray(data.methods) ? data.methods : [];
    paymentDemo = data.paymentDemo || null;
    renderMethods();
  }).catch(function () { renderMethods(); });
  renderMethods();
}());
