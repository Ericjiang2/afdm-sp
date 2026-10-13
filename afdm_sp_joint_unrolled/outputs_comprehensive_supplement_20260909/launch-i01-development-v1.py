"""Launch one finite, unique I-01 development batch on the authorized server."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import time

R = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909')
ROOT = R / 'source-i01-development-v1'
INPUTS = R / 'i01-development-inputs-v1'
GPU = 'GPU-fe13c694-2050-c9f0-2904-b806f6f6b0c2'
SOCKET = '/data/guoyikun/tmp/g_afdm_supp0909.sock'
PYTHON = '/home/guoyikun/.conda/envs/AFDM/bin/python'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--stop', type=int, required=True)
    args = parser.parse_args()
    if not 0 <= args.start < args.stop <= 192 or args.stop - args.start > 16:
        raise ValueError('batch must contain 1..16 design blocks')
    name = f'i01-development-b{args.start:03d}-{args.stop:03d}-v1'
    session = 'g_afdm_supp_' + name.replace('-', '_')
    out = R / name
    count = (args.stop - args.start) * 18
    limit = max(512 * 1024**2, count * 2 * 1024**2 + 32 * 1024**2)
    duration = 1200 if count == 18 else 3600
    with (R / 'i01-development-launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if out.exists() or (R / (name + '.sh')).exists():
            raise ValueError('batch already created; no automatic restart')
        panes = subprocess.run(['tmux', '-S', SOCKET, 'list-panes', '-a', '-F',
                                '#{session_name} #{pane_pid} #{pane_dead}'],
                               capture_output=True, text=True, timeout=10)
        if panes.returncode and 'no server running' not in panes.stderr:
            raise RuntimeError(panes.stderr)
        live = [line for line in panes.stdout.splitlines()
                if line.startswith('g_afdm_supp_') and line.split()[-1] == '0']
        if len(live) >= 2:
            raise RuntimeError('two task receiver jobs already active')
        probe = subprocess.run(['nvidia-smi', '--query-gpu=uuid,memory.free,memory.used,utilization.gpu',
                                '--format=csv,noheader,nounits'], capture_output=True,
                               text=True, check=True, timeout=10)
        rows = [line.split(',') for line in probe.stdout.splitlines()
                if line.split(',')[0].strip() == GPU]
        if len(rows) != 1 or float(rows[0][1]) < 6144:
            raise RuntimeError('GPU UUID/free-memory admission failed')
        if float(rows[0][2]) > 18432 and float(rows[0][3]) > 90:
            raise RuntimeError('shared GPU strong collision')
        if shutil.disk_usage(R).free < limit + 16 * 1024**3:
            raise OSError('insufficient project disk reserve')
        manifest = json.loads((ROOT / 'source-manifest.json').read_text())
        for rel, expected in manifest.items():
            if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != expected:
                raise ValueError('source snapshot changed: ' + rel)
        deadline = int(time.time()) + duration
        command = ['timeout', '--signal=TERM', '--kill-after=15s', str(duration + 15) + 's',
                   PYTHON, '-m', 'afdm_sp_joint_unrolled.supplement_feedback_run',
                   '--protocol', str(INPUTS / 'data-protocol.json'),
                   '--development-protocol', str(INPUTS / 'development-protocol.json'),
                   '--quote', str(INPUTS / 'quote-summary.json'),
                   '--checkpoint', '/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk',
                   '--out', str(out), '--start', str(args.start), '--stop', str(args.stop),
                   '--max-full-calls', str(count), '--max-output-bytes', str(limit),
                   '--threads', '1', '--deadline-unix', str(deadline), '--device', 'cuda:0']
        env = dict(PYTHONPATH=str(ROOT / 'source'), PYTHONDONTWRITEBYTECODE='1',
                   CUDA_VISIBLE_DEVICES=GPU, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                   MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', TMPDIR=str(R / 'tmp'),
                   MPLCONFIGDIR=str(R / 'tmp/matplotlib'), XDG_CACHE_HOME=str(R / 'tmp/cache'))
        shell = R / (name + '.sh')
        with shell.open('x') as stream:
            stream.write('#!/bin/bash\nset -u\ncd ' + shlex.quote(str(ROOT)) + '\n')
            for key, value in env.items():
                stream.write('export ' + key + '=' + shlex.quote(value) + '\n')
            stream.write(shlex.join(command) + ' > ' + shlex.quote(str(R / (name + '.log'))) + ' 2>&1\n')
            stream.write('printf "%s\\n" "$?" > ' + shlex.quote(str(R / (name + '.exit'))) + '\n')
        admission = dict(batch=name, session=session, deadline_unix=deadline, max_F=count,
                         output_cap_bytes=limit, gpu_preflight=probe.stdout, existing_task_panes=live,
                         source_manifest_sha256=hashlib.sha256((ROOT / 'source-manifest.json').read_bytes()).hexdigest(),
                         scope='development only; ledger reserved by runner before first F; no retry or COST-02 inference')
        with (R / (name + '.admission.json')).open('x') as stream:
            json.dump(admission, stream, indent=2)
        subprocess.run(['tmux', '-S', SOCKET, 'new-session', '-d', '-s', session,
                        'bash', str(shell)], check=True, timeout=10)
        print(json.dumps(admission))
        print(subprocess.run(['tmux', '-S', SOCKET, 'list-panes', '-t', session,
                              '-F', '#{pane_pid} #{pane_dead}'], capture_output=True,
                             text=True, check=True, timeout=10).stdout)


if __name__ == '__main__':
    main()
