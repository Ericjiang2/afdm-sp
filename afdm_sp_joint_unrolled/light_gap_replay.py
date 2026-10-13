"""Read-only pilot inputs, independently budgeted CPU decoder replays.

No receiver or GPU call is made here. Cached clipped LLRs are development
observations, not new independent samples. Original evidence remains immutable.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import torch

from .bottleneck_pilot import hashes, load_state, sha
from .e1_ldpc import build_code, decode_llr, extract_info
from .supplement_adjacent_run import save_state
from .supplement_timing import _bounded_json
from .supplement_timing_integrity import BoundFiles, OutputMeter

CODE_KEYS = ('G', 'H', 'free_cols', 'chk', 'var', 'row_ptr')
ARMS = ('I1', 'BP_EST_NOISE', 'BP_TRUE_BASE', 'BP_TRUE_NOISE',
        'EP_EST_NOISE', 'EP_TRUE_NOISE')
BETAS = (.5, .75, 1., 1.5, 2.)


def calibrated_llr(llr, beta, clip):
    value = np.asarray(llr)
    if (value.ndim != 1 or not value.size or np.iscomplexobj(value)
            or not np.isfinite(value).all() or not np.isfinite(beta) or beta <= 0
            or not np.isfinite(clip) or clip <= 0 or np.any(np.abs(value) > clip)):
        raise ValueError('finite real previously clipped LLR and positive beta/clip required')
    return np.clip(float(beta) * value, -clip, clip)


def check_decode_identity(actual, expected):
    for key in ('decoded', 'info_hat'):
        if not np.array_equal(actual[key], expected[key]):
            raise ValueError('beta=1 changed old decoder output: ' + key)
    if bool(actual['decode_ok']) != bool(expected['decode_ok']):
        raise ValueError('beta=1 changed old syndrome status')


def replay_decode(code, state, beta, clip, maxiter):
    llr = calibrated_llr(state['llr'], beta, clip)
    if llr.shape != (code['n'],):
        raise ValueError('cached LLR and code size differ')
    decoded, ok = decode_llr(code, llr, maxiter=maxiter)
    value = dict(llr=llr, decoded=decoded, info_hat=extract_info(code, decoded),
                 decode_ok=bool(ok))
    if beta == 1:
        check_decode_identity(value, state)
    return value


def decoder_scores(value, truth):
    llr, bits = np.asarray(value['llr']), np.asarray(truth['coded'])
    info, expected_info = np.asarray(value['info_hat']), np.asarray(truth['info'])
    if (llr.shape != bits.shape or info.shape != expected_info.shape
            or not np.isin(bits, (0, 1)).all() or not np.isin(expected_info, (0, 1)).all()):
        raise ValueError('invalid decoder scoring dimensions or truth bits')
    errors = int(np.count_nonzero(info != expected_info))
    margin = (1 - 2 * bits.astype(float)) * llr
    probability_one = .5 * (1 - np.tanh(llr / 2))
    return dict(FER=int(errors > 0), info_bit_errors=errors, info_bits=int(info.size),
                decoded_codeword_bit_errors=int(np.count_nonzero(value['decoded'] != bits)),
                raw_bit_errors=int(np.count_nonzero((llr < 0) != bits)),
                coded_bits=int(bits.size), decode_ok=bool(value['decode_ok']),
                bit_NLL=float(np.logaddexp(0, -margin).mean()),
                bit_Brier=float(np.square(probability_one - bits).mean()))


class LightRun:
    """New-run reservations with separate call kinds and no device substitution."""
    def __init__(self, root, stage, bounds, byte_limit, guard):
        self.root, self.stage, self.guard = Path(root), stage, guard
        self.out = self.root / stage
        self.out.mkdir(parents=True, exist_ok=False)
        self.meter = OutputMeter(self.root, byte_limit)
        self.meter.adopt_tree(self.root)
        self.bounds = dict(bounds)
        self.counts = {kind: 0 for kind in bounds if kind != 'seconds'}
        self.started = time.time()
        self.deadline = time.monotonic() + bounds['seconds']
        self.records, self.active = [], None

    def check(self):
        if time.monotonic() >= self.deadline:
            raise TimeoutError('light stage deadline reached')
        self.guard.check()

    def write(self, name, value):
        path = self.out / name
        _bounded_json(path, value, self.root, self.meter.limit, meter=self.meter)
        return path

    def reserve(self, kind, identity):
        self.check()
        if self.active is not None:
            raise RuntimeError('previous reserved call is not closed')
        if kind not in self.counts or self.counts[kind] >= self.bounds[kind]:
            raise RuntimeError('light call budget exhausted: ' + kind)
        self.counts[kind] += 1
        token = f'{kind}-{self.counts[kind]:05d}'
        self.active = dict(identity, token=token, kind=kind)
        self.write(token + '-reserve.json', dict(self.active, reserved_at=time.time()))
        return token

    def call(self, kind, identity, fn, score, provenance, *, device='cpu'):
        token = self.reserve(kind, identity)
        if device != 'cpu':
            raise ValueError('this light driver measures CPU calls only')
        started, cpu = time.perf_counter(), time.process_time()
        value = fn()
        seconds, cpu_seconds = time.perf_counter() - started, time.process_time() - cpu
        self.check()
        artifact = save_state(self.out / (token + '.npz'), value, self.meter, readback=True)
        record = dict(self.active, seconds=seconds, CPU_seconds=cpu_seconds,
                      state=artifact, scores=score(value), **provenance)
        path = self.write(token + '-result.json', record)
        self.records.append(dict(identity, kind=kind, record=str(path), sha256=sha(path),
                                 seconds=seconds, CPU_seconds=cpu_seconds, scores=record['scores']))
        self.active = None
        return value, record

    def fail(self, exc):
        self.write('failure.json', dict(status='FAILED', stage=self.stage, calls=self.counts,
                   active=self.active, error=repr(exc), traceback=traceback.format_exc(),
                   started_at=self.started, finished_at=time.time()))


def verified_record(entry, old_root):
    path = Path(entry['record'])
    if not path.resolve().is_relative_to(Path(old_root).resolve()) or sha(path) != entry['sha256']:
        raise ValueError('old record location or content changed')
    record = json.loads(path.read_text())
    for key in ('block', 'snr', 'split', 'arm'):
        if record[key] != entry[key]:
            raise ValueError('old record identity differs: ' + key)
    raw_path = Path(record['state']['file']['path'])
    if not raw_path.resolve().is_relative_to(Path(old_root).resolve()):
        raise ValueError('old state outside bound pilot root')
    return record, load_state(record['state'])


def setup_guard(args, contract):
    package = Path(__file__).resolve().parent
    manifest = json.loads(args.source_manifest.read_text())
    if set(manifest) != {str(p.relative_to(package)) for p in package.rglob('*.py')}:
        raise ValueError('isolated package source inventory differs')
    files = {package / name: digest for name, digest in manifest.items()}
    files.update({args.contract: args.contract_sha256,
                  args.source_manifest: args.source_sha256})
    old_root = Path(contract['old_root'])
    files.update({old_root / name: digest for name, digest in contract['old_inputs'].items()})
    return BoundFiles(files)


def validate_contract(contract):
    if (contract.get('schema') != 'i1-light-llr-replay-v1'
            or contract.get('device') != 'cpu' or contract.get('threads') != 1
            or tuple(contract['arms']) != ARMS or tuple(contract['betas']) != BETAS
            or contract['snrs'] != [7, 8] or contract['clip'] != 20.
            or contract['ldpc_maxiter'] != 50 or contract['engineering_blocks'] != 2
            or contract['development_blocks'] != 64
            or contract['bounds'] != {'engineering': {'D': 120, 'seconds': 300},
                                      'development': {'D': 3840, 'seconds': 1800}}
            or contract['output_bytes'] != 1024**3):
        raise ValueError('replay differs from frozen development contract')


def execute(args):
    if sha(args.contract) != args.contract_sha256 or sha(args.source_manifest) != args.source_sha256:
        raise ValueError('contract or source manifest hash changed')
    contract = json.loads(args.contract.read_text())
    validate_contract(contract)
    root = args.root.resolve()
    if not root.is_relative_to(Path('/data/guoyikun/')):
        raise ValueError('real replay outputs must be under /data/guoyikun/')
    guard = setup_guard(args, contract)
    if args.stage == 'development':
        if args.admission is None or sha(args.admission) != args.admission_sha256:
            raise ValueError('development needs a hashed engineering admission')
        admission = json.loads(args.admission.read_text())
        if (admission['status'] != 'PASS' or admission['contract_sha256'] != args.contract_sha256
                or admission['source_sha256'] != args.source_sha256
                or admission['engineering_summary_sha256'] != sha(root / 'engineering/summary.json')):
            raise ValueError('engineering admission does not bind this replay')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run = LightRun(root, args.stage, contract['bounds'][args.stage], contract['output_bytes'], guard)
    try:
        cache = run.out / 'code-cache'
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        code_identity = hashes({key: code[key] for key in CODE_KEYS})
        old_root = Path(contract['old_root'])
        old_stage = old_root / 'runs' / args.stage
        environment = json.loads((old_stage / 'environment.json').read_text())
        if code_identity != environment['code_identity']:
            raise ValueError('new cache changed old LDPC code')
        run.write('environment.json', dict(pid=os.getpid(), hostname=os.uname().nodename,
            started_at=run.started, device='cpu', numpy=np.__version__, torch=torch.__version__,
            threads=torch.get_num_threads(), code_identity=code_identity,
            contract_sha256=args.contract_sha256, source_manifest_sha256=args.source_sha256))
        summary = json.loads((old_stage / 'summary.json').read_text())
        if summary['status'] != 'COMPLETE':
            raise ValueError('old pilot is incomplete')
        index = {}
        for item in summary['records']:
            key = item['block'], item['snr'], item['arm']
            if key in index:
                raise ValueError('duplicate old observation')
            index[key] = item
        blocks = contract[args.stage + '_blocks']
        exogenous = {item['block']: item for item in summary['exogenous']}
        if set(exogenous) != set(range(blocks)) or len(summary['exogenous']) != blocks:
            raise ValueError('old independent block inventory differs')
        beta_one = 0
        input_inventory = []
        for block in range(blocks):
            run.check()
            exo = exogenous[block]
            truth = load_state(exo['state'])
            if hashes({key: truth[key] for key in exo['hashes']}) != exo['hashes']:
                raise ValueError('old exogenous arrays changed')
            for snr in contract['snrs']:
                for arm in contract['arms']:
                    item = index[block, snr, arm]
                    record, state = verified_record(item, old_root)
                    if item['split'] != exo['split']:
                        raise ValueError('record and exogenous split differ')
                    input_hash = hashes({'llr': state['llr']})
                    input_inventory.append(dict(record=item['record'], sha256=item['sha256'],
                                                state=record['state']['file']))
                    for beta in contract['betas']:
                        identity = dict(block=block, snr=snr, arm=arm, split=item['split'], beta=beta)
                        run.call('D', identity,
                            lambda: replay_decode(code, state, beta, contract['clip'], contract['ldpc_maxiter']),
                            lambda value: decoder_scores(value, truth),
                            dict(source_record=item['record'], source_record_sha256=item['sha256'],
                                 source_llr_hash=input_hash['llr'], exogenous_hashes=exo['hashes'],
                                 input_llr_was_clipped=True, beta_one_identity=(beta == 1),
                                 truth_access='offline scoring only'))
                        if hashes({'llr': state['llr']}) != input_hash:
                            raise ValueError('replay mutated original LLR')
                        beta_one += int(beta == 1)
            print(json.dumps(dict(stage=args.stage, block=block, calls=run.counts)), flush=True)
        if run.counts != {'D': blocks * len(ARMS) * len(BETAS) * 2}:
            raise ValueError('missing scheduled decoder calls')
        if hashes({key: code[key] for key in CODE_KEYS}) != code_identity:
            raise ValueError('decoder mutated code arrays')
        for item in input_inventory:
            if sha(item['record']) != item['sha256'] or sha(item['state']['path']) != item['state']['sha256']:
                raise ValueError('old terminal evidence changed during replay')
        for exo in exogenous.values():
            if sha(exo['state']['file']['path']) != exo['state']['file']['sha256']:
                raise ValueError('old exogenous evidence changed during replay')
        guard.verify()
        run.meter.verify()
        report = dict(schema='i1-light-replay-stage-v1', status='COMPLETE', stage=args.stage,
            calls=dict(run.counts, F=0, T=0), bounds=run.bounds, records=run.records,
            independent_blocks=blocks, snrs=contract['snrs'], beta_one_exact_replays=beta_one,
            input_inventory=input_inventory, exogenous=list(exogenous.values()), code_identity=code_identity,
            started_at=run.started, finished_at=time.time(), wall_seconds=time.time() - run.started,
            contract_sha256=args.contract_sha256, source_manifest_sha256=args.source_sha256,
            truth_scope='offline scoring only; cached development blocks, not independent confirmation',
            raw_readback='all saved array dtype/shape/content hashes verified')
        run.write('summary.json', report)
        run.meter.verify()
        print(json.dumps({key: report[key] for key in ('status', 'calls', 'wall_seconds')}), flush=True)
    except BaseException as exc:
        run.fail(exc)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('engineering', 'development'), required=True)
    for name in ('root', 'contract', 'source-manifest'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('contract-sha256', 'source-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--admission', type=Path)
    parser.add_argument('--admission-sha256')
    execute(parser.parse_args())


if __name__ == '__main__':
    main()
