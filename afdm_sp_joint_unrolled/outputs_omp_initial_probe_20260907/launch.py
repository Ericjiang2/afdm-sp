"""One bounded three-process deinlab packet, with explicit exit accounting."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parent
PYTHON='/home/guoyikun/.conda/envs/AFDM/bin/python'


def save(value):
    path=ROOT/'queue-status.tmp'
    path.write_text(json.dumps(value,indent=2)+'\n')
    os.replace(path,ROOT/'queue-status.json')


def main():
    with (ROOT/'launch.lock').open('x') as lock:lock.write(str(os.getpid()))
    started=time.time()
    status=dict(started=started,complete=False,runs=[],deadline=started+1800,
                scope='new small exploratory probe, not previous Mission budget')
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4')
    processes=[]
    try:
        for slot,rep in enumerate((90700,90701,90702)):
            output=ROOT/f'rep{rep}'
            if output.exists():raise FileExistsError(output)
            argv=['taskset','-c',f'{4*slot}-{4*slot+3}','timeout','1800',PYTHON,'-u','-m',
                  'afdm_sp_joint_unrolled.omp_initial_probe','--replicate',str(rep),'--frames','16',
                  '--snrs','8','12','16','--verify','--out',str(output)]
            log=(ROOT/f'rep{rep}.log').open('x')
            process=subprocess.Popen(argv,cwd=ROOT/'source',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            log.close()
            row=dict(replicate=rep,pid=process.pid,started=time.time(),exit_code=None,argv=argv)
            status['runs'].append(row);processes.append((process,row));save(status)
        while any(p.poll() is None for p,_ in processes):
            for process,row in processes:
                code=process.poll()
                if code is not None and row['exit_code'] is None:
                    row.update(exit_code=code,ended=time.time());save(status)
            if time.time()>status['deadline']:
                raise TimeoutError('30-minute exploratory packet expired')
            time.sleep(2)
        for process,row in processes:
            row.update(exit_code=process.returncode,ended=row.get('ended',time.time()))
        if any(r['exit_code']!=0 for r in status['runs']):
            raise RuntimeError('one or more probe streams failed; retain partial evidence')
        status['complete']=True
    except Exception as error:
        status['failure']=repr(error)
        for process,row in processes:
            if process.poll() is None:
                os.killpg(process.pid,15)
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,9);process.wait()
            row.update(exit_code=process.returncode,ended=time.time())
        raise
    finally:
        status['ended']=time.time();save(status)


if __name__=='__main__':main()
