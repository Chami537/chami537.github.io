"""Photo metadata persistence helpers."""

import os

from PIL import Image

from backend.data import BASE_DIR
from backend.exif_utils import decimal_to_dms
from backend.storage import repository_for


def set_gps(filename, lat, lng):
    """Write GPS coordinates to a raw photo and synchronize photos.json."""
    filename = os.path.basename(filename)
    path = os.path.join(BASE_DIR, 'raw_photos', filename)
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        return

    with Image.open(path) as img:
        exif = img.getexif()
        exif[34853] = {
            1: 'N' if lat >= 0 else 'S',
            2: decimal_to_dms(lat),
            3: 'E' if lng >= 0 else 'W',
            4: decimal_to_dms(lng),
        }
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(path, 'JPEG', quality=95, exif=exif.tobytes())

    photos_data = repository_for('photos.json').list()

    for photo in photos_data:
        if photo['filename'] == filename:
            photo.setdefault('exif', {})['gps'] = {'lat': round(lat, 6), 'lng': round(lng, 6)}
            break
    else:
        photos_data.append({'filename': filename, 'exif': {'gps': {'lat': round(lat, 6), 'lng': round(lng, 6)}}})

    repository_for('photos.json').save(photos_data)
    print(f"GPS 已写入: {filename}")
    print(f"  纬度: {lat} ({'N' if lat >= 0 else 'S'})")
    print(f"  经度: {lng} ({'E' if lng >= 0 else 'W'})")
    print("  photos.json 已同步更新")
