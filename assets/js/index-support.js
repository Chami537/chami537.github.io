// Donation/support card. Payment providers stay configuration-driven.
(function () {
  var dialog = document.getElementById('support-dialog');
  var trigger = document.getElementById('support-trigger');
  var methodsEl = document.getElementById('support-methods');
  var statusEl = document.getElementById('support-status');
  if (!dialog || !trigger) return;

  var selectedAmount = 10;
  var methods = [];
  var applePay = null;

  function renderMethods() {
    if (!methods.length) {
      methodsEl.innerHTML = '<div class="support-empty">收款渠道正在准备中，先把这份喜欢收下了。</div>';
    } else {
      methodsEl.innerHTML = methods.map(function (method) {
      var url = safeExternalUrl(method.url);
      var label = htmlEncode(method.label || '支持');
      var description = htmlEncode(method.description || '');
      if (!url) return '<button type="button" class="support-method disabled" disabled><span><strong>' + label + '</strong><small>' + description + '</small></span><em>待接入</em></button>';
      return '<a class="support-method" href="' + htmlEncode(url) + '" target="_blank" rel="noopener noreferrer"><span><strong>' + label + '</strong><small>' + description + '</small></span><em>打开 ↗</em></a>';
      }).join('');
    }
    if (applePay && applePay.enabled) {
      methodsEl.insertAdjacentHTML('afterbegin', '<div class="support-apple-pay-shell"><apple-pay-button id="support-apple-pay" buttonstyle="black" type="plain" locale="zh-CN"></apple-pay-button><small>Apple Pay 官方按钮</small></div>');
      var appleButton = document.getElementById('support-apple-pay');
      if (!window.ApplePaySession || !ApplePaySession.canMakePayments()) {
        appleButton.setAttribute('disabled', '');
        appleButton.parentElement.classList.add('disabled');
        appleButton.parentElement.querySelector('small').textContent = '当前设备或浏览器暂不支持';
      } else {
        appleButton.addEventListener('click', beginApplePay);
      }
    }
  }

  function beginApplePay() {
    if (!applePay.merchantValidationEndpoint) {
      statusEl.textContent = 'Apple Pay 尚未配置商户验证接口。';
      return;
    }
    statusEl.textContent = '正在准备 Apple Pay…';
    var request = { countryCode: applePay.countryCode || 'CN', currencyCode: applePay.currencyCode || 'CNY', total: { label: 'Chami', amount: selectedAmount.toFixed(2) }, supportedNetworks: ['visa', 'masterCard', 'amex'], merchantCapabilities: ['supports3DS'] };
    var session;
    try { session = new ApplePaySession(3, request); } catch (error) { statusEl.textContent = 'Apple Pay 暂不可用，请稍后再试。'; return; }
    session.onvalidatemerchant = function (event) {
      fetch(applePay.merchantValidationEndpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ validationURL: event.validationURL }) })
        .then(function (response) { if (!response.ok) throw new Error('merchant validation failed'); return response.json(); })
        .then(function (merchantSession) { session.completeMerchantValidation(merchantSession); })
        .catch(function () { statusEl.textContent = '商户验证失败，未发起支付。'; session.abort(); });
    };
    session.onpaymentauthorized = function () {
      statusEl.textContent = '已收到支付凭证，等待服务端处理…';
      session.completePayment(ApplePaySession.STATUS_FAILURE);
      statusEl.textContent = '服务端支付处理尚未启用，本次未扣款。';
    };
    session.oncancel = function () { statusEl.textContent = '已取消支付。'; };
    session.begin();
  }

  function open() {
    dialog.hidden = false;
    requestAnimationFrame(function () { dialog.classList.add('show'); });
    document.body.classList.add('support-dialog-open');
    statusEl.textContent = '选择金额后打开收款渠道。';
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
      statusEl.textContent = '已选择 ¥' + selectedAmount + '，请选择收款渠道。';
    });
  });

  fetch('data/support.json?v=' + (window.TS || Date.now())).then(function (response) {
    return response.ok ? response.json() : null;
  }).then(function (data) {
    if (!data) return;
    if (data.title) document.getElementById('support-dialog-title').textContent = data.title;
    if (data.description) document.getElementById('support-description').textContent = data.description;
    methods = Array.isArray(data.methods) ? data.methods : [];
    applePay = data.applePay || null;
    renderMethods();
  }).catch(function () { renderMethods(); });
  renderMethods();
}());
