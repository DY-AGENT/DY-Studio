import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
CATALOG = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
MODELS = {m['id']: m for m in CATALOG}
REVIEWED_REPOS = {
    'image': 'stable-diffusion-v1-5/stable-diffusion-v1-5',
    'music': 'ACE-Step/Ace-Step1.5', 'video': 'zai-org/CogVideoX-2b',
    'mesh': 'stabilityai/TripoSR', 'cutout': 'u2net',
}
REVIEWED_REVISIONS = {
    'image': '451f4fe16113bff5a5d2269ed5ad43b0592e9a14',
    'music': '19671f406d603126926c1b7e2adc169acbcade22',
    'video': '1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01',
    'mesh': '5b521936b01fbe1890f6f9baed0254ab6351c04a',
    'cutout': 'u2net-md5-60024c5c889badc19c04ad937298a77b',
}
for folder in ('jobs', 'uploads', 'results', 'models', 'cache', 'engines'):
    (DATA / folder).mkdir(parents=True, exist_ok=True)

def environment():
    env = os.environ.copy()
    env.update(PYTHONUTF8='1', PYTHONUNBUFFERED='1', HF_HOME=str(DATA / 'cache' / 'huggingface'),
               U2NET_HOME=str(DATA / 'models' / 'cutout'), HF_HUB_DISABLE_TELEMETRY='1',
               TOKENIZERS_PARALLELISM='false', DO_NOT_TRACK='1',
               PIP_CACHE_DIR=str(DATA / 'cache' / 'pip'), TORCH_HOME=str(DATA / 'cache' / 'torch'),
               NUMBA_CACHE_DIR=str(DATA / 'cache' / 'numba'), MPLCONFIGDIR=str(DATA / 'cache' / 'matplotlib'))
    return env

def runtime(kind):
    base = DATA / ('music-runtime' if kind == 'music' else 'runtime')
    return base / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')

def installed(kind):
    return runtime(kind).exists() and (DATA / 'models' / kind / 'ready.json').exists()

def save_json(path, value):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

def safe_path(base, value):
    base = Path(base).resolve()
    path = (base / value).resolve()
    if not path.is_relative_to(base):
        raise ValueError('This file path is not allowed.')
    return path

def commercial_model(kind):
    model = MODELS.get(kind, {})
    if (model.get('repo') != REVIEWED_REPOS.get(kind)
            or model.get('revision') != REVIEWED_REVISIONS.get(kind)
            or model.get('commercial_allowed') is not True):
        raise ValueError('Commercial use terms have not been verified for this model. Only reviewed models can run.')
    return model

def write_rights(destination, job):
    model = commercial_model(job['kind'])
    manifest = DATA / 'models' / job['kind'] / 'download.json'
    download = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    note = ('The selected model license permits commercial use subject to its terms. '
            'Rights to input images, lyrics, reference material and third-party content in outputs must be checked separately. '
            'This notice does not guarantee exclusive copyright, non-infringement or eligibility for copyright registration. '
            'Model and code redistribution terms are distinct from the terms for using generated files.')
    rights = dict(model=model['model'], repository=model['repo'], download=download,
                  license=model['license'], source=model['source'], license_source=model['license_source'],
                  commercial_use='permitted_subject_to_original_terms', conditions=model['commercial_note'],
                  notice=note, reviewed_on='2026-10-07', job_id=job['id'])
    save_json(destination / 'rights.json', rights)
    (destination / 'commercial-use.txt').write_text(
        'Commercial use notice for generated assets\n\nModel: ' + model['model'] + '\nLicense: ' + model['license'] +
        '\nOfficial terms: ' + model['license_source'] + '\n\n' + model['commercial_note'] + '\n\n' + note +
        '\n\nThis file records provenance. It does not apply a new model license to the generated asset.\n',
        encoding='utf-8')
