// Admin tab orchestration. Domain modules provide the load functions.
var _adminTabLoads = {};
var _adminScriptLoads = {};
var _adminScriptVersion = (function() {
  var script = document.querySelector('script[src*="admin-tabs.js"]');
  return script ? new URL(script.src, document.baseURI).search : '';
})();

var _adminTabScripts = {
  work: ['admin-work.js'],
  about: ['admin-about.js'],
  contact: ['admin-social.js'],
  friends: ['admin-social.js'],
  music: ['admin-music.js'],
  stack: ['admin-stack.js'],
  tracks: ['admin-tracks.js'],
  readme: ['admin-readme.js'],
  health: ['admin-health.js'],
  essays: [
    'admin-essay-tag-state.js', 'admin-essay-taxonomy.js', 'admin-essay-tag-order.js',
    'admin-essay-tag-actions.js', 'admin-essay-security.js', 'admin-essay-meta.js',
    'admin-essay-content.js', 'admin-essay-local-sync.js', 'admin-essay-formatting.js',
    'admin-essay-media.js', 'admin-ai.js', 'admin-essays-view.js'
  ],
  photos: [
    'admin-photo-list.js', 'admin-photo-tags.js', 'admin-photo-metadata.js',
    'admin-photo-files.js', 'admin-photo-stories.js', 'admin-upload.js'
  ]
};

function _ensureAdminTabLoaded(name) {
  var scripts = _adminTabScripts[name] || [];
  if (!_adminTabLoads[name]) {
    _adminTabLoads[name] = scripts.reduce(function(chain, filename) {
      return chain.then(function() {
        if (_adminScriptLoads[filename]) return _adminScriptLoads[filename];
        _adminScriptLoads[filename] = new Promise(function(resolve, reject) {
          var script = document.createElement('script');
          script.src = 'assets/js/' + filename + _adminScriptVersion;
          script.onload = resolve;
          script.onerror = function() { reject(new Error('无法加载 ' + filename)); };
          document.body.appendChild(script);
        });
        return _adminScriptLoads[filename];
      });
    }, Promise.resolve());
  }
  return _adminTabLoads[name];
}

// Keep the public function names available for existing inline handlers and integrations.
function _lazyFunction(name, tab) {
  window[name] = function() {
    var args = arguments;
    return _ensureAdminTabLoaded(tab).then(function() {
      return window[name].apply(window, args);
    });
  };
}
_lazyFunction('loadAbout', 'about');
_lazyFunction('loadTracks', 'tracks');
_lazyFunction('loadReadme', 'readme');
function _activateTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  var tabBtn = document.querySelector('.tab-btn[data-tab="' + name + '"]');
  if (tabBtn) {
    tabBtn.classList.add('active');
    tabBtn.scrollIntoView({behavior: 'smooth', block: 'nearest', inline: 'center'});
  }
  document.getElementById('tab-' + name).classList.add('active');
}

async function _loadTab(name) {
  try {
    await _ensureAdminTabLoaded(name);
  } catch (error) {
    if (typeof toast === 'function') toast('页面模块加载失败，请刷新重试', true);
    return;
  }
  if (name === 'dashboard') loadDashboard();
  if (name === 'work') loadWork();
  if (name === 'essays') window['essay' + 'Entry']();
  else clearInterval(window._autosaveInterval);
  if (name === 'photos') loadPhotos();
  if (name === 'about') loadAbout();
  if (name === 'contact') loadContact();
  if (name === 'friends') loadFriends();
  if (name === 'tracks') loadTracks();
  if (name === 'music') loadMusic();
  if (name === 'stack') loadStack();
  if (name === 'git') refreshGitStatus();
  if (name === 'readme') loadReadme();
  if (name === 'health') loadHealth();
}

function switchTab(name) {
  _activateTab(name);
  _loadTab(name);
}
