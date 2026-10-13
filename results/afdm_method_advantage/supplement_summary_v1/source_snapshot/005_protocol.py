"""One immutable attempt per stage, with observable resource/source contracts."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import runpy
import signal
import subprocess
import sys
import time

from experiments.afdm_shared_channel_20261004.common import dump, hashes

ROOT=Path(__file__).resolve().parents[2]
MISSION=ROOT/'.mission/20261004_21-37-05-afdm-higher-order-information'
ARTIFACT=ROOT/'results/afdm_higher_order_information'
PACKAGE=Path(__file__).resolve().parent
BINDING=ROOT/'.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py'


def committed_sources(paths):
    """Require this task's executing package bytes in HEAD; old helpers hash-bound."""
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    checked={}
    for path in sorted({Path(p).resolve() for p in paths}):
        if not path.is_relative_to(PACKAGE) or path.suffix!='.py': continue
        relative=str(path.relative_to(ROOT))
        gitpath=subprocess.run(['git','ls-files','--full-name','--',relative],cwd=ROOT,
                               check=True,capture_output=True,text=True).stdout.strip()
        if not gitpath: raise ValueError(f'uncommitted study source: {relative}')
        blob=subprocess.run(['git','show',f'{head}:{gitpath}'],cwd=ROOT,check=True,capture_output=True).stdout
        if blob!=path.read_bytes(): raise ValueError(f'study source differs from HEAD: {relative}')
        checked[relative]=hashlib.sha256(blob).hexdigest()
    return dict(head=head,committed_task_source_sha256=checked,
                other_sources='frozen helpers and artifacts independently SHA-256 bound')


def _observations(config):
    count=config.get('new_observations')
    if isinstance(count,bool) or not isinstance(count,int) or count<0:
        raise ValueError('config must declare a nonnegative integer new_observations')
    if 'seed' not in config: raise ValueError('config must declare seed')
    if config.get('receiver_calls',0)!=0 or config.get('decoder_calls',0)!=0:
        raise ValueError('new receiver and decoder calls are not authorized')
    return count


def run(stage,config,sources,calculate,wall_seconds=600):
    """calculate(output: Path) saves raw and returns a JSON-compatible summary.

    ARTIFACT is results/afdm_higher_order_information; output is ARTIFACT/stage.
    Every config requires seed and new_observations (0 for saved-data/integrals).
    Failed registrations conservatively retain their reserved observation count.
    """
    import re
    import numpy as np
    import scipy
    from threadpoolctl import threadpool_limits
    started,cpu_started,wall_started=time.monotonic(),time.process_time(),time.time()
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*',stage): raise ValueError('unsafe stage name')
    count=_observations(config)
    contract_path=MISSION/'run_contract.json'; contract=json.loads(contract_path.read_text())
    if not np.isfinite(wall_seconds) or not 0<wall_seconds<=contract['max_wall_seconds']:
        raise ValueError('wall cap exceeds run contract')
    paths=[Path(__file__),PACKAGE/'__init__.py',BINDING,contract_path,
           ROOT/'experiments/afdm_shared_channel_20261004/common.py',*map(Path,sources)]
    fingerprint=hashes(paths); git=committed_sources(paths)
    ARTIFACT.mkdir(parents=True,exist_ok=True)
    now=wall_started; output=ARTIFACT/stage
    # The lock covers admission only, not numerical execution or benchmark scheduling.
    with (ARTIFACT/'.admission.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        reserved=sum(json.loads(p.read_text())['config']['new_observations'] for p in ARTIFACT.glob('*/registration.json'))
        if reserved+count>contract['max_new_development_observations']:
            raise ValueError('new development observation budget exceeded')
        output.mkdir(exist_ok=False)
        registration=dict(schema='higher-order-attempt/1',stage=stage,config=config,_config=config,
            argv=sys.argv,_argv=sys.argv,seed=config['seed'],source_sha256=fingerprint,
            git=git,git_head=git['head'],pid=os.getpid(),wall_cap_seconds=wall_seconds,
            started_utc=datetime.fromtimestamp(now,timezone.utc).isoformat(),
            deadline_utc=datetime.fromtimestamp(now+wall_seconds,timezone.utc).isoformat(),
            cumulative_reserved_new_observations=reserved+count,
            evidence_level='local mathematical/development; no receiver/decoder/confirmation')
        dump(output/'registration.json',registration)
        fcntl.flock(lock,fcntl.LOCK_UN)
    old_handler=signal.getsignal(signal.SIGALRM)

    def timeout(_signum,_frame): raise TimeoutError('registered wall deadline exceeded')

    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[name]='1'
    os.environ['CUDA_VISIBLE_DEVICES']=''
    try:
        signal.signal(signal.SIGALRM,timeout)
        signal.setitimer(signal.ITIMER_REAL,max(.001,wall_seconds-(time.monotonic()-started)))
        with threadpool_limits(limits=1):
            binding=runpy.run_path(str(BINDING))['blas_binding']()
            dump(output/'environment.json',dict(python=sys.version,executable=sys.executable,
                numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),
                effective_blas=binding,environment={k:os.environ[k] for k in ('OMP_NUM_THREADS',
                    'OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','CUDA_VISIBLE_DEVICES')}))
            snapshot=output/'source_snapshot'; snapshot.mkdir()
            for index,path in enumerate(sorted({p.resolve() for p in paths})):
                with (snapshot/f'{index:03d}_{path.name}').open('xb') as handle: handle.write(path.read_bytes())
            result=calculate(output)
            if hashes(paths)!=fingerprint: raise RuntimeError('bound sources changed during stage')
            if runpy.run_path(str(BINDING))['blas_binding']()!=binding:
                raise RuntimeError('effective numerical thread binding changed')
            dump(output/'results.json',result)
            total=sum(p.stat().st_size for p in ARTIFACT.rglob('*') if p.is_file())
            if total>contract['output_limit_bytes']: raise RuntimeError('task output byte cap exceeded')
            artifacts=hashes(p for p in output.rglob('*') if p.is_file())
            peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            dump(output/'attempt.json',dict(status='complete',exit_code=0,
                wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu_started,
                peak_rss_bytes=int(peak if sys.platform=='darwin' else 1024*peak),
                peak_rss_scope='whole-process cumulative high-water, not isolated kernel memory',
                artifact_sha256=artifacts,total_task_output_bytes=total))
    except BaseException as error:
        dump(output/'attempt.json',dict(status='invalid_partial',exit_code=1,error=repr(error),
             wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu_started,
             reserved_new_observations=count))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0); signal.signal(signal.SIGALRM,old_handler)
    print(json.dumps(dict(stage=stage,output=str(output),wall_seconds=time.monotonic()-started)))
    return result
