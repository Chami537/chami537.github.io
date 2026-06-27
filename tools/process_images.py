"""Process raw photos into multiple sizes and update photos.json.
Usage: python process_images.py   or   python manage.py process-images
"""
import os
import json
from PIL import Image, ExifTags

RAW_DIR = 'raw_photos'
IMG_DIR = 'images'
DATA_FILE = 'data/photos.json'
SIZES = {'sm': 400, 'md': 800, 'lg': 1920}


def format_shutter(val):
    try:
        v = float(val)
        if 0 < v < 1:
            return f"1/{int(round(1/v))}s"
        return f"{int(v)}s" if v.is_integer() else f"{v}s"
    except (ValueError, TypeError):
        return str(val)


def format_aperture(val):
    try:
        return f"f/{float(val):g}"
    except (ValueError, TypeError):
        return str(val)


def format_focal(val):
    try:
        return f"{int(float(val))}mm"
    except (ValueError, TypeError):
        return str(val)


def extract_gps(exif_dict):
    """从 _getexif() 原始字典中安全提取 GPS 经纬度 (Tag 34853 = GPSInfo)"""
    if not exif_dict or 34853 not in exif_dict:
        return None
    gps_info = exif_dict[34853]
    try:
        def dms_to_decimal(value):
            return float(value[0]) + (float(value[1]) / 60.0) + (float(value[2]) / 3600.0)

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
    if not os.path.exists(RAW_DIR):
        os.makedirs(RAW_DIR)
        print(f"已创建 {RAW_DIR}/ 文件夹，请将原图放入后重试。")
        return

    for size in SIZES:
        os.makedirs(os.path.join(IMG_DIR, size), exist_ok=True)

    photos_data = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            photos_data = json.load(f)

    existing_files = {p['filename'] for p in photos_data}
    new_count = 0

    for filename in sorted(os.listdir(RAW_DIR)):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        if filename in existing_files:
            continue

        raw_path = os.path.join(RAW_DIR, filename)
        print(f"处理: {filename} ...")

        try:
            with Image.open(raw_path) as img:
                exif_info = extract_exif(img)

                if img.mode != 'RGB':
                    img = img.convert('RGB')

                for size_name, max_width in SIZES.items():
                    ratio = max_width / float(img.size[0])
                    if ratio < 1:
                        new_h = int(float(img.size[1]) * ratio)
                        resized = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
                    else:
                        resized = img.copy()
                    save_path = os.path.join(IMG_DIR, size_name, filename)
                    resized.save(save_path, 'JPEG', quality=85)

                photos_data.append({"filename": filename, "exif": exif_info})
                new_count += 1

        except Exception as e:
            print(f"  出错: {e}")

    if new_count > 0:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(photos_data, f, ensure_ascii=False, indent=2)
        print(f"完成！导入 {new_count} 张新照片。")
    else:
        print("没有发现需要处理的新照片。")


if __name__ == "__main__":
    process_all_images()
