"""EXIF extraction and formatting utilities for the Chami CMS."""

from PIL import ExifTags

ALLOWED_IMAGE_EXTENSIONS = frozenset({'jpg', 'jpeg', 'png', 'gif', 'webp'})


def get_image_ext(filename):
    """Return lowercase extension if the filename has a valid image extension."""
    if '.' in filename:
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext in ALLOWED_IMAGE_EXTENSIONS:
            return ext
    return None


def decimal_to_dms(d):
    """Convert decimal degrees to (deg, min, sec) tuple.
    Always returns positive values; N/S/E/W tags carry the direction."""
    d = abs(d)
    deg = int(d)
    m = (d - deg) * 60
    min_val = int(m)
    sec = (m - min_val) * 60
    return (deg, min_val, sec)


def dms_to_decimal(value):
    """Convert EXIF DMS (deg, min, sec) tuple to decimal degrees."""
    return float(value[0]) + float(value[1]) / 60.0 + float(value[2]) / 3600.0


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
    """Safely extract GPS coordinates from a PIL EXIF dictionary."""
    if not exif_dict:
        return None
    try:
        gps_info = exif_dict.get_ifd(34853) if hasattr(exif_dict, 'get_ifd') else exif_dict.get(34853)
    except (KeyError, TypeError, ValueError):
        return None
    if not gps_info or not isinstance(gps_info, dict):
        return None
    try:
        lat = dms_to_decimal(gps_info[2])
        if gps_info.get(1, 'N') == 'S':
            lat = -lat
        lng = dms_to_decimal(gps_info[4])
        if gps_info.get(3, 'E') == 'W':
            lng = -lng
        return {'lat': round(lat, 6), 'lng': round(lng, 6)}
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def _format_exif_value(value):
    if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
        value = float(value)
        if value.is_integer():
            value = int(value)
    return str(value)


def _read_exif_ifd(exif_raw, ifd):
    try:
        return exif_raw.get_ifd(ifd)
    except (KeyError, TypeError, ValueError):
        return {}


def _collect_exif_tags(exif_raw):
    tags = {}
    ifds = [exif_raw, _read_exif_ifd(exif_raw, 34665)]
    for source in ifds:
        for key, value in source.items():
            name = ExifTags.TAGS.get(key, key)
            tags[name] = _format_exif_value(value)
    return tags


def _extract_exif_date(tags):
    for date_key in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
        if date_key in tags:
            return str(tags[date_key]).replace(':', '-', 2).rsplit(':', 1)[0]
    return None


def extract_exif(img):
    """Extract camera, lens, exposure, date, and GPS metadata from a PIL image."""
    exif_raw = img.getexif()
    if not exif_raw:
        return {}
    tags = _collect_exif_tags(exif_raw)
    exif_data = {}
    if 'Make' in tags: exif_data['camera'] = tags['Make']
    if 'Model' in tags: exif_data['model'] = tags['Model']
    if 'ExposureTime' in tags: exif_data['shutter'] = format_shutter(tags['ExposureTime'])
    if 'FNumber' in tags: exif_data['aperture'] = format_aperture(tags['FNumber'])
    if 'ISOSpeedRatings' in tags: exif_data['iso'] = tags['ISOSpeedRatings']
    if 'FocalLength' in tags: exif_data['focal'] = format_focal(tags['FocalLength'])
    date = _extract_exif_date(tags)
    if date:
        exif_data['date'] = date
    gps_data = extract_gps(exif_raw)
    if gps_data:
        exif_data['gps'] = gps_data
    return exif_data


def without_camera_model(exif_data):
    """Keep public photo metadata free of camera brand/model fields."""
    return {key: value for key, value in exif_data.items() if key not in ('camera', 'model')}
