// Main page section renderers.

function renderFriends(data) {
  var html = '<div class="friends-label">FRIEND</div>';
  data.forEach((f, i) => {
    var href = htmlEncode(f.url);
    if (/^https?:\/\//i.test(f.url)) { html += '<a href="' + href + '">' + htmlEncode(f.name) + '</a>'; }
    else { html += '<span>' + htmlEncode(f.name) + '</span>'; }
  });
  return html;
}

function renderMusic(data) {
  const themes = [
    ['rgba(255,77,77,0.10)', '#ff4d4d'],
    ['rgba(0,102,255,0.10)', '#0066ff'],
    ['rgba(255,184,0,0.10)', '#ffb800'],
    ['rgba(0,200,83,0.10)', '#00c853'],
    ['rgba(156,39,176,0.10)', '#9c27b0'],
  ];
  return data.map((m, i) => {
    var num = String(i + 1).padStart(2, '0');
    var t = themes[i % themes.length];
    return '<div class="music-row" data-src="music/' + htmlEncode(m.filename) + '" style="--theme:' + t[0] + ';--idx-color:' + t[1] + '">' +
      '<span class="idx">' + num + '</span>' +
      '<span class="info"><span class="title">' + htmlEncode(m.title) + '</span>' +
      '<span class="artist">' + htmlEncode(m.artist) + '</span></span>' +
      '<span class="time"></span>' +
      '</div>';
  }).join('');
}

function renderContact(data) {
  return data.map(c => {
    var inner = '<span class="value">' + htmlEncode(c.label) + ' <span style="color:#999;font-weight:400;">' + htmlEncode(c.handle) + '</span></span>';
    if (c.url) {
      return '<a href="' + htmlEncode(c.url) + '" target="_blank" rel="noopener noreferrer" class="contact-row">' + inner + '<span class="arr">→</span></a>';
    }
    return '<div class="contact-row">' + inner + '</div>';
  }).join('');
}

function renderStack(data) {
  var colors = ['#ff4d4d','#ff6d00','#ffb800','#0066ff','#00c853','#9c27b0'];
  return data.map(function(c, i) {
    return '<span class="stack-chip" style="--chip-color:' + colors[i % 6] + '">' + htmlEncode(c) + '</span>';
  }).join('');
}

