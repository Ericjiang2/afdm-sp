"""S-01 single-factor counterexample development. Not robustness confirmation."""
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

from .budgeted_frame_store import publish_json
from .budgeted_support_eval import build_receiver
from .direction_receiver import CHECKPOINT_HASH
from .direction_run import json_value
from .direction_logging import publish_snapshot
from .direction_select import paired_interval
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver, recipe_by_id
from .supplement_data import CAMPAIGN_ID, LIMITS, SupplementData, campaign_rng
from .supplement_h01 import RECIPE_ID as BSTAR
from .supplement_profile import score_errors
from .supplement_run import sha, sources

STAGE = 'S-01'
RECIPE_ID = BSTAR
SPLIT = 'counterexample'
SNRS = (7, 8, 9)
N_BLOCKS = LIMITS['counterexample']
UNITS = (
    dict(id='integer', scenario='integer'),
    dict(id='overlap', scenario='overlap'),
    dict(id='P4', scenario='P4'),
    dict(id='P12', scenario='P12'),
    dict(id='rho25', scenario='rho25'),
    dict(id='rho75', scenario='rho75'),
)
UNIT_IDS = tuple(u['id'] for u in UNITS)
BLOCKED_UNITS = ('G1',)
TOTAL_F = N_BLOCKS * len(SNRS) * len(UNITS)
MAX_REPAIR_F = 192  # The original rho-entry failure and the failed cfg-entry repair.
LEDGER_NAME = 'supplement-s01-counterexample-ledger'
FAILURE_RESERVE_BYTES = 256 * 1024
PER_FULL_ESTIMATE_BYTES = 8 * 1024 ** 2
GPU_FRACTION = .30
N_BATCHES = 12
LEGACY_SET = 'legacy-six'
G1_SET = 'physical-g1'
FORBIDDEN_CLAIMS = (
    'robustness confirmed',
    'G1 executed',
    'true P given to receiver',
    'cartesian product',
    'F_R confirmation',
    'rerun 16T',
)
PRE_REGISTERED_CONTRASTS = (
    dict(id='integer-overlap', first='integer', second='overlap'),
    dict(id='P12-P4', first='P12', second='P4'),
    dict(id='rho75-rho25', first='rho75', second='rho25'),
)


def system_for(spec):
    system = spec.get('system') or {}
    cfg = _make_config_a(1024, float(system['v_mean']), int(system['P_paths']),
                         1000. * float(system['tau_spread']), 4.)
    cfg.rho = float(system['rho'])
    cfg.use_frac_doppler = bool(system['use_frac_doppler'])
    cfg.k_leak = int(system['k_leak'])
    cfg.frac_prune_rel_thres = float(system['frac_prune_rel_thres'])
    cfg.delay_collision = spec.get('delay_collision')
    return cfg


def unit_ids(unit_set):
    if unit_set == LEGACY_SET:
        return UNIT_IDS
    if unit_set == G1_SET:
        return ('G1',)
    raise ValueError('unknown S-01 unit set')


def _identities(start, stop, snrs, units=UNIT_IDS, *, unit_set=LEGACY_SET):
    if (not isinstance(snrs, list) or not snrs or any(s not in SNRS for s in snrs) or
            len(set(snrs)) != len(snrs)):
        raise ValueError('S-01 snrs must be a unique subset of 7/8/9')
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= N_BLOCKS:
        raise ValueError('S-01 blocks must lie in counterexample[0,192)')
    allowed = unit_ids(unit_set)
    if not units or any(u not in allowed for u in units) or len(set(units)) != len(units):
        raise ValueError('S-01 units must be the frozen ready set')
    if unit_set == LEGACY_SET and any(u in BLOCKED_UNITS for u in units):
        raise ValueError('G1 is blocked pending a numerical contract')
    return {(block, int(snr), unit) for block in range(start, stop)
            for snr in snrs for unit in units}


def validate_args(args):
    if args.split != SPLIT:
        raise ValueError('S-01 uses only the counterexample split')
    unit_set = getattr(args, 'unit_set', LEGACY_SET)
    units = unit_ids(unit_set)
    if unit_set == G1_SET and args.resume_failed_batch is not None:
        raise ValueError('G1 does not inherit the historical failed-cell retry allowance')
    snrs = [int(s) for s in args.snrs]
    identities = _identities(args.start, args.stop, snrs, units, unit_set=unit_set)
    recovery, reused = read_recovery(args, identities)
    n_full = len(identities) - len(reused)
    if args.max_full_calls != n_full:
        raise ValueError('S-01 F reservation must equal requested cells minus verified reuse')
    if type(args.deadline_unix) is not int or args.deadline_unix <= int(time.time()):
        raise ValueError('future integer unix deadline required')
    per_full = 64 * 1024**2 if unit_set == G1_SET else PER_FULL_ESTIMATE_BYTES
    estimated = n_full * per_full + 32 * 1024 ** 2
    if args.max_output_bytes < estimated:
        raise ValueError('output budget below S-01 estimate')
    if recipe_by_id(RECIPE_ID)['id'] != RECIPE_ID:
        raise ValueError('S-01 recipe identity drifted')
    return dict(snrs=snrs, identities=identities, n_full=n_full, estimated=estimated,
                recovery=recovery, reused=reused, unit_set=unit_set, units=units)


def read_recovery(args, identities):
    """Recover the two recorded entry failures without repeating successful cells."""
    if args.resume_failed_batch is None:
        return None, {}
    return _read_recovery_source(args, identities, args.resume_failed_batch)


def _read_recovery_source(args, identities, batch, depth=0):
    batch = Path(batch).resolve()
    if batch == args.out.resolve() or batch.parent != args.out.resolve().parent:
        raise ValueError('S-01 recovery must use a distinct batch in the same ledger root')
    contract = json.loads((batch / 'contract.json').read_text())
    summary = json.loads((batch / 'summary.json').read_text())
    if (contract.get('campaign_id') != CAMPAIGN_ID or contract.get('stage') != STAGE or
            contract.get('split') != SPLIT or contract.get('recipe_id') != RECIPE_ID or
            contract.get('protocol_sha256') != sha(args.protocol) or
            contract.get('checkpoint_sha256') != sha(args.checkpoint) or
            summary.get('status') != 'completed_with_failures' or summary.get('exitcode') != 1 or
            _identities(contract['start'], contract['stop'], list(contract['snrs'])) != identities):
        raise ValueError('S-01 recovery source contract/identity mismatch')
    previous = contract.get('recovery')
    prior_reused = {}
    if previous:
        if depth or previous.get('prior_recovery'):
            raise ValueError('S-01 recovery is bounded to the two recorded entry failures')
        rebuilt, prior_reused = _read_recovery_source(
            args, identities, previous['source_batch'], depth + 1)
        if (json.dumps(previous, sort_keys=True) != json.dumps(rebuilt, sort_keys=True) or
                previous != summary.get('recovery') or summary['calls_completed'] != 0):
            raise ValueError('S-01 failed recovery ancestry/content mismatch')
    if summary.get('calls_reused', 0) != len(prior_reused):
        raise ValueError('S-01 historical reuse count mismatch')
    failures = {}
    for entry in summary['failures']:
        path = batch / Path(entry['path']).name
        if sha(path) != entry['sha256']:
            raise ValueError('S-01 recovery failure hash mismatch')
        failure = json.loads(path.read_text())
        identity = failure['identity']
        key = (identity['block'], identity['snr'], identity['unit'])
        expected_error = ('UnboundLocalError', "local variable 'cfg' referenced before assignment") if previous else (
            'ValueError', 'constellation differs from frozen data power/order')
        if (key in failures or identity != entry['identity'] or key[2] not in ('rho25', 'rho75') or
                failure.get('FER') is not None or
                (failure.get('exception'), failure.get('message')) != expected_error):
            raise ValueError('S-01 recovery is limited to the recorded receiver entry failures')
        failures[key] = dict(path=str(path), sha256=sha(path))
    reused = {}
    records = {(r['block'], r['snr'], r['unit']): r['FER'] for r in summary['records']}
    for path in sorted(batch.glob('frame-*.json')):
        row = json.loads(path.read_text())
        key = (row['block_id'], row['SNR'], row['unit'])
        if (key in reused or key in failures or key not in records or records[key] != row['FER'] or
                row.get('rho') != .5 or key[2] in ('rho25', 'rho75') or
                row.get('recipe_id') != RECIPE_ID or row.get('split') != SPLIT or
                row.get('candidate_eligible') or row.get('deployable') or
                row.get('true_P_to_receiver') or row.get('FER') not in (0, 1)):
            raise ValueError('S-01 recovery successful record mismatch')
        if previous:
            source = prior_reused.get(key)
            if (source is None or row.get('reused_from') != dict(
                    path=source['path'], sha256=source['sha256']) or
                    {k: v for k, v in row.items() if k != 'reused_from'} != source['row']):
                raise ValueError('S-01 historical successful record provenance mismatch')
        elif row.get('reused_from'):
            raise ValueError('S-01 original batch declares unregistered reuse')
        reused[key] = dict(row=row, path=str(path), sha256=sha(path))
    if (not failures or set(reused) != set(records) or
            len(summary['records']) != len(reused) or
            set(reused) | set(failures) != identities or
            summary['calls_attempted'] != len(identities) - len(prior_reused) or
            summary['calls_completed'] + len(prior_reused) != len(reused)):
        raise ValueError('S-01 recovery does not cover the original attempted identities')
    manifest = dict(
        source_batch=str(batch), contract_sha256=sha(batch / 'contract.json'),
        summary_sha256=sha(batch / 'summary.json'),
        previous_attempted_F=summary['calls_attempted'] + (previous['previous_attempted_F'] if previous else 0),
        previous_completed_F=len(reused),
        previous_failed_F=len(failures) + (previous['previous_failed_F'] if previous else 0),
        failed_identities=sorted(failures),
        reused=[dict(identity=key, path=value['path'], sha256=value['sha256'])
                for key, value in sorted(reused.items())],
        failures=[dict(identity=key, **value) for key, value in sorted(failures.items())],
        policy='one source-bound repair; same cells; successful records reused; old failure retained')
    if previous:
        manifest['prior_recovery'] = previous
    return manifest, reused


def recovery_lineage(recovery):
    """At most the original rho failure and its cfg-entry failed repair."""
    rows = []
    while recovery:
        rows.append(recovery)
        if len(rows) > 2:
            raise ValueError('S-01 recovery history exceeds the frozen two-failure bound')
        recovery = recovery.get('prior_recovery')
    return rows


def reserve_s01(out, contract):
    ledger = out.parent / LEDGER_NAME
    ledger.mkdir(exist_ok=True)
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        unit_set = contract.get('unit_set', LEGACY_SET)
        requested = _identities(contract['start'], contract['stop'], list(contract['snrs']),
                                unit_ids(unit_set), unit_set=unit_set)
        recovery = contract.get('recovery')
        if unit_set == G1_SET and recovery:
            raise ValueError('G1 has no automatic retry allowance')
        reused = {tuple(r['identity']) for r in recovery['reused']} if recovery else set()
        requested -= reused
        if contract['max_full_calls'] != len(requested):
            raise ValueError('invalid S-01 identity reservation')
        used = 0
        retry_allowance = len(requested) if recovery else 0
        sources = {r['source_batch'] for r in recovery_lineage(recovery)}
        source_reserved = set()
        for path in ledger.glob('reservation-*.json'):
            row = json.loads(path.read_text())
            if row.get('campaign_id') != CAMPAIGN_ID or row.get('stage') != STAGE:
                raise ValueError('invalid shared S-01 reservation')
            if row.get('unit_set', LEGACY_SET) != unit_set:
                raise ValueError('S-01 unit sets require distinct run roots')
            prior = {tuple(item) for item in row['identities']}
            if requested & prior:
                if row['out'] in sources and requested <= prior:
                    source_reserved.add(row['out'])
                else:
                    raise ValueError('S-01 block/snr/unit already reserved')
            used += row['max_full_calls']
            retry_allowance += row.get('retry_failed_F', 0)
        if recovery and source_reserved != sources:
            raise ValueError('S-01 recovery requires the intact source reservation')
        total_f = N_BLOCKS * len(SNRS) if unit_set == G1_SET else TOTAL_F
        retry_cap = 0 if unit_set == G1_SET else MAX_REPAIR_F
        if retry_allowance > retry_cap or used + len(requested) > total_f + retry_allowance:
            raise ValueError('cumulative S-01 unique-cell plus recorded-failure cap exceeded')
        key = hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger / f'reservation-{key}.json', dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, out=str(out.resolve()),
            max_full_calls=len(requested), identities=sorted(requested),
            calls_reserved={'F': len(requested), 'T': 0, 'E': 0},
            reused_identities=sorted(reused), retry_failed_F=len(requested) if recovery else 0,
            recovery=recovery,
            unit_set=unit_set,
            policy=('physical G1 only; 576 unique F; no retry allowance' if unit_set == G1_SET else
                    'single-factor units; G1 blocked; only source-bound failed-cell recovery')))
    return str(ledger)


def output_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())


def contrast_registry():
    rows = [dict(spec, kind='scene') for spec in PRE_REGISTERED_CONTRASTS]
    if len(rows) != 3:
        raise ValueError('S-01 development contrast family must be 3')
    return rows


def development_contrasts(table, blocks):
    rows = []
    n = len(blocks)
    for snr in SNRS:
        for spec in contrast_registry():
            first = table[(snr, spec['first'])]
            second = table[(snr, spec['second'])]
            if len(first) != n or len(second) != n:
                raise ValueError('paired S-01 contrast length mismatch')
            detail = paired_interval(list(first), list(second), comparisons=3)
            rows.append(dict(spec, snr=snr, n=n, delta=detail['delta'],
                             interval=detail['interval'], wins=detail['wins'],
                             losses=detail['losses'],
                             scope='S-01 development; not F_R confirmation'))
    return rows


def _read_batch(batch, *, unit_set=LEGACY_SET):
    batch = Path(batch)
    if (batch / 'batch-failure.json').exists():
        raise ValueError('failed S-01 batch present')
    summary = json.loads((batch / 'summary.json').read_text())
    contract = json.loads((batch / 'contract.json').read_text())
    if (summary.get('status') != 'complete' or summary.get('exitcode') != 0 or
            summary.get('failures')):
        raise ValueError('incomplete or failed S-01 batch')
    units = unit_ids(unit_set)
    is_g1 = unit_set == G1_SET
    if (contract.get('recipe_id') != RECIPE_ID or
            list(contract.get('units', [])) != list(units) or
            contract.get('unit_set', LEGACY_SET) != unit_set or
            contract.get('split') != SPLIT or bool(contract.get('g1_executed')) != is_g1):
        raise ValueError('S-01 batch binding mismatch')
    if summary['calls_completed'] != summary['calls_attempted']:
        raise ValueError('S-01 attempted/completed mismatch')
    recovery = contract.get('recovery')
    if is_g1 and recovery:
        raise ValueError('G1 cannot reuse the historical repair lineage')
    if recovery != summary.get('recovery'):
        raise ValueError('S-01 recovery contract/summary mismatch')
    reused = {tuple(r['identity']): r for r in recovery['reused']} if recovery else {}
    if summary.get('calls_reused', 0) != len(reused):
        raise ValueError('S-01 reused count differs from the recovery manifest')
    for ancestor in recovery_lineage(recovery):
        original = Path(ancestor['source_batch'])
        for name in ('contract', 'summary'):
            if sha(original / f'{name}.json') != ancestor[f'{name}_sha256']:
                raise ValueError('S-01 recovery source changed before harvest')
        for failure in ancestor['failures']:
            if sha(failure['path']) != failure['sha256']:
                raise ValueError('S-01 recovery failure evidence changed')
        for source in ancestor['reused']:
            if sha(source['path']) != source['sha256']:
                raise ValueError('S-01 recovery successful source changed before harvest')
    cells = {}
    detail = []
    missing_input_hashes = 0
    for path in batch.glob('frame-*.json'):
        row = json.loads(path.read_text())
        if (row.get('candidate_eligible') or row.get('deployable') or
                row.get('FER') not in (0, 1) or row.get('unit') not in units or
                row.get('true_P_to_receiver') or (row.get('scenario') == 'G1') != is_g1):
            raise ValueError('invalid S-01 frame contract')
        key = (int(row['SNR']), row['unit'], int(row['block_id']))
        identity = (key[2], key[0], key[1])
        if key in cells:
            raise ValueError('duplicate S-01 frame')
        if identity in reused:
            source = reused[identity]
            reference = dict(path=source['path'], sha256=source['sha256'])
            if row.get('reused_from') != reference or sha(source['path']) != source['sha256']:
                raise ValueError('S-01 reused frame provenance mismatch')
            original_row = json.loads(Path(source['path']).read_text())
            if ({k: v for k, v in row.items() if k != 'reused_from'} !=
                    {k: v for k, v in original_row.items() if k != 'reused_from'}):
                raise ValueError('S-01 reused frame content changed')
        elif 'reused_from' in row:
            raise ValueError('S-01 frame declares unregistered reuse')
        if not row.get('input_hashes'):
            missing_input_hashes += 1
        if is_g1:
            from .supplement_g1 import audit_frame_evidence
            if row.get('frame_protocol_sha256') != contract['protocol_sha256']:
                raise ValueError('G1 frame protocol changed')
            audit_frame_evidence(row, batch)
            detail.append(row)
        cells[key] = int(row['FER'])
    expected = {(snr, unit, block) for block, snr, unit in _identities(
        contract['start'], contract['stop'], list(contract['snrs']), units, unit_set=unit_set)}
    if set(cells) != expected or len(cells) != summary['calls_completed'] + len(reused):
        raise ValueError('S-01 frame identities/counts differ from the batch contract')
    return dict(F=len(cells), attempted_F=summary['calls_attempted'],
                new_completed_F=summary['calls_completed'], reused_F=len(reused),
                previous_attempted_F=recovery['previous_attempted_F'] if recovery else 0,
                previous_failed_F=recovery['previous_failed_F'] if recovery else 0,
                missing_input_hashes=missing_input_hashes, cells=cells, detail=detail)


def harvest_run(run_root, *, unit_set=LEGACY_SET):
    """Read completed S-01 batches. Not F_R confirmation."""
    root = Path(run_root)
    units = unit_ids(unit_set)
    is_g1 = unit_set == G1_SET
    batches = sorted(p for p in root.glob('batch-*') if p.is_dir())
    all_batches = {p.resolve() for p in batches}
    superseded = set()
    for batch in batches:
        contract = json.loads((batch / 'contract.json').read_text())
        recovery = contract.get('recovery')
        if recovery:
            source = Path(recovery['source_batch']).resolve()
            if source not in all_batches or source == batch.resolve() or source in superseded:
                raise ValueError('S-01 recovery must replace one existing failed batch once')
            superseded.add(source)
    batches = [p for p in batches if p.resolve() not in superseded]
    if len(batches) != N_BATCHES:
        raise ValueError('S-01 harvest requires 12 complete batches')
    totals = {'F': 0}
    accounting = dict(attempted_F=0, failed_F=0, reused_F=0,
                      new_completed_F=0, unique_completed_F=0)
    missing_input_hashes = 0
    cells = {}
    detail = []
    g1_binding = None
    for batch in batches:
        row = _read_batch(batch, unit_set=unit_set)
        if is_g1:
            contract = json.loads((batch / 'contract.json').read_text())
            binding = {k: contract[k] for k in ('protocol_sha256', 'checkpoint_sha256', 'source_sha256')}
            if g1_binding is not None and g1_binding != binding:
                raise ValueError('G1 batches use different frozen inputs')
            g1_binding = binding
            detail.extend(row['detail'])
        totals['F'] += row['F']
        accounting['attempted_F'] += row['attempted_F'] + row['previous_attempted_F']
        accounting['failed_F'] += row['previous_failed_F']
        accounting['reused_F'] += row['reused_F']
        accounting['new_completed_F'] += row['new_completed_F']
        accounting['unique_completed_F'] += row['F']
        missing_input_hashes += row['missing_input_hashes']
        overlap = cells.keys() & row['cells'].keys()
        if overlap:
            raise ValueError('overlapping S-01 frame identities')
        cells.update(row['cells'])
    expected_f = N_BLOCKS * len(SNRS) if is_g1 else TOTAL_F
    if totals['F'] != expected_f:
        raise ValueError('S-01 harvest totals differ from the selected unit set')
    blocks = list(range(N_BLOCKS))
    table = {}
    for snr in SNRS:
        for unit in units:
            table[(snr, unit)] = [cells[(snr, unit, block)] for block in blocks]
    fer = {snr: {unit: float(sum(table[(snr, unit)]) / len(blocks))
                 for unit in units}
           for snr in SNRS}
    result = dict(
        schema='supplement-s01-harvest-v1',
        status='complete_development_not_confirmation',
        calls=totals, n_blocks=N_BLOCKS, snrs=list(SNRS), units=list(units), unit_set=unit_set,
        execution_accounting=accounting,
        superseded_failed_batches=sorted(str(p) for p in superseded),
        input_hashes_missing_from_original_records=missing_input_hashes,
        provenance_limitations=(['Legacy successful records lack producer-captured input hashes; '
                                 'their immutable records, source, protocol and seeds are retained.']
                                if missing_input_hashes else []),
        blocked_units=[] if is_g1 else list(BLOCKED_UNITS), recipe_id=RECIPE_ID, fer_by_cell=fer,
        contrasts=[] if is_g1 else development_contrasts(table, blocks),
        not_claims=[c for c in FORBIDDEN_CLAIMS if not is_g1 or c != 'G1 executed'],
        rerun_16T=False, g1_executed=is_g1,
        cartesian_product=False, true_P_to_receiver=False,
        scope='S-01 physical G1 development; not F_R confirmation' if is_g1 else
              'S-01 counterexample development; G1 blocked; not F_R confirmation')
    if is_g1:
        from .supplement_g1 import summarize_physical_records
        result['physical_model'] = summarize_physical_records(detail, blocks, SNRS)
        result['source_binding'] = g1_binding
    return result


def execute(args):
    args.out.mkdir(parents=True, exist_ok=False)
    previous = signal.getsignal(signal.SIGALRM)
    attempted = completed = 0
    failures = []
    records = []
    active = None
    command = [sys.executable, *sys.argv]

    def publish(path, value):
        size = len(json.dumps(value, sort_keys=True, allow_nan=False).encode())
        if output_bytes(args.out) + size > args.max_output_bytes - FAILURE_RESERVE_BYTES:
            raise OSError('output publication would exceed frozen storage budget')
        publish_json(path, value)

    try:
        parsed = validate_args(args)
        if sha(args.checkpoint) != CHECKPOINT_HASH:
            raise ValueError('checkpoint mismatch')
        torch.set_num_threads(1)
        device = torch.device(args.device)
        if device.type not in ('cpu', 'cuda') or (
                device.type == 'cuda' and not torch.cuda.is_available()):
            raise ValueError('requested device unavailable')
        if device.type == 'cuda':
            index = 0 if device.index is None else device.index
            torch.cuda.set_per_process_memory_fraction(GPU_FRACTION, index)

        def timeout(_s, _f):
            raise TimeoutError('S-01 batch deadline')

        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix - time.time())
        (args.out / 'code-cache').mkdir()
        code = build_code(cache_dir=args.out / 'code-cache')
        data = SupplementData(args.protocol, code)
        is_g1 = parsed['unit_set'] == G1_SET
        units = [dict(id=name, scenario=name) for name in parsed['units']]
        missing = [name for name in (*UNIT_IDS, *BLOCKED_UNITS) if name not in data.protocol['scenarios']]
        if missing:
            raise ValueError('S-01 protocol missing scenarios')
        if not is_g1 and data.protocol['scenarios']['G1'].get('admitted') is not False:
            raise ValueError('G1 must remain unadmitted')
        systems = {unit['id']: system_for(data.protocol['scenarios'][unit['scenario']])
                   for unit in units}
        if is_g1:
            data.validate_g1(systems['G1'], data.protocol['scenarios']['G1'])
        contract = dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, split=SPLIT,
            start=args.start, stop=args.stop, snrs=parsed['snrs'],
            recipe_id=RECIPE_ID, units=list(parsed['units']), unit_set=parsed['unit_set'],
            blocked_units=[] if is_g1 else list(BLOCKED_UNITS),
            device=str(device), gpu_allocator_fraction=GPU_FRACTION,
            max_full_calls=args.max_full_calls,
            calls_reserved={'F': args.max_full_calls, 'T': 0, 'E': 0},
            source_sha256=sources(), checkpoint_sha256=sha(args.checkpoint),
            protocol_sha256=sha(args.protocol), deadline_unix=args.deadline_unix,
            max_output_bytes=args.max_output_bytes, command=command,
            recovery=parsed['recovery'],
            g1_executed=is_g1, cartesian_product=False, true_P_to_receiver=False,
            policy='single-factor units; receiver nomination frozen; explicit physical G1 admission')
        contract['config_sha256'] = hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode()).hexdigest()
        contract['ledger'] = reserve_s01(args.out, contract)
        publish(args.out / 'contract.json', contract)
        models = {}
        receivers = {}
        active_units = {unit for block, snr, unit in parsed['identities'] - parsed['reused'].keys()}
        for unit in units:
            if unit['id'] not in active_units:
                continue
            scenario_system = systems[unit['id']]
            rho = float(scenario_system.rho)
            if rho not in models:
                models[rho] = build_receiver(args.checkpoint, scenario_system, 1024, args.device,
                                             receiver_shell='direct40', active_cap=40)
            receivers[unit['id']] = BaselineReceiver(
                models[rho], code, RECIPE_ID, system=scenario_system)

        def fail(exc, identity):
            item = dict(status='failed', identity=identity, exception=type(exc).__name__,
                        message=str(exc), traceback=traceback.format_exc(), FER=None)
            path = args.out / f'failure-{len(failures):05d}.json'
            publish(path, item)
            failures.append(dict(path=str(path), sha256=sha(path), identity=identity))

        for block in range(args.start, args.stop):
            order = list(units)
            campaign_rng(SPLIT, block, 'order').shuffle(order)
            for snr in parsed['snrs']:
                for unit in order:
                    identity = (block, int(snr), unit['id'])
                    cached = parsed['reused'].get(identity)
                    if cached is not None:
                        if sha(cached['path']) != cached['sha256']:
                            raise ValueError('S-01 recovery source changed after validation')
                        row = dict(cached['row'], reused_from={
                            'path': cached['path'], 'sha256': cached['sha256']})
                        publish(args.out / f'frame-{unit["id"]}-{snr}-{block:03d}.json', row)
                        records.append(dict(block=block, snr=snr, unit=unit['id'], FER=row['FER']))
                        continue
                    if attempted >= args.max_full_calls or time.time() >= args.deadline_unix:
                        raise TimeoutError('S-01 budget/deadline exhausted')
                    attempted += 1
                    active = dict(block=block, snr=snr, unit=unit['id'],
                                  full_call_started=True, started_unix=time.time())
                    publish(args.out / f'call-F-{attempted:05d}-started.json', active)
                    try:
                        frame = data.make_frame(systems[unit['id']], SPLIT, block, snr,
                                                scenario=unit['scenario'])
                        if not is_g1 and frame.metadata.get('scenario') in BLOCKED_UNITS:
                            raise AssertionError('G1 frame generated')
                        if int(systems[unit['id']].P_paths) != int(
                                data.protocol['scenarios'][unit['scenario']]['system']['P_paths']):
                            raise AssertionError('true P leaked into a different system')
                        receiver_started = time.perf_counter()
                        result = receivers[unit['id']].run(frame.observed, audit=True)
                        receiver_seconds = time.perf_counter() - receiver_started
                        scores = score_errors(result, frame._truth)
                        params = frame._truth.get('params') or {}
                        row = dict(schema='supplement-s01-frame-v1', split=SPLIT,
                                   block_id=block, SNR=snr, unit=unit['id'],
                                   scenario=unit['scenario'], recipe_id=RECIPE_ID,
                                   P_paths=int(systems[unit['id']].P_paths),
                                   P_actual=params.get('P_actual'),
                                   use_frac_doppler=bool(systems[unit['id']].use_frac_doppler),
                                   delay_collision=systems[unit['id']].delay_collision,
                                   rho=float(systems[unit['id']].rho),
                                   input_hashes=frame.metadata['input_hashes'],
                                   frame_protocol_sha256=frame.metadata['protocol_sha256'],
                                   true_P_to_receiver=False, candidate_eligible=False,
                                   deployable=False, **scores)
                        if is_g1:
                            from .supplement_g1 import evidence_arrays
                            arrays = evidence_arrays(frame, result)
                            remaining = args.max_output_bytes - output_bytes(args.out) - FAILURE_RESERVE_BYTES
                            if sum(a.nbytes for a in arrays.values()) + 1024**2 > remaining:
                                raise OSError('G1 raw evidence would exceed storage budget')
                            snapshot = args.out / f'raw-G1-{snr}-{block:03d}.npz'
                            row.update(physical_model=frame.metadata['physical_model'],
                                raw_evidence=publish_snapshot(snapshot, arrays),
                                receiver_seconds=receiver_seconds,
                                timing_scope='instrumented development receiver; not COST-02',
                                capacity_trace=result['capacity_trace'])
                        publish(args.out / f'frame-{unit["id"]}-{snr}-{block:03d}.json',
                                json_value(row))
                        completed += 1
                        records.append(dict(block=block, snr=snr, unit=unit['id'], FER=row['FER']))
                    except (TimeoutError, KeyboardInterrupt):
                        raise
                    except Exception as exc:
                        fail(exc, active)
                        continue
                    active = None
        signal.setitimer(signal.ITIMER_REAL, 0)
        status = 'completed_with_failures' if failures else 'complete'
        publish(args.out / 'summary.json', dict(
            status=status, exitcode=1 if failures else 0,
            calls_attempted=attempted, calls_completed=completed,
            calls_reused=len(parsed['reused']), recovery=parsed['recovery'],
            records=records, failures=failures, command=command,
            recipe_id=RECIPE_ID, units=list(parsed['units']), g1_executed=is_g1,
            gpu_allocator_fraction=GPU_FRACTION,
            scope='S-01 development; not confirmation'))
        return 1 if failures else 0
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
    for name in ('protocol', 'checkpoint', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--split', required=True)
    p.add_argument('--start', type=int, required=True)
    p.add_argument('--stop', type=int, required=True)
    p.add_argument('--snrs', type=json.loads, required=True)
    p.add_argument('--deadline-unix', type=int, required=True)
    p.add_argument('--max-full-calls', type=int, required=True)
    p.add_argument('--max-output-bytes', type=int, required=True)
    p.add_argument('--device', required=True)
    p.add_argument('--resume-failed-batch', type=Path)
    p.add_argument('--unit-set', choices=(LEGACY_SET, G1_SET), default=LEGACY_SET)
    return execute(p.parse_args())


if __name__ == '__main__':
    sys.exit(main())
