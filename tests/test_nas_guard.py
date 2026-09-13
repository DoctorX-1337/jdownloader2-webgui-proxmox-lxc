import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('nas_guard',Path(__file__).resolve().parents[1]/'scripts/check-nas.py')
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

@pytest.mark.parametrize('line',[
    '10 1 8:1 / /mnt/downloads rw - ext4 /dev/sda1 rw',
    '10 1 0:10 / /mnt/downloads rw - cifs //192.0.2.30/media rw',
    '10 1 0:10 /Downloads /mnt/downloads rw - cifs //other-nas/media rw',
    '10 1 0:10 /Downloads /mnt/other rw - cifs //192.0.2.30/media rw',
])
def test_guard_rejects_local_filesystem_wrong_source_and_wrong_subfolder(monkeypatch,line):
    monkeypatch.setattr(guard.Path,'read_text',lambda self:line)
    touched=[]
    monkeypatch.setattr(guard.tempfile,'TemporaryFile',lambda **kwargs:touched.append(kwargs))
    with pytest.raises(OSError):guard.check()
    assert not touched

@pytest.mark.parametrize('root,mount_root',[('/Downloads','/Downloads'),('/Downloads/Test Folder',r'/Downloads/Test\040Folder')])
def test_guard_accepts_exact_network_mount_and_cleans_probe(monkeypatch,root,mount_root):
    monkeypatch.setenv('NAS_ROOT',root)
    monkeypatch.setattr(guard.Path,'read_text',lambda self:f'10 1 0:10 {mount_root} /mnt/downloads rw - cifs //192.0.2.30/media rw')
    class Probe:
        closed=False
        def __enter__(self):return self
        def __exit__(self,*args):self.closed=True
        def write(self,value):pass
        def flush(self):pass
        def fileno(self):return 42
    class Space:f_bavail=100;f_frsize=4096;f_blocks=200
    probe=Probe()
    monkeypatch.setattr(guard.tempfile,'TemporaryFile',lambda **kwargs:probe)
    monkeypatch.setattr(guard.os,'fsync',lambda fd:None)
    monkeypatch.setattr(guard.os,'statvfs',lambda path:Space,raising=False)
    result=guard.check()
    assert result['online'] and result['writable'] and result['free']==409600
    assert probe.closed
