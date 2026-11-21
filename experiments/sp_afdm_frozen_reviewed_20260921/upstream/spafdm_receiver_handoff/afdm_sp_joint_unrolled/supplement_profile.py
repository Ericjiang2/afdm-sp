"""Supplement COST-01: bounded, instrumented engineering F/T/E quotes only."""
from __future__ import annotations

import argparse
import fcntl
from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
import subprocess
from unittest.mock import patch

# Must precede numerical imports in the standalone CLI.
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import numpy as np
import torch
from . import classical_joint_unrolled as joint
from . import direction_receiver as receiver_api
from . import v3_initial
from . import afdm_baselines as afb
from . import decision_gateA as gate
from .budgeted_support_eval import build_receiver, load_prior
from .budgeted_frame_store import publish_json
from .decision_gateA import make_genie_lambda
from .direction_receiver import ObservedReceiver, CHECKPOINT_HASH
from .direction_data import validate_observed
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_data import SupplementData, CAMPAIGN_ID, campaign_rng
from .supplement_run import sha, sources, json_value, array_hash, reserve, publish_terminal

PRIOR_HASH = '74f23844a95ea36ea90490f7aa5fca76bd14ff8a97f954f4387a4e85c852444e'
ARMS = {'A2': ('b0', None, 1.), 'B0': ('b0', None, 1.), 'old-Bstar': ('sbl', .001, .5)}
A2_SOURCE = {
    'contract': 'direction_cost.py main contract[A2], build_receiver/load_prior/run_frame calls',
    'implementation': 'budgeted_support_eval.run_frame baseline: host OMP40 H0, achievable scorer, F2P M96/two rounds/defer prune/protect2/topk, direct40',
    'capacity': 'fixed nomination40, receiver_extension0, active_cap40; no true P_actual',
    'prior_sha256': PRIOR_HASH,
    'historical_other_path': 'e1_ldpc_coded_eval.run_gate uses true P_actual; NOT this direction_cost denominator',
    'adapter_change': 'same estimated-H scorer and outer path, shared direction_receiver.terminal_decode; old evaluator removed; runtime equivalence not assumed',
}


class A2Model:
    """Observed-only adapter for the direction_cost A2, not a new A2 recipe."""
    def __init__(self, model, system, lookup):
        self.model, self.system, self.lookup = model, system, lookup
        self.cfg = model.cfg
        self.use_soft_decisions = model.use_soft_decisions
        self.observed = None

    def __call__(self, y, pilot, sigma2, constellation, **kwargs):
        cfg = self.cfg
        if self.observed is None:
            raise ValueError('A2 requires validated original host observations')
        yn, pn = self.observed['y'], self.observed['pilot']
        phi = afb.construct_sensing_matrix(cfg.N, pn, cfg.c1, cfg.c2, cfg.l_max, cfg.k_max)
        _, support = afb.omp_sparse(yn, phi, 40)
        support = np.asarray(support, dtype=int)
        gains = np.linalg.lstsq(phi[:, support], yn, rcond=None)[0]
        h0 = self.system.gen_h_daft(gains, support // 5, support % 5 - 2)
        head = self.model.cand_active_rel
        head.set_refine_config(2, 96, True, 2)
        # The legacy factory parameter is named H_true; it receives estimated H0 here.
        head._gateA_scorer = make_genie_lambda(h0, cfg.rho, self.lookup, 2, 5)
        head._gateA_tau = -1e9
        kwargs.pop('initial_estimator')
        kwargs.update(enable_support_repair=True, receiver_extension=0, active_support_cap=40)
        return self.model(y, pilot, sigma2, constellation, **kwargs)


class A2Receiver(ObservedReceiver):
    def run(self, observed, **kwargs):
        validate_observed(observed, self.model.cfg.N)
        self.model.observed = observed
        try:
            return super().run(observed, **kwargs)
        finally:
            self.model.observed = None


def gpu_snapshot(device):
    if device.type != 'cuda':
        return {'status': 'not_applicable_cpu'}
    command = ['nvidia-smi', '--query-gpu=index,uuid,utilization.gpu,memory.used,memory.total',
               '--format=csv,noheader,nounits']
    completed = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    return dict(command=command, exitcode=completed.returncode,
                stdout=completed.stdout, stderr=completed.stderr,
                scope='whole-device instantaneous occupancy; not per-process SM utilization')


def sync(device):
    if device.type == 'cuda':
        torch.cuda.synchronize(device)


class OperatorProfile:
    """Synchronized inclusive function samples; nested times must not be summed."""
    def __init__(self, device):
        self.device, self.rows, self.stack = device, [], ExitStack()

    def wrap(self, module, name, label):
        original = getattr(module, name)
        def measured(*args, **kwargs):
            sync(self.device)
            wall, cpu = time.perf_counter(), time.process_time()
            status = 'failed'
            try:
                value = original(*args, **kwargs)
                sync(self.device)
                status = 'complete'
                return value
            finally:
                self.rows.append(dict(operator=label, status=status,
                    seconds=time.perf_counter()-wall, CPU_seconds=time.process_time()-cpu))
        self.stack.enter_context(patch.object(module, name, measured))

    def __enter__(self):
        for module, name, label in (
            (joint, 'construct_sensing_matrix_torch', 'dictionary_torch'),
            (afb, 'construct_sensing_matrix', 'dictionary_host'),
            (afb, 'omp_sparse', 'host_CE_OMP'),
            (gate, 'whitened_suffstats', 'A2_achievable_whitening'),
            (joint, 'omp_sparse_torch', 'CE_OMP'),
            (v3_initial, 'omp_sparse_torch', 'CE_initial_OMP'),
            (joint, 'soft_gain_update', 'DA_LS_feedback_gain'),
            (joint, 'mp_detect_bp_torch', 'outer_BP'),
            (receiver_api, 'mp_detect_bp_torch', 'terminal_BP'),
            (receiver_api, 'demap_llr', 'LLR'),
            (receiver_api, 'decode_llr', 'LDPC')):
            self.wrap(module, name, label)
        return self

    def __exit__(self, *exc):
        return self.stack.__exit__(*exc)


def validate_args(args):
    if not 0 <= args.start < args.stop <= 32 or args.snr != 8:
        raise ValueError('profile uses engineering blocks [0,32), 8dB prior domain')
    if not math.isfinite(args.deadline_unix) or args.deadline_unix <= time.time():
        raise ValueError('future finite deadline required')
    arms = json.loads(args.arms)
    if not isinstance(arms, list) or not arms or any(a not in ARMS for a in arms) or len(set(arms)) != len(arms):
        raise ValueError('arms must be unique explicit JSON A2/B0/old-Bstar list')
    count = (args.stop-args.start)*len(arms)
    for cap in (args.max_full_calls, args.max_terminal_calls, args.max_ce_calls):
        if type(cap) is not int or not count <= cap <= 24:
            raise ValueError('each F/T/E cap must cover requested calls and be at most24')
    if 'A2' in arms and args.prior is None:
        raise ValueError('A2 requires the original content-bound direct40 prior400')
    return arms


def reservation_calls(row):
    """Read the shared ledger, recovering v1 profile T/E from its bound contract."""
    calls=row.get('calls_reserved')
    if calls is None:
        path=Path(row['out'])/'contract.json'
        if path.exists():
            old=json.loads(path.read_text())
            payload={k:v for k,v in old.items() if k not in ('config_sha256','ledger')}
            digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
            if digest != row['contract_sha256'] or old.get('config_sha256') != digest:
                raise ValueError('legacy profile contract hash mismatch')
            calls=old.get('calls_reserved')
            if calls is None:
                raise ValueError('legacy profile contract lacks F/T/E limits')
        else:
            calls=dict(F=row['max_full_calls'],T=0,E=0)
    if (not isinstance(calls,dict) or set(calls) != {'F','T','E'} or
            any(type(v) is not int or v < 0 for v in calls.values()) or
            calls['F'] != row['max_full_calls']):
        raise ValueError('invalid shared F/T/E reservation')
    return calls


def reserve_profile(out,contract):
    """Extend the existing ledger and lock; one atomic F/T/E reservation."""
    limits=dict(F=128,T=256,E=128)
    requested=reservation_calls(dict(contract,out=str(out)))
    ledger=out.parent/'supplement-engineering-ledger'
    ledger.mkdir(exist_ok=True)
    with (ledger/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        totals=dict(F=0,T=0,E=0)
        for path in ledger.glob('reservation-*.json'):
            row=json.loads(path.read_text())
            if row['campaign_id'] != CAMPAIGN_ID:
                raise ValueError('foreign campaign reservation')
            for kind,count in reservation_calls(row).items():totals[kind]+=count
        if any(totals[k]+requested[k]>limits[k] for k in limits):
            raise ValueError('cumulative engineering F128/T256/E128 cap exceeded')
        key=hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger/f'reservation-{key}.json',dict(campaign_id=CAMPAIGN_ID,
            out=str(out.resolve()),max_full_calls=requested['F'],calls_reserved=requested,
            contract_sha256=contract['config_sha256'],
            policy='conservative reservation; failures and unused quotas never automatically reclaimed'))
    return str(ledger)


def assert_content_unchanged(args,contract):
    if sources()!=contract['source_sha256']:
        raise ValueError('source snapshot changed')
    for name in ('checkpoint','protocol','prior'):
        expected=contract[name+'_sha256']
        if expected is not None and sha(getattr(args,name))!=expected:
            raise ValueError(name+' content changed')


def score_errors(value,truth):
    info,coded=np.asarray(truth['info']),np.asarray(truth['coded'])
    ihat,decoded,hard=(np.asarray(value[k]) for k in ('info_hat','decoded','x_hard'))
    if (info.ndim!=1 or coded.ndim!=1 or not info.size or not coded.size or
            ihat.shape!=info.shape or decoded.shape!=coded.shape or
            hard.ndim!=1 or hard.size*2!=coded.size or not np.isfinite(hard).all()):
        raise ValueError('bit/symbol dimensions or finite values invalid; broadcasting forbidden')
    if any(not np.isin(a,(0,1)).all() for a in (info,coded,ihat,decoded)):
        raise ValueError('nonbinary bit array')
    errors=int(np.count_nonzero(ihat!=info))
    raw=np.concatenate((hard.real<0,hard.imag<0)).astype(np.uint8)
    return dict(FER=int(errors>0),coded_bit_errors=errors,
        raw_bit_errors=int(np.count_nonzero(raw!=coded)),
        decoded_codeword_bit_errors=int(np.count_nonzero(decoded!=coded)),
        raw_bits_denominator=int(coded.size),coded_bits_denominator=int(info.size),
        offline_truth_access='error scoring only')


def execute(args):
    args.out.mkdir(parents=True, exist_ok=False)
    start, cpu0 = time.perf_counter(), time.process_time()
    counts = dict(F=0, T=0, E=0)
    active, records, operators = None, [], None
    previous = signal.getsignal(signal.SIGALRM)
    command = [sys.executable, *sys.argv]
    try:
        arms = validate_args(args)
        def timeout(_signal, _frame):
            raise TimeoutError('profile deadline reached')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix-time.time())
        torch.set_num_threads(1)
        device = torch.device(args.device)
        if device.type not in ('cpu','cuda') or (device.type == 'cuda' and not torch.cuda.is_available()):
            raise ValueError('requested device unavailable')
        if sha(args.checkpoint) != CHECKPOINT_HASH:
            raise ValueError('checkpoint hash mismatch')
        if 'A2' in arms and sha(args.prior) != PRIOR_HASH:
            raise ValueError('A2 prior hash mismatch')
        (args.out/'code-cache').mkdir()
        code = build_code(cache_dir=args.out/'code-cache')
        data = SupplementData(args.protocol, code)
        system = _make_config_a(1024, 2., 8, 10., 4.)
        contract = dict(campaign_id=CAMPAIGN_ID, purpose='COST-01 engineering quote, not COST-02',
            split='engineering', scenario='G0', start=args.start, stop=args.stop, snr=args.snr,
            arms=arms, A2_source=A2_SOURCE, old_Bstar='direction prototype-development cached sbl-s0.5',
            source_sha256=sources(), protocol_sha256=sha(args.protocol), checkpoint_sha256=sha(args.checkpoint),
            prior_sha256=sha(args.prior) if 'A2' in arms else None,
            code_sha256={k: array_hash(code[k]) for k in ('G','H')},
            device=str(device), threads=torch.get_num_threads(),
            affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
            calls_reserved=dict(F=args.max_full_calls,T=args.max_terminal_calls,E=args.max_ce_calls),
            campaign_engineering_caps=dict(F=128,T=256,E=128),
            max_full_calls=args.max_full_calls, deadline_unix=args.deadline_unix,
            command=command, versions=dict(torch=torch.__version__,numpy=np.__version__,python=sys.version),
            boundaries=dict(F='observed host y through scorer preparation, dictionary, outer receiver, cancellation, BP, LLR, LDPC; evaluator excluded',
                T='same F final estimated H/sigma; cancellation plus BP/LLR/LDPC',
                E='observed OMP40 plus family gain estimate on prepared dictionary; not entire outer CE or physical refit'),
            feedback={'detector_to_CE':'actual DA_LS_feedback_gain operator samples',
                      'LDPC_extrinsic':'not_implemented; no fabricated timing'},
            operator_scope='synchronized inclusive nested samples; do not sum with full calls',
            gpu_utilization='nvidia-smi occupancy sampled before/after each call; snapshots are not time averages')
        contract['config_sha256'] = hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
        contract['ledger'] = reserve_profile(args.out, contract)
        publish_json(args.out/'contract.json',contract)
        model = build_receiver(args.checkpoint,system,1024,args.device,receiver_shell='direct40',active_cap=40)
        normal = ObservedReceiver(model, code)
        a2 = None
        if 'A2' in arms:
            lookup, _ = load_prior(args.prior,8,1024,l_max=102,k_max=2,nomination_cap=40,receiver_shell='direct40')
            a2 = A2Receiver(A2Model(model,system,lookup),code)
        def measure(kind, arm, frame, fn):
            nonlocal active, operators
            if time.time() >= args.deadline_unix or counts[kind] >= contract['calls_reserved'][kind]:
                raise RuntimeError('profile deadline or call cap exhausted')
            assert_content_unchanged(args,contract)
            counts[kind] += 1
            active = dict(kind=kind, arm=arm, block=frame.metadata['block'], ordinal=counts[kind],
                input_hashes=frame.metadata['input_hashes'])
            publish_json(args.out/f'started-{kind}-{counts[kind]:03d}.json',active)
            sync(device)
            if device.type == 'cuda': torch.cuda.reset_peak_memory_stats(device)
            occupancy_before=gpu_snapshot(device)
            wall, cpu = time.perf_counter(),time.process_time()
            with OperatorProfile(device) as operators:
                value = fn()
                sync(device)
            elapsed, cpu_seconds = time.perf_counter()-wall,time.process_time()-cpu
            assert_content_unchanged(args,contract)
            record = dict(attempt=active, seconds=elapsed, CPU_seconds=cpu_seconds,
                CPU_utilization_ratio=cpu_seconds/elapsed, operators=operators.rows,
                gpu_occupancy_before=occupancy_before,gpu_occupancy_after=gpu_snapshot(device),
                peak_gpu_allocated_bytes=int(torch.cuda.max_memory_allocated(device)) if device.type=='cuda' else 0,
                peak_gpu_reserved_bytes=int(torch.cuda.max_memory_reserved(device)) if device.type=='cuda' else 0,
                process_peak_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                rss_unit='bytes' if sys.platform=='darwin' else 'KiB',
                truth_access='none', config_sha256=contract['config_sha256'])
            return value, record
        def finish(record):
            nonlocal active
            path=args.out/f'sample-{active["kind"]}-{active["ordinal"]:03d}.json'
            publish_json(path,json_value(record))
            records.append(dict(path=str(path),sha256=sha(path)))
            active=None
        for block in range(args.start,args.stop):
            active=dict(kind='generation',block=block,split='engineering',scenario='G0',snr=8,
                        protocol_sha256=contract['protocol_sha256'])
            publish_json(args.out/f'generation-{block:03d}-started.json',active)
            assert_content_unchanged(args,contract)
            frame=data.make_frame(system,'engineering',block,8)
            assert_content_unchanged(args,contract)
            order=list(arms);campaign_rng('engineering',block,'order').shuffle(order)
            for arm in order:
                assert_content_unchanged(args,contract)
                family, parameter, scale=ARMS[arm]
                recv=a2 if arm=='A2' else normal
                value, rec=measure('F',arm,frame,lambda:recv.run(frame.observed,
                    family=family,parameter=parameter,terminal_scale=scale,audit=True))
                rec['terminal']=publish_terminal(args.out/f'terminal-{block}-{arm}.npz',value)
                rec['H_sha256']=array_hash(value['H']);rec['sigma2_terminal']=value['sigma2_terminal']
                rec.update(score_errors(value,frame._truth))
                finish(rec)
                obs=frame.observed
                terminal,rec=measure('T',arm,frame,lambda:receiver_api.terminal_decode(
                    obs['y']-value['H']@obs['pilot'],value['H'],value['sigma2_terminal'],
                    obs['constellation'],code,device=args.device,audit=True))
                rec.update(H_sha256=array_hash(value['H']),decoded_sha256=array_hash(terminal['decoded']))
                rec.update(score_errors(terminal,frame._truth))
                finish(rec)
                active=dict(kind='E_preparation',arm=arm,block=block,
                            input_hashes=frame.metadata['input_hashes'])
                cfg=model.cfg
                y=torch.tensor(obs['y'],dtype=cfg.dtype,device=device)
                p=torch.tensor(obs['pilot'],dtype=cfg.dtype,device=device)
                sigma=torch.tensor(obs['sigma2'],dtype=cfg.rdtype,device=device)
                sync(device);t0=time.perf_counter()
                phi=joint.construct_sensing_matrix_torch(1024,p,cfg.c1,cfg.c2,102,2,cdtype=cfg.dtype)
                sync(device);prep=time.perf_counter()-t0
                estimator=v3_initial.InitialEstimator(family,parameter)
                with torch.no_grad():
                    ce,rec=measure('E',arm,frame,lambda:estimator(y,phi,40,sigma))
                rec.update(dictionary_preparation_seconds=prep,estimator=estimator.record,
                    coefficient_sha256=array_hash(ce[0].detach().cpu().numpy()),support=ce[1])
                finish(rec)
        assert_content_unchanged(args,contract)
        signal.setitimer(signal.ITIMER_REAL,0)
        publish_json(args.out/'complete.json',dict(status='complete',exitcode=0,calls=counts,
            records=records,command=command,wall_seconds=time.perf_counter()-start,
            CPU_seconds=time.process_time()-cpu0,scope='engineering quote only; no formal mean/p95 gate',
            config_sha256=contract['config_sha256']))
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL,0)
        publish_json(args.out/'failure.json',dict(status='failed',exitcode=130 if isinstance(exc,KeyboardInterrupt) else 1,
            exception=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),calls=counts,
            active_attempt=active,operators=operators.rows if operators else [],records=records,command=command))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','checkpoint','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--prior',type=Path)
    for name in ('start','stop','max-full-calls','max-terminal-calls','max-ce-calls'):
        p.add_argument('--'+name,type=int,required=True)
    p.add_argument('--deadline-unix',type=float,required=True)
    p.add_argument('--snr',type=float,required=True)
    p.add_argument('--device',required=True)
    p.add_argument('--arms',required=True,help='explicit JSON list, e.g. ["A2","B0","old-Bstar"]')
    return execute(p.parse_args())


if __name__=='__main__':
    sys.exit(main())
