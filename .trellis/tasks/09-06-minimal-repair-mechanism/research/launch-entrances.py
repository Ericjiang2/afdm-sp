"""Frozen S4 mean/Q/C paired comparison with bounded parallel workers."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
BASE=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s4_20260906')
SOURCE=BASE/'source-v2';PY='/home/guoyikun/.conda/envs/AFDM/bin/python'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['smoke','dev']);mode=ap.parse_args().mode
    calibration=BASE/('identity-temperature.json' if mode=='smoke' else 'feedback-calibration.json')
    if mode=='dev':
        assert json.loads((BASE/'entrances-smoke-validation.json').read_text())['passed']
        assert json.loads(calibration.read_text())['passed']
    names=[('entrances-smoke',998,2)] if mode=='smoke' else [(f'entrances-dev-rep{r}',r,64) for r in range(3)]
    report=dict(pid=os.getpid(),mode=mode,started_at=time.time(),source=str(SOURCE),complete=False,runs=[])
    status=BASE/f'entrances-{mode}-batch.json';status.touch(exist_ok=False)
    def save():status.write_text(json.dumps(report,indent=2))
    save();running=[]
    for slot,(name,rep,n) in enumerate(names):
        cmd=[PY,'-u','-m','afdm_sp_joint_unrolled.budgeted_support_eval','--ckpt',str(BASE.parent.parent/'afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk'),
             '--calibration',str(BASE.parent/'s2_20260906/calibration-snr8/cache_snr8.pt'),'--snr','8','--replicate',str(rep),'--frames',str(n),
             '--arms','baseline','temperature_mean','jsoft','covariance','--feedback-calibration',str(calibration),'--soft-observe','--out',str(BASE/name)]
        log=(BASE/f'{name}.log').open('x');aff=f'{16+slot*4}-{19+slot*4}'
        p=subprocess.Popen(['taskset','-c',aff,*cmd],cwd=SOURCE,env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4'),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        row=dict(name=name,pid=p.pid,cmd=cmd,affinity=aff,started_at=time.time(),exit_code=None);report['runs'].append(row);running.append((p,log,row));save()
    while running:
        for p,log,row in list(running):
            code=p.poll()
            if code is None and time.time()-row['started_at']>1800:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                code=124
            if code is not None:
                row.update(exit_code=code,elapsed_seconds=time.time()-row['started_at']);log.close();running.remove((p,log,row));save()
        if running:time.sleep(1)
    report.update(complete=True,elapsed_seconds=time.time()-report['started_at']);save()
if __name__=='__main__':main()
