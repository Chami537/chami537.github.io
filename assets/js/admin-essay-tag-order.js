// Drag-to-reorder behavior for essay tag rows.

var _tagDragSrc = null;
var _tagJustDragged = false;

function tagDragStart(event) {
  _tagDragSrc = event.currentTarget;
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData('text/plain', event.currentTarget.getAttribute('data-tag'));
}

function tagDragOver(event) {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
}

async function tagDrop(event) {
  event.preventDefault();
  event.stopPropagation();
  _tagJustDragged = true;
  setTimeout(function() { _tagJustDragged = false; }, 200);
  var source = _tagDragSrc;
  var destination = event.currentTarget;
  if (!source || !destination || source === destination) return;
  var sourceTag = source.getAttribute('data-tag');
  var destinationTag = destination.getAttribute('data-tag');
  if (!sourceTag && !destinationTag) return;
  var row = destination.closest('.essay-tag-row') || document;
  var ordered = [];
  row.querySelectorAll('.tag-tab-btn').forEach(function(chip) {
    var tag = chip.getAttribute('data-tag');
    if (tag) ordered.push(tag);
  });
  var sourceIndex = ordered.indexOf(sourceTag);
  var destinationIndex = ordered.indexOf(destinationTag);
  if (sourceIndex < 0 || destinationIndex < 0) return;
  ordered.splice(sourceIndex, 1);
  ordered.splice(destinationIndex, 0, sourceTag);
  await saveTagOrder(_mergeVisibleTagOrder(ordered));
  var selectedTag = ordered[Math.min(destinationIndex, ordered.length - 1)];
  if (row.id === 'essay-type-tabs') currentEssayTypeTag = selectedTag || currentEssayTypeTag;
  else if (row.id === 'essay-subtag-tabs') currentEssayChildTag = selectedTag || currentEssayChildTag;
  else currentEssayTag = selectedTag || currentEssayTag;
  window['essay' + 'Entry']();
}

async function saveTagOrder(order) {
  try {
    await api('PUT', '/api/tags/order', {order: order});
  } catch (error) {
    toast('保存标签顺序失败', true);
  }
}

function _mergeVisibleTagOrder(visibleOrder) {
  var visibleSet = new Set(visibleOrder);
  var merged = [];
  var inserted = false;
  _essayTagOrder.forEach(function(tag) {
    if (visibleSet.has(tag)) {
      if (!inserted) {
        merged = merged.concat(visibleOrder);
        inserted = true;
      }
      return;
    }
    merged.push(tag);
  });
  if (!inserted) merged = merged.concat(visibleOrder);
  return _uniqueEssayTags(merged);
}
