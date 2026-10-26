import asyncio
from pathlib import Path
import pytest
from fastapi import HTTPException
from backend.app.extractions import Extractions


class Engine:
    def __init__(self, root):
        self.root = str(root)
        self.calls = []
        self.queue = []
        self.links = [{'uuid':'9007199254740993','packageUUID':'9','name':'test.part1.rar'},
                      {'uuid':'2','packageUUID':'9','name':'test.part2.rar'}]
        self.archives = [{'archiveId':'native-archive','archiveName':'test','states':{'test.part1.rar':'COMPLETE','test.part2.rar':'COMPLETE'}}]
    async def downloads(self): return self.links
    async def packages(self): return [{'uuid':'9','name':'Package','saveTo':self.root}]
    async def call(self, path, *params):
        self.calls.append((path, params))
        if path == '/extraction/getArchiveInfo': return self.archives
        if path == '/extraction/getQueue': return self.queue
        if path == '/extraction/startExtractionNow': return {'123':True}
        return True


def test_catalog_retains_exact_ids_and_caches_native_scan(tmp_path):
    async def scenario():
        engine = Engine(tmp_path)
        service = Extractions()
        first = (await service.snapshot(engine))[0]
        assert first['state'] == 'ready' and first['actionable']
        assert first['linkIds'] == ['9007199254740993','2']
        await service.snapshot(engine)
        assert len([c for c in engine.calls if c[0].endswith('getArchiveInfo')]) == 1
        assert all(c[0] in ('/extraction/getArchiveInfo','/extraction/getQueue') for c in engine.calls)
    asyncio.run(scenario())


def test_duplicate_basenames_disable_actions(tmp_path):
    async def scenario():
        engine = Engine(tmp_path)
        engine.links.append({'uuid':'3','packageUUID':'10','name':'test.part1.rar'})
        service = Extractions()
        assert not (await service.snapshot(engine))[0]['actionable']
        with pytest.raises(HTTPException) as error:
            await service.action(engine, tmp_path, 'native-archive', 'start')
        assert error.value.status_code == 409
        assert not any(c[0].endswith('startExtractionNow') for c in engine.calls)
    asyncio.run(scenario())


def test_restart_uses_fresh_folder_and_only_selected_archive(tmp_path):
    async def scenario():
        engine = Engine(tmp_path)
        service = Extractions()
        await service.action(engine, tmp_path, 'native-archive', 'restart')
        settings = next(c for c in engine.calls if c[0].endswith('setArchiveSettings'))
        ident, change = settings[1]
        assert ident == 'native-archive' and set(change) == {'extractPath'}
        assert Path(change['extractPath']).parent == tmp_path
        assert Path(change['extractPath']).name.startswith('Entpackt-Neustart-')
        assert ('/extraction/startExtractionNow',([9007199254740993,2],[])) in engine.calls
        assert not any('config/' in c[0] or 'getArchiveSettings' in c[0] for c in engine.calls)
    asyncio.run(scenario())


def test_cancel_resolves_current_controller_without_starting_other_jobs(tmp_path):
    async def scenario():
        engine = Engine(tmp_path)
        engine.queue = [{**engine.archives[0], 'controllerStatus':'RUNNING','controllerId':123}]
        service = Extractions()
        await service.action(engine, tmp_path, 'native-archive', 'cancel')
        assert engine.calls[-1] == ('/extraction/cancelExtraction',(123,))
        assert not any(c[0].endswith('startExtractionNow') for c in engine.calls)
    asyncio.run(scenario())


@pytest.mark.parametrize('problem',['outside','incomplete','running','gone'])
def test_restart_rejects_unsafe_or_stale_jobs(tmp_path,problem):
    async def scenario():
        engine = Engine(tmp_path)
        if problem == 'outside': engine.root = str(tmp_path.parent)
        if problem == 'incomplete': engine.archives[0]['states']['test.part2.rar'] = 'MISSING'
        if problem == 'running': engine.queue = [{**engine.archives[0],'controllerStatus':'RUNNING','controllerId':123}]
        if problem == 'gone': engine.archives = []
        with pytest.raises(HTTPException):
            await Extractions().action(engine, tmp_path, 'native-archive', 'restart')
        assert not any(c[0].endswith(('startExtractionNow','setArchiveSettings')) for c in engine.calls)
    asyncio.run(scenario())
