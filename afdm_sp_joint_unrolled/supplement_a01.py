"""A-01 controlled soft-failure factorial. Truth-assisted; not deployable."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

for _key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import numpy as np
import torch

from .afdm_baselines import construct_sensing_matrix
from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import physical_cluster_weights
from .budgeted_support_eval import build_receiver
from .direction_factorial import residual_ledger
from .direction_logging import publish_snapshot
from .direction_physical import SOFT_LAMBDAS, fit_physical_observed
from .direction_physical_receiver import PhysicalChannelRefit
from .direction_receiver import CHECKPOINT_HASH, terminal_decode
from .direction_run import json_value
from .supplement_development_analysis import analyze_development, development_table
from .direction_structure import _fit_ls, _svd
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .representation_ledger import merged_truth_ledger
from .supplement_baselines import BaselineReceiver, recipe_by_id
from .supplement_data import CAMPAIGN_ID, LIMITS, SupplementData, campaign_rng
from .supplement_detectors import terminal as catalog_terminal
from .supplement_h01 import FROZEN_D1_SHA256, RECIPE_ID as BSTAR, detectors_from_d1, load_d1_freeze
from .supplement_m01 import require_support
from .supplement_profile import score_errors
from .supplement_run import sha, sources
from .supplement_a01_cache import load_manifest, read_state
from .supplement_a01_diagnostics import fit_diagnostics, terminal_diagnostics

STAGE = 'A-01'
RECIPE_ID = BSTAR
SPLIT = 'mechanism'
SNRS = (7, 8, 9)
N_BLOCKS = LIMITS['mechanism']
SOFT_LAMBDA = .01
GEOM = ('est', 'true')
CONSTRAINT = ('none', 'soft', 'hard')
DATA = ('xsoft', 'xtrue')
CORE_ARMS = tuple(f'{g}-{c}-{d}' for g in GEOM for c in CONSTRAINT for d in DATA)
BRIDGE_ARMS = ('S0-soft', 'S0-hard', 'I-soft', 'I-hard')
ARMS = CORE_ARMS + BRIDGE_ARMS
TOTAL_F = N_BLOCKS * len(SNRS)
TOTAL_E = len(ARMS) * TOTAL_F
TOTAL_T = 2 * TOTAL_E
# Historical totals above describe the immutable v1 producer. New execution
# also charges the two shared geometry preparations before its 16 arm fits.
PREPARATION_PASSES = 2
E_PER_STATE = PREPARATION_PASSES + len(ARMS)
T_PER_STATE = 2 * len(ARMS)
LEDGER_NAME = 'supplement-a01-mechanism-ledger'
FAILURE_RESERVE_BYTES = 256 * 1024
PER_FULL_ESTIMATE_BYTES = 40 * 1024 ** 2
GPU_FRACTION = .35
FORBIDDEN_CLAIMS = (
    'deployable structure',
    'F_A confirmation',
    'optimal detector',
    'core arms are legal flow',
    'rerun 16T',
)


def _arm_spec(arm):
    if arm in BRIDGE_ARMS:
        mask, cons = arm.split('-')
        return dict(kind='bridge', mask=mask, constraint=cons, data='xsoft',
                    legal_flow_comparable=mask == 'S0')
    geom, cons, data = arm.split('-')
    if geom not in GEOM or cons not in CONSTRAINT or data not in DATA:
        raise ValueError('unknown A-01 core arm')
    return dict(kind='core', geometry=geom, constraint=cons, data=data,
                legal_flow_comparable=False)


def snapshot_from_result(frame, result):
    obs, truth = frame.observed, frame._truth
    if 'x_soft' not in result:
        raise ValueError('A-01 requires receiver x_soft; M-01 snapshots omit it')
    snap = dict(
        Hhat=np.array(result['H'], copy=True),
        Htrue=np.array(truth['H'], copy=True),
        y=np.array(obs['y'], copy=True),
        pilot=np.array(obs['pilot'], copy=True),
        data=np.array(truth['data'], copy=True),
        x_soft=np.array(result['x_soft'], copy=True),
        noise=np.array(truth['noise'], copy=True),
        sigma2_thermal=np.asarray(obs['sigma2']),
        sigma2_terminal=np.asarray(result['sigma2_terminal']),
        constellation=np.array(obs['constellation'], copy=True),
        info=np.array(truth['info'], copy=True),
        coded=np.array(truth['coded'], copy=True),
        decoded=np.array(result['decoded'], copy=True),
        support=np.asarray(result['support'], dtype=np.int64),
        gains=np.asarray(result['gains']))
    require_support(snap)
    residual_ledger(snap, snap['Hhat'], snap['Hhat'])
    return snap


def _sensing(system, pilot, x, ids):
    n = len(pilot)
    if not len(ids):
        return np.zeros((n, 0), complex)
    return construct_sensing_matrix(
        system.N_total, np.asarray(pilot) + np.asarray(x),
        system.c1, system.c2, system.l_max_cap, system.k_max_cap)[:, ids]


def _shape_from_groups(incidence, coefficients):
    k = len(coefficients)
    if incidence.size == 0:
        return np.zeros((k, 0), complex)
    cols = []
    for j in range(incidence.shape[1]):
        mask = incidence[:, j]
        col = np.zeros(k, complex)
        vec = coefficients[mask]
        nrm = float(np.linalg.norm(vec))
        col[mask] = vec / nrm if nrm > 0 else vec
        cols.append(col)
    return np.column_stack(cols)


def prepare_legal_bridge(snapshot, system):
    """Freeze the original observed-only bounded search once on the original S0.

    Both constraints and the I-mask restriction consume this one basis. A basis
    made from the same unconstrained LS vector would contain that optimum and
    would test a different, often vacuous constraint.
    """
    support = require_support(snapshot)
    public = PhysicalChannelRefit(system, 'm-param-budget').geometry
    A = _sensing(public, snapshot['pilot'], snapshot['x_soft'], support)
    return fit_physical_observed(public, snapshot['y'], A, support, snapshot['gains'],
        float(snapshot['sigma2_terminal']), 'm-param-budget')


def prepare_from_frame(frame, snapshot, system, *, before_call=None, after_call=None):
    if (before_call is None) != (after_call is None):
        raise ValueError('both preparation accounting callbacks are required')
    support = require_support(snapshot)
    params = frame._truth['params']
    truth = merged_truth_ledger(params, system.k_max_cap, threshold=0.)
    true_ids = {e['column'] for e in truth['entries']
                if e['above_threshold'] and e['column'] is not None
                and 0 <= e['delay'] <= system.l_max_cap}
    I = np.asarray(sorted(set(support.tolist()) & true_ids), dtype=int)
    geometry = {k: params[k] for k in ('taps', 'l_i', 'k_real')}
    if before_call is not None:
        before_call('core_reference')
    if len(I):
        W_true = physical_cluster_weights(system, geometry)[I, :]
        incidence_true = np.abs(W_true) > 0
        A_ref = _sensing(system, snapshot['pilot'], snapshot['x_soft'], I)
        g_ref, _ = _fit_ls(A_ref, snapshot['y'])
        W_est = _shape_from_groups(incidence_true, g_ref)
    else:
        W_true = np.zeros((0, 0), complex)
        incidence_true = np.zeros((0, 0), bool)
        W_est = np.zeros((0, 0), complex)
        g_ref = np.zeros(0, complex)
    if after_call is not None:
        after_call('core_reference')
    if before_call is not None:
        before_call('legal_search')
    legal = prepare_legal_bridge(snapshot, system)
    if after_call is not None:
        after_call('legal_search')
    truth_coefficients = {e['column']: complex(e['real'], e['imag'])
                          for e in truth['entries'] if e['column'] is not None
                          and 0 <= e['delay'] <= system.l_max_cap}
    return dict(snapshot=snapshot, I=I, S0=support, W_true=W_true, W_est=W_est, W_s0=legal['basis'],
                geometry=geometry, truth_support=sorted(true_ids),
                pairing_verified=True, geometry_frozen_before_data=True,
                reference_coefficients=g_ref, legal_geometry=legal['diagnostics'],
                bridge_definition='original_bounded_physical_search_once_on_S0',
                truth_coefficients=truth_coefficients,
                preparation_solver_calls=dict(core_reference=int(bool(len(I))),
                    legal_search=int(legal['diagnostics']['query_count'])))


def _constrained(A, y, W, constraint):
    if constraint == 'none':
        g, details = _fit_ls(A, y)
        return g, dict(details, constraint='none')
    if W.size == 0:
        g, details = _fit_ls(A, y) if constraint == 'soft' else (
            np.zeros(A.shape[1], complex), {'rank': 0})
        return g, dict(details, constraint=constraint, zero_basis=True)
    u, _, _, rank, _ = _svd(W)
    if constraint == 'hard':
        latent, details = _fit_ls(A @ W, y)
        return W @ latent, dict(details, constraint='hard', basis_rank=rank)
    if SOFT_LAMBDA not in SOFT_LAMBDAS:
        raise ValueError('A-01 soft lambda is not in the frozen table')
    complement = np.eye(A.shape[1]) - u[:, :rank] @ u[:, :rank].conj().T
    lam = float(SOFT_LAMBDA * np.linalg.norm(A, 'fro') ** 2 / max(A.shape[1], 1))
    if lam == 0:
        g, details = _fit_ls(A, y)
    else:
        g, details = _fit_ls(np.vstack((A, np.sqrt(lam) * complement)),
                             np.concatenate((y, np.zeros(A.shape[1]))))
    return g, dict(details, constraint='soft', soft_lambda_normalized=SOFT_LAMBDA,
                   soft_lambda=lam, basis_rank=rank)


def _channel(system, coefficients, ids):
    n = system.N_total
    if not len(ids):
        return np.zeros((n, n), complex)
    width = 2 * system.k_max_cap + 1
    return system.gen_h_daft(coefficients, ids // width, ids % width - system.k_max_cap)


def fit_arm(prepared, system, arm):
    spec = _arm_spec(arm)
    s = prepared['snapshot']
    if spec['kind'] == 'core':
        ids = prepared['I']
        x = s['x_soft'] if spec['data'] == 'xsoft' else s['data']
        A = _sensing(system, s['pilot'], x, ids)
        W = prepared['W_est'] if spec['geometry'] == 'est' else prepared['W_true']
        g, details = _constrained(A, s['y'], W, spec['constraint'])
        truth_level = 'geometry_oracle+true_groups'
        if spec['data'] == 'xtrue':
            truth_level += '+true_symbols'
        if spec['geometry'] == 'true':
            truth_level += '+true_shape'
    else:
        ids = prepared['S0'] if spec['mask'] == 'S0' else prepared['I']
        A = _sensing(system, s['pilot'], s['x_soft'], ids)
        if spec['mask'] == 'S0':
            W = prepared['W_s0']
        else:
            index = [int(np.where(prepared['S0'] == i)[0][0]) for i in ids] if len(ids) else []
            W = prepared['W_s0'][index, :] if len(index) else np.zeros((0, prepared['W_s0'].shape[1]), complex)
        g, details = _constrained(A, s['y'], W, spec['constraint'])
        truth_level = 'none' if spec['legal_flow_comparable'] else 'support_mask_I'
    H = _channel(system, g, ids)
    residual = residual_ledger(s, H, H)
    return dict(coefficients=g, atom_ids=np.asarray(ids, dtype=int), H=H,
                A=A, basis=W, residual=residual, diagnostics=details, spec=spec,
                truth_access_level=truth_level)


def detect_arm(prepared, fitted, code, arm, detector, *, device, before_call):
    if detector == 'EP10':
        raise ValueError('A-01 must not use EP10')
    s = prepared['snapshot']
    before_call('terminal', arm, detector)
    H, z = fitted['H'], s['y'] - fitted['H'] @ s['pilot']
    if detector == 'BP':
        result = terminal_decode(z, H, float(s['sigma2_terminal']),
                                 s['constellation'].copy(), code, device=device, audit=True)
    else:
        result = catalog_terminal(z, H, float(s['sigma2_terminal']),
                                  s['constellation'].copy(), code, detector, device=str(device))
    result.update(arm_id=f'A_{arm}', detector=detector,
                  atom_ids=fitted['atom_ids'].tolist(),
                  coefficients=fitted['coefficients'], Hfit=H,
                  residual=fitted['residual'], candidate_eligible=False,
                  deployable=False, truth_access_level=fitted['truth_access_level'],
                  legal_flow_comparable=fitted['spec']['legal_flow_comparable'])
    result['info_errors'] = int(np.count_nonzero(result['info_hat'] != s['info']))
    result['FER'] = int(result['info_errors'] > 0)
    return result


def _identities(start, stop, snrs):
    if (not isinstance(snrs, list) or not snrs or any(s not in SNRS for s in snrs) or
            len(set(snrs)) != len(snrs)):
        raise ValueError('A-01 snrs must be a unique subset of 7/8/9')
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= N_BLOCKS:
        raise ValueError('A-01 blocks must lie in mechanism[0,256)')
    return {(block, int(snr)) for block in range(start, stop) for snr in snrs}


def validate_args(args):
    if args.split != SPLIT:
        raise ValueError('A-01 uses only the mechanism split')
    snrs = [int(s) for s in args.snrs]
    identities = _identities(args.start, args.stop, snrs)
    n_states = len(identities)
    replay = getattr(args, 'replay_manifest', None) is not None
    n_full = 0 if replay else n_states
    n_ce = E_PER_STATE * n_states
    n_terminal = T_PER_STATE * n_states
    if (args.max_full_calls != n_full or args.max_ce_calls != n_ce or
            args.max_terminal_calls != n_terminal):
        raise ValueError('A-01 F/E/T reservation must equal requested identities')
    if type(args.deadline_unix) is not int or args.deadline_unix <= int(time.time()):
        raise ValueError('future integer unix deadline required')
    estimated = n_states * PER_FULL_ESTIMATE_BYTES + 32 * 1024 ** 2
    if args.max_output_bytes < estimated:
        raise ValueError('output budget below A-01 snapshot estimate')
    load_d1_freeze(args.d1, args.d1_sha256)
    if recipe_by_id(RECIPE_ID)['id'] != RECIPE_ID:
        raise ValueError('A-01 recipe identity drifted')
    if len(ARMS) != 16:
        raise ValueError('A-01 requires 12 core arms plus 4 bridge arms')
    return dict(snrs=snrs, identities=identities, n_states=n_states, replay=replay,
                n_full=n_full, n_ce=n_ce,
                n_terminal=n_terminal, estimated=estimated)


def reserve_a01(out, contract):
    replay_sha = contract.get('replay_manifest_sha256')
    ledger = out.parent / (LEDGER_NAME + ('-matched-replay-v1' if replay_sha else ''))
    ledger.mkdir(exist_ok=True)
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        requested = _identities(contract['start'], contract['stop'], list(contract['snrs']))
        full_calls = 0 if replay_sha else len(requested)
        if (contract['max_full_calls'] != full_calls or
                contract['max_ce_calls'] != E_PER_STATE * len(requested) or
                contract['max_terminal_calls'] != T_PER_STATE * len(requested)):
            raise ValueError('invalid A-01 identity reservation')
        used = 0
        for path in ledger.glob('reservation-*.json'):
            row = json.loads(path.read_text())
            if (row.get('campaign_id') != CAMPAIGN_ID or row.get('stage') != STAGE or
                    'identities' not in row):
                raise ValueError('invalid shared A-01 reservation')
            prior = {tuple(item) for item in row['identities']}
            if replay_sha and row.get('replay_manifest_sha256') != replay_sha:
                raise ValueError('A-01 replay lineage changed within the shared ledger')
            if requested & prior:
                raise ValueError('A-01 block/snr already reserved')
            used += len(prior)
        if used + len(requested) > TOTAL_F:
            raise ValueError('cumulative A-01 768-state cap exceeded')
        key = hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger / f'reservation-{key}.json', dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, out=str(out.resolve()),
            max_full_calls=full_calls, max_ce_calls=E_PER_STATE * len(requested),
            max_terminal_calls=T_PER_STATE * len(requested),
            replay_manifest_sha256=replay_sha,
            calls_reserved={'F': full_calls, 'E': E_PER_STATE * len(requested),
                            'T': T_PER_STATE * len(requested)},
            identities=sorted(requested),
            policy='no retry; two metered preparations and 16 arms per state; only S0 bridge legal'))
    return str(ledger)


def output_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())




def development_contrasts(table, detectors, blocks, *, manifest):
    return analyze_development('A-01', table, detectors, blocks, manifest)


def _read_batch(batch, d1_sha256, detectors):
    batch = Path(batch)
    if (batch / 'batch-failure.json').exists():
        raise ValueError('failed A-01 batch present')
    summary = json.loads((batch / 'summary.json').read_text())
    contract = json.loads((batch / 'contract.json').read_text())
    if (summary.get('status') != 'complete' or summary.get('exitcode') != 0 or
            summary.get('failures')):
        raise ValueError('incomplete or failed A-01 batch')
    if (contract.get('d1_sha256') != d1_sha256 or contract.get('recipe_id') != RECIPE_ID or
            list(contract.get('arms', [])) != list(ARMS) or
            'EP10' in contract.get('detectors', [])):
        raise ValueError('A-01 batch binding mismatch')
    pair = tuple(contract['detectors'])
    if detectors is None:
        detectors = pair
    elif pair != detectors:
        raise ValueError('detector pair changed across A-01 batches')
    if summary['calls_completed'] != summary['calls_attempted']:
        raise ValueError('A-01 attempted/completed mismatch')
    cells = {}
    for path in batch.glob('cell-*.json'):
        row = json.loads(path.read_text())
        if (row.get('candidate_eligible') or row.get('deployable') or
                row.get('FER') not in (0, 1) or row.get('arm') not in ARMS):
            raise ValueError('invalid A-01 cell contract')
        if row['arm'] in BRIDGE_ARMS[:2] and not row.get('legal_flow_comparable'):
            raise ValueError('S0 bridge must be legal-flow comparable')
        if row['arm'] in CORE_ARMS and row.get('legal_flow_comparable'):
            raise ValueError('core A-01 arm must not be marked legal flow')
        key = (int(row['SNR']), f"{row['arm']}__{row['detector']}", int(row['block_id']))
        if key in cells:
            raise ValueError('duplicate A-01 cell')
        cells[key] = int(row['FER'])
    snapshots = list(batch.glob('snapshot-*.npz'))
    if snapshots:
        snap = snapshots[0]
    else:
        state = json.loads(next(batch.glob('cached-state-*.json')).read_text())
        from .supplement_a01_cache import checked_path
        snap = checked_path(state['source']['snapshot'])
    with np.load(snap) as arrays:
        fields = tuple(sorted(arrays.files))
    if 'x_soft' not in fields or 'support' not in fields:
        raise ValueError('A-01 snapshot omitted x_soft or support')
    completed = summary['calls_completed']
    return dict(detectors=detectors, F=completed['F'], E=completed['E'], T=completed['T'],
                cells=cells, snapshot_fields=fields,
                schema=contract.get('schema', 'legacy-v1'),
                replay_manifest_sha256=contract.get('replay_manifest_sha256'),
                core_changes=summary.get('unchanged_core_differences', []))


def harvest_run(run_root, *, contrast_manifest, d1_sha256=FROZEN_D1_SHA256):
    """Read completed A-01 batches. Not F_A confirmation."""
    root = Path(run_root)
    batches = sorted(p for p in root.glob('batch-*') if p.is_dir())
    if len(batches) != 16:
        raise ValueError('A-01 harvest requires 16 complete batches')
    detectors = None
    totals = {'F': 0, 'E': 0, 'T': 0}
    cells = {}
    snapshot_fields = None
    run_mode = None
    core_changes = []
    for batch in batches:
        row = _read_batch(batch, d1_sha256, detectors)
        mode = (row['schema'], row['replay_manifest_sha256'])
        if run_mode is not None and mode != run_mode:
            raise ValueError('A-01 run method or replay lineage changed across batches')
        run_mode = mode
        core_changes.extend(row['core_changes'])
        detectors = row['detectors']
        for key in totals:
            totals[key] += row[key]
        if snapshot_fields is None:
            snapshot_fields = row['snapshot_fields']
        elif row['snapshot_fields'] != snapshot_fields:
            raise ValueError('A-01 snapshot fields changed across batches')
        overlap = cells.keys() & row['cells'].keys()
        if overlap:
            raise ValueError('overlapping A-01 cell identities')
        cells.update(row['cells'])
    expected = dict(F=0 if run_mode[1] else TOTAL_F,
                    E=E_PER_STATE * TOTAL_F if run_mode[0] == 'supplement-a01-run-v2' else TOTAL_E,
                    T=TOTAL_T)
    if totals != expected:
        raise ValueError('A-01 harvest does not match the method-specific F/E/T contract')
    blocks = list(range(N_BLOCKS))
    table = development_table('A-01', cells, detectors, blocks)
    fer = {snr: {cell: float(sum(table[(snr, cell)]) / len(blocks))
                 for cell in {c for s, c in table if s == snr}}
           for snr in SNRS}
    return dict(
        schema='supplement-a01-harvest-v2',
        status='complete_development_not_confirmation',
        calls=totals, n_blocks=N_BLOCKS, snrs=list(SNRS), arms=list(ARMS),
        detectors=list(detectors), recipe_id=RECIPE_ID, d1_sha256=d1_sha256,
        snapshot_fields=list(snapshot_fields),
        snapshot_has_x_soft=True, snapshot_has_support=True,
        bridge_definition=('original_bounded_physical_search_once_on_S0'
                           if run_mode[0] == 'supplement-a01-run-v2' else 'legacy_same_data_ls_by_delay'),
        replay_manifest_sha256=run_mode[1], unchanged_core_differences=core_changes,
        fer_by_cell=fer, contrasts=development_contrasts(table, detectors, blocks, manifest=contrast_manifest),
        not_claims=list(FORBIDDEN_CLAIMS), rerun_16T=False,
        scope='A-01 development; truth-assisted factorial; not F_A confirmation')


def execute(args):
    args.out.mkdir(parents=True, exist_ok=False)
    previous = signal.getsignal(signal.SIGALRM)
    attempted = {'F': 0, 'E': 0, 'T': 0}
    completed = {'F': 0, 'E': 0, 'T': 0}
    failures = []
    records = []
    active = None
    command = [sys.executable, *sys.argv]
    written_bytes = 0
    solver_calls = dict(core_reference=0, legal_search=0, arm_refits=0)
    core_changes = []
    started = time.perf_counter()

    def publish(path, value):
        nonlocal written_bytes
        size = len(json.dumps(value, sort_keys=True, allow_nan=False).encode())
        if written_bytes + size > args.max_output_bytes - FAILURE_RESERVE_BYTES:
            raise OSError('output publication would exceed frozen storage budget')
        publish_json(path, value)
        written_bytes += path.stat().st_size

    def snapshot(path, arrays):
        nonlocal written_bytes
        upper = sum(int(np.asarray(a).nbytes * 1.05) + 4096 for a in arrays.values())
        if written_bytes + upper > args.max_output_bytes - FAILURE_RESERVE_BYTES:
            raise OSError('snapshot publication would exceed frozen storage budget')
        receipt = publish_snapshot(path, arrays)
        written_bytes += path.stat().st_size
        return receipt

    try:
        parsed = validate_args(args)
        d1, d1_sha = load_d1_freeze(args.d1, args.d1_sha256)
        detectors = detectors_from_d1(d1)
        if sha(args.checkpoint) != CHECKPOINT_HASH:
            raise ValueError('checkpoint mismatch')
        replay_manifest = None
        replay_index = {}
        if parsed['replay']:
            replay_manifest = load_manifest(args.replay_manifest,
                protocol_sha256=sha(args.protocol), d1_sha256=d1_sha,
                recipe_id=RECIPE_ID, checkpoint_sha256=sha(args.checkpoint))
            replay_index = {(r['block'], r['snr']): r for r in replay_manifest['frames']}
        torch.set_num_threads(1)
        device = torch.device(args.device)
        if device.type not in ('cpu', 'cuda') or (
                device.type == 'cuda' and not torch.cuda.is_available()):
            raise ValueError('requested device unavailable')
        if device.type == 'cuda':
            index = 0 if device.index is None else device.index
            torch.cuda.set_per_process_memory_fraction(GPU_FRACTION, index)

        def timeout(_signal, _frame):
            raise TimeoutError('A-01 batch deadline')

        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix - time.time())
        (args.out / 'code-cache').mkdir()
        code = build_code(cache_dir=args.out / 'code-cache')
        written_bytes = output_bytes(args.out)
        data = SupplementData(args.protocol, code)
        system = _make_config_a(1024, 2., 8, 10., 4.)
        contract = dict(
            schema='supplement-a01-run-v2',
            campaign_id=CAMPAIGN_ID, stage=STAGE, split=SPLIT,
            start=args.start, stop=args.stop, snrs=parsed['snrs'],
            recipe_id=RECIPE_ID, detectors=list(detectors), arms=list(ARMS),
            d1_sha256=d1_sha, device=str(device), gpu_allocator_fraction=GPU_FRACTION,
            max_full_calls=args.max_full_calls, max_ce_calls=args.max_ce_calls,
            max_terminal_calls=args.max_terminal_calls,
            calls_reserved={'F': args.max_full_calls, 'E': args.max_ce_calls,
                            'T': args.max_terminal_calls},
            source_sha256=sources(), checkpoint_sha256=sha(args.checkpoint),
            protocol_sha256=sha(args.protocol), deadline_unix=args.deadline_unix,
            max_output_bytes=args.max_output_bytes, command=command,
            replay_manifest_sha256=sha(args.replay_manifest) if replay_manifest else None,
            preparation_passes=PREPARATION_PASSES,
            bridge_definition='original_bounded_physical_search_once_on_S0',
            policy='two preparation E plus 16 arm E and 32 T; cached replay has zero F')
        contract['config_sha256'] = hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode()).hexdigest()
        contract['ledger'] = reserve_a01(args.out, contract)
        publish(args.out / 'contract.json', contract)
        receiver = None
        if not parsed['replay']:
            model = build_receiver(args.checkpoint, system, 1024, args.device,
                                   receiver_shell='direct40', active_cap=40)
            receiver = BaselineReceiver(model, code, RECIPE_ID, system=system)

        def fail(exc, identity):
            item = dict(status='failed', identity=identity, exception=type(exc).__name__,
                        message=str(exc), traceback=traceback.format_exc(), FER=None)
            path = args.out / f'failure-{len(failures):05d}.json'
            publish(path, item)
            failures.append(dict(path=str(path), sha256=sha(path), identity=identity))

        def charge(kind, meta):
            nonlocal active
            if time.time() >= args.deadline_unix:
                raise TimeoutError('deadline before A-01 call')
            key = {'CE': 'E', 'terminal': 'T', 'full': 'F'}[kind]
            cap = {'F': args.max_full_calls, 'E': args.max_ce_calls, 'T': args.max_terminal_calls}[key]
            if attempted[key] >= cap:
                raise RuntimeError('reserved ' + key + ' budget exhausted')
            attempted[key] += 1
            active = dict(meta, call_key=key, ordinal=attempted[key], started_unix=time.time())
            publish(args.out / f'started-{key}-{attempted[key]:06d}.json', active)

        for block in range(args.start, args.stop):
            for snr in parsed['snrs']:
                active = None
                if time.time() >= args.deadline_unix:
                    raise TimeoutError('A-01 budget/deadline exhausted')
                state_started = time.perf_counter()
                try:
                    frame = data.make_frame(system, SPLIT, block, snr)
                except (TimeoutError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    fail(exc, dict(block=block, snr=snr, full_call_started=False))
                    continue
                try:
                    old_cells = {}
                    if parsed['replay']:
                        source_state = replay_index[(block, snr)]
                        snap, proof, old_cells = read_state(source_state, frame, code)
                        publish(args.out / f'cached-state-{snr}-{block:06d}.json',
                            dict(block=block, snr=snr, source=source_state, **proof))
                    else:
                        charge('full', dict(block=block, snr=snr, recipe_id=RECIPE_ID))
                        result = receiver.run(frame.observed, audit=True)
                        snap = snapshot_from_result(frame, result)
                        snapshot(args.out / f'snapshot-{snr}-{block:06d}.npz', snap)
                        scores = score_errors(result, frame._truth)
                        publish(args.out / f'normal-full-{snr}-{block:06d}.json', json_value(dict(
                            schema='supplement-a01-full-v1', split=SPLIT, block_id=block, SNR=snr,
                            recipe_id=RECIPE_ID, support=np.asarray(result['support']).astype(int).tolist(),
                            truth_access_level='none', candidate_eligible=False, deployable=False,
                            **scores)))
                        completed['F'] += 1

                    def before_preparation(phase):
                        charge('CE', dict(block=block, snr=snr, phase=phase))

                    def after_preparation(_phase):
                        completed['E'] += 1

                    prep_started = time.perf_counter()
                    prepared = prepare_from_frame(frame, snap, system,
                        before_call=before_preparation, after_call=after_preparation)
                    preparation_seconds = time.perf_counter() - prep_started
                    if not prepared['geometry_frozen_before_data']:
                        raise AssertionError('A-01 geometry must freeze before data arms')
                    for name, count in prepared['preparation_solver_calls'].items():
                        solver_calls[name] += count
                    prep_arrays = {k: prepared[k] for k in ('I', 'S0', 'W_true', 'W_est', 'W_s0', 'reference_coefficients')}
                    prep_receipt = snapshot(args.out / f'geometry-{snr}-{block:06d}.npz', prep_arrays)
                    publish(args.out / f'geometry-{snr}-{block:06d}.json', json_value(dict(
                        block=block, snr=snr, bridge_definition=prepared['bridge_definition'],
                        legal_geometry=prepared['legal_geometry'],
                        solver_calls=prepared['preparation_solver_calls'],
                        seconds=preparation_seconds, snapshot=prep_receipt)))
                    order = list(ARMS)
                    campaign_rng(SPLIT, block, 'order').shuffle(order)
                    for arm in order:
                        charge('CE', dict(block=block, snr=snr, arm=arm))
                        fit_started = time.perf_counter()
                        fitted = fit_arm(prepared, system, arm)
                        fit_seconds = time.perf_counter() - fit_started
                        completed['E'] += 1
                        solver_calls['arm_refits'] += int(not (
                            fitted['spec']['constraint'] == 'hard' and fitted['basis'].size == 0))
                        diagnostic_started = time.perf_counter()
                        diagnostics, fit_arrays = fit_diagnostics(prepared, fitted, system)
                        diagnostic_seconds = time.perf_counter() - diagnostic_started
                        fit_receipt = snapshot(args.out / f'fit-{snr}-{block:06d}-{arm}.npz', fit_arrays)
                        publish(args.out / f'fit-{snr}-{block:06d}-{arm}.json', json_value(dict(
                            block=block, snr=snr, arm=arm, diagnostics=diagnostics,
                            solver=fitted['diagnostics'], fit_seconds=fit_seconds,
                            offline_diagnostic_seconds=diagnostic_seconds, snapshot=fit_receipt)))
                        for detector in detectors:
                            def before(kind, which, det, arm=arm):
                                if which != arm:
                                    raise AssertionError('arm mismatch')
                                charge(kind, dict(block=block, snr=snr, arm=arm, detector=det))
                            if device.type == 'cuda':
                                torch.cuda.synchronize(device)
                            terminal_started = time.perf_counter()
                            row = detect_arm(prepared, fitted, code, arm, detector,
                                             device=device, before_call=before)
                            if device.type == 'cuda':
                                torch.cuda.synchronize(device)
                            terminal_seconds = time.perf_counter() - terminal_started
                            calibration = terminal_diagnostics(row, snap)
                            terminal_arrays = {k: row[k] for k in ('llr', 'decoded', 'info_hat')}
                            terminal_receipt = snapshot(
                                args.out / f'terminal-{snr}-{block:06d}-{arm}-{detector}.npz', terminal_arrays)
                            old = old_cells.get(f'{arm}__{detector}')
                            regression = None if old is None else dict(
                                original_FER=old['FER'], original_info_errors=old['info_errors'],
                                unchanged=old['info_errors'] == row['info_errors'],
                                expected_unchanged=arm in CORE_ARMS)
                            if regression and arm in CORE_ARMS and not regression['unchanged']:
                                core_changes.append(dict(block=block, snr=snr, arm=arm,
                                    detector=detector, new_info_errors=row['info_errors'], **regression))
                            publish(args.out / f'cell-{snr}-{block:06d}-{arm}-{detector}.json',
                                    json_value(dict(schema='supplement-a01-cell-v2',
                                                    block_id=block, SNR=snr, arm=arm,
                                                    detector=detector, FER=row['FER'],
                                                    info_errors=row['info_errors'],
                                                    candidate_eligible=False, deployable=False,
                                                    legal_flow_comparable=row['legal_flow_comparable'],
                                                    truth_access_level=row['truth_access_level'],
                                                    terminal_seconds=terminal_seconds,
                                                    terminal_snapshot=terminal_receipt,
                                                    calibration=calibration, regression=regression)))
                            completed['T'] += 1
                    record = dict(block=block, snr=snr, I=prepared['I'].tolist(),
                                  elapsed_seconds=time.perf_counter() - state_started)
                    records.append(record)
                    print(json.dumps(dict(event='state-complete', **record)), flush=True)
                except (TimeoutError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    fail(exc, active or dict(block=block, snr=snr))
                    continue
                active = None
        signal.setitimer(signal.ITIMER_REAL, 0)
        status = 'completed_with_failures' if failures else 'complete'
        exitcode = 1 if failures else 0
        publish(args.out / 'summary.json', dict(
            status=status, exitcode=exitcode, calls_attempted=attempted,
            calls_completed=completed, records=records, failures=failures,
            command=command, detectors=list(detectors), recipe_id=RECIPE_ID,
            d1_sha256=d1_sha, gpu_allocator_fraction=GPU_FRACTION, arms=list(ARMS),
            replay_manifest_sha256=contract['replay_manifest_sha256'],
            preparation_solver_calls=solver_calls, unchanged_core_differences=core_changes,
            elapsed_seconds=time.perf_counter()-started, output_bytes_before_summary=written_bytes,
            scope='A-01 development; truth-assisted factorial; not confirmation'))
        return exitcode
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish_json(args.out / 'batch-failure.json', dict(
            status='failed', exception=type(exc).__name__, message=str(exc)[:16384],
            traceback=traceback.format_exc()[-32768:],
            calls_attempted=attempted, calls_completed=completed, active_attempt=active))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'checkpoint', 'out', 'd1'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--d1-sha256', required=True)
    p.add_argument('--split', required=True)
    p.add_argument('--start', type=int, required=True)
    p.add_argument('--stop', type=int, required=True)
    p.add_argument('--snrs', type=json.loads, required=True)
    p.add_argument('--deadline-unix', type=int, required=True)
    p.add_argument('--max-full-calls', type=int, required=True)
    p.add_argument('--max-ce-calls', type=int, required=True)
    p.add_argument('--max-terminal-calls', type=int, required=True)
    p.add_argument('--max-output-bytes', type=int, required=True)
    p.add_argument('--device', required=True)
    p.add_argument('--replay-manifest', type=Path,
                   help='Source-bound original A-01 states; disables full receiver calls')
    return execute(p.parse_args())


if __name__ == '__main__':
    sys.exit(main())
