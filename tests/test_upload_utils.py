from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from backend.upload_utils import save_upload_atomically


def test_save_upload_atomically_creates_parent_and_replaces(tmp_path):
    destination = tmp_path / 'nested' / 'file.bin'
    upload = FileStorage(stream=BytesIO(b'payload'), filename='file.bin')

    save_upload_atomically(upload, str(destination))

    assert destination.read_bytes() == b'payload'
    assert not destination.with_name('file.bin.uploading').exists()


def test_save_upload_atomically_removes_partial_file_on_replace_failure(tmp_path, monkeypatch):
    destination = tmp_path / 'file.bin'
    upload = FileStorage(stream=BytesIO(b'payload'), filename='file.bin')

    def fail_replace(_source, _target):
        raise OSError('replace failed')

    monkeypatch.setattr('backend.upload_utils.os.replace', fail_replace)

    with pytest.raises(OSError, match='replace failed'):
        save_upload_atomically(upload, str(destination))

    assert not destination.exists()
    assert not destination.with_name('file.bin.uploading').exists()
