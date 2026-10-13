"""Task-owned external deadline; environment and evidence stay in the data root."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

job_path = Path(sys.argv[1]).resolve()
expected = sys.argv[2]
if hashlib.sha256(job_path.read_bytes()).hexdigest() != expected:
    raise ValueError('job specification checksum differs')
job = json.loads(job_path.read_text())
root = Path(job['root']).resolve()
if not root.is_relative_to(Path('/data/guoyikun/')) or not job_path.is_relative_to(root):
    raise ValueError('job outside authorized data root')
name = job['name']
cache = root / 'cache' / name
cache.mkdir(parents=True, exist_ok=False)
env = os.environ.copy()
env.update({key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')})
env.update(PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
for key in ('TMPDIR', 'TEMP', 'TMP', 'XDG_CACHE_HOME', 'MPLCONFIGDIR', 'NUMBA_CACHE_DIR', 'TORCH_HOME'):
    directory = cache / key.lower()
    directory.mkdir()
    env[key] = str(directory)
started = time.time()
launch = dict(job=job, job_sha256=expected, pid=os.getpid(), started_at=started,
              timeout_seconds=job['timeout_seconds'], environment_overrides={k: env[k] for k in
              ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'TMPDIR', 'CUDA_VISIBLE_DEVICES')})
with (root / 'evidence' / (name + '-launch.json')).open('x') as f:
    json.dump(launch, f, indent=2)
exit_code, timed_out = None, False
with (root / 'logs' / (name + '.log')).open('x') as log:
    try:
        process = subprocess.run(job['command'], cwd=job['cwd'], env=env, stdout=log,
                                 stderr=subprocess.STDOUT, timeout=job['timeout_seconds'])
        exit_code = process.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
result = dict(name=name, exit_code=exit_code, timed_out=timed_out, started_at=started,
              finished_at=time.time(), wall_seconds=time.time()-started)
with (root / 'evidence' / (name + '-exit.json')).open('x') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result), flush=True)
if timed_out or exit_code != 0:
    sys.exit(124 if timed_out else exit_code)
