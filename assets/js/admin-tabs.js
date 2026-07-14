// Admin tab orchestration. Domain modules provide the load functions.
function _activateTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  var tabBtn = document.querySelector('.tab-btn[data-tab="' + name + '"]');
  if (tabBtn) tabBtn.classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
}

function _loadTab(name) {
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
