"""EXIF formatting utilities for the Chami CMS — GPS conversion, shutter/aperture/focal formatting."""

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
