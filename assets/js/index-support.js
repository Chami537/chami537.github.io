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
    if (paymentDemo && paymentDemo.enabled) {
      methodsEl.insertAdjacentHTML('afterbegin', '<button type="button" class="support-method support-pay-button" id="support-pay-button"><span><strong><i aria-hidden="true">⊹</i> 支持此项目</strong><small>确认金额后继续</small></span><em class="support-pay-action">继续</em></button>');
      var payButton = document.getElementById('support-pay-button');
      payButton.addEventListener('click', runSupportAnimation);
    }
  }

  function runSupportAnimation() {
    var button = document.getElementById('support-pay-button');
    if (!button || button.classList.contains('is-processing')) return;
    button.classList.add('is-processing');
    statusEl.textContent = '正在确认 ¥' + selectedAmount + '…';
    setTimeout(function () { statusEl.textContent = '正在准备支持流程…'; }, 520);
    setTimeout(function () { button.classList.remove('is-processing'); statusEl.textContent = '演示完成，未连接真实支付接口。'; }, 1250);
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
    paymentDemo = data.paymentDemo || null;
    renderMethods();
  }).catch(function () { renderMethods(); });
  renderMethods();
}());
