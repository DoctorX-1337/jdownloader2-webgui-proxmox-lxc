"""Only this adapter talks to JDownloader's loopback API."""
import os
import httpx

class EngineUnavailable(Exception):
    pass

class JDownloader:
    def __init__(self):
        host = os.getenv('JD_HOST', '127.0.0.1')
        if host != '127.0.0.1':
            raise ValueError('Die JDownloader-API muss auf 127.0.0.1 liegen.')
        self.base = f'http://{host}:{int(os.getenv("JD_PORT", "3128"))}'
        self.client = httpx.AsyncClient(timeout=12, trust_env=False)

    async def call(self, endpoint, *params):
        try:
            # The local API expects native positional values in a params array.
            # Credentials and long link batches must not appear in URL queries.
            response = await self.client.post(self.base + endpoint, json={'params':list(params)})
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict) or 'type' in body:
                raise EngineUnavailable()
            return body.get('data')
        except (httpx.HTTPError, ValueError):
            raise EngineUnavailable() from None

    async def downloads(self):
        query = {k: True for k in ('bytesLoaded','bytesTotal','speed','eta','status','finished','running','enabled','host','finishedDate','extractionStatus','skipped')}
        query.update(startAt=0, maxResults=-1)
        links = await self.call('/downloadsV2/queryLinks', query)
        # IDs exceed JS's safe integer range over time; serialize as strings.
        for link in links:
            link['uuid'] = str(link['uuid'])
            link['packageUUID'] = str(link.get('packageUUID', ''))
            # JDownloader omits false values from its JSON output. Preserve
            # their meaning so paused links show a resume action in the UI.
            for key in ('enabled', 'finished', 'running', 'skipped'):
                link.setdefault(key, False)
        return links

    async def grabber(self):
        links = await self.call('/linkgrabberv2/queryLinks', {'startAt':0,'maxResults':-1,'host':True,'url':True,'availability':True,'enabled':True,'advancedStatus':True,'bytesTotal':True})
        for link in links:
            link['uuid'] = str(link['uuid'])
            link['packageUUID'] = str(link.get('packageUUID', ''))
        return links
