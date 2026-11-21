"""Three CPU-only calibration jobs, using the already verified S1 source."""
import json
import argparse
import os
from pathlib import Path
import subprocess
import time

import numpy as np

BASE = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s2_20260906')
SOURCE = BASE.parent / 's0s1_20260906/source-trace-v1'
PYTHON = '/home/guoyikun/.conda/envs/AFDM/bin/python'
ap = argparse.ArgumentParser()
ap.add_argument('--snrs',type=int,nargs='+',default=[7,8,9])
ap.add_argument('--label',choices=['calibration','highsnr-calibration'],default='calibration')
ap.add_argument('--cpu-start',type=int,default=32)
args = ap.parse_args()
if len(set(args.snrs))!=len(args.snrs) or args.cpu_start<0:
    raise ValueError('invalid calibration queue identifiers')
seed_base = int(np.random.SeedSequence([20260905, 2, 0, 0, 9]).generate_state(1)[0])
status_path = BASE / f'{args.label}-status.json'
status_path.touch(exist_ok=False)
report = dict(pid=os.getpid(), source=str(SOURCE), split='D_cal', seed_base=seed_base,
              cuda_visible_devices='', started_at=time.time(), complete=False, runs=[])
env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4')
running = []
for slot,snr in enumerate(args.snrs):
    affinity=f'{args.cpu_start+4*slot}-{args.cpu_start+4*slot+3}'
    out = BASE / f'calibration-snr{snr}'
    out.mkdir(exist_ok=False)
    cmd = ['nice', '-n', '10', 'taskset', '-c', affinity, PYTHON, '-u', '-m',
           'afdm_sp_joint_unrolled.decision_harvest', '--snr', str(snr),
           '--n-frames', '400', '--n-total', '1024', '--p-paths', '8', '--tau-ms', '10',
           '--v-mean', '2', '--fs-factor', '4', '--M', '96', '--p-pad', '64',
           '--seed-base', str(seed_base), '--out', str(out)]
    log = (BASE / f'calibration-snr{snr}.log').open('x')
    proc = subprocess.Popen(cmd, cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT)
    row = dict(snr=snr, affinity=affinity, pid=proc.pid, cmd=cmd, started_at=time.time(),
               exit_code=None, timeout_seconds=480)
    report['runs'].append(row)
    running.append((proc, log, row))
status_path.write_text(json.dumps(report, indent=2))
while running:
    for proc, log, row in list(running):
        code = proc.poll()
        if code is None and time.time()-row['started_at'] > row['timeout_seconds']:
            proc.kill()
            proc.wait()
            code = 124
            row['failure'] = 'registered calibration timeout'
        if code is not None:
            log.close()
            row.update(exit_code=code, elapsed_seconds=time.time()-row['started_at'])
            running.remove((proc, log, row))
            status_path.write_text(json.dumps(report, indent=2))
    if running:
        time.sleep(2)
report.update(complete=True, elapsed_seconds=time.time()-report['started_at'])
status_path.write_text(json.dumps(report, indent=2))
