"""Bounded, fail-fast Stage 3 main shard launcher."""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent


def launch(out, commit):
    available=len(os.sched_getaffinity(0))
    load=os.getloadavg()
    jobs=min(24,available-16-math.ceil(load[0]))
    if jobs<1:
        raise RuntimeError(f'No slot at the required headroom: {available} CPUs, load {load}')
    print(f'Launch {jobs} single-thread shards, affinity CPUs={available}, load={load}',flush=True)
    deadline=time.monotonic()+30*60
    processes, streams = [],[]
    started=time.monotonic()
    clock=os.sysconf('SC_CLK_TCK')
    last_n=0
    try:
        for i in range(jobs):
            log=(out/f'm100-{i:02d}.log').open('x')
            streams.append(log)
            argv=[sys.executable,'-u',str(HERE/'run.py'),'main','--out',str(out),'--commit',commit,
                  '--shard',str(i),'--shards',str(jobs)]
            processes.append(subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT))
        while True:
            codes=[p.poll() for p in processes]
            if any(c not in (0,None) for c in codes):
                i=next(i for i,c in enumerate(codes) if c not in (0,None))
                raise RuntimeError((out/f'm100-{i:02d}.log').read_text()[-7000:])
            if all(c==0 for c in codes):
                break
            active=0.
            for p,c in zip(processes,codes,strict=True):
                if c is None:
                    # This child remains a zombie until next poll, so /proc stays present.
                    fields=Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()
                    active+=(int(fields[11])+int(fields[12]))/clock
            usage=resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu=usage.ru_utime+usage.ru_stime+active
            if cpu>14400 or time.monotonic()>=deadline:
                raise TimeoutError(f'Main run budget exceeded: {cpu/3600:.3f} core-h')
            if time.monotonic()-started>20:
                n=0
                for path in out.glob('main-*.jsonl'):
                    with path.open('rb') as f:
                        n+=sum(chunk.count(b'\n') for chunk in iter(lambda:f.read(1<<16),b''))
                if n>=1360 and last_n<1360 or n>=6800 and last_n<6800:
                    prediction=cpu*13600/(n*3600)
                    print(f'Cost gate at {n} rows: {prediction:.3f} projected core-h',flush=True)
                    if prediction>4:
                        raise TimeoutError('Projected main CPU cost exceeds four core-hours')
                last_n=n
            time.sleep(4)
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            p.wait()
        for f in streams:
            f.close()
    ru=resource.getrusage(resource.RUSAGE_CHILDREN)
    metadata=dict(jobs=jobs,wall_seconds=time.monotonic()-started,core_hours=(ru.ru_utime+ru.ru_stime)/3600,
                  load_at_start=list(load),commit=commit)
    with (out/'main_receipt.json').open('x') as f:
        json.dump(metadata,f,indent=2)
    print(f'MAIN DONE {metadata}',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    p.add_argument('commit')
    args=p.parse_args()
    launch(args.out,args.commit)
