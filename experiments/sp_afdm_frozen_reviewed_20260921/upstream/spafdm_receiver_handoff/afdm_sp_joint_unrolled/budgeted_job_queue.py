"""Bounded Linux experiment packets; detached invocation is owned by the caller."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time


def write_status(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def validate_packet(packet, now):
    for key in ('reserved_seconds', 'remaining_seconds_at_registration', 'deadline_unix',
                'registered_unix', 'estimated_seconds', 'margin_fraction'):
        if not isinstance(packet[key], (int, float)) or not math.isfinite(packet[key]) or packet[key] < 0:
            raise ValueError('budget and time values must be finite and nonnegative')
    if packet['stage'] not in ('S2', 'S3S4', 'V3', 'DIRECTION'):
        raise ValueError('only approved development stages are supported')
    reserve = packet['reserved_seconds']
    if not 0 < reserve <= min(7200, packet['remaining_seconds_at_registration']):
        raise ValueError('packet exceeds phase or first-packet budget')
    if packet['deadline_unix'] <= now or packet['deadline_unix'] - packet['registered_unix'] > reserve:
        raise ValueError('deadline expired or exceeds reservation')
    if packet['margin_fraction'] < .2:
        raise ValueError('at least 20 percent margin required')
    if packet['estimated_seconds'] * (1 + packet['margin_fraction']) + 6 > reserve:
        raise ValueError('estimated cost exceeds reservation')
    if packet['slots'] not in (1, 2):
        raise ValueError('development starts with at most two slots')
    affinities = packet['cpu_sets']
    if len(affinities) != packet['slots'] or any(len(set(s)) != 4 for s in affinities):
        raise ValueError('each slot needs four distinct CPU cores')
    if len(set(sum(affinities, []))) != 4 * len(affinities):
        raise ValueError('CPU slots overlap')
    if type(packet.get('blas_threads', 4)) is not int or packet.get('blas_threads', 4) not in (1, 4):
        raise ValueError('registered BLAS thread count must be 1 or 4')
    if packet['stage'] in ('V3', 'DIRECTION'):
        remaining=packet['v3_remaining'] if packet['stage']=='V3' else packet['campaign_remaining']
        caps=dict(host_seconds=28800,gpu_seconds=28800,cpu_core_seconds=460800)
        if set(remaining)!=set(caps) or any(type(v) not in (int,float) or not math.isfinite(v)
                or not 0<=v<=caps[k] for k,v in remaining.items()):
            raise ValueError('invalid independent v3 resource ledger')
        if reserve>remaining['host_seconds'] or reserve*4*packet['slots']>remaining['cpu_core_seconds']:
            raise ValueError('v3 packet exceeds host or core-time reservation')
        if any(j['device']=='cuda' for j in packet['jobs']) and reserve>remaining['gpu_seconds']:
            raise ValueError('v3 packet exceeds GPU reservation')
    names = [job['name'] for job in packet['jobs']]
    if len(names) != len(set(names)) or any(not n or Path(n).name != n for n in names):
        raise ValueError('invalid or duplicate job identity')
    for job in packet['jobs']:
        if not job['argv'] or any(not isinstance(x, str) for x in job['argv']):
            raise ValueError('command must be an argument list')
        if job['device'] not in ('cpu', 'cuda'):
            raise ValueError('invalid device')
        if job['device'] == 'cuda' and not 0 < job['reserved_gpu_mib'] <= 22 * 1024:
            raise ValueError('invalid GPU memory reservation')


def process_identity(pid):
    try:
        stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return dict(pid=pid, start_ticks=stat[19], boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    except FileNotFoundError:
        return None


def memory_mib():
    result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                            check=True, capture_output=True, text=True)
    return sum(int(x) for x in result.stdout.split())


def run_packet(manifest):
    packet = json.loads(manifest.read_text())
    validate_packet(packet, time.time())
    root = manifest.parent
    with (root/'queue.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status_path = root/'queue-status.json'
        digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
        old = json.loads(status_path.read_text()) if status_path.exists() else None
        if old:
            if old['manifest_sha256'] != digest:
                raise ValueError('immutable packet changed')
            for row in old['runs']:
                if row['exit_code'] is None and process_identity(row['identity']['pid']) == row['identity']:
                    raise RuntimeError('previous worker still alive; observe it before recovery')
            # No implicit retry: caller must reconcile artifacts and register the
            # same missing identities in an explicit recovery packet.
            raise FileExistsError('packet already attempted; reconcile outputs before recovery')
        for name, expected in packet['source_hashes'].items():
            if hashlib.sha256((Path(packet['cwd'])/name).read_bytes()).hexdigest() != expected:
                raise ValueError('source snapshot changed')
        allowed = os.sched_getaffinity(0)
        if not set(sum(packet['cpu_sets'], [])).issubset(allowed):
            raise ValueError('requested CPU cores unavailable')
        status = dict(manifest_sha256=digest, identity=process_identity(os.getpid()),
                      started_at=time.time(), complete=False, runs=[], peak_gpu_mib=0)
        write_status(status_path, status)
        pending = list(packet['jobs'])
        running = []
        try:
            while pending or running:
                # The reservation includes polling and the five-second TERM
                # grace period; do not spend cleanup time beyond its deadline.
                if time.time() >= packet['deadline_unix'] - 6:
                    raise TimeoutError('packet absolute deadline reached')
                if any(j['device'] == 'cuda' for j in packet['jobs']):
                    used = memory_mib()
                    status['peak_gpu_mib'] = max(status['peak_gpu_mib'], used)
                    if used > 22 * 1024:
                        raise RuntimeError('GPU memory budget exceeded')
                for slot in range(packet['slots']):
                    if not pending or any(x[3] == slot for x in running):
                        continue
                    job = pending.pop(0)
                    if job['device'] == 'cuda' and memory_mib() + job['reserved_gpu_mib'] > 22 * 1024:
                        raise RuntimeError('insufficient reserved GPU memory')
                    affinity = ','.join(map(str, packet['cpu_sets'][slot]))
                    threads = str(packet.get('blas_threads', 4))
                    env = dict(os.environ, OMP_NUM_THREADS=threads, OPENBLAS_NUM_THREADS=threads, MKL_NUM_THREADS=threads)
                    if job['device'] == 'cpu':
                        env['CUDA_VISIBLE_DEVICES'] = ''
                    log = (root/(job['name']+'.log')).open('x')
                    process = subprocess.Popen(['taskset', '-c', affinity, *job['argv']], cwd=packet['cwd'],
                                               env=env, stdin=subprocess.DEVNULL, stdout=log,
                                               stderr=subprocess.STDOUT, start_new_session=True)
                    row = dict(name=job['name'], identity=process_identity(process.pid), started_at=time.time(),
                               exit_code=None, affinity=affinity, device=job['device'])
                    status['runs'].append(row)
                    running.append((process, log, row, slot))
                    write_status(status_path, status)
                for process, log, row, slot in list(running):
                    code = process.poll()
                    if code is not None:
                        row.update(exit_code=code, ended_at=time.time())
                        log.close()
                        running.remove((process, log, row, slot))
                write_status(status_path, status)
                if running:
                    time.sleep(.5)
            status['complete'] = True
        except BaseException as error:
            status['failure'] = repr(error)
            raise
        finally:
            for process, log, row, slot in running:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                row.update(exit_code=process.returncode, ended_at=time.time())
                log.close()
            status['ended_at'] = time.time()
            write_status(status_path, status)
        return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    run_packet(parser.parse_args().manifest)
