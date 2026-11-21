"""Measure the frozen S1 achievable arm at historical waterfall SNR8; no method selection."""
import json
import os
from pathlib import Path
import subprocess
import time

BASE = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s0s1_20260906')
PYTHON = '/home/guoyikun/.conda/envs/AFDM/bin/python'
CKPT = '/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk'
status_path = BASE / 'budget-1024-batch.json'
status_path.touch(exist_ok=False)
report = {'pid': os.getpid(), 'started_at': time.time(), 'runs': [], 'complete': False}
status_path.write_text(json.dumps(report, indent=2))
for name, omp, blas in [('budget-1024-achievable-snr8', 4, 4)]:
    output = BASE / name
    output.mkdir(exist_ok=False)
    cmd = [PYTHON, '-u', '-m', 'afdm_sp_joint_unrolled.e1_ldpc_coded_eval',
           '--ckpt', CKPT, '--variant', 'C2-rel', '--mp-mode', 'bp', '--p-paths', '8',
           '--tau-spread', '.010', '--n-total', '1024', '--v-mean', '2', '--fs-factor', '4',
           '--snr-list', '8', '--frames-per-snr', '1024', '--seed', '20260906',
           '--cdtype', 'complex64', '--refine-rounds', '2', '--cand-topm', '96',
           '--defer-prune-until-final', '--protect-added', '2', '--n-outer-iter', '10',
           '--gateA-scorer', 'achievable', '--gateA-calib-frames', '400', '--require-cuda',
           '--trace-jsonl', '--arm-order-seed', '20260906', '--out', str(output)]
    env = dict(os.environ, OMP_NUM_THREADS=str(omp), OPENBLAS_NUM_THREADS=str(blas))
    started = time.time()
    run = dict(name=name, cmd=cmd, omp=omp, openblas=blas, started_at=started)
    with (BASE / f'{name}.log').open('x') as log:
        try:
            result = subprocess.run(cmd, cwd=BASE / 'source-trace-v1', env=env,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            run['exit_code'] = result.returncode
        except subprocess.TimeoutExpired:
            run['exit_code'] = 124
            run['failure'] = 'registered 1800-second budget timeout'
    run['elapsed_seconds'] = time.time() - started
    report['runs'].append(run)
    status_path.write_text(json.dumps(report, indent=2))
report['complete'] = True
report['elapsed_seconds'] = time.time() - report['started_at']
status_path.write_text(json.dumps(report, indent=2))
