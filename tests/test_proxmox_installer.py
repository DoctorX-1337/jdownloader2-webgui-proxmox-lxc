"""Validate installer boundaries without creating guests or mounts."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('installer', Path(__file__).parents[1]/'scripts/proxmox-install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@pytest.mark.parametrize('value', [r'\\nas.example\Downloads', '//nas.example/Downloads', r'\\nas.example\Freigabe\Unterordner'])
def test_share_parser(value):
    source, parts = installer.parse_share(value)
    assert source.startswith('//nas.example/') and len(source.split('/')) == 4
    assert all(part not in ('.','..') for part in parts)


@pytest.mark.parametrize('value', ['//nas/share/../etc','//nas/share/a,b','//nas/share/a\nfile','//nas','//nas/share//folder'])
def test_share_parser_rejects_injection(value):
    with pytest.raises(ValueError): installer.parse_share(value)


def test_private_file_never_overwrites(tmp_path):
    target = tmp_path/'credential'
    installer.private_file(target, 'synthetic-test-secret')
    with pytest.raises(FileExistsError): installer.private_file(target, 'replacement')
    assert target.read_text() == 'synthetic-test-secret'
