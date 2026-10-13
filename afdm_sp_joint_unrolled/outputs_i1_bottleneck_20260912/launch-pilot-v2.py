"""Resume before first scientific call; CPU exact-byte gate exception is evidence-bound.

See evidence/remote-cpu-recovery.json. Numerical receiver source is unchanged.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    path = ROOT/'evidence'/name
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, allow_nan=False, indent=2)
        f.write('\n')


def child(name, command, cwd, env, seconds):
    start = time.time()
    with (ROOT/'logs'/(name+'.log')).open('x') as log:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        write(name+'-launch.json', dict(pid=process.pid, started_at=start,
            command=command, cwd=str(cwd), timeout_seconds=seconds))
        timed_out = False
        try:
            code = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait(timeout=10)
        result = dict(name=name, pid=process.pid, exit_code=code, timed_out=timed_out,
                      started_at=start, finished_at=time.time(), wall_seconds=time.time()-start)
        write(name+'-exit.json', result)
    print(json.dumps(result), flush=True)
    if code!=0 or timed_out:
        raise RuntimeError(name+' did not complete successfully')
    return result


def environment(source):
    env = os.environ.copy()
    scratch = Path('/data/guoyikun/tmp/afdm-bottleneck-20260912')
    scratch.mkdir(exist_ok=True)
    env.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
        CUDA_VISIBLE_DEVICES='0', TMPDIR=str(scratch), TEMP=str(scratch), TMP=str(scratch),
        NUMBA_CACHE_DIR=str(scratch/'numba'), XDG_CACHE_HOME=str(scratch/'cache'),
        MPLCONFIGDIR=str(scratch/'matplotlib'), TORCH_HOME=str(scratch/'torch'))
    return env


def main():
    contract_path = ROOT/'inputs/contract.json'
    contract = json.loads(contract_path.read_text())
    sources = {name: ROOT/('source-'+name) for name in ('golden','current')}
    # Source-bound real numerical unit tests. One pre-existing, unused oracle-data
    # adapter test was separately reproduced on the unchanged baseline archive.
    modules = ['test_bottleneck_feedback_consumers','test_bottleneck_pilot',
        'test_supplement_detectors',
        'test_supplement_feedback_controller.ControllerBoundaryTests',
        'test_supplement_feedback_controller.ControllerTests.test_enabled_changes_actual_next_detector_and_ce',
        'test_supplement_feedback_controller.ControllerTests.test_enabled_feedback_ce_audit_matches_consumed_moments',
        'test_supplement_feedback_bp','test_supplement_feedback_adapter',
        'test_supplement_feedback_schedule.ScheduleTests.test_default_and_explicit_original_and_reduced_calls',
        'test_supplement_feedback_schedule.ScheduleTests.test_schedule_domain_immutable']
    child('numerical-tests-v2', [PYTHON,'-B','-m','unittest','-v']+
          ['afdm_sp_joint_unrolled.'+m for m in modules], sources['current'],
          environment(sources['current']), 300)
    stage_exits = []
    for stage in ('golden','engineering','development'):
        source = sources['golden' if stage=='golden' else 'current']
        manifest = source/'source-manifest.json'
        command = [PYTHON,'-B','-m','afdm_sp_joint_unrolled.bottleneck_pilot',
            '--stage',stage,'--root',str(ROOT/'runs'),'--contract',str(contract_path),
            '--contract-sha256',sha(contract_path),'--source-manifest',str(manifest),
            '--source-sha256',sha(manifest)]
        if stage=='development':
            engineering_path = ROOT/'runs/engineering/summary.json'
            engineering = json.loads(engineering_path.read_text())
            if (engineering['status']!='COMPLETE' or engineering['calls']!={'F':20,'T':28}
                    or len(engineering['engineering_comparisons'])!=4
                    or len(engineering['ep_qualification'])!=8):
                raise ValueError('engineering evidence incomplete')
            means = {}
            for arm in contract['full_arms']+contract['terminal_arms']:
                costs = [row['seconds'] for row in engineering['records'] if row['arm']==arm]
                if len(costs)!=4:
                    raise ValueError('quote missing an engineering arm')
                means[arm] = sum(costs)/len(costs)
            overhead = max(0., engineering['wall_seconds']-
                           sum(row['seconds'] for row in engineering['records']))/4
            projected = 1.5*128*(sum(means.values())+overhead)+60
            if projected>contract['bounds']['development']['seconds']:
                raise RuntimeError('conservative development quote exceeds fixed wall budget')
            admission = dict(status='PASS', contract_sha256=sha(contract_path),
                source_manifest_sha256=sha(manifest), engineering_summary_sha256=sha(engineering_path),
                projected_development_seconds=projected, quote_mean_seconds=means,
                quote_overhead_per_observation=overhead,
                ep_stable_pairs=sum(row['stable'] for row in engineering['ep_qualification']),
                ep_total_pairs=8,
                ep_scope='finite capped reference; stability failure never implies BP optimality',
                default_replay='continuous relative L2<=1e-6, exact hard/decoded/support; hashes retained')
            write('engineering-admission.json', admission)
            proof = ROOT/'evidence/engineering-admission.json'
            command += ['--admission',str(proof),'--admission-sha256',sha(proof)]
        stage_exits.append(child(stage, command, source, environment(source),
                                 contract['bounds'][stage]['seconds']))
    total = sum(row['wall_seconds'] for row in stage_exits)
    if total>contract['total_bounds']['seconds']:
        raise RuntimeError('execution stage wall-time total exceeded contract')
    write('pipeline-complete-v2.json', dict(status='COMPLETE', stages=stage_exits,
        execution_wall_seconds=total, completed_at=time.time(), pid=os.getpid(),
        scope='collection complete; independent raw audit and analysis still required'))


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        write('pipeline-failure-v2.json', dict(status='FAILED', error=repr(error),
                                           pid=os.getpid(), stopped_at=time.time()))
        raise
