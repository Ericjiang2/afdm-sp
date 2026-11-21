"""S4 bounded GPU queue; each run has an independent immutable output."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
BASE=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s4_20260906')
S2=BASE.parent/'s2_20260906'
SOURCE=BASE/'source-v1'
PY='/home/guoyikun/.conda/envs/AFDM/bin/python'
CKPT=BASE.parent.parent/'afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk'

def job(name,rep,n,extra=()):
    return dict(name=name,timeout=1200,cmd=[PY,'-u','-m','afdm_sp_joint_unrolled.budgeted_support_eval',
        '--ckpt',str(CKPT),'--calibration',str(S2/'calibration-snr8/cache_snr8.pt'),
        '--snr','8','--replicate',str(rep),'--frames',str(n),'--out',str(BASE/name),*extra])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['smoke','cal','dev']);mode=ap.parse_args().mode
    if mode=='smoke':
        (BASE/'identity-temperature.json').write_text(json.dumps(dict(split='D_cal',snr=8,selected_temperature=1.,scope='engineering identity fixture; not fitted calibration')))
        jobs=[job('identity-smoke',998,2,('--arms','baseline','temperature_mean','--feedback-calibration',str(BASE/'identity-temperature.json'))),
              job('cal-smoke',997,2,('--split','cal','--arms','baseline','--soft-observe'))]
    elif mode=='cal':
        assert json.loads((BASE/'smoke-validation.json').read_text())['passed']
        jobs=[job(f'cal-rep{r}',r,64,('--split','cal','--arms','baseline','--soft-observe')) for r in (10,11,12)]
    else:
        assert json.loads((BASE/'feedback-calibration.json').read_text())['passed']
        jobs=[job(f'dev-rep{r}',r,64,('--arms','baseline','temperature_mean','--feedback-calibration',str(BASE/'feedback-calibration.json'),'--soft-observe')) for r in range(3)]
    path=BASE/f'{mode}-batch.json';path.touch(exist_ok=False)
    report=dict(mode=mode,pid=os.getpid(),source=str(SOURCE),started_at=time.time(),complete=False,runs=[],scope='S4 exploratory; concurrent timing not G2')
    def save():path.write_text(json.dumps(report,indent=2))
    save()
    # One extra GPU lane on disjoint host cores while S2 controls occupy 0-11.
    for row in jobs:
        env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
        with (BASE/f"{row['name']}.log").open('x') as log:
            p=subprocess.Popen(['taskset','-c','16-19',*row['cmd']],cwd=SOURCE,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            row.update(pid=p.pid,started_at=time.time(),exit_code=None);report['runs'].append(row);save()
            try:code=p.wait(timeout=row['timeout'])
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                code=124
            row.update(exit_code=code,elapsed_seconds=time.time()-row['started_at']);save()
            if code!=0:report['failure']='job failed; pending rows not launched';break
    report.update(complete=True,elapsed_seconds=time.time()-report['started_at']);save()
if __name__=='__main__':main()
