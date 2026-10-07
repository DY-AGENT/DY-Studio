import base64
import http.client
import json
import queue
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from common import safe_path

class InputTests(unittest.TestCase):
    def test_engine_progress_survives_tqdm_prefix(self):
        line = ' 12%|xx |\rSTUDIO_EVENT {"message":"step 3", "progress":22}\n'
        self.assertEqual(server.progress_event(line)['progress'], 22)
        self.assertIsNone(server.progress_event('ordinary output'))
        self.assertIsNone(server.progress_event('STUDIO_EVENT not-json'))

    def test_second_launch_does_not_rewrite_live_jobs(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'jobs'
            folder.mkdir()
            live = folder / 'active.json'
            original = json.dumps(dict(id='active', status='running'))
            live.write_text(original, encoding='utf-8')
            with patch.object(server, 'DATA', Path(temp)), patch.object(server, 'PORT', server.PORT), \
                    patch.object(server, 'ThreadingHTTPServer', side_effect=OSError('in use')), \
                    patch.object(sys, 'argv', ['server.py', '--no-browser']):
                self.assertEqual(server.main(), 1)
            self.assertEqual(live.read_text(encoding='utf-8'), original)

    def test_uninstalled_generation_is_rejected(self):
        with patch.object(server, 'installed', return_value=False):
            with self.assertRaisesRegex(ValueError, '설치'):
                server.validate(dict(kind='image', prompt='a flower'))

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            for value in ('../outside.txt', '../../file', str(Path(temp).parent / 'outside')):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    safe_path(temp, value)

    def test_invalid_parameters_do_not_reach_gpu(self):
        with patch.object(server, 'installed', return_value=True):
            for changes in (dict(seed=-2), dict(size=4096), dict(duration=600), dict(prompt='')):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    server.validate(dict(kind='image', prompt='a flower', **{k:v for k,v in changes.items() if k!='prompt'})
                                    if 'prompt' not in changes else dict(kind='image', **changes))

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        (self.data / 'uploads').mkdir()
        self.patch = patch.object(server, 'DATA', self.data)
        self.patch.start()
        self.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.port = self.http.server_address[1]
        self.port_patch = patch.object(server, 'PORT', self.port)
        self.port_patch.start()
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.port_patch.stop()
        self.patch.stop()
        self.temp.cleanup()

    def post(self, path, body, token=None, host=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=4)
        headers = {'Content-Type':'application/json', 'X-Studio-Token':token or '',
                   'Host':host or f'127.0.0.1:{self.port}'}
        conn.request('POST', path, json.dumps(body), headers)
        response = conn.getresponse()
        result = response.status, json.loads(response.read())
        conn.close()
        return result

    def test_missing_token_cannot_upload(self):
        status, _ = self.post('/api/upload', dict(name='test.png', data='eA=='))
        self.assertEqual(status, 403)
        self.assertFalse(list((self.data / 'uploads').iterdir()))

    def test_foreign_host_cannot_use_session_token(self):
        status, _ = self.post('/api/upload', dict(name='test.png',data='eA=='),
                              server.TOKEN, f'attacker.invalid:{self.port}')
        self.assertEqual(status, 403)

    def test_upload_renames_supplied_path(self):
        raw = b'test-only image bytes; decoding is performed by the worker'
        status, body = self.post('/api/upload', dict(name='../../image.png',
                        data=base64.b64encode(raw).decode()), server.TOKEN)
        self.assertEqual(status, 200)
        self.assertNotIn('/', body['upload'])
        self.assertEqual((self.data / 'uploads' / body['upload']).read_bytes(), raw)

    def test_nonimage_extension_is_rejected(self):
        status, _ = self.post('/api/upload', dict(name='script.exe',data='eA=='), server.TOKEN)
        self.assertEqual(status, 400)

class QueueTests(unittest.TestCase):
    def test_running_process_can_be_cancelled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'jobs').mkdir()
            (root / 'install.py').write_text('import time\nprint(\'STUDIO_EVENT {"message":"cancellation-ready","progress":50}\',flush=True)\ntime.sleep(60)\n')
            with patch.object(server,'ROOT',root), patch.object(server,'DATA',root), \
                 patch.object(server,'JOBS',{}), patch.object(server,'PENDING',queue.Queue()), \
                 patch.object(server.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)):
                job = server.create_job(dict(kind='image',action='install'))
                thread = threading.Thread(target=server.worker_loop)
                thread.start()
                deadline = time.monotonic() + 6
                while job['message'] != 'cancellation-ready' and time.monotonic() < deadline:
                    time.sleep(.025)
                self.assertEqual(job['message'],'cancellation-ready')
                server.cancel_job(job['id'])
                server.PENDING.put(None)
                thread.join(timeout=8)
                self.assertFalse(thread.is_alive())
                self.assertEqual(job['status'],'cancelled')
                self.assertIsNone(server.PROCESS)

    def test_real_subprocesses_run_sequentially_and_cancelled_queue_is_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'jobs').mkdir()
            (root / 'install.py').write_text('import time\nprint(\'STUDIO_EVENT {"message":"test worker","progress":50}\',flush=True)\ntime.sleep(.3)\n')
            with patch.object(server,'ROOT',root), patch.object(server,'DATA',root), \
                 patch.object(server,'JOBS',{}), patch.object(server,'PENDING',queue.Queue()), \
                 patch.object(server.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)):
                one = server.create_job(dict(kind='image',action='install'))
                cancelled = server.create_job(dict(kind='mesh',action='install'))
                two = server.create_job(dict(kind='video',action='install'))
                server.cancel_job(cancelled['id'])
                thread = threading.Thread(target=server.worker_loop)
                thread.start()
                server.PENDING.put(None)
                thread.join(timeout=10)
                self.assertFalse(thread.is_alive())
                self.assertEqual(one['status'],'completed')
                self.assertEqual(two['status'],'completed')
                self.assertEqual(cancelled['status'],'cancelled')
                self.assertNotIn('started',cancelled)
                self.assertGreaterEqual(two['started'],one['finished'])
                self.assertIsNone(server.PROCESS)

if __name__ == '__main__':
    unittest.main()
