"""Bounded independent S2 jobs. Run only inside the isolated deinlab directory."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

BASE = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s2_20260906')
SOURCE = BASE/'source-v2'
PYTHON = '/home/guoyikun/.conda/envs/AFDM/bin/python'
CKPT = str(BASE.parent.parent/'afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk')


def diagnostic(name, snr, rep, frames, extra=()):
    return dict(name=name, timeout=1200, creates_out=True, cmd=[
        PYTHON, '-u', '-m', 'afdm_sp_joint_unrolled.budgeted_support_eval',
        '--ckpt', CKPT, '--calibration', str(BASE/f'calibration-snr{snr}/cache_snr{snr}.pt'),
        '--snr', str(snr), '--replicate', str(rep), '--frames', str(frames),
        '--out', str(BASE/name), *extra])


def main():
    global SOURCE
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['smoke','matrix','refs-smoke','refs','controls-smoke','controls'])
    mode = ap.parse_args().mode
    if mode.startswith('refs'):
        SOURCE = BASE/'source-v3'
    if mode.startswith('controls'):
        SOURCE = BASE/'source-v5'
    old = json.loads((BASE.parent/'s0s1_20260906/budget-1024-batch.json').read_text())
    if not old['complete'] or any(r['exit_code'] != 0 for r in old['runs']):
        raise RuntimeError('S1 timing must complete successfully before GPU concurrency')
    status_path = BASE/f'{mode}-batch.json'
    status_path.touch(exist_ok=False)
    if mode == 'controls-smoke':
        jobs = [diagnostic('controls-baseline',8,998,1,('--arms','baseline')),
                diagnostic('uncoded-smoke',15,996,2,('--uncoded',)),
                diagnostic('conservative-smoke',8,996,2,('--arms','baseline','conservative'))]
        concurrency = 2
    elif mode == 'controls':
        if not json.loads((BASE/'controls-smoke-validation.json').read_text())['passed']:
            raise RuntimeError('remaining-controls engineering gate has not passed')
        jobs = [diagnostic(f'conservative-rep{rep}',8,rep,64,('--arms','baseline','conservative')) for rep in range(3)]
        jobs += [diagnostic(f'uncoded-snr{snr}-rep{rep}',snr,rep,64,('--uncoded',))
                 for snr in (15,20) for rep in range(3)]
        concurrency = 3
    elif mode == 'refs-smoke':
        jobs = [diagnostic('i3-smoke-cpu',8,998,1,('--local-actions','--device','cpu')),
                diagnostic('i5-smoke-cpu',8,998,2,('--arms','position_true','position_rounded','--device','cpu'))]
        concurrency = 2
    elif mode == 'refs':
        if not json.loads((BASE/'refs-smoke-validation.json').read_text())['passed']:
            raise RuntimeError('I3/I5 smoke gate has not passed')
        jobs = [diagnostic(f'i5-rep{rep}',8,rep,8,('--arms','position_true','position_rounded'))
                for rep in range(3)]
        jobs += [diagnostic(f'i3-rep{rep}',8,rep,8,('--local-actions',)) for rep in range(3)]
        for job in jobs:
            job['timeout'] = 1800
        concurrency = 3
    elif mode == 'matrix':
        if not json.loads((BASE/'smoke-validation.json').read_text())['passed']:
            raise RuntimeError('S2 smoke/replay gate has not passed')
        jobs = [diagnostic(f'dev-snr{snr}-rep{rep}',snr,rep,64)
                for snr in (7,8,9) for rep in range(3)]
        concurrency = 3
    else:
        e1 = dict(name='e1-parity-8',timeout=480,creates_out=False,cmd=[
            PYTHON,'-u','-m','afdm_sp_joint_unrolled.e1_ldpc_coded_eval',
            '--ckpt',CKPT,'--variant','C2-rel','--mp-mode','bp','--p-paths','8',
            '--tau-spread','.010','--n-total','1024','--v-mean','2','--fs-factor','4',
            '--snr-list','7','--frames-per-snr','8','--seed','20260601','--cdtype','complex64',
            '--refine-rounds','2','--cand-topm','96','--defer-prune-until-final',
            '--protect-added','2','--n-outer-iter','10','--gateA-scorer','achievable',
            '--gateA-calib-frames','400','--require-cuda','--trace-jsonl',
            '--arm-order-seed','20260906','--out',str(BASE/'e1-parity-8')])
        jobs = [e1,diagnostic('smoke-observed',8,999,2),
                diagnostic('smoke-no-observer',8,999,2,('--arms','baseline','--no-observe'))]
        concurrency = 2
    report = dict(mode=mode,pid=os.getpid(),source=str(SOURCE),started_at=time.time(),
                  complete=False,runs=[],concurrency=concurrency,
                  scope='concurrent engineering/development; not G2 latency evidence')
    pending, running = list(jobs), []
    def save():
        status_path.write_text(json.dumps(report,indent=2))
    save()
    if mode == 'refs':
        report['waiting_for'] = 'matrix-batch complete; preserve GPU throughput'
        save()
        while not json.loads((BASE/'matrix-batch.json').read_text())['complete']:
            if time.time()-report['started_at'] > 3600:
                raise RuntimeError('reference queue exceeded dependency wait budget')
            time.sleep(10)
        report['waiting_for'] = None
        save()
    while pending or running:
        if time.time()-report['started_at'] > 7200:
            report['unstarted'] = [j['name'] for j in pending]
            pending.clear()
            for _,_,row,_ in running:
                row['timeout'] = 0
        for slot in range(concurrency):
            if not pending or any(r[3] == slot for r in running):
                continue
            row = pending.pop(0)
            if not row['creates_out']:
                (BASE/row['name']).mkdir(exist_ok=False)
            log = (BASE/f"{row['name']}.log").open('x')
            offset = 32 if mode == 'refs-smoke' else 0
            affinity = f'{offset+slot*4}-{offset+slot*4+3}'
            env = dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
            if mode == 'refs-smoke':
                env['CUDA_VISIBLE_DEVICES'] = ''
            proc = subprocess.Popen(['taskset','-c',affinity,*row['cmd']],cwd=SOURCE,
                                    env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            row.update(pid=proc.pid,affinity=affinity,started_at=time.time(),exit_code=None)
            report['runs'].append(row)
            running.append((proc,log,row,slot))
            save()
        for proc,log,row,slot in list(running):
            code = proc.poll()
            if code is None and time.time()-row['started_at'] > row['timeout']:
                os.killpg(proc.pid,signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL)
                    proc.wait()
                code = 124
                row['failure'] = 'registered timeout; partial frames retained'
            if code is not None:
                row.update(exit_code=code,elapsed_seconds=time.time()-row['started_at'])
                log.close()
                running.remove((proc,log,row,slot))
                save()
        if running:
            time.sleep(1)
    report.update(complete=True,elapsed_seconds=time.time()-report['started_at'])
    save()


if __name__ == '__main__':
    main()
