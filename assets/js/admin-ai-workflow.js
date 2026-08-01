/* Shared, in-memory review helpers for AI candidates. Nothing is persisted here. */
(function() {
  function tokenize(value) {
    return String(value || '').match(/\s+|[\u4e00-\u9fff]|[A-Za-z0-9_]+|[^\s\w]/g) || [];
  }

  function renderDiff(container, original, candidate) {
    container.replaceChildren();
    var left = document.createElement('pre');
    var right = document.createElement('pre');
    left.className = 'admin-ai-diff admin-ai-diff-old';
    right.className = 'admin-ai-diff admin-ai-diff-new';
    var oldTokens = tokenize(original);
    var newTokens = tokenize(candidate);
    var oldText = oldTokens.join('');
    var newText = newTokens.join('');
    if (oldText.length + newText.length > 16000) {
      left.textContent = original;
      right.textContent = candidate;
      container.append(left, right);
      return;
    }
    var common = 0;
    while (common < oldTokens.length && common < newTokens.length &&
      oldTokens[common] === newTokens[common]) common++;
    var suffix = 0;
    while (suffix < oldTokens.length - common && suffix < newTokens.length - common &&
      oldTokens[oldTokens.length - 1 - suffix] === newTokens[newTokens.length - 1 - suffix]) suffix++;
    var oldMiddle = oldTokens.slice(common, oldTokens.length - suffix).join('');
    var newMiddle = newTokens.slice(common, newTokens.length - suffix).join('');
    left.appendChild(document.createTextNode(oldTokens.slice(0, common).join('')));
    if (oldMiddle) {
      var removed = document.createElement('mark');
      removed.className = 'admin-ai-diff-removed';
      removed.textContent = oldMiddle;
      left.appendChild(removed);
    }
    left.appendChild(document.createTextNode(oldTokens.slice(oldTokens.length - suffix).join('')));
    right.appendChild(document.createTextNode(newTokens.slice(0, common).join('')));
    if (newMiddle) {
      var added = document.createElement('mark');
      added.className = 'admin-ai-diff-added';
      added.textContent = newMiddle;
      right.appendChild(added);
    }
    right.appendChild(document.createTextNode(newTokens.slice(newTokens.length - suffix).join('')));
    container.append(left, right);
  }

  function createSession(options) {
    return {
      domain: options.domain,
      task: options.task,
      recordId: options.recordId || '',
      original: options.original || '',
      candidate: options.candidate || '',
      snapshot: options.snapshot,
      getCurrent: options.getCurrent,
      controller: null
    };
  }

  function isSnapshotCurrent(session) {
    return typeof session.getCurrent !== 'function' || session.getCurrent() === session.snapshot;
  }

  window.AdminAiWorkflow = {
    createSession: createSession,
    isSnapshotCurrent: isSnapshotCurrent,
    renderDiff: renderDiff,
    abort: function(session) {
      if (session && session.controller) session.controller.abort();
    }
  };
})();
