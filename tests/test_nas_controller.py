import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('nas_controller',Path(__file__).parents[1]/'scripts/nas-controller.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

@pytest.fixture
def controller(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'LAST',tmp_path/'last')
    monkeypatch.setattr(module,'BLOCKED',tmp_path/'blocked')
    return module

def test_active_state_survives_stop_and_slow_startup(controller,monkeypatch):
    state=['RUNNING']
    calls=[]
    def call(endpoint,*args):
        calls.append(endpoint)
        if endpoint.endswith('start'): state[0]='RUNNING';return None
        if state[0]=='unavailable': raise OSError()
        return state[0]
    monkeypatch.setattr(controller,'call',call)
    controller.remember();controller.block()
    assert controller.BLOCKED.read_text()=='RUNNING'
    state[0]='unavailable'
    assert not controller.recover()
    assert controller.BLOCKED.exists()
    state[0]='IDLE'
    assert controller.recover() and state[0]=='RUNNING'
    assert calls.count('/downloadcontroller/start')==1
    assert controller.recover()
    assert calls.count('/downloadcontroller/start')==1

@pytest.mark.parametrize('state',['IDLE','PAUSE','PAUSED','STOPPING'])
def test_deliberately_idle_or_paused_controller_is_not_started(controller,monkeypatch,state):
    calls=[]
    def call(endpoint,*args):calls.append(endpoint);return state
    monkeypatch.setattr(controller,'call',call)
    controller.remember();controller.block()
    assert controller.recover()
    assert '/downloadcontroller/start' not in calls

def test_unresponsive_engine_uses_last_known_intent_and_preserves_marker(controller,monkeypatch):
    controller.LAST.write_text('RUNNING')
    def unavailable(*args): raise OSError()
    monkeypatch.setattr(controller,'call',unavailable)
    controller.block()
    assert controller.BLOCKED.read_text()=='RUNNING'
    controller.LAST.write_text('IDLE')
    controller.block()
    assert controller.BLOCKED.read_text()=='RUNNING'
    assert not controller.recover()
