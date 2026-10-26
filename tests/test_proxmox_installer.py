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

def test_prompt_recovers_from_broken_console_encoding(monkeypatch):
    answers=iter([UnicodeDecodeError('utf-8',b'\xc3',0,1,'invalid continuation byte'),'damaged\ufffdvalue','local-lvm'])
    def answer(_):
        value=next(answers)
        if isinstance(value,Exception):raise value
        return value
    monkeypatch.setattr('builtins.input',answer)
    assert installer.prompt('Storage','local',lambda s:s in ('local','local-lvm'))=='local-lvm'

def test_command_output_with_broken_bytes_does_not_abort(monkeypatch):
    class Result:
        returncode=0
        stdout='storage description \ufffd'
    def command(*args,**kwargs):
        assert kwargs['encoding']=='utf-8' and kwargs['errors']=='replace'
        return Result()
    monkeypatch.setattr(installer.subprocess,'run',command)
    assert installer.run(['pvesh','get','/storage']).startswith('storage description')

@pytest.mark.parametrize(('existing','expected'),[
    ([], 'jdownloader2'),
    (['jdownloader2'], 'jdownloader2-01'),
    (['JDownloader2','jdownloader2-01','jdownloader2-02'], 'jdownloader2-03'),
    (['jdownloader2','jdownloader2-02'], 'jdownloader2-01'),
])
def test_automatic_hostname_uses_next_free_suffix(existing,expected):
    assert installer.automatic_hostname(existing)==expected
