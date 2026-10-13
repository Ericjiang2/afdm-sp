"""Bounded I1 pilot, with observed-only full arms and explicit terminal oracles.

The CLI runs from an immutable source snapshot. Old campaign budgets and data
loaders are never reused. Numerical primitives and evidence writers are shared.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
from types import MappingProxyType

import numpy as np
import torch

from .budgeted_support_diagnostics import array_hash
from .budgeted_support_eval import build_receiver, make_frame
from .direction_data import validate_observed
from .direction_receiver import terminal_decode
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_adjacent_run import rng_state, save_state
from .supplement_baselines import BaselineReceiver
from .supplement_detectors import qualification_pair, terminal as ep_terminal
from .supplement_feedback import CodeFeedback
from .supplement_feedback_schedule import UniformBPSchedule
from .supplement_profile import score_errors
from .supplement_timing import _bounded_json
from .supplement_timing_integrity import BoundFiles, OutputMeter

NAMESPACE = (20260912, 112500, 731921)
FULL_ARMS = ('I1', 'I1_DET_ONLY', 'I1_CE_ONLY', 'I1_ZERO')
TERMINAL_ARMS = ('BP_EST_NOISE', 'BP_TRUE_BASE', 'BP_TRUE_NOISE',
                 'EP_EST_NOISE', 'EP_TRUE_NOISE')
EP_RECIPE = 'stable-EP-40-d0.5'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_pilot_namespace(namespace):
    if (not isinstance(namespace, (tuple, list)) or len(namespace) != 3
            or any(type(word) is not int or not 0 <= word < 2**32 for word in namespace)):
        raise ValueError('pilot namespace requires three uint32 seed words')
    return tuple(namespace)


def pilot_rng(block, component, *, split, namespace=NAMESPACE):
    if (type(block) is not int or block < 0 or type(component) is not int
            or component not in (1, 2, 3) or type(split) is not int or split not in (1, 2)):
        raise ValueError('explicit pilot block, component 1..3, and engineering/development split required')
    namespace = validate_pilot_namespace(namespace)
    return np.random.default_rng(np.random.SeedSequence([*namespace, split, block, component]))


def generate_exogenous(system, code, block, *, split, namespace=NAMESPACE):
    """Use the same physical generator; namespace changes only the random inputs."""
    def factory(replicate, index, component, *, split):
        if replicate != 0 or index != block:
            raise ValueError('legacy generator changed the requested identity')
        return pilot_rng(index, component, split=split, namespace=namespace)
    before = np.random.get_state()
    try:
        raw = make_frame(system, code, 0, block, 7, split=split, rng_factory=factory)
    finally:
        np.random.set_state(before)
    for value in raw.values():
        if isinstance(value, np.ndarray):
            value.flags.writeable = False
    return raw


def observed_at_snr(raw, snr):
    if type(snr) is not int or snr not in (7, 8):
        raise ValueError('this pilot has exactly SNR 7 and 8')
    variance = 10.**(-snr/10)
    # The same H, codeword and standard complex noise are used at both SNRs.
    observed = dict(y=raw['H']@(raw['pilot']+raw['data'])+np.sqrt(variance)*raw['noise'],
                    pilot=raw['pilot'].copy(), sigma2=np.asarray(variance),
                    constellation=np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j]))
    for value in observed.values():
        value.flags.writeable = False
    validate_observed(observed, len(raw['pilot']))
    return MappingProxyType(observed)


def hashes(values):
    return {key: array_hash(value) for key, value in values.items()}


def run_full(receiver, code, observed, arm):
    """No truth-bearing argument is accepted by a full receiver arm."""
    if arm not in FULL_ARMS:
        raise ValueError('unknown full receiver arm')
    kwargs = dict(checkpoint=1, control='zero' if arm=='I1_ZERO' else 'legal')
    # Leave the original/default I1 constructor literally unchanged for golden replay.
    if arm in ('I1_DET_ONLY', 'I1_CE_ONLY'):
        kwargs['consumer'] = 'detector' if arm=='I1_DET_ONLY' else 'ce'
    feedback = CodeFeedback(code, **kwargs)
    result = receiver.run(observed, audit=False, code_feedback=feedback,
                          bp_schedule=UniformBPSchedule(outer_bp_iterations=12))
    if not result['baseline_eligible']:
        raise ValueError('I1 initializer did not complete its fixed algorithm')
    decoder = [r for r in result['code_feedback_records'] if r['stage']=='decoder']
    if len(decoder)!=1 or decoder[0]['iteration']!=1:
        raise ValueError('checkpoint decoder count or position changed')
    if len([r for r in result['code_feedback_records'] if r['stage']=='CE_consume'])!=9:
        raise ValueError('CE consumer count changed')
    return result


def terminal_inputs(observed, estimated_H, true_H, sigma_base, arm):
    """The only true-channel injection boundary; cancellation uses that same H."""
    if arm not in TERMINAL_ARMS:
        raise ValueError('unknown terminal intervention')
    H = true_H if '_TRUE_' in arm else estimated_H
    variance = sigma_base if arm.endswith('_BASE') else float(observed['sigma2'])
    z = observed['y']-H@observed['pilot']
    return z, H, variance


def offline_scores(result, truth, H):
    scores = score_errors(result, truth)
    llr = np.asarray(result['llr'])
    bits = np.asarray(truth['coded'])
    if llr.shape!=bits.shape or not np.isfinite(llr).all():
        raise ValueError('terminal LLR and codeword dimensions differ')
    margin = (1-2*bits.astype(float))*llr
    p1 = .5*(1-np.tanh(llr/2))
    high = np.abs(llr)>=5
    scores.update(bit_NLL=float(np.logaddexp(0, -margin).mean()),
                  bit_Brier=float(np.square(p1-bits).mean()),
                  high_confidence_bits=int(high.sum()),
                  high_confidence_wrong=int(np.count_nonzero(high & (margin<0))),
                  channel_NMSE=float(np.linalg.norm(H-truth['H'])**2 /
                                     np.linalg.norm(truth['H'])**2),
                  decode_ok=bool(result['decode_ok']))
    return scores


def restore(metadata, arrays):
    if isinstance(metadata, dict):
        if set(metadata)=={'array', 'shape', 'dtype', 'sha256'}:
            value = arrays[metadata['array']]
            if (list(value.shape)!=metadata['shape'] or str(value.dtype)!=metadata['dtype']
                    or array_hash(value)!=metadata['sha256']):
                raise ValueError('raw array shape, dtype or content changed')
            return value.copy()
        if set(metadata)=={'complex_real', 'complex_imag'}:
            return complex(metadata['complex_real'], metadata['complex_imag'])
        return {key: restore(value, arrays) for key, value in metadata.items()}
    if isinstance(metadata, list):
        return [restore(value, arrays) for value in metadata]
    return metadata


def load_state(artifact):
    path = Path(artifact['file']['path'])
    if sha(path)!=artifact['file']['sha256']:
        raise ValueError('raw file checksum changed: '+str(path))
    with np.load(path, allow_pickle=False) as arrays:
        if set(arrays.files)!=set(artifact['file']['fields']):
            raise ValueError('raw array inventory changed')
        return restore(artifact['metadata'], arrays)


def compare_full(left, right):
    """Inherited 1e-6 engineering tolerance, with exact decisions/support."""
    result = {}
    for key in ('H', 'sigma2', 'sigma2_terminal', 'x_soft', 'gains', 'mu', 'var', 'llr'):
        a, b = np.asarray(left[key]), np.asarray(right[key])
        if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('full replay shape/finite mismatch: '+key)
        norm = float(np.linalg.norm(b))
        difference = float(np.linalg.norm(a-b))
        relative = difference/norm if norm else (0. if not difference else float('inf'))
        if relative>1e-6:
            raise ValueError('full replay exceeds 1e-6: '+key)
        result[key] = dict(relative_l2=relative, exact_hash=array_hash(a)==array_hash(b))
    for key in ('x_hard', 'decoded', 'info_hat', 'support'):
        if not np.array_equal(left[key], right[key]):
            raise ValueError('full replay decision/support mismatch: '+key)
        result[key] = dict(elementwise_exact=True)
    return result


def validate_contract(contract):
    if (contract.get('schema')!='i1-bottleneck-pilot-v1'
            or tuple(contract['namespace'])!=NAMESPACE or contract['snrs']!=[7, 8]
            or contract['engineering_blocks']!=2 or contract['development_blocks']!=64
            or tuple(contract['full_arms'])!=FULL_ARMS
            or tuple(contract['terminal_arms'])!=TERMINAL_ARMS
            or contract['ep_recipe']!=EP_RECIPE or contract['device']!='cuda:0'):
        raise ValueError('request differs from the fixed pilot design')
    expected = {'golden': {'F':4, 'T':0, 'seconds':600},
                'engineering': {'F':20, 'T':28, 'seconds':1200},
                'development': {'F':512, 'T':640, 'seconds':5400}}
    if contract['bounds']!=expected or contract['total_bounds']!={
            'F':536, 'T':668, 'seconds':7200, 'output_bytes':8*1024**3,
            'threads':1, 'gpu_memory_fraction':.25}:
        raise ValueError('pilot call, storage, compute or wall-time budget changed')


class Run:
    """Immutable reservations before calls; every exception remains charged."""
    def __init__(self, root, stage, contract, guard):
        self.root, self.stage, self.contract, self.guard = Path(root), stage, contract, guard
        self.out = self.root/stage
        self.out.mkdir(exist_ok=False)
        self.meter = OutputMeter(self.root, contract['total_bounds']['output_bytes'])
        self.meter.adopt_tree(self.root)
        self.bounds = contract['bounds'][stage]
        self.started = time.time()
        self.deadline = time.monotonic()+self.bounds['seconds']
        self.counts = dict(F=0, T=0)
        self.records = []
        self.active = None

    def check(self):
        if time.monotonic()>=self.deadline:
            raise TimeoutError('stage deadline reached; no further calls admitted')
        self.guard.check()

    def write(self, name, value):
        path = self.out/name
        _bounded_json(path, value, self.meter.root, self.meter.limit, meter=self.meter)
        return path

    def reserve(self, kind, identity):
        self.check()
        if kind not in self.counts or self.counts[kind]>=self.bounds[kind]:
            raise RuntimeError('stage call budget exhausted: '+kind)
        self.counts[kind] += 1
        token = f'{kind}-{self.counts[kind]:04d}'
        self.active = dict(token=token, kind=kind, **identity)
        self.write(token+'-reserve.json', dict(self.active, reserved_at=time.time()))
        return token

    def call(self, kind, identity, fn, observed, truth, score_H, extra=None):
        token = self.reserve(kind, identity)
        before_inputs = hashes(observed)
        before_rng = rng_state('cuda:0')
        torch.cuda.synchronize()
        started, cpu = time.perf_counter(), time.process_time()
        value = fn()
        torch.cuda.synchronize()
        seconds, cpu_seconds = time.perf_counter()-started, time.process_time()-cpu
        if hashes(observed)!=before_inputs or rng_state('cuda:0')!=before_rng:
            raise ValueError('receiver changed shared observed input or RNG state')
        self.check()
        H = value['H'] if kind=='F' else score_H
        scores = offline_scores(value, truth, H)
        artifact = save_state(self.out/(token+'.npz'), value, self.meter, readback=True)
        record = dict(self.active, observed_hashes=before_inputs, scores=scores,
                      seconds=seconds, CPU_seconds=cpu_seconds, state=artifact,
                      rng_unchanged=True, input_unchanged=True, truth_access='offline scoring only')
        if extra:
            record.update(extra)
        path = self.write(token+'-result.json', record)
        self.records.append(dict(identity, kind=kind, record=str(path), sha256=sha(path),
                                 scores=scores, seconds=seconds, CPU_seconds=cpu_seconds))
        self.active = None
        return value, record


def source_guard(args, contract):
    package = Path(__file__).resolve().parent
    manifest = json.loads(args.source_manifest.read_text())
    files = {package/name: digest for name, digest in manifest.items()}
    if set(manifest)!={str(p.relative_to(package)) for p in package.rglob('*.py')}:
        raise ValueError('snapshot source inventory differs')
    files.update({args.contract: args.contract_sha256,
                  args.source_manifest: args.source_sha256,
                  Path(contract['checkpoint_path']): contract['checkpoint_sha256']})
    return BoundFiles(files)


def execute(args):
    if sha(args.contract)!=args.contract_sha256 or sha(args.source_manifest)!=args.source_sha256:
        raise ValueError('contract or snapshot manifest hash differs')
    contract = json.loads(args.contract.read_text())
    validate_contract(contract)
    root = args.root.resolve()
    if not root.is_relative_to(Path('/data/guoyikun/')):
        raise ValueError('real pilot outputs must be under /data/guoyikun/')
    if args.stage=='development':
        if args.admission is None or sha(args.admission)!=args.admission_sha256:
            raise ValueError('development needs a hashed engineering admission')
        admission = json.loads(args.admission.read_text())
        if (admission.get('status')!='PASS' or admission['contract_sha256']!=args.contract_sha256
                or admission['source_manifest_sha256']!=args.source_sha256
                or sha(root/'engineering/summary.json')!=admission['engineering_summary_sha256']):
            raise ValueError('engineering admission identity mismatch')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required; no CPU fallback')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.cuda.set_per_process_memory_fraction(.25, torch.device('cuda:0'))
    guard = source_guard(args, contract)
    run = Run(root, args.stage, contract, guard)
    try:
        cache = run.out/'code-cache'
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        system = _make_config_a(1024, 2., 8, 10., 4.)
        model = build_receiver(contract['checkpoint_path'], system, 1024, 'cuda:0',
                               receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, 'B0-p2-s0.5', system=system)
        run.write('environment.json', dict(pid=os.getpid(), hostname=os.uname().nodename,
            started_at=run.started, torch=torch.__version__, numpy=np.__version__,
            cuda=torch.version.cuda, device=torch.cuda.get_device_name(0),
            threads=torch.get_num_threads(), source_manifest_sha256=args.source_sha256,
            contract_sha256=args.contract_sha256, checkpoint_sha256=contract['checkpoint_sha256'],
            code_identity=hashes({k: code[k] for k in ('G','H','free_cols','chk','var','row_ptr')})))
        split = 2 if args.stage=='development' else 1
        blocks = contract['development_blocks'] if split==2 else contract['engineering_blocks']
        qualifications, comparisons, exogenous = [], [], []
        for block in range(blocks):
            run.check()
            raw = generate_exogenous(system, code, block, split=split)
            raw_file = save_state(run.out/f'exogenous-{block:03d}.npz', raw, run.meter, readback=True)
            exo = dict(block=block, split=split, state=raw_file,
                hashes=hashes({k: raw[k] for k in ('H','info','coded','data','pilot','noise')}))
            run.write(f'exogenous-{block:03d}.json', exo)
            exogenous.append(exo)
            for snr in contract['snrs']:
                observed = observed_at_snr(raw, snr)
                saved_obs = save_state(run.out/f'observed-{block:03d}-{snr}.npz',
                                       dict(observed), run.meter, readback=True)
                run.write(f'observed-{block:03d}-{snr}.json', dict(block=block, snr=snr,
                    split=split, state=saved_obs, exogenous_hashes=exo['hashes']))
                identity = dict(block=block, snr=snr, split=split)
                full = {}
                arms = ('I1',) if args.stage=='golden' else FULL_ARMS
                for arm in arms:
                    value, record = run.call('F', dict(identity, arm=arm),
                        lambda arm=arm: run_full(receiver, code, observed, arm),
                        observed, raw, None)
                    full[arm] = value
                if args.stage=='golden':
                    continue
                i1 = full['I1']
                if args.stage=='engineering':
                    repeat, _ = run.call('F', dict(identity, arm='I1_REPEAT'),
                        lambda: run_full(receiver, code, observed, 'I1'), observed, raw, None)
                    old_index = 2*block+contract['snrs'].index(snr)+1
                    old = json.loads((root/'golden'/f'F-{old_index:04d}-result.json').read_text())
                    if old['observed_hashes']!=hashes(observed):
                        raise ValueError('old/new source replay input identity mismatch')
                    comparisons.append(dict(identity, repeat=compare_full(repeat, i1),
                                             golden=compare_full(i1, load_state(old['state']))))
                terminal_results = {}
                for arm in TERMINAL_ARMS:
                    z, H, sigma = terminal_inputs(observed, i1['H'], raw['H'], i1['sigma2_terminal'], arm)
                    def invoke(arm=arm, z=z, H=H, sigma=sigma):
                        if arm.startswith('BP'):
                            return terminal_decode(z, H, sigma, observed['constellation'], code,
                                                   device='cuda:0', audit=False)
                        return ep_terminal(z, H, sigma, observed['constellation'], code,
                                           EP_RECIPE, device='cuda:0')
                    extra = dict(truth_access='true channel terminal intervention + offline scoring'
                                 if '_TRUE_' in arm else 'offline scoring only',
                                 terminal_input_hashes=hashes(dict(z=z, H=H, sigma=np.asarray(sigma),
                                                                 constellation=observed['constellation'])),
                                 sigma=sigma, I1_sigma_base=i1['sigma2_terminal'])
                    value, _ = run.call('T', dict(identity, arm=arm), invoke, observed, raw, H, extra)
                    terminal_results[arm] = value
                if args.stage=='engineering':
                    for arm in ('EP_EST_NOISE', 'EP_TRUE_NOISE'):
                        z, H, sigma = terminal_inputs(observed, i1['H'], raw['H'], i1['sigma2_terminal'], arm)
                        value, _ = run.call('T', dict(identity, arm=arm+'_DOUBLE'),
                            lambda: ep_terminal(z, H, sigma, observed['constellation'], code,
                                                EP_RECIPE, device='cuda:0', doubled=True),
                            observed, raw, H, dict(truth_access='true channel terminal intervention + offline scoring'
                                if '_TRUE_' in arm else 'offline scoring only'))
                        qualifications.append(dict(identity, arm=arm,
                            **qualification_pair(terminal_results[arm], value)))
                print(json.dumps(dict(stage=args.stage, block=block, snr=snr, calls=run.counts,
                    FER={arm: int(np.any(value['info_hat']!=raw['info'])) for arm, value in full.items()})), flush=True)
        if run.counts!={k: run.bounds[k] for k in ('F','T')}:
            raise ValueError('completed stage has missing scheduled calls')
        guard.verify()
        run.meter.verify()
        summary = dict(schema='i1-bottleneck-stage-v1', status='COMPLETE', stage=args.stage,
            contract_sha256=args.contract_sha256, source_manifest_sha256=args.source_sha256,
            calls=run.counts, bounds=run.bounds, started_at=run.started, finished_at=time.time(),
            wall_seconds=time.time()-run.started, records=run.records, exogenous=exogenous,
            engineering_comparisons=comparisons, ep_qualification=qualifications,
            peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
            raw_readback='all saved array dtype/shape/content hashes verified',
            truth_scope='full arms observed-only; named TRUE terminal interventions; offline scoring')
        run.write('summary.json', summary)
        run.meter.verify()
        print(json.dumps(dict(status='COMPLETE', stage=args.stage, calls=run.counts,
                              wall_seconds=summary['wall_seconds'])), flush=True)
    except BaseException as exc:
        # Preserve the reservation even when execution or validation fails.
        run.write('failure.json', dict(status='FAILED', stage=args.stage, calls=run.counts,
            active=run.active, error=repr(exc), traceback=traceback.format_exc(),
            started_at=run.started, finished_at=time.time()))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True, choices=('golden','engineering','development'))
    for name in ('root', 'contract', 'source-manifest'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('contract-sha256', 'source-sha256'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--admission', type=Path)
    parser.add_argument('--admission-sha256')
    execute(parser.parse_args())


if __name__=='__main__':
    main()
