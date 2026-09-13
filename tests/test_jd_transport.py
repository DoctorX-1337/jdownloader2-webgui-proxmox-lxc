import asyncio
import json
import httpx
from backend.app.jd import JDownloader

def test_secret_parameters_are_only_in_post_body():
    async def run():
        engine=JDownloader()
        await engine.client.aclose()
        seen=[]
        def handler(request):
            seen.append(request)
            return httpx.Response(200,json={})
        engine.client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        await engine.call('/accountsV2/addAccount','test.example','test-user','test-secret-with-&-characters')
        request=seen[0]
        assert request.method=='POST'
        assert not request.url.query
        assert json.loads(request.content)=={'params':['test.example','test-user','test-secret-with-&-characters']}
        await engine.client.aclose()
    asyncio.run(run())

def test_omitted_false_values_still_identify_paused_download():
    async def run():
        engine=JDownloader()
        await engine.client.aclose()
        def handler(request):
            return httpx.Response(200,json={'data':[{'uuid':42,'name':'paused.bin'}]})
        engine.client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        row=(await engine.downloads())[0]
        assert row['uuid']=='42'
        assert row['enabled'] is False and row['running'] is False and row['finished'] is False
        await engine.client.aclose()
    asyncio.run(run())
