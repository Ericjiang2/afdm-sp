"""Fixed-capacity calibration/verification; bounded queues, no truth-sized receiver."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
import numpy as np
BASE=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s4_20260906')
SOURCE=BASE/'source-v3';PY='/home/guoyikun/.conda/envs/AFDM/bin/python'
CAPS=(8,16,24,32,40)

def receiver(name,cap,rep,n,start=0,split='cal',arms=('baseline',),temperature='identity-temperature.json',observe=False):
    prior=BASE/f'prior-cap{cap}/cache_snr8.pt' if cap else BASE.parent/'s2_20260906/calibration-snr8/cache_snr8.pt'
    cmd=[PY,'-u','-m','afdm_sp_joint_unrolled.budgeted_support_eval','--ckpt',str(BASE.parent.parent/'afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk'),
         '--calibration',str(prior),'--snr','8','--replicate',str(rep),'--frames',str(n),'--start-frame',str(start),'--split',split,'--arms',*arms,'--out',str(BASE/name)]
    if cap:cmd+=['--active-cap',str(cap)]
    if len(arms)>1:cmd+=['--feedback-calibration',str(BASE/temperature)]
    if observe:cmd+=['--soft-observe']
    return dict(name=name,cmd=cmd,timeout=1200)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prior-smoke','prior','smoke','fit','validation','dev']);mode=ap.parse_args().mode
    jobs=[];cpu=mode.startswith('prior');concurrency=5 if cpu else 3
    if cpu:
        if mode=='prior':assert json.loads((BASE/'capacity-prior-smoke-validation.json').read_text())['passed']
        seed=int(np.random.SeedSequence([20260905,2,20,0,9]).generate_state(1)[0])
        for cap in CAPS:
            name=f'prior-cap{cap}' if mode=='prior' else f'prior-smoke-cap{cap}'
            jobs.append(dict(name=name,timeout=480,cmd=[PY,'-u','-m','afdm_sp_joint_unrolled.decision_harvest','--snr','8','--n-frames',str(400 if mode=='prior' else 2),'--n-total','1024','--p-paths','8','--tau-ms','10','--v-mean','2','--fs-factor','4','--M','96','--p-pad','64','--seed-base',str(seed),'--nomination-cap',str(cap//5),'--out',str(BASE/name)]))
    elif mode=='smoke':
        q=json.loads((BASE/'capacity-prior-batch.json').read_text());assert q['complete'] and len(q['runs'])==5 and all(r['exit_code']==0 for r in q['runs'])
        jobs=[receiver('capacity-legacy-replay',None,998,2,split='dev')]
        jobs += [receiver(f'capacity-smoke{c}',c,997,2,arms=('baseline','covariance')) for c in CAPS]
    elif mode=='fit':
        assert json.loads((BASE/'capacity-smoke-validation.json').read_text())['passed']
        jobs=[receiver(f'capacity-fit{c}-rep{r}',c,r,16,observe=True) for c in CAPS for r in (20,21,22)]
    else:
        cal=json.loads((BASE/'fixed-feedback-calibration.json').read_text());assert cal['passed'];cap=cal['active_cap']
        comparison_arms=('baseline','covariance') if cal['selected_temperature']==1 else ('baseline','temperature_mean','covariance')
        if mode=='validation':jobs=[receiver(f'capacity-validation-rep{r}',cap,r,16,start=16,arms=comparison_arms,temperature='fixed-feedback-calibration.json',observe=True) for r in (20,21,22)]
        else:
            assert json.loads((BASE/'capacity-validation-report.json').read_text())['engineering_passed']
            jobs=[receiver(f'capacity-dev-rep{r}',cap,r,64,split='dev',arms=comparison_arms,temperature='fixed-feedback-calibration.json',observe=True) for r in range(3)]
    status=BASE/f'capacity-{mode}-batch.json';status.touch(exist_ok=False)
    report=dict(pid=os.getpid(),mode=mode,started_at=time.time(),source=str(SOURCE),complete=False,runs=[],concurrency=concurrency)
    def save():status.write_text(json.dumps(report,indent=2))
    save();running=[];pending=list(jobs)
    while running or pending:
        for slot in range(concurrency):
            if not pending or any(x[3]==slot for x in running):continue
            row=pending.pop(0);env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
            if cpu:env['CUDA_VISIBLE_DEVICES']=''
            off=36 if cpu else 16;aff=f'{off+4*slot}-{off+4*slot+3}'
            if cpu:(BASE/row['name']).mkdir(exist_ok=False)
            log=(BASE/f"{row['name']}.log").open('x')
            p=subprocess.Popen(['taskset','-c',aff,*row['cmd']],cwd=SOURCE,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            row.update(pid=p.pid,affinity=aff,started_at=time.time(),exit_code=None);report['runs'].append(row);running.append((p,log,row,slot));save()
        for p,log,row,slot in list(running):
            code=p.poll()
            if code is None and time.time()-row['started_at']>row['timeout']:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                code=124
            if code is not None:
                row.update(exit_code=code,elapsed_seconds=time.time()-row['started_at']);log.close();running.remove((p,log,row,slot));save()
        if running:time.sleep(1)
    report.update(complete=True,elapsed_seconds=time.time()-report['started_at']);save()
if __name__=='__main__':main()
