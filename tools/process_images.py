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
from backend.data import load_json, atomic_write_json
from backend.ssg import _parse_date
from backend.exif_utils import extract_exif as _extract_exif, without_camera_model as _without_camera_model

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'raw_photos')
IMG_DIR = os.path.join(BASE_DIR, 'images')
SIZES = {'sm': 400, 'md': 800, 'lg': 1920}


def process_all_images():
    """Sync: process ALL raw_photos files, update photos.json with full EXIF.
    Preserves user-set fields (date, size, tags). Generates missing thumbnails."""
    if not os.path.exists(RAW_DIR):
        os.makedirs(RAW_DIR)
        print(f"已创建 {RAW_DIR}/ 文件夹，请将原图放入后重试。")
        return

    for size in SIZES:
        os.makedirs(os.path.join(IMG_DIR, size), exist_ok=True)

    # Load existing data to preserve user-edited fields (date, size, tags)
    existing = {}
    for p in load_json('photos.json'):
        existing[p['filename']] = p

    photos_data = []
    new_count = 0
    updated_count = 0

    # Preserve order from existing photos.json; append new files at end
    raw_files = {f for f in os.listdir(RAW_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))}
    ordered = [f for f in existing if f in raw_files]
    ordered += [f for f in sorted(raw_files) if f not in existing]

    for filename in ordered:

        raw_path = os.path.join(RAW_DIR, filename)
        old_entry = existing.pop(filename, None)
        is_new = old_entry is None
        had_exif = old_entry and 'exif' in old_entry and old_entry['exif']

        print(f"{'[新]' if is_new else '[更新]' if not had_exif else '[同步]'} {filename} ...")

        try:
            with Image.open(raw_path) as img:
                # Always extract EXIF
                exif_info = _without_camera_model(_extract_exif(img))

                # Generate thumbnails (skip if already exist)
                for size_name, max_width in SIZES.items():
                    out_path = os.path.join(IMG_DIR, size_name, filename)
                    if os.path.exists(out_path):
                        continue  # thumbnail exists, skip
                    if img.mode != 'RGB':
                        rgb_img = img.convert('RGB')
                    else:
                        rgb_img = img
                    ratio = max_width / float(img.size[0])
                    if ratio < 1:
                        new_h = int(float(img.size[1]) * ratio)
                        resized = rgb_img.resize((max_width, new_h), Image.Resampling.LANCZOS)
                    else:
                        resized = rgb_img.copy()
                    resized.save(out_path, 'JPEG', quality=85)

                # Build entry: EXIF from file, user fields from old entry
                entry = {'filename': filename, 'exif': exif_info}
                if old_entry:
                    if old_entry.get('date'):
                        entry['date'] = old_entry['date']
                    elif exif_info.get('date'):
                        entry['date'] = _parse_date(exif_info['date'])
                    for field in ('size', 'tags'):
                        if field in old_entry:
                            entry[field] = old_entry[field]
                elif exif_info.get('date'):
                    entry['date'] = _parse_date(exif_info['date'])

                photos_data.append(entry)
                if is_new:
                    new_count += 1
                elif not had_exif:
                    updated_count += 1

        except Exception as e:
            print(f"  出错: {e}")
            # Keep old entry on failure
            if old_entry:
                photos_data.append(old_entry)

    # Any remaining entries in existing are for files not in raw_photos/
    # Keep only if thumbnails still exist; warn and drop orphans
    orphaned = 0
    for leftover in existing.values():
        fn = leftover.get('filename', '')
        sm_path = os.path.join(IMG_DIR, 'sm', fn)
        if os.path.exists(sm_path):
            photos_data.append(leftover)
        else:
            print(f"  [清理] {fn} — 原图已删除且无缩略图，移除")
            orphaned += 1

    # Atomic write
    atomic_write_json('photos.json', photos_data)

    print(f"完成！总计 {len(photos_data)} 张照片，新增 {new_count}，补全 EXIF {updated_count}。" + (f" 清理孤儿条目 {orphaned}。" if orphaned else ""))


if __name__ == "__main__":
    process_all_images()
