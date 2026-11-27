"""Process raw photos into multiple sizes and update photos.json.
Usage: python process_images.py   or   python manage.py process-images

Now works as a sync tool: processes ALL raw_photos files, re-extracts EXIF,
updates photos.json entries. Skips thumbnail generation for already-existing
thumbnails to save time.
"""
import os
import sys
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.repositories import PHOTO_REPOSITORY
from backend.ssg import _parse_date
from backend.exif_utils import extract_exif as _extract_exif, without_camera_model as _without_camera_model
from backend.image_utils import PHOTO_SIZES, photo_dimensions, write_photo_variants

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'raw_photos')
IMG_DIR = os.path.join(BASE_DIR, 'images')
SIZES = dict(PHOTO_SIZES)


def _ordered_filenames(existing, raw_files):
    ordered = [filename for filename in existing if filename in raw_files]
    ordered.extend(sorted(raw_files - existing.keys()))
    return ordered


def _build_photo_entry(filename, old_entry, exif_info):
    # Existing metadata may include fields recovered or edited in the admin
    # panel that are no longer present in a re-encoded raw file. Treat it as
    # authoritative and only fill genuinely missing EXIF fields from source.
    preserved_exif = dict((old_entry or {}).get('exif') or {})
    for key, value in exif_info.items():
        if key not in preserved_exif or preserved_exif[key] in (None, ''):
            preserved_exif[key] = value
    entry = {'filename': filename, 'exif': preserved_exif or exif_info}
    date = old_entry.get('date') if old_entry else None
    if not date and exif_info.get('date'):
        date = _parse_date(exif_info['date'])
    if date:
        entry['date'] = date
    if old_entry:
        for field in ('size', 'tags'):
            if field in old_entry:
                entry[field] = old_entry[field]
    return entry


def _prepare_directories():
    if not os.path.exists(RAW_DIR):
        os.makedirs(RAW_DIR)
        print(f"已创建 {RAW_DIR}/ 文件夹，请将原图放入后重试。")
        return False
    for size in SIZES:
        os.makedirs(os.path.join(IMG_DIR, size), exist_ok=True)
    return True


def _write_thumbnails(img, filename):
    write_photo_variants(img, IMG_DIR, filename, SIZES.items(), only_missing=True)


def _process_photo(filename, old_entry):
    raw_path = os.path.join(RAW_DIR, filename)
    with Image.open(raw_path) as img:
        exif_info = _without_camera_model(_extract_exif(img))
        _write_thumbnails(img, filename)
    entry = _build_photo_entry(filename, old_entry, exif_info)
    entry.update(photo_dimensions(IMG_DIR, filename))
    return entry


def _preserve_orphans(existing, photos_data):
    orphaned = 0
    for leftover in existing.values():
        filename = leftover.get('filename', '')
        if os.path.exists(os.path.join(IMG_DIR, 'sm', filename)):
            leftover.update(photo_dimensions(IMG_DIR, filename))
            photos_data.append(leftover)
            continue
        print(f"  [清理] {filename} — 原图已删除且无缩略图，移除")
        orphaned += 1
    return orphaned


def process_all_images():
    """Sync: process ALL raw_photos files, update photos.json with full EXIF.
    Preserves user-set fields (date, size, tags). Generates missing thumbnails."""
    if not _prepare_directories():
        return

    existing = {photo['filename']: photo for photo in PHOTO_REPOSITORY.list()}
    raw_files = {
        filename for filename in os.listdir(RAW_DIR)
        if filename.lower().endswith(('.jpg', '.jpeg', '.png'))
    }
    photos_data = []
    new_count = 0
    updated_count = 0

    for filename in _ordered_filenames(existing, raw_files):
        old_entry = existing.pop(filename, None)
        label = '[新]' if old_entry is None else ('[同步]' if old_entry.get('exif') else '[更新]')
        print(f"{label} {filename} ...")
        try:
            photos_data.append(_process_photo(filename, old_entry))
        except Exception as e:
            print(f"  出错: {e}")
            if old_entry:
                photos_data.append(old_entry)
            continue
        new_count += int(old_entry is None)
        updated_count += int(old_entry is not None and not old_entry.get('exif'))

    orphaned = _preserve_orphans(existing, photos_data)
    concurrent = PHOTO_REPOSITORY.replace_merging(photos_data)
    if concurrent:
        print(f"保留同步期间新增照片 {len(concurrent)} 张。")

    print(f"完成！总计 {len(photos_data)} 张照片，新增 {new_count}，补全 EXIF {updated_count}。" + (f" 清理孤儿条目 {orphaned}。" if orphaned else ""))


def refresh_dimensions():
    """Backfill metadata from published files even when raw_photos is absent."""
    with PHOTO_REPOSITORY.lock:
        photos = PHOTO_REPOSITORY.list()
        measured = 0
        for photo in photos:
            dimensions = photo_dimensions(IMG_DIR, photo['filename'])
            if dimensions:
                photo.update(dimensions)
                measured += 1
        PHOTO_REPOSITORY.save(photos)
    print(f'照片尺寸已更新: {measured}/{len(photos)}')


if __name__ == "__main__":
    if '--refresh-dimensions' in sys.argv:
        refresh_dimensions()
    else:
        process_all_images()
