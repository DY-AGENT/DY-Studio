"""Real SDK stdio/HTTP round trips with isolated jobs; no model downloads or GPU work."""
import asyncio
import base64
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import mcp_server

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


class BridgeBoundaryTests(unittest.TestCase):
    def test_rejects_foreign_workspace_and_unrecorded_result(self):
        client = mcp_server.StudioClient()
        with patch.object(client, 'request', return_value=json.dumps({'studio_root': '/another/workspace'}).encode()):
            with self.assertRaisesRegex(ValueError, 'another or older'):
                client.state()
        job_id = 'a' * 32
        job = {'id': job_id, 'files': [{'name': 'secret.txt', 'url': '/uploads/secret.txt'}]}
        with patch.object(client, 'job', return_value=job):
            for name in ('../secret.txt', 'secret.txt', 'C:\\secret.txt'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    client.asset(job_id, name)


@unittest.skipUnless(HAS_MCP, 'Install requirements-mcp.txt to run real MCP round trips.')
class StdioRoundTripTests(unittest.TestCase):
    def test_cold_start_and_two_clients_share_one_app_without_model_downloads(self):
        import shutil
        import socket
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('server.py', 'common.py', 'catalog.json', 'mcp_server.py'):
                shutil.copy2(mcp_server.ROOT / name, root / name)
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            origin = f'http://127.0.0.1:{port}'

            async def connect():
                parameters = StdioServerParameters(command=sys.executable, args=[str(root / 'mcp_server.py'), '--start-studio', '--port', str(port)])
                async with stdio_client(parameters) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        result = await session.call_tool('studio_status', {})
                        self.assertFalse(result.isError, result.content)
                        state = json.loads(result.content[0].text)
                        self.assertEqual(len(state['models']), 5)
                        self.assertTrue(all(not model['installed'] for model in state['models']))
                        self.assertEqual(state['queued_or_running'], 0)
                        first = json.load(urllib.request.urlopen(origin + '/api/state', timeout=5))
                        async with stdio_client(parameters) as (reader2, writer2):
                            async with ClientSession(reader2, writer2) as session2:
                                await session2.initialize()
                                result2 = await session2.call_tool('studio_status', {})
                                self.assertFalse(result2.isError, result2.content)
                                second = json.load(urllib.request.urlopen(origin + '/api/state', timeout=5))
                                self.assertEqual(first['token'], second['token'])
                                self.assertFalse(second['jobs'])
                                self.assertFalse(list((root / 'data/models').rglob('*')))

            try:
                asyncio.run(asyncio.wait_for(connect(), timeout=30))
            finally:
                try:
                    state = json.load(urllib.request.urlopen(origin + '/api/state', timeout=5))
                    req = urllib.request.Request(origin + '/api/shutdown', data=b'{}', headers={'X-Studio-Token': state['token']})
                    urllib.request.urlopen(req, timeout=5).read()
                    for _ in range(40):
                        try:
                            urllib.request.urlopen(origin + '/api/state', timeout=1).read()
                        except OSError:
                            break
                        time.sleep(0.1)
                except OSError:
                    pass

    def test_tools_share_http_queue_errors_cancellation_and_result_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            for folder in ('jobs', 'uploads', 'results', 'models'):
                (data / folder).mkdir()
            fixture_id = 'b' * 32
            folder = data / 'results' / fixture_id
            folder.mkdir()
            asset = b'isolated binary fixture; not a generated GPU image'
            (folder / 'asset.png').write_bytes(asset)
            (folder / 'rights.json').write_text('{"license":"fixture"}', encoding='utf-8')
            (data / 'jobs' / (fixture_id + '.log')).write_text('fixture log\n', encoding='utf-8')
            completed = dict(id=fixture_id, created=0, kind='image', action='generate', status='completed', progress=100,
                             files=[dict(name=name, url=f'/results/{fixture_id}/{name}') for name in ('asset.png', 'rights.json')])
            jobs, pending = {fixture_id: completed}, queue.Queue()
            with patch.object(server, 'DATA', data), patch.object(server, 'JOBS', jobs), patch.object(server, 'PENDING', pending), \
                    patch.object(server, 'installed', return_value=True), patch.object(server, 'hardware', return_value={'gpu': None, 'free_disk_gb': 100}):
                http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
                port = http.server_address[1]
                with patch.object(server, 'PORT', port):
                    thread = threading.Thread(target=http.serve_forever, daemon=True)
                    thread.start()
                    try:
                        asyncio.run(asyncio.wait_for(self.exercise(port, jobs, pending, fixture_id, asset), timeout=60))
                    finally:
                        http.shutdown()
                        http.server_close()
                        thread.join(timeout=5)

    async def exercise(self, port, jobs, pending, fixture_id, asset):
        parameters = StdioServerParameters(command=sys.executable, args=[str(mcp_server.ROOT / 'mcp_server.py'), '--port', str(port)])
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                self.assertEqual(len(tools), 10)
                self.assertTrue(next(t for t in tools if t.name == 'studio_status').annotations.readOnlyHint)
                self.assertTrue(next(t for t in tools if t.name == 'studio_cancel_job').annotations.destructiveHint)

                async def call(name, args=None):
                    result = await session.call_tool(name, args or {})
                    self.assertFalse(result.isError, result.content)
                    return json.loads(result.content[0].text)

                state = await call('studio_status')
                self.assertEqual(len(state['models']), 5)
                self.assertNotIn('token', state)
                uploaded = await call('studio_upload_image', {'name': '../../fixture.png', 'data_base64': base64.b64encode(asset).decode()})
                self.assertNotIn('/', uploaded['upload'])
                for kind in ('image', 'music', 'video', 'mesh', 'cutout'):
                    job = await call('studio_generate', {'kind': kind, 'prompt': 'test prompt', 'upload': uploaded['upload']})
                    self.assertIn(job['id'], jobs)
                    self.assertEqual(job['status'], 'queued')
                    cancelled = await call('studio_cancel_job', {'job_id': job['id']})
                    self.assertEqual(cancelled['status'], 'cancelled')
                self.assertEqual(pending.qsize(), 5)
                for args in ({'kind': 'image', 'prompt': 'test', 'size': 4096}, {'kind': 'image', 'prompt': 'test', 'seed': -2}, {'kind': 'mesh', 'upload': '../secret.txt'}):
                    result = await session.call_tool('studio_generate', args)
                    self.assertTrue(result.isError)
                self.assertEqual(pending.qsize(), 5)
                install = await call('studio_install_model', {'kind': 'cutout'})
                self.assertEqual(install['action'], 'install')
                self.assertEqual(pending.qsize(), 6)
                self.assertEqual(len((await call('studio_list_jobs', {'limit': 100}))['jobs']), 7)
                self.assertEqual((await call('studio_get_job', {'job_id': fixture_id}))['status'], 'completed')
                self.assertEqual(len((await call('studio_get_results', {'job_id': fixture_id}))['files']), 2)
                binary = await session.call_tool('studio_read_result', {'job_id': fixture_id, 'filename': 'asset.png'})
                self.assertFalse(binary.isError)
                self.assertEqual(base64.b64decode(binary.content[0].resource.blob), asset)
                text = await session.call_tool('studio_read_result', {'job_id': fixture_id, 'filename': 'rights.json'})
                self.assertEqual(json.loads(text.content[0].resource.text)['license'], 'fixture')
                self.assertEqual((await call('studio_get_log', {'job_id': fixture_id}))['text'].splitlines(), ['fixture log'])
                denied = await session.call_tool('studio_read_result', {'job_id': fixture_id, 'filename': '../../catalog.json'})
                self.assertTrue(denied.isError)


if __name__ == '__main__':
    unittest.main()
