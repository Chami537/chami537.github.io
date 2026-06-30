"""Process raw photos into multiple sizes and update photos.json.
Usage: python process_images.py   or   python manage.py process-images

Now works as a sync tool: processes ALL raw_photos files, re-extracts EXIF,
updates photos.json entries. Skips thumbnail generation for already-existing
thumbnails to save time.
"""
import os
import sys
import json
from PIL import Image, ExifTags
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.data import atomic_write, dms_to_decimal, format_shutter, format_aperture, format_focal

RAW_DIR = 'raw_photos'
IMG_DIR = 'images'
DATA_FILE = 'data/photos.json'
SIZES = {'sm': 400, 'md': 800, 'lg': 1920}


# format_shutter, format_aperture, format_focal — imported from backend.data


def extract_gps(exif_dict):
    """从 _getexif() 原始字典中安全提取 GPS 经纬度 (Tag 34853 = GPSInfo)"""
    if not exif_dict or 34853 not in exif_dict:
        return None
    gps_info = exif_dict[34853]
    try:
        lat = dms_to_decimal(gps_info[2])
        if gps_info.get(1, 'N') == 'S':
            lat = -lat

        lng = dms_to_decimal(gps_info[4])
        if gps_info.get(3, 'E') == 'W':
            lng = -lng

        return {"lat": round(lat, 6), "lng": round(lng, 6)}
    except Exception:
        return None


def extract_exif(img):
    exif_data = {}
    exif_raw = img._getexif()
    if not exif_raw:
        return exif_data

    tags = {ExifTags.TAGS.get(k, k): str(v) for k, v in exif_raw.items()}

    if 'Model' in tags:
        exif_data['model'] = tags['Model']
    elif 'Make' in tags:
        exif_data['camera'] = tags['Make']
    if 'FocalLength' in tags:
        exif_data['focal'] = format_focal(tags['FocalLength'])
    if 'FNumber' in tags:
        exif_data['aperture'] = format_aperture(tags['FNumber'])
    if 'ExposureTime' in tags:
        exif_data['shutter'] = format_shutter(tags['ExposureTime'])
    if 'ISOSpeedRatings' in tags:
        exif_data['iso'] = tags['ISOSpeedRatings']

    gps_data = extract_gps(exif_raw)
    if gps_data:
        exif_data['gps'] = gps_data

    return exif_data


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
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            for p in json.load(f):
                existing[p['filename']] = p

    photos_data = []
    new_count = 0
    updated_count = 0

    for filename in sorted(os.listdir(RAW_DIR)):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        raw_path = os.path.join(RAW_DIR, filename)
        old_entry = existing.pop(filename, None)
        is_new = old_entry is None
        had_exif = old_entry and 'exif' in old_entry and old_entry['exif']

        print(f"{'[新]' if is_new else '[更新]' if not had_exif else '[同步]'} {filename} ...")

        try:
            with Image.open(raw_path) as img:
                # Always extract EXIF
                exif_info = extract_exif(img)

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
                    if old_entry.get('size'):
                        entry['size'] = old_entry['size']
                    if old_entry.get('tags'):
                        entry['tags'] = old_entry['tags']

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
    atomic_write(DATA_FILE, photos_data)

    print(f"完成！总计 {len(photos_data)} 张照片，新增 {new_count}，补全 EXIF {updated_count}。" + (f" 清理孤儿条目 {orphaned}。" if orphaned else ""))


if __name__ == "__main__":
    process_all_images()
