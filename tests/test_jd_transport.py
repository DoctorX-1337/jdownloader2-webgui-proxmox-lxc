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

def test_native_package_query_requests_totals_and_preserves_large_ids():
    async def run():
        engine=JDownloader()
        await engine.client.aclose()
        requests=[]
        def handler(request):
            requests.append(request)
            return httpx.Response(200,json={'data':[{'uuid':9007199254740993,'name':'Archive','bytesLoaded':25,'bytesTotal':100,'childCount':2}]})
        engine.client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        row,=await engine.packages()
        assert row['uuid']=='9007199254740993'
        assert row['finished'] is False and row['running'] is False and row['enabled'] is False
        assert requests[0].url.path=='/downloadsV2/queryPackages'
        query,=json.loads(requests[0].content)['params']
        assert all(query[key] for key in ('bytesLoaded','bytesTotal','childCount','speed','eta','finished','running','enabled'))
        await engine.client.aclose()
    asyncio.run(run())

def test_native_advanced_status_exposes_only_normalized_extraction_telemetry():
    async def run():
        engine=JDownloader()
        await engine.client.aclose()
        def handler(request):
            assert json.loads(request.content)['params'][0]['advancedStatus']
            return httpx.Response(200,json={'data':[{'uuid':42,'packageUUID':99,'advancedStatus':{'PluginProgress':{'id':'EXTRACTION','current':25,'total':100,'eta':9000,'label':'Extracting...'},'ExtractionStatus':{'id':'RUNNING'}}}]})
        engine.client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        link,=await engine.downloads()
        assert link['extraction']['progress']==25 and link['extraction']['eta']==9
        assert link['extractionStatus']=='RUNNING'
        assert 'advancedStatus' not in link
        await engine.client.aclose()
    asyncio.run(run())
