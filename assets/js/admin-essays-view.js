// Essay list loading and tag navigation rendering.

async function loadEssays() {
  try {
    const data = await api('GET', '/api/essays');
    _essayAllData = data;
    const ordered = await loadEssayTagOrder(data);
    _essayTagOrder = ordered.slice();
    const groups = _essayTechGroups(data);
    const primaryTags = _essayAdminPrimaryTags(ordered, groups.topicSet, groups.typeSet);
    syncEssayFilterState(primaryTags);
    renderEssayTagTabs(ordered, groups, primaryTags);
    renderEssayList(filterEssayData(data));
    updatePinCount(data);
  } catch(e) { toast(e.message, true); }
}

window['essay' + 'Entry'] = loadEssays;
onAdminDataReset(loadEssays);

async function loadEssayTagOrder(data) {
  let ordered = [];
  try { ordered = await api('GET', '/api/tags/order'); }
  catch(e) { console.warn('Failed to load tag order:', e); }
  data.forEach(function(essay) {
    _essayTagParts(essay.tag).forEach(function(tag) {
      if (!ordered.includes(tag)) ordered.push(tag);
    });
  });
  return ordered;
}

function syncEssayFilterState(primaryTags) {
  if (!currentEssayTag && primaryTags.length) currentEssayTag = primaryTags[0];
  if (currentEssayTag !== '技术') {
    currentEssayChildTag = null;
    currentEssayTypeTag = null;
  }
  if (currentEssayTag && !primaryTags.includes(currentEssayTag)) {
    currentEssayTag = primaryTags[0] || null;
    currentEssayChildTag = null;
    currentEssayTypeTag = null;
  }
}

function essayTagButton(tag, active, action, removable) {
  const cls = 'tag-tab-btn' + (active ? ' active' : '');
  if (removable) {
    return '<span class="' + cls + '" style="display:inline-flex;align-items:center;gap:4px">' +
      '<span onclick="' + action + '" style="cursor:pointer;">' + esc(tag) + '</span>' +
      '<span onclick="event.stopPropagation();deleteTagFromTabs(\'' + esc(tag) + '\')" class="tag-tab-del" title="删除标签">×</span></span>';
  }
  return '<span class="' + cls + '" draggable="true" data-tag="' + esc(tag) + '">' + esc(tag) + '</span>';
}

function renderEssayTagGroup(element, tags, allLabel, switchFn) {
  if (!tags.length) {
    element.innerHTML = '';
    element.style.display = 'none';
    return;
  }
  let html = '<span class="tag-tab-btn' + (!switchFn.current ? ' active' : '') + '" draggable="true" data-tag="">' + allLabel + '</span>';
  tags.forEach(function(tag) {
    const active = tag === switchFn.current;
    const action = switchFn.name + '(\'' + esc(tag) + '\')';
    html += essayTagButton(tag, active, action, essayDeleteTagMode);
  });
  element.innerHTML = html;
  element.style.display = 'flex';
}

function renderEssayTagTabs(ordered, groups, primaryTags) {
  const main = document.getElementById('essay-tag-tabs');
  main.innerHTML = primaryTags.map(function(tag) {
    const action = 'switchEssayTag(\'' + esc(tag) + '\')';
    return essayTagButton(tag, tag === currentEssayTag, action, essayDeleteTagMode && !ESSAY_MAIN_TAGS.includes(tag));
  }).join('');

  const childTags = _orderedEssayTags(ordered.filter(t => groups.topicSet.has(t)), ESSAY_TECH_TOPICS);
  const typeTags = _orderedEssayTags(ordered.filter(t => groups.typeSet.has(t)), ESSAY_TECH_TYPES);
  const subTabs = document.getElementById('essay-subtag-tabs');
  const typeTabs = document.getElementById('essay-type-tabs');
  if (currentEssayTag === '技术') {
    renderEssayTagGroup(subTabs, childTags, '全部主题', {name:'switchEssayChildTag', current:currentEssayChildTag});
    renderEssayTagGroup(typeTabs, typeTags, '全部类型', {name:'switchEssayTypeTag', current:currentEssayTypeTag});
  } else {
    renderEssayTagGroup(subTabs, [], '全部主题', {name:'switchEssayChildTag', current:null});
    renderEssayTagGroup(typeTabs, [], '全部类型', {name:'switchEssayTypeTag', current:null});
  }

  document.querySelectorAll('#essay-tag-tabs .tag-tab-btn, #essay-subtag-tabs .tag-tab-btn, #essay-type-tabs .tag-tab-btn').forEach(function(el) {
    el.addEventListener('dragstart', tagDragStart);
    el.addEventListener('dragover', tagDragOver);
    el.addEventListener('drop', tagDrop);
    el.addEventListener('dragend', function() { _tagDragSrc = null; });
    el.addEventListener('click', function() {
      if (_tagJustDragged) return;
      if (el.closest('#essay-type-tabs')) switchEssayTypeTag(el.getAttribute('data-tag'));
      else if (el.closest('#essay-subtag-tabs')) switchEssayChildTag(el.getAttribute('data-tag'));
      else switchEssayTag(el.getAttribute('data-tag'));
    });
  });
}

function filterEssayData(data) {
  return data.filter(function(essay) {
    const tags = _essayTagParts(essay.tag);
    if (!tags.length) return currentEssayTag === '随笔';
    if (currentEssayTag === '技术' && currentEssayChildTag && (!tags.includes('技术') || !tags.includes(currentEssayChildTag))) return false;
    if (currentEssayTag === '技术' && currentEssayTypeTag && (!tags.includes('技术') || !tags.includes(currentEssayTypeTag))) return false;
    return tags.includes(currentEssayTag);
  });
}

function renderEssayList(data) {
  const list = document.getElementById('essay-list');
  if (!data.length) {
    list.innerHTML = '<div class="empty-state">该标签下暂无文章，点击右上角新建</div>';
    return;
  }
  list.innerHTML = data.map(function(e) { return `
    <div class="card${e.password_set ? ' card-password' : ''}">
      <div class="card-header">
        <div class="essay-header-row">
          ${pinBtn(e)}
          <div>
            <div class="card-title">${esc(e.title)}</div>
            <div class="card-meta">${esc(e.date)} · ${e.readTime} min · slug: ${esc(e.slug)}</div>
            <div class="card-meta epigraph">${esc(e.epigraph||'')}</div>
          </div>
        </div>
        <div class="card-actions">
          ${passwordBtn(e)}
          <button class="btn btn-sm" onclick="editEssayMeta('${esc(e.slug)}')">元数据</button>
          <button class="btn btn-sm" onclick="editEssayContent('${esc(e.slug)}')">编辑正文</button>
          <button class="btn btn-sm btn-danger" onclick="deleteEssay('${esc(e.slug)}')">删除</button>
        </div>
      </div>
      <div class="card-meta"><a class="essay-discuss-link" href="https://github.com/Chami537/chami537.github.io/discussions?discussions_q=${esc(e.slug)}" target="_blank" rel="noopener">查看讨论 →</a></div>
    </div>`; }).join('');
}
