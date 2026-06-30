"""GPS 标注面板 — 独立运行，不依赖 manage.py
Usage: python gps_panel.py
打开浏览器 → 在地图上点击设置照片的 GPS 坐标
"""
import os
import sys
import webbrowser
import threading
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.data import load_json, atomic_write_json
from backend.ssg import _extract_gps, _set_gps

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'raw_photos')

app = Flask(__name__)


@app.route('/')
def panel():
    return PANEL_HTML


@app.route('/images/<path:subpath>')
def serve_images(subpath):
    return send_from_directory(os.path.join(BASE_DIR, 'images'), subpath)


@app.route('/api/gps/photos')
def list_photos():
    """列出 raw_photos/ 中所有照片及其 GPS 状态"""
    photos = []
    photos_json = load_json('photos.json')
    if os.path.exists(RAW_DIR):
        for fn in sorted(os.listdir(RAW_DIR)):
            if not fn.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            path = os.path.join(RAW_DIR, fn)
            info = {'filename': fn}
            try:
                img = Image.open(path)
                info['size'] = img.size
                for pe in photos_json:
                    if pe.get('filename') == fn and pe.get('date'):
                        info['date'] = pe['date']
                        break
                gps_data = _extract_gps(img._getexif())
                if gps_data:
                    info['gps'] = gps_data
                img.close()
            except Exception as e:
                info['error'] = str(e)
            photos.append(info)
    return jsonify(photos)


@app.route('/api/gps/set-date', methods=['POST'])
def set_date():
    data = request.json
    filename = data.get('filename', '')
    date_val = data.get('date', '').strip()
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400
    photos_data = load_json('photos.json')
    for p in photos_data:
        if p.get('filename') == filename:
            if date_val:
                p['date'] = date_val
            else:
                p.pop('date', None)
            atomic_write_json('photos.json', photos_data)
            return jsonify({'status': 'ok', 'date': date_val})
    # Not in photos.json yet — auto-create entry if file exists in raw_photos/
    if os.path.exists(os.path.join(RAW_DIR, filename)):
        entry = {'filename': filename}
        if date_val:
            entry['date'] = date_val
        photos_data.append(entry)
        atomic_write_json('photos.json', photos_data)
        return jsonify({'status': 'ok', 'date': date_val})
    return jsonify({'error': 'File not found in raw_photos/'}), 404

@app.route('/api/gps/delete', methods=['POST'])
def delete_photo():
    data = request.json
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400
    safe = os.path.basename(filename)
    # Remove from raw_photos/
    rpath = os.path.join(RAW_DIR, safe)
    if os.path.exists(rpath):
        os.remove(rpath)
    # Remove from images/ + lg/md/sm
    for sub in ['', 'lg', 'md', 'sm']:
        ipath = os.path.join(BASE_DIR, 'images', sub, safe)
        if os.path.exists(ipath):
            os.remove(ipath)
    # Remove from photos.json
    pd = load_json('photos.json')
    pd = [p for p in pd if p.get('filename') != filename]
    atomic_write_json('photos.json', pd)
    return jsonify({'status': 'deleted'})



@app.route('/api/gps/set', methods=['POST'])
def set_gps():
    """写入 GPS 到照片 EXIF + 更新 photos.json"""
    data = request.json
    filename = data.get('filename', '')
    lat = data.get('lat')
    lng = data.get('lng')

    if not filename or lat is None or lng is None:
        return jsonify({'error': 'Missing filename/lat/lng'}), 400

    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'File not found'}), 404

    try:
        _set_gps(filename, float(lat), float(lng))
        return jsonify({'status': 'ok', 'lat': lat, 'lng': lng})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


PANEL_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GPS 标注面板</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', system-ui, sans-serif; display: flex; height: 100vh; }
.sidebar {
  width: 340px; min-width: 340px; background: #1a1a1c; color: #e8e6e3;
  display: flex; flex-direction: column; overflow: hidden;
}
.sidebar h1 {
  font-size: 18px; font-weight: 700; padding: 20px 24px 16px;
  border-bottom: 1px solid #2e2e30;
}
.photo-list {
  flex: 1; overflow-y: auto; padding: 12px;
}
.photo-card {
  display: flex; gap: 10px; align-items: center;
  background: #222; border-radius: 8px; padding: 8px; margin-bottom: 8px;
  cursor: pointer; transition: background .2s; border: 2px solid transparent;
}
.photo-card:hover { background: #2a2a2c; }
.photo-card.selected { border-color: #ffb800; background: #2a2a2c; }
.photo-card .thumb {
  width: 56px; height: 56px; object-fit: cover; border-radius: 4px; flex-shrink: 0;
  background: #333;
}
.photo-card .info { min-width: 0; }
.photo-card .name { font-size: 12px; font-weight: 600; word-break: break-all; margin-bottom: 4px; }
.photo-card .meta { font-size: 10px; color: #888; }
.photo-card .meta .has-gps { color: #00c853; font-weight: 700; }
.photo-card .meta .no-gps { color: #666; }
.photo-card .card-del { position: absolute; top: 4px; right: 4px; background: none; border: none; color: #666; font-size: 14px; cursor: pointer; padding: 2px 6px; border-radius: 4px; z-index: 3; }
.photo-card .card-del:hover { color: #ff4d4d; background: rgba(255,77,77,0.15); }
#map { flex: 1; }
.leaflet-crosshair { cursor: crosshair !important; }
.status-bar {
  padding: 12px 24px; border-top: 1px solid #2e2e30;
  font-size: 12px; color: #888; text-align: center;
}

/* Date modal */
.date-modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 9999; justify-content: center; align-items: center; }
.date-modal.show { display: flex; }
.date-modal .modal-card {
  background: #2a2a2c; border-radius: 12px; padding: 24px;
  min-width: 280px; box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.date-modal .modal-card h3 { font-size: 15px; margin-bottom: 16px; color: #fff; }
.date-modal .modal-card input { width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid #555; background: #1a1a1c; color: #fff; font-size: 14px; font-family: inherit; margin-bottom: 16px; }
.date-modal .modal-card .btn-row { display: flex; gap: 8px; justify-content: flex-end; }
.date-modal .modal-card button { padding: 6px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; font-weight: 600; }
.date-modal .modal-card .btn-save { background: #ffb800; color: #000; }
.date-modal .modal-card .btn-cancel { background: #444; color: #ccc; }
</style>
</head>
<body>

<div class="sidebar">
  <h1>📷 GPS 标注面板</h1>
  <div class="photo-list" id="photo-list">加载中...</div>
  <div class="status-bar" id="status">点击左侧照片 → 在地图上点击设定坐标</div>
</div>
<div id="map"></div>

<script>
var currentPhoto = null;
var photos = [];
var marker = null;
var pendingLatLng = null;  // 待保存的坐标
var map = null;

// 加载照片列表（不依赖地图）
function loadPhotos() {
  fetch('/api/gps/photos?v=' + Date.now()).then(function(r) { return r.json(); }).then(function(data) {
    photos = data;
    var html = '';
    data.forEach(function(p) {
      var hasGps = p.gps ? true : false;
      var escFn = p.filename.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
      html += '<div class="photo-card' + (currentPhoto === p.filename ? ' selected' : '') + '" data-filename="' + escFn + '" onclick="selectPhoto(this.dataset.filename)">' +
        '<img src="/images/sm/' + encodeURIComponent(p.filename) + '" class="thumb" loading="lazy">' +
        '<div class="info">' +
          '<div class="name">' + escFn + '</div>' +
          '<div class="meta">' +
            '<span class="card-date" data-filename="' + escFn + '" onclick="event.stopPropagation();editDate(this.dataset.filename, this)">' + (p.date || '\u6dfb\u52a0\u65e5\u671f') + '</span>' +
            ' <button class=\"card-del\" data-fn=\"' + escFn + '\" onclick=\"event.stopPropagation();deletePanelPhoto(this.dataset.fn)\" title=\"删除照片\">\u00d7</button>' +
            (p.size ? p.size[0] + '\u00d7' + p.size[1] + ' \u00b7 ' : '') +
            (hasGps ? '<span class="has-gps">\u5df2\u6807\u6ce8 ' + p.gps.lat + ', ' + p.gps.lng + '</span>' : '<span class="no-gps">\u672a\u6807\u6ce8</span>') +
          '</div>' +
        '</div>' +
      '</div>';
    });
    document.getElementById('photo-list').innerHTML = html || '<div style="color:#666;padding:20px;text-align:center">\u6ca1\u6709\u7167\u7247\uff0c\u8bf7\u5148\u5c06\u539f\u7247\u653e\u5165 raw_photos/</div>';
  }).catch(function(e) {
    document.getElementById('photo-list').innerHTML = '<div style="color:#f44;padding:20px">\u52a0\u8f7d\u5931\u8d25: ' + e.message + '</div>';
  });
}

function setStatus(msg) {
  document.getElementById('status').innerHTML = msg;
}

var MONTHS_ED = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function parseDate(text) {
  var m = text.match(/(\w+) (\d+), (\d{4})/);
  if (!m) return '';
  var mi = MONTHS_ED.indexOf(m[1]);
  if (mi < 0) return '';
  return m[3] + '-' + String(mi+1).padStart(2,'0') + '-' + String(m[2]).padStart(2,'0');
}
function editDate(fn, el) {
  var modal = document.getElementById('date-modal');
  modal._fn = fn;
  modal._cur = el.textContent;
  var iso = parseDate(el.textContent);
  document.getElementById('date-input').value = iso;
  modal.classList.add('show');
}

function saveDate() {
  var modal = document.getElementById('date-modal');
  var val = document.getElementById('date-input').value;
  var fn = modal._fn;
  modal.classList.remove('show');
  if (!val) return;
  var parts = val.split('-');
  var d = new Date(+parts[0], +parts[1] - 1, +parts[2]);
  var display = MONTHS_ED[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
  fetch('/api/gps/set-date', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: fn, date: display})
  }).then(function(r) {
    if (r.ok) loadPhotos();
  });
}

function cancelDate() {
  document.getElementById('date-modal').classList.remove('show');
}

function deletePanelPhoto(fn) {
  if (!confirm('删除 ' + fn + ' 及其所有缩略图？')) return;
  fetch('/api/gps/delete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: fn})
  }).then(function(r) { return r.json(); }).then(function(d) {
    if (d.status === 'deleted') { loadPhotos(); setStatus('已删除 ' + fn); }
  });
}

function selectPhoto(filename) {
  currentPhoto = filename;
  document.querySelectorAll('.photo-card').forEach(function(el) {
    el.classList.toggle('selected', el.querySelector('.name').textContent === filename);
  });
  var p = photos.find(function(x) { return x.filename === filename; });
  if (p && p.gps && map) {
    if (marker) map.removeLayer(marker);
    marker = L.marker([p.gps.lat, p.gps.lng]).addTo(map).bindPopup(
      '<b>' + filename + '</b><br>' + p.gps.lat + ', ' + p.gps.lng
    ).openPopup();
    map.setView([p.gps.lat, p.gps.lng], 15);
  } else if (map) {
    if (marker) { map.removeLayer(marker); marker = null; }
  }
  setStatus('\u5df2\u9009\u4e2d ' + filename + ' \u2014 \u5728\u5730\u56fe\u4e0a\u70b9\u51fb\u8bbe\u5b9a\u5750\u6807');
}


function initMap() {
  if (typeof L === 'undefined') {
    document.getElementById('map').innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#888;font-size:14px;">\u5730\u56fe\u52a0\u8f7d\u5931\u8d25<br>\u8bf7\u68c0\u67e5\u7f51\u7edc\u8fde\u63a5</div>';
    setStatus('\u26a0 \u5730\u56fe\u672a\u52a0\u8f7d\uff0c\u4f46\u7167\u7247\u5217\u8868\u4ecd\u53ef\u4f7f\u7528');
    return;
  }
  map = L.map('map').setView([22.5431, 113.9579], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OSM'
  }).addTo(map);

  map.on('click', function(e) {
    if (!currentPhoto) return;
    var lat = e.latlng.lat.toFixed(6);
    var lng = e.latlng.lng.toFixed(6);

    pendingLatLng = {lat: parseFloat(lat), lng: parseFloat(lng)};

    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lng]).addTo(map).bindPopup(
      '<b>' + currentPhoto + '</b><br>' + lat + ', ' + lng
    ).openPopup();

    setStatus('\u25cf ' + Math.abs(parseFloat(lat)).toFixed(4) + '\u00b0' + (parseFloat(lat) >= 0 ? 'N' : 'S') + ', ' + Math.abs(parseFloat(lng)).toFixed(4) + '\u00b0' + (parseFloat(lng) >= 0 ? 'E' : 'W') + '  <button onclick="saveGps()" style="background:#ffb800;color:#000;border:none;padding:3px 12px;border-radius:4px;cursor:pointer;font-weight:700;margin-left:12px;">\u4fdd\u5b58</button>');
  });
}

function saveGps() {
  if (!currentPhoto || !pendingLatLng) return;
  setStatus('\u4fdd\u5b58\u4e2d...');
  fetch('/api/gps/set', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: currentPhoto, lat: pendingLatLng.lat, lng: pendingLatLng.lng})
  }).then(function(r) { return r.json(); }).then(function(d) {
    if (d.status === 'ok') {
      setStatus('\u2713 ' + currentPhoto + ' \u2192 ' + Math.abs(pendingLatLng.lat).toFixed(4) + '\u00b0' + (pendingLatLng.lat >= 0 ? 'N' : 'S') + ', ' + Math.abs(pendingLatLng.lng).toFixed(4) + '\u00b0' + (pendingLatLng.lng >= 0 ? 'E' : 'W'));
      pendingLatLng = null;
      loadPhotos();
    } else {
      setStatus('\u2717 \u9519\u8bef: ' + (d.error || 'unknown'));
    }
  }).catch(function(e) {
    setStatus('\u2717 \u7f51\u7edc\u9519\u8bef: ' + e.message);
  });
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    currentPhoto = null;
    if (marker && map) { map.removeLayer(marker); marker = null; }
    document.querySelectorAll('.photo-card').forEach(function(el) { el.classList.remove('selected'); });
    setStatus('\u5df2\u53d6\u6d88\u9009\u4e2d');
  }
});

// 先执行照片列表（不等地图）
loadPhotos();

// 动态加载 Leaflet —— 避免 CDN 挂起时阻塞整个页面的 JS 执行
(function () {
  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js';
  s.onload = function () { setTimeout(initMap, 100); };
  s.onerror = function () {
    document.getElementById('map').innerHTML =
      '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#888;font-size:14px;text-align:center">' +
      '地图加载失败<br>请检查网络连接</div>';
    setStatus('\u26a0 地图未加载，但照片列表仍可使用');
  };
  document.head.appendChild(s);
})();
</script>


<div class="date-modal" id="date-modal" onclick="if(event.target===this)cancelDate()">
  <div class="modal-card">
    <h3>修改拍摄日期</h3>
    <input type="date" id="date-input">
    <div class="btn-row">
      <button class="btn-cancel" onclick="cancelDate()">取消</button>
      <button class="btn-save" onclick="saveDate()">保存</button>
    </div>
  </div>
</div>

</body>
</html>'''


if __name__ == '__main__':
    os.makedirs(RAW_DIR, exist_ok=True)
    url = 'http://127.0.0.1:5001'
    print(f"GPS 标注面板 → {url}")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    app.run(host='127.0.0.1', port=5001, debug=False)
