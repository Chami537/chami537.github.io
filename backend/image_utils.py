"""Shared photo resizing and measured dimensions; never infer variant widths."""

from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageOps


# The upload path's longest-edge limits are canonical, including portrait photos.
PHOTO_SIZES = (('lg', 1920), ('md', 800), ('sm', 400))


def write_photo_variants(image, image_dir, filename, sizes=PHOTO_SIZES, only_missing=False):
    oriented = ImageOps.exif_transpose(image)
    for name, limit in sizes:
        path = Path(image_dir) / name / filename
        if only_missing and path.is_file():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        thumb = oriented.convert('RGB')
        thumb.thumbnail((limit, limit), Image.Resampling.LANCZOS)
        thumb.save(path, quality=85)


def photo_dimensions(image_dir, filename):
    """Read published variants; width/height describe the largest available one."""
    variants = {}
    for name, _limit in PHOTO_SIZES:
        path = Path(image_dir) / name / filename
        if path.is_file():
            with Image.open(path) as image:
                # EXIF orientation affects the browser's displayed dimensions.
                width, height = image.size
                if image.getexif().get(274) in (5, 6, 7, 8):
                    width, height = height, width
                variants[name] = {'width': width, 'height': height}
    if not variants:
        return {}
    largest = max(variants.values(), key=lambda item: item['width'] * item['height'])
    return {**largest, 'variants': variants}


def local_image_path(url, base_dir):
    """Resolve public image URLs without network access or escaping images/."""
    parsed = urlsplit(url)
    if parsed.netloc and parsed.netloc != 'chami537.github.io':
        return None
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        return None
    relative = unquote(parsed.path).removeprefix('../').lstrip('/')
    if not relative.startswith('images/'):
        return None
    root = (Path(base_dir) / 'images').resolve()
    path = (Path(base_dir) / relative).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def image_dimensions(path):
    try:
        with Image.open(path) as image:
            width, height = image.size
            if image.getexif().get(274) in (5, 6, 7, 8):
                width, height = height, width
            return width, height
    except (OSError, ValueError):
        return None
