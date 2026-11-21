"""Run the registered calibration replay, main block, and analysis under one CPU budget."""
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from phase2 import CAP_SECONDS, WORKERS, write


HERE = Path(__file__).resolve().parent


def cpu_seconds(active=()):
    tick = os.sysconf("SC_CLK_TCK")
    cpu = 0.
    for process in active:
        stat = Path(f"/proc/{process.pid}/stat").read_text().rsplit(")",1)[1].split()
        cpu += (int(stat[11])+int(stat[12]))/tick
    for kind in (resource.RUSAGE_SELF,resource.RUSAGE_CHILDREN):
        usage = resource.getrusage(kind)
        cpu += usage.ru_utime + usage.ru_stime
    return cpu


def batch(out, label, commands):
    running, logs = [], []
    try:
        for i, command in enumerate(commands):
            stream = (out/f"{label}_{i:02d}.log").open("x")
            logs.append(stream)
            running.append(subprocess.Popen([sys.executable,"-u",*map(str,command)],
                                            stdout=stream,stderr=subprocess.STDOUT))
        while True:
            codes = [p.poll() for p in running]
            for i, code in enumerate(codes):
                if code not in (0,None):
                    raise RuntimeError(f"{label} process {i} exited {code}: {(out/f'{label}_{i:02d}.log').read_text()[-5000:]}")
            active = [p for p,code in zip(running,codes,strict=True) if code is None]
            # Reserve a full sample interval plus shutdown at maximum occupancy.
            if cpu_seconds(active) >= CAP_SECONDS - 2*(WORKERS+1):
                raise TimeoutError("10 core-hour budget reached")
            if not active:
                return
            time.sleep(1)
    finally:
        for p in running:
            if p.poll() is None:
                p.terminate()
        for p in running:
            p.wait()
        for stream in logs:
            stream.close()


def main(out):
    os.umask(0o077)
    os.environ.update(TMPDIR="/data/guoyikun/tmp",PYTHONDONTWRITEBYTECODE="1",CUDA_VISIBLE_DEVICES="",
                      OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",NUMEXPR_NUM_THREADS="1")
    start = time.monotonic()
    state = "STOPPED"
    try:
        batch(out,"verify",[[HERE/"phase2.py","verify","--out",out]])
        for block in ("calibration","main"):
            print(f"Starting {block} with {WORKERS} single-thread workers",flush=True)
            batch(out,block,[[HERE/"phase2.py",block,"--out",out,"--shard",i] for i in range(WORKERS)])
            batch(out,block+"_analysis",[[HERE/"analyze_v2.py",block,out]])
        state = "DONE"
    finally:
        try:
            write(out/"run_receipt.json",dict(status=state,core_hours=cpu_seconds()/3600,
                                               wall_seconds=time.monotonic()-start),
                  dict(workers=WORKERS,threads=1,core_hour_cap=CAP_SECONDS/3600))
        finally:
            (out/"STATUS").write_text(state+"\n")
            print(state,flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
