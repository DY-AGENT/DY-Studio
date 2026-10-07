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
        raise ValueError('허용되지 않은 파일 경로입니다.')
    return path

def commercial_model(kind):
    model = MODELS.get(kind, {})
    if (model.get('repo') != REVIEWED_REPOS.get(kind)
            or model.get('revision') != REVIEWED_REVISIONS.get(kind)
            or model.get('commercial_allowed') is not True):
        raise ValueError('상업 이용 조건이 확인되지 않은 모델입니다. 공식 라이선스를 확인한 모델만 실행합니다.')
    return model

def write_rights(destination, job):
    model = commercial_model(job['kind'])
    manifest = DATA / 'models' / job['kind'] / 'download.json'
    download = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    note = ('선택한 모델의 라이선스는 조건을 지키는 상업 이용을 허용합니다. '
            '입력 이미지·가사·참조 자료와 결과에 포함된 타인의 권리는 별도로 확인해야 합니다. '
            '이 안내는 생성물의 독점 저작권, 비침해 또는 저작권 등록 가능성을 보증하지 않습니다. '
            '모델·코드 재배포 조건과 생성 파일의 이용 조건은 구분됩니다.')
    rights = dict(model=model['model'], repository=model['repo'], download=download,
                  license=model['license'], source=model['source'], license_source=model['license_source'],
                  commercial_use='permitted_subject_to_original_terms', conditions=model['commercial_note'],
                  notice=note, reviewed_on='2026-10-07', job_id=job['id'])
    save_json(destination / 'rights.json', rights)
    (destination / 'commercial-use.txt').write_text(
        '생성물 상업 이용 안내\n\n모델: ' + model['model'] + '\n라이선스: ' + model['license'] +
        '\n공식 조건: ' + model['license_source'] + '\n\n' + model['commercial_note'] + '\n\n' + note +
        '\n\n이 파일은 출처 확인을 위한 안내입니다. 모델 라이선스를 생성물에 새로 부여하는 문서가 아닙니다.\n',
        encoding='utf-8')
