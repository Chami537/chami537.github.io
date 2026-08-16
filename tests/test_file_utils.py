from pathlib import Path

import pytest

from backend.file_utils import atomic_write_text


def test_atomic_write_text_creates_parent_and_replaces(tmp_path):
    target = tmp_path / 'nested' / 'output.txt'

    atomic_write_text(str(target), '内容')

    assert target.read_text(encoding='utf-8') == '内容'
    assert not Path(str(target) + '.tmp').exists()


def test_atomic_write_text_cleans_temporary_on_failure(tmp_path, monkeypatch):
    target = tmp_path / 'output.txt'
    monkeypatch.setattr('backend.file_utils.os.replace', lambda *_: (_ for _ in ()).throw(OSError('replace failed')))

    with pytest.raises(OSError, match='replace failed'):
        atomic_write_text(str(target), '内容')

    assert not target.exists()
    assert not Path(str(target) + '.tmp').exists()
