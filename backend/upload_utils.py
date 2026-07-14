"""Shared upload validation helpers for admin file endpoints."""

from PIL import Image
from flask import jsonify
from xml.etree import ElementTree

from backend.data import get_image_ext

MAX_IMAGE_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_MUSIC_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_GPX_UPLOAD_BYTES = 5 * 1024 * 1024


class UploadValidationError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def upload_error_response(exc):
    return jsonify({"error": str(exc)}), exc.status


def _file_size(file_storage):
    stream = file_storage.stream
    pos = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(pos)
    return size


def _require_file(file_storage):
    if file_storage is None:
        raise UploadValidationError("No file")
    if not file_storage.filename:
        raise UploadValidationError("No filename")


def validate_image_upload(file_storage):
    """Validate an uploaded image and return (extension, opened Pillow image)."""
    _require_file(file_storage)
    ext = get_image_ext(file_storage.filename)
    if not ext:
        raise UploadValidationError("不支持的文件类型")
    if _file_size(file_storage) > MAX_IMAGE_UPLOAD_BYTES:
        raise UploadValidationError("File too large", 413)

    try:
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        img.load()
        file_storage.stream.seek(0)
    except Exception as exc:
        file_storage.stream.seek(0)
        raise UploadValidationError("Invalid or corrupted image file") from exc
    return ext, img


def validate_music_upload(file_storage):
    """Validate an uploaded MP3 and return its lowercase extension."""
    _require_file(file_storage)
    filename = file_storage.filename.lower()
    if not filename.endswith('.mp3'):
        raise UploadValidationError("Only .mp3 files")
    if _file_size(file_storage) > MAX_MUSIC_UPLOAD_BYTES:
        raise UploadValidationError("File too large", 413)

    pos = file_storage.stream.tell()
    header = file_storage.stream.read(16)
    file_storage.stream.seek(pos)
    has_id3 = header.startswith(b'ID3')
    has_frame_sync = len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
    if not (has_id3 or has_frame_sync):
        raise UploadValidationError("Invalid MP3 file")
    return 'mp3'


def validate_gpx_upload(file_storage):
    """Validate a small GPX XML upload without resolving external resources."""
    _require_file(file_storage)
    if not file_storage.filename.lower().endswith('.gpx'):
        raise UploadValidationError("Only .gpx files")
    if _file_size(file_storage) > MAX_GPX_UPLOAD_BYTES:
        raise UploadValidationError("File too large", 413)
    try:
        root = ElementTree.parse(file_storage.stream).getroot()
    except (ElementTree.ParseError, OSError, ValueError) as exc:
        file_storage.stream.seek(0)
        raise UploadValidationError("Invalid GPX file") from exc
    finally:
        file_storage.stream.seek(0)
    if root.tag.rsplit('}', 1)[-1].lower() != 'gpx':
        raise UploadValidationError("Invalid GPX file")
    return 'gpx'
