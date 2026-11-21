"""Explicit-device soft observation with same-device frozen baseline replay."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

BASE=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s2_20260906')
SOURCE=BASE/'source-v4'
PYTHON='/home/guoyikun/.conda/envs/AFDM/bin/python'
CKPT=BASE.parent.parent/'afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk'


def command(name,rep,frames,observed,device):
    return [PYTHON,'-u','-m','afdm_sp_joint_unrolled.budgeted_support_eval',
            '--ckpt',str(CKPT),'--calibration',str(BASE/'calibration-snr8/cache_snr8.pt'),
            '--snr','8','--replicate',str(rep),'--frames',str(frames),'--device',device,
            '--arms','baseline','--out',str(BASE/name),*(['--soft-observe'] if observed else [])]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--device',required=True,choices=['cpu','cuda'])
    device=ap.parse_args().device
    prefix=f'soft-{device}'
    env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
    if device=='cpu':env['CUDA_VISIBLE_DEVICES']=''
    if device=='cuda' and not json.loads((BASE/'refs-batch.json').read_text())['complete']:
        raise RuntimeError('GPU reference queue has not released its resource')
    status=BASE/f'{prefix}-batch.json'
    status.touch(exist_ok=False)
    report=dict(pid=os.getpid(),started_at=time.time(),complete=False,runs=[],source=str(SOURCE),
                scope=f'{device} outer-feedback observation; no deployable gain established')
    def save():status.write_text(json.dumps(report,indent=2))
    save()
    try:
        for suffix,observed,source,frames in [('reference-v3',False,BASE/'source-v3',1),
                                              ('smoke-observed',True,SOURCE,2),('smoke-control',False,SOURCE,2)]:
            name=f'{prefix}-{suffix}'
            started=time.time()
            cmd=['taskset','-c','32-35',*command(name,998,frames,observed,device)]
            with (BASE/f'{name}.log').open('x') as log:
                result=subprocess.run(cmd,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            report['runs'].append(dict(name=name,cmd=cmd,exit_code=result.returncode,elapsed_seconds=time.time()-started))
            save()
            if result.returncode!=0:raise RuntimeError(f'{name} failed')
        rows=lambda name:[json.loads(x) for x in (BASE/name/'frames.jsonl').read_text().splitlines()]
        observed,control=rows(f'{prefix}-smoke-observed'),rows(f'{prefix}-smoke-control')
        metrics=('raw_errors','info_errors','decode_ok','output_h_sha256','output_x_sha256','sigma2_final')
        checks={k:all(a['arms']['baseline'][k]==b['arms']['baseline'][k] for a,b in zip(observed,control)) for k in metrics}
        checks['frames_and_inputs']=len(observed)==len(control)==2 and all(a['input_hashes']==b['input_hashes'] for a,b in zip(observed,control))
        checks['stage_records']=all(len(r['arms']['baseline']['soft_feedback'])==18 for r in observed)
        old=rows(f'{prefix}-reference-v3')[0]
        checks['v3_same_device_baseline_replay']=all(control[0]['arms']['baseline'][k]==old['arms']['baseline'][k] for k in metrics)
        validation=dict(passed=all(checks.values()),checks=checks,scope=f'{device} transparency and same-device v3 replay')
        (BASE/f'{prefix}-smoke-validation.json').write_text(json.dumps(validation,indent=2))
        if not validation['passed']:raise RuntimeError('bit-exact transparency gate failed; diagnosis required')
        running=[]
        for rep in range(3):
            name=f'{prefix}-dev-rep{rep}'
            affinity=f'{32+rep*4}-{35+rep*4}'
            cmd=['taskset','-c',affinity,*command(name,rep,64,True,device)]
            log=(BASE/f'{name}.log').open('x')
            proc=subprocess.Popen(cmd,cwd=SOURCE,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            row=dict(name=name,pid=proc.pid,cmd=cmd,affinity=affinity,started_at=time.time(),exit_code=None)
            report['runs'].append(row);running.append((proc,log,row));save()
        while running:
            for proc,log,row in list(running):
                code=proc.poll()
                if code is None and time.time()-row['started_at']>900:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=124
                    row['failure']='registered 900-second observation deadline'
                if code is not None:
                    row.update(exit_code=code,elapsed_seconds=time.time()-row['started_at'])
                    log.close();running.remove((proc,log,row));save()
            if running:time.sleep(1)
        report['complete']=True
    except Exception as exc:
        report['failure']=dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        report['elapsed_seconds']=time.time()-report['started_at'];save()


if __name__=='__main__':main()
