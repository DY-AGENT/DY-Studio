"""Loopback-only creative studio. The UI needs only Python's standard library."""
import argparse
import base64
import json
import mimetypes
import os
import queue
import secrets
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote
from common import ROOT, DATA, MODELS, CATALOG, environment, installed, runtime, save_json, safe_path, commercial_model

TOKEN = secrets.token_urlsafe(32)
JOBS = {}
LOCK = threading.RLock()
PENDING = queue.Queue()
PROCESS = None
STOPPING = False
PORT = 8768
CREATION = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def update(job, **values):
    with LOCK:
        job.update(values)
        save_json(DATA / 'jobs' / (job['id'] + '.json'), job)

def progress_event(line):
    # tqdm can prefix a callback with a carriage-return progress bar.
    marker = 'STUDIO_EVENT '
    index = line.find(marker)
    if index < 0:
        return None
    try:
        value = json.loads(line[index + len(marker):])
        return value if isinstance(value, dict) else None
    except ValueError:
        return None

def hardware():
    gpu = None
    try:
        out = subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total,memory.used',
                                       '--format=csv,noheader,nounits'], timeout=4,
                                      creationflags=CREATION, encoding='utf-8')
        name, total, used = out.splitlines()[0].rsplit(',', 2)
        gpu = dict(name=name.strip(), total_mb=int(total), used_mb=int(used))
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return dict(gpu=gpu, free_disk_gb=round(shutil.disk_usage(DATA).free / 1024**3, 1))

def validate(payload):
    kind = payload.get('kind')
    action = payload.get('action', 'generate')
    if kind not in MODELS or action not in ('generate', 'install'):
        raise ValueError('This operation is not supported.')
    commercial_model(kind)
    if action == 'install':
        # Resume/reinstall reuses downloaded weights instead of reserving them twice.
        folder = DATA / 'models' / kind
        existing_gb = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()) / 1024**3
        needed_gb = max(0, MODELS[kind]['disk_gb'] - existing_gb) + 3
        if shutil.disk_usage(DATA).free / 1024**3 < needed_gb:
            raise ValueError('Not enough disk space. Check the model size and available space.')
        return dict(kind=kind, action=action)
    if not installed(kind):
        raise ValueError('Install this model first in Model management.')
    prompt = str(payload.get('prompt', '')).strip()
    if not MODELS[kind]['input'] and not (1 <= len(prompt) <= (512 if kind == 'music' else 1500)):
        raise ValueError('Enter a prompt: up to 512 characters for music or 1500 for images and video.')
    upload = payload.get('upload', '')
    if MODELS[kind]['input']:
        path = safe_path(DATA / 'uploads', upload)
        if not upload or not path.is_file():
            raise ValueError('Upload an object image first.')
    seed = int(payload.get('seed', -1))
    if not (-1 <= seed < 2**32):
        raise ValueError('The seed must be -1 or an integer from 0 to 4294967295.')
    size = int(payload.get('size', 512))
    if size not in (384, 512, 640):
        raise ValueError('This resolution is not supported.')
    duration = int(payload.get('duration', 30))
    if duration not in (10, 20, 30, 60):
        raise ValueError('This music duration is not supported.')
    lyrics = str(payload.get('lyrics', ''))
    if len(lyrics) > 4096:
        raise ValueError('Lyrics can contain up to 4096 characters.')
    return dict(action=action, kind=kind, prompt=prompt, upload=upload, seed=seed, size=size,
                duration=duration, lyrics=lyrics, negative=str(payload.get('negative', ''))[:1500],
                instrumental=bool(payload.get('instrumental', True)))

def create_job(payload):
    values = validate(payload)
    with LOCK:
        if sum(j['status'] in ('queued', 'running') for j in JOBS.values()) >= 10:
            raise ValueError('The queue is full. Wait for a job to finish before adding another.')
        if values['action'] == 'install' and any(j['kind'] == values['kind'] and j['action'] == 'install'
                 and j['status'] in ('queued', 'running') for j in JOBS.values()):
            raise ValueError('This model is already queued for installation or being installed.')
        job = dict(id=uuid.uuid4().hex, created=time.time(), status='queued', progress=0,
                   message='Queued', files=[], **values)
        JOBS[job['id']] = job
        update(job)
        PENDING.put(job['id'])
    return job

def cancel_job(job_id):
    global PROCESS
    with LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise ValueError('Job not found.')
        if job['status'] == 'queued':
            update(job, status='cancelled', message='Cancelled', finished=time.time())
        elif job['status'] == 'running':
            update(job, status='cancelling', message='Cancelling · releasing GPU memory')
            if PROCESS:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(PROCESS.pid), '/T', '/F'],
                                   capture_output=True, creationflags=CREATION, timeout=15)
                else:
                    PROCESS.terminate()

def worker_loop():
    global PROCESS
    while True:
        job_id = PENDING.get()
        if job_id is None:
            return
        job = JOBS[job_id]
        with LOCK:
            if job['status'] != 'queued':
                continue
            update(job, status='running', started=time.time(), message='Preparing to run')
            exe = sys.executable if job['action'] == 'install' else str(runtime(job['kind']))
            script = ROOT / ('install.py' if job['action'] == 'install' else 'worker.py')
            log_path = DATA / 'jobs' / (job_id + '.log')
            try:
                PROCESS = subprocess.Popen([exe, '-u', str(script), job_id], cwd=ROOT,
                             env=environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             encoding='utf-8', errors='replace', creationflags=CREATION)
            except Exception as exc:
                update(job, status='failed', message=str(exc), finished=time.time())
                continue
        try:
            with log_path.open('w', encoding='utf-8') as log:
                for line in PROCESS.stdout:
                    log.write(line)
                    log.flush()
                    event = progress_event(line)
                    if event is not None:
                        if job['status'] == 'running':
                            update(job, **{k: v for k, v in event.items()
                                          if k in ('progress', 'message', 'files', 'metrics')})
                code = PROCESS.wait()
            if job['status'] == 'cancelling':
                update(job, status='cancelled', message='Cancelled · GPU memory released', finished=time.time())
            elif code:
                if job.get('message') in ('Preparing to run', 'Loading model'):
                    update(job, message='Job failed · check the log for details.')
                update(job, status='failed', finished=time.time())
            else:
                update(job, status='completed', progress=100, finished=time.time(),
                       message='Installation complete' if job['action'] == 'install' else 'Generation complete · GPU memory released')
        except Exception as exc:
            if PROCESS and PROCESS.poll() is None:
                PROCESS.kill()
                PROCESS.wait()
            update(job, status='failed', message=str(exc), finished=time.time())
        finally:
            with LOCK:
                if PROCESS and PROCESS.stdout:
                    PROCESS.stdout.close()
                PROCESS = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{PORT}', f'localhost:{PORT}')

    def send(self, value, code=200):
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def file(self, path):
        if not path.is_file():
            self.send_error(404)
            return
        self.send_response(200)
        mime = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') else ''))
        self.send_header('Content-Length', str(path.stat().st_size))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        with path.open('rb') as f:
            shutil.copyfileobj(f, self.wfile)

    def do_GET(self):
        if not self.valid_host():
            self.send_error(403)
            return
        path = unquote(urlsplit(self.path).path)
        try:
            if path == '/api/state':
                with LOCK:
                    jobs = sorted(JOBS.values(), key=lambda j: j['created'], reverse=True)
                    self.send(dict(token=TOKEN, models=[dict(m, installed=installed(m['id'])) for m in CATALOG],
                                   jobs=jobs, hardware=hardware()))
            elif path.startswith('/results/'):
                self.file(safe_path(DATA / 'results', path[len('/results/'):]))
            elif path.startswith('/uploads/'):
                self.file(safe_path(DATA / 'uploads', path[len('/uploads/'):]))
            elif path.startswith('/logs/') and path.endswith('.log'):
                self.file(safe_path(DATA / 'jobs', path[len('/logs/'):]))
            else:
                self.file(safe_path(ROOT / 'web', 'index.html' if path == '/' else path.lstrip('/')))
        except ValueError:
            self.send_error(400)

    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-Studio-Token') != TOKEN:
            self.send(dict(error='Refresh this page and try again.'), 403)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not (0 < size <= 28 * 1024 * 1024):
                raise ValueError('The request is too large. Images can be up to 20MB.')
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError('Invalid request.')
            if self.path == '/api/jobs':
                self.send(create_job(payload), 201)
            elif self.path == '/api/cancel':
                cancel_job(str(payload.get('id', '')))
                self.send(dict(ok=True))
            elif self.path == '/api/upload':
                ext = str(payload.get('name', '')).rsplit('.', 1)[-1].lower()
                if ext not in ('png', 'jpg', 'jpeg', 'webp'):
                    raise ValueError('Only PNG, JPEG and WebP images are supported.')
                raw = base64.b64decode(payload['data'], validate=True)
                if not raw or len(raw) > 20 * 1024 * 1024:
                    raise ValueError('Images can be up to 20MB.')
                name = uuid.uuid4().hex + '.' + ext
                (DATA / 'uploads' / name).write_bytes(raw)
                self.send(dict(upload=name, url='/uploads/' + name))
            elif self.path == '/api/open-results':
                if os.name == 'nt':
                    os.startfile(DATA / 'results')
                self.send(dict(ok=True))
            elif self.path == '/api/shutdown':
                for job in list(JOBS.values()):
                    if job['status'] in ('queued', 'running'):
                        cancel_job(job['id'])
                self.send(dict(ok=True))
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self.send(dict(error='Request not found.'), 404)
        except (ValueError, KeyError, TypeError) as exc:
            self.send(dict(error=str(exc)), 400)

def main():
    global PORT
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int, default=8768)
    args = parser.parse_args()
    PORT = args.port
    # Claim the port before recovery: a second launch must never rewrite live jobs.
    try:
        server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    except OSError:
        print(f'Port {PORT} is already in use. Close the previous Studio or use --port.')
        return 1
    for path in (DATA / 'jobs').glob('*.json'):
        try:
            job = json.loads(path.read_text(encoding='utf-8'))
            if job['status'] in ('running', 'queued', 'cancelling'):
                update(job, status='interrupted', message='Interrupted when the app closed · you can run it again.')
            JOBS[job['id']] = job
        except (ValueError, KeyError):
            pass
    threading.Thread(target=worker_loop, daemon=True).start()
    print(f'DY Creative Studio: http://127.0.0.1:{PORT}', flush=True)
    if not args.no_browser:
        webbrowser.open(f'http://127.0.0.1:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for job in list(JOBS.values()):
            if job['status'] in ('queued', 'running'):
                cancel_job(job['id'])
        server.server_close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
