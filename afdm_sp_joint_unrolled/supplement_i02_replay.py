"""Finite I-02 evidence recovery from audited caches; no independent samples."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import traceback

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import numpy as np
import torch

from .direction_cancel_receiver import CancellationTransform
from .direction_receiver import terminal_decode
from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_a01_diagnostics import terminal_diagnostics
from .supplement_i02_cache import (SCHEMA, RECIPE, checked_path, file_binding,
    load_inputs, validate_identities, validate_lineage)
from .supplement_i02_diagnostics import cancellation_diagnostics
from .supplement_data import CAMPAIGN_ID, SupplementData
from .supplement_profile import score_errors
from .supplement_run import sha

TERMINAL_FIELDS = ('mu', 'var', 'llr', 'decoded', 'info_hat', 'x_hard')


def replay_state(snapshot, system, code, *, device, before_call, after_call=None):
    """Three E/T pairs. Baseline uses the actual saved I0 terminal unchanged."""
    if not callable(before_call):
        raise ValueError('explicit call accounting callback required')
    dev = torch.device(device)
    if dev.type == 'cuda' and not torch.cuda.is_available():
        raise ValueError('requested CUDA unavailable')
    s = snapshot
    for mode in (None, 'scalar', 'diagonal', 'lowrank'):
        arm = 'I02-' + (mode or 'baseline')
        transformed, timings = None, {}
        if mode is None:
            result = {k: s[k].copy() for k in TERMINAL_FIELDS}
        else:
            callback = CancellationTransform(system, mode)
            before_call('E', arm)
            wall, cpu = time.perf_counter(), time.process_time()
            transformed = callback(**{k: s[k].copy() for k in
                ('y', 'pilot', 'H', 'x_soft', 'support')},
                sigma_base=float(s['sigma2_terminal']))
            timings['E'] = dict(wall_seconds=time.perf_counter() - wall,
                                cpu_seconds=time.process_time() - cpu)
            if after_call is not None:
                after_call('E', arm)
            before_call('T', arm)
            if dev.type == 'cuda':
                torch.cuda.synchronize(dev)
                torch.cuda.reset_peak_memory_stats(dev)
            wall, cpu = time.perf_counter(), time.process_time()
            result = terminal_decode(transformed['z'], transformed['H'],
                transformed['sigma_out'], s['constellation'].copy(), code, device=dev, audit=True)
            if dev.type == 'cuda':
                torch.cuda.synchronize(dev)
            timings['T'] = dict(wall_seconds=time.perf_counter() - wall,
                cpu_seconds=time.process_time() - cpu,
                peak_gpu_bytes=torch.cuda.max_memory_allocated(dev) if dev.type == 'cuda' else 0)
            if after_call is not None:
                after_call('T', arm)
        wall, cpu = time.perf_counter(), time.process_time()
        diagnostics, arrays = cancellation_diagnostics(s, transformed, mode)
        diagnostics['terminal_calibration'] = terminal_diagnostics(result, s)
        timings['offline_diagnostics'] = dict(wall_seconds=time.perf_counter() - wall,
                                              cpu_seconds=time.process_time() - cpu)
        yield dict(arm=arm, mode=mode, terminal=result, diagnostics=diagnostics,
                   arrays=arrays, cancellation=None if mode is None else transformed['diagnostics'],
                   timings=timings, reused_terminal=mode is None)


def output_bytes(root):
    return sum(path.stat().st_size for path in Path(root).rglob('*') if path.is_file())


def save_arrays(path, arrays, budget_root, limit):
    if any(np.asarray(v).dtype.hasobject or not np.isfinite(v).all() for v in arrays.values()):
        raise ValueError('nonfinite/object recovery arrays')
    if output_bytes(budget_root) + sum(np.asarray(v).nbytes for v in arrays.values()) + 262144 > limit:
        raise OSError('recovery output budget exhausted')
    fd, temporary = tempfile.mkstemp(prefix='.arrays-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)
    return dict(file_binding(path), md5=hashlib.md5(path.read_bytes()).hexdigest(),
                array_hashes={k: array_hash(v) for k, v in arrays.items()})


def verify_source(args):
    manifest = json.loads(args.source_manifest.read_text())
    if any(sha(args.source_root / name) != digest for name, digest in manifest.items()):
        raise ValueError('frozen I-02 recovery source changed')


def build_recovery_code(output, code_hashes):
    if set(code_hashes) != {'G', 'H'}:
        raise ValueError('both original LDPC array hashes are required')
    cache_dir = Path(output) / 'code-cache'
    cache_dir.mkdir()
    code = build_code(cache_dir=cache_dir)
    if any(array_hash(code[k]) != digest
           for k, digest in code_hashes.items()):
        raise ValueError('frozen LDPC code hash mismatch')
    return code


def read_manifest(args):
    if sha(args.manifest) != args.manifest_sha256:
        raise ValueError('I-02 recovery manifest hash mismatch')
    manifest = json.loads(args.manifest.read_text())
    if (manifest.get('schema') != SCHEMA or manifest.get('campaign_id') != CAMPAIGN_ID
            or manifest.get('recipe_id') != RECIPE
            or manifest.get('protocol_sha256') != sha(args.protocol)
            or manifest.get('checkpoint_sha256') != sha(args.checkpoint)):
        raise ValueError('I-02 recovery manifest input binding mismatch')
    validate_identities(manifest['frames'])
    for binding in manifest['source_batches'] + [manifest['original_audit']]:
        checked_path(binding)
    return manifest


def preflight(args, manifest, code, system, progress):
    data = SupplementData(args.protocol, code)
    proofs = []
    for row in manifest['frames']:
        progress['active'] = [row['block'], row['snr']]
        snapshot, record, old = load_inputs(row)
        progress['generator_reconstructions'] += 1
        frame = data.make_frame(system, 'design', row['block'], row['snr'])
        proof = validate_lineage(snapshot, record, old, frame, system, code)
        stem = f"{row['block']:03d}-{row['snr']}"
        proof['truth'] = save_arrays(args.out / f'truth-{stem}.npz',
            {k: frame._truth[k] for k in ('H', 'data', 'noise')}, args.out, args.max_output_bytes)
        proof.update(block=row['block'], snr=row['snr'])
        path = args.out / f'proof-{stem}.json'
        publish_json(path, proof)
        proofs.append(file_binding(path))
        progress['states_completed'] += 1
        print(json.dumps(dict(event='lineage-complete', block=row['block'], snr=row['snr'])), flush=True)
    return dict(proofs=proofs, scope='zero F/E/T; regenerated omitted truth exactly matches producer hashes')


def reserve_replay(args, manifest):
    if not 0 <= args.start_index < args.stop_index <= 576:
        raise ValueError('invalid I-02 replay index range')
    ledger = args.out.parent / 'i02-recovery-ledger-v1'
    ledger.mkdir(exist_ok=True)
    identities = [[r['block'], r['snr']] for r in manifest['frames'][args.start_index:args.stop_index]]
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        occupied = set()
        for path in ledger.glob('reservation-*.json'):
            prior = json.loads(path.read_text())
            if (prior['manifest_sha256'] != args.manifest_sha256 or
                    prior['source_manifest_sha256'] != sha(args.source_manifest)):
                raise ValueError('incompatible I-02 recovery reservation')
            occupied.update(tuple(v) for v in prior['identities'])
        if occupied & {tuple(v) for v in identities}:
            raise ValueError('I-02 recovery identities already reserved; no retry')
        digest = hashlib.sha256(str(args.out.resolve()).encode()).hexdigest()
        publish_json(ledger / f'reservation-{digest}.json', dict(identities=identities,
            manifest_sha256=args.manifest_sha256, source_manifest_sha256=sha(args.source_manifest),
            calls_reserved=dict(F=0, E=len(identities)*3, T=len(identities)*3),
            policy='no retry/reclaim; original blocks are not new independent samples'))


def run_replay(args, manifest, code, system, progress):
    if (sha(args.preflight / 'summary.json') != args.preflight_sha256):
        raise ValueError('I-02 preflight summary changed')
    lineage = json.loads((args.preflight / 'summary.json').read_text())
    if (lineage['status'] != 'complete' or lineage['states_completed'] != 576
            or lineage['manifest_sha256'] != args.manifest_sha256
            or lineage['calls_attempted'] != dict(F=0, E=0, T=0)):
        raise ValueError('all original I-02 states must pass lineage before E/T')
    proof_map = {}
    for binding in lineage['proofs']:
        proof = json.loads(checked_path(binding).read_text())
        proof_map[(proof['block'], proof['snr'])] = proof
    if len(proof_map) != 576:
        raise ValueError('incomplete lineage proof grid')
    reserve_replay(args, manifest)
    rows, mismatch = [], []
    for original in manifest['frames'][args.start_index:args.stop_index]:
        snapshot, _, old = load_inputs(original)
        proof = proof_map[(original['block'], original['snr'])]
        with np.load(checked_path(proof['truth']), allow_pickle=False) as archive:
            snapshot.update(Htrue=archive['H'], data=archive['data'], noise=archive['noise'])
        def before_call(kind, arm):
            if time.time() >= args.deadline_unix:
                raise TimeoutError('I-02 recovery deadline')
            progress['calls_attempted'][kind] += 1
            progress['active'] = [original['block'], original['snr'], arm, kind]
            publish_json(args.out / f"call-{kind}-{progress['calls_attempted'][kind]:05d}.json",
                         dict(identity=progress['active'], started_unix=time.time()))
        def after_call(kind, arm):
            progress['calls_completed'][kind] += 1
        for cell in replay_state(snapshot, system, code, device=args.device,
                                 before_call=before_call, after_call=after_call):
            score = score_errors(cell['terminal'], snapshot)
            differences = {key: dict(old=old[cell['arm']][key], replay=value)
                           for key, value in score.items() if old[cell['arm']][key] != value}
            stem = f"{original['block']:03d}-{original['snr']}-{cell['arm']}"
            arrays = {k: cell['terminal'][k] for k in TERMINAL_FIELDS}
            arrays.update(cell['arrays'])
            raw = save_arrays(args.out / f'terminal-{stem}.npz', arrays, args.out.parent,
                               args.max_output_bytes)
            row = dict(schema='supplement-i02-recovery-frame-v1', block=original['block'],
                snr=original['snr'], arm=cell['arm'], scores=score,
                original_error_differences=differences, reused_terminal=cell['reused_terminal'],
                original_record=original['record'], original_terminal=original['terminal'],
                terminal=raw, diagnostics=cell['diagnostics'], cancellation=cell['cancellation'],
                timings=cell['timings'], graphs=cell['terminal'].get('graphs', []),
                scope='development cache replay; old missing timings not recovered')
            path = args.out / f'frame-{stem}.json'
            publish_json(path, row)
            rows.append(file_binding(path))
            if differences:
                mismatch.append(dict(block=original['block'], snr=original['snr'],
                                     arm=cell['arm'], differences=differences))
        progress['states_completed'] += 1
        print(json.dumps(dict(event='replay-complete', block=original['block'], snr=original['snr'],
                              mismatches=len(mismatch))), flush=True)
        if mismatch:
            raise ValueError('I-02 replay error differences retained; inspect before expanding')
    return dict(records=rows, error_differences=mismatch,
                reused_terminals=progress['states_completed'], scope='development replay; not confirmation')


def execute(args):
    if not time.time() < args.deadline_unix <= time.time() + (1200 if args.phase == 'preflight' else 2700):
        raise ValueError('I-02 finite phase deadline required')
    if not 0 < args.max_output_bytes <= 8 * 1024**3:
        raise ValueError('I-02 output cap must not exceed eight GiB')
    args.out.mkdir(parents=True, exist_ok=False)
    progress = dict(calls_attempted=dict(F=0, E=0, T=0), calls_completed=dict(F=0, E=0, T=0),
                    generator_reconstructions=0, states_completed=0, active=None)
    previous = signal.getsignal(signal.SIGALRM)
    wall, cpu = time.perf_counter(), time.process_time()
    try:
        def timeout(_signal, _frame):
            raise TimeoutError('I-02 recovery finite deadline exhausted')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix - time.time())
        verify_source(args)
        manifest = read_manifest(args)
        torch.set_num_threads(1)
        dev = torch.device(args.device)
        if args.phase == 'preflight' and dev.type != 'cpu':
            raise ValueError('lineage preflight is CPU-only')
        if dev.type == 'cuda':
            if not torch.cuda.is_available():
                raise ValueError('requested CUDA unavailable')
            torch.cuda.set_per_process_memory_fraction(.30, dev)
        code = build_recovery_code(args.out, manifest['code_sha256'])
        system = _make_config_a(1024, 2., 8, 10., 4.)
        publish_json(args.out / 'contract.json', dict(phase=args.phase, command=sys.argv,
            manifest_sha256=args.manifest_sha256, source_manifest_sha256=sha(args.source_manifest),
            deadline_unix=args.deadline_unix, max_output_bytes=args.max_output_bytes,
            device=str(dev), threads=1, gpu_fraction=.30,
            start_index=args.start_index, stop_index=args.stop_index))
        result = (preflight(args, manifest, code, system, progress) if args.phase == 'preflight' else
                  run_replay(args, manifest, code, system, progress))
        verify_source(args)
        for binding in manifest['source_batches']:
            checked_path(binding)
        progress['active'] = None
        summary = dict(status='complete', exitcode=0, **progress, **result,
            manifest_sha256=args.manifest_sha256, elapsed_seconds=time.perf_counter()-wall,
            process_cpu_seconds=time.process_time()-cpu, output_bytes=output_bytes(args.out),
            not_claims=['independent confirmation', 'historical missing timing recovery', 'formal COST-02'])
        publish_json(args.out / 'summary.json', summary)
        print(json.dumps({k: v for k, v in summary.items() if k not in ('proofs', 'records')}), flush=True)
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish_json(args.out / 'failure.json', dict(status='failed', exception=type(exc).__name__,
            message=str(exc), traceback=traceback.format_exc(), **progress,
            elapsed_seconds=time.perf_counter()-wall))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('preflight', 'replay'), required=True)
    for name in ('out', 'manifest', 'source-root', 'source-manifest', 'protocol', 'checkpoint'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('manifest-sha256', 'device'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--deadline-unix', type=int, required=True)
    parser.add_argument('--max-output-bytes', type=int, required=True)
    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument('--stop-index', type=int, default=576)
    parser.add_argument('--preflight', type=Path)
    parser.add_argument('--preflight-sha256')
    return execute(parser.parse_args())


if __name__ == '__main__':
    sys.exit(main())
