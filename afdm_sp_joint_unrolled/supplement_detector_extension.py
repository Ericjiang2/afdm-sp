"""Validation and immutable accounting for the approved DET-01 BP extension."""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

from .budgeted_frame_store import publish_json
from .supplement_baseline_select import read_json
from .supplement_data import CAMPAIGN_ID

ADDITIONAL_IDS = ('BP80', 'BP160')
STAGES = ('additional-qualification', 'additional-development')
QUALIFICATION_T = 16
DEVELOPMENT_T = 384
TOTAL_T = 400
OUTPUT_CAP = 1024**3
WALL_SECONDS = 3600
ALLOCATION_SCHEMA = 'supplement-detector-additional-allocation-v1'
DET01R_ALLOCATION_SCHEMA = 'supplement-detector-det01r-allocation-v1'
ADMISSION_SCHEMA = 'supplement-detector-additional-stage-admission-v1'
RESERVATION_SCHEMA = 'supplement-detector-additional-reservation-v1'
DET01R_PROTOCOL = 'DET-01R-v1'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _reference(value, label, *, structured=True):
    if not isinstance(value, dict):
        raise ValueError(label + ' reference missing')
    path = Path(value.get('path', ''))
    if not path.is_absolute() or not path.is_file():
        raise ValueError(label + ' needs an existing absolute path')
    path = path.resolve()
    digest = value.get('sha256')
    if not isinstance(digest, str) or _sha(path) != digest:
        raise ValueError(label + ' reference changed')
    body = read_json(path, digest)[0] if structured else None
    return path, digest, body


def validate_allocation(path, expected_sha, source_manifest):
    allocation, digest = read_json(path, expected_sha)
    if allocation.get('schema') == DET01R_ALLOCATION_SCHEMA:
        return validate_det01r_allocation(path, expected_sha, source_manifest)
    fixed = {
        'schema': ALLOCATION_SCHEMA,
        'status': 'allocated_not_runtime_admission',
        'campaign_id': CAMPAIGN_ID,
        'issue': 'DET-01',
        'candidates': list(ADDITIONAL_IDS),
        'qualification_T': QUALIFICATION_T,
        'development_T': DEVELOPMENT_T,
        'total_T_cap': TOTAL_T,
        'hard_wall_seconds': WALL_SECONDS,
        'output_cap_bytes': OUTPUT_CAP,
        'new_F': 0, 'new_E': 0,
        'training': False, 'confirmation_access': False,
        'source_manifest': source_manifest,
    }
    if any(type(allocation.get(key)) is not type(value) or allocation[key] != value
           for key, value in fixed.items()):
        raise ValueError('additional allocation differs from approved scope')
    deadline = allocation.get('deadline_unix')
    admitted = allocation.get('admitted_unix')
    if (type(deadline) not in (int, float) or not math.isfinite(deadline) or
            type(admitted) not in (int, float) or not math.isfinite(admitted) or
            not 0 < deadline-admitted <= WALL_SECONDS):
        raise ValueError('additional allocation needs one bounded common deadline')
    if not isinstance(allocation.get('run_root'), str) or not Path(allocation['run_root']).is_absolute():
        raise ValueError('additional allocation needs one absolute run root')
    references = allocation.get('references')
    required = ('approval', 'budget_transfer', 'proposal', 'residual_contract',
                'original_qualification_admission',
                'original_development_admission')
    if not isinstance(references, dict) or set(references) != set(required):
        raise ValueError('additional allocation reference set differs')
    bound = {str(Path(path).resolve()): digest}
    bodies = {}
    for name in required:
        ref_path, ref_sha, body = _reference(
            references[name], name, structured=name not in ('proposal', 'residual_contract'))
        bound[str(ref_path)] = ref_sha
        bodies[name] = body
    approval = bodies['approval']
    transfer = bodies['budget_transfer']
    if (approval.get('status') !=
            'USER_APPROVED_SCOPE_AMENDMENT_IMPLEMENTATION_NOT_RUNTIME_ADMISSION' or
            approval.get('candidates') != list(ADDITIONAL_IDS) or
            approval.get('qualification_calls_T') != QUALIFICATION_T or
            approval.get('development_calls_T') != DEVELOPMENT_T or
            approval.get('total_T_cap') != TOTAL_T or
            approval.get('new_F') != 0 or approval.get('new_E') != 0 or
            approval.get('training') is not False or
            approval.get('confirmation_access') is not False):
        raise ValueError('user approval does not authorize additional allocation')
    if (transfer.get('status') != 'APPROVED_ALLOCATION_DESIGN_NOT_RUNTIME_ADMISSION' or
            transfer.get('approval_sha256') != allocation['references']['approval']['sha256'] or
            transfer.get('original_T') != 512 or transfer.get('replacement_T') != 512 or
            transfer.get('incremental_total_T') != 0 or
            transfer.get('replacement_units') != [
                {'stage':'DET-01-additional-qualification','T':16},
                {'stage':'DET-01-additional-development','T':384},
                {'stage':'DET-01-stability-probes-retained','T':112}]):
        raise ValueError('budget transfer does not preserve the approved 512T total')
    allocation['_sha256'] = digest
    allocation['_path'] = str(Path(path).resolve())
    allocation['_bound_files'] = bound
    allocation['_bodies'] = bodies
    return allocation


def validate_det01r_allocation(path, expected_sha, source_manifest):
    """Development-only successor allocation. Does not rerun or rewrite 16T."""
    allocation, digest = read_json(path, expected_sha)
    fixed = {
        'schema': DET01R_ALLOCATION_SCHEMA,
        'status': 'allocated_not_runtime_admission',
        'protocol': DET01R_PROTOCOL,
        'campaign_id': CAMPAIGN_ID,
        'issue': 'DET-01R',
        'candidates': list(ADDITIONAL_IDS),
        'qualification_T': 0,
        'development_T': DEVELOPMENT_T,
        'total_T_cap': DEVELOPMENT_T,
        'prior_qualification_T_charged': QUALIFICATION_T,
        'hard_wall_seconds': WALL_SECONDS,
        'output_cap_bytes': OUTPUT_CAP,
        'new_F': 0, 'new_E': 0,
        'training': False, 'confirmation_access': False,
        'rerun_16T': False, 'rewrite_16T_bytes': False,
        'source_manifest': source_manifest,
    }
    if any(type(allocation.get(key)) is not type(value) or allocation[key] != value
           for key, value in fixed.items()):
        raise ValueError('DET-01R allocation differs from amended scope')
    deadline = allocation.get('deadline_unix')
    admitted = allocation.get('admitted_unix')
    if (type(deadline) not in (int, float) or not math.isfinite(deadline) or
            type(admitted) not in (int, float) or not math.isfinite(admitted) or
            not 0 < deadline - admitted <= WALL_SECONDS):
        raise ValueError('DET-01R allocation needs one bounded common deadline')
    if not isinstance(allocation.get('run_root'), str) or not Path(allocation['run_root']).is_absolute():
        raise ValueError('DET-01R allocation needs one absolute run root')
    references = allocation.get('references')
    required = ('protocol_amendment', 'execution_split', 'dual_status', 'selection_freeze',
                'historical_qualification', 'historical_contract', 'predecessor_allocation',
                'original_qualification_admission', 'original_development_admission')
    if not isinstance(references, dict) or set(references) != set(required):
        raise ValueError('DET-01R allocation reference set differs')
    bound = {str(Path(path).resolve()): digest}
    bodies = {}
    for name in required:
        ref_path, ref_sha, body = _reference(
            references[name], name, structured=name != 'protocol_amendment')
        bound[str(ref_path)] = ref_sha
        bodies[name] = body
    dual = bodies['dual_status']
    split = bodies['execution_split']
    selection = bodies['selection_freeze']
    if (dual.get('historical_frozen_verifier_status') != 'FAIL' or
            dual.get('corrected_revalidation_status') != 'PASS' or
            dual.get('rerun_performed') is not False or
            dual.get('qualification_bytes_modified') is not False or
            dual.get('do_not_rewrite_v2_verifier_as_pass') is not True):
        raise ValueError('DET-01R dual status does not preserve frozen-verifier failure')
    if (split.get('only_changed_file') != 'supplement_detectors.py' or
            split.get('only_changed_functions') != ['qualification_pair'] or
            split.get('identical_execution_functions') is not True):
        raise ValueError('DET-01R execution closure is not verifier-only')
    if (selection.get('status') != 'frozen_before_384T_and_before_any_BP_development_result' or
            selection.get('h01_may_start_only_after_d1_freeze') is not True or
            'BP80' not in selection.get('candidate_set', []) or
            'BP160' not in selection.get('candidate_set', [])):
        raise ValueError('DET-01R selection rule is not prospectively frozen')
    predecessor = bodies['predecessor_allocation']
    if predecessor.get('schema') != ALLOCATION_SCHEMA:
        raise ValueError('DET-01R predecessor is not the closed DET-01 allocation')
    allocation['_sha256'] = digest
    allocation['_path'] = str(Path(path).resolve())
    allocation['_bound_files'] = bound
    allocation['_bodies'] = bodies
    return allocation


def validate_stage_admission(args, allocation, caches, *, require_live=True):
    if args.stage not in STAGES:
        raise ValueError('unknown additional detector stage')
    admission, admission_sha = read_json(args.admission)
    if (not isinstance(caches, list) or not caches or
            type(args.max_terminal_calls) is not int or type(args.max_output_bytes) is not int):
        raise ValueError('explicit caches and integer resource limits required')
    calls = QUALIFICATION_T if args.stage == STAGES[0] else len(caches)*len(ADDITIONAL_IDS)
    expected = {
        'schema': ADMISSION_SCHEMA, 'status': 'admitted',
        'campaign_id': CAMPAIGN_ID, 'stage': args.stage,
        'allocation_path': allocation['_path'],
        'allocation_sha256': allocation['_sha256'],
        'caches': caches, 'detectors': list(ADDITIONAL_IDS),
        'calls': {'F':0, 'T':calls, 'E':0},
        'deadline_unix': allocation['deadline_unix'],
        'max_output_bytes': OUTPUT_CAP,
        'ledger_path': str(Path(allocation['run_root']).resolve() /
                           'supplement-detector-additional-ledger'),
    }
    if any(admission.get(key) != value for key, value in expected.items()):
        raise ValueError('additional stage admission is not bound to this request')
    if args.deadline_unix != allocation['deadline_unix'] or (require_live and time_expired(args.deadline_unix)):
        raise TimeoutError('additional allocation common deadline expired')
    if args.max_output_bytes != OUTPUT_CAP or args.max_terminal_calls != calls:
        raise ValueError('additional stage finite resource bounds differ')
    root = Path(allocation['run_root']).resolve()
    if Path(args.out).resolve() == root or not Path(args.out).resolve().is_relative_to(root):
        raise ValueError('additional output escapes its one-GiB run root')
    allocation['_bound_files'][str(Path(args.admission).resolve())] = admission_sha
    return admission


def time_expired(deadline):
    import time
    return time.time() >= deadline


def identities(stage, blocks):
    blocks = list(blocks)
    if stage not in STAGES or any(type(block) is not int for block in blocks):
        raise ValueError('invalid additional identity stage or block type')
    if stage == STAGES[0] and blocks != list(range(4)):
        raise ValueError('qualification requires all four original engineering blocks')
    if stage == STAGES[1] and (
            not 1 <= len(blocks) <= 16 or not 0 <= blocks[0] <= blocks[-1] < 192 or
            blocks != list(range(blocks[0], blocks[-1] + 1))):
        raise ValueError('development requires contiguous 1..16 blocks within 0..192')
    doubled = (False, True) if stage == STAGES[0] else (False,)
    return [[stage, block, detector, repeat]
            for block in blocks for detector in ADDITIONAL_IDS
            for repeat in doubled]


def reserve(ledger, out, allocation, stage, blocks, source_sha256):
    ledger = Path(ledger).resolve()
    root = Path(allocation['run_root']).resolve()
    if ledger != root / 'supplement-detector-additional-ledger':
        raise ValueError('additional reservation must use its canonical ledger')
    if Path(out).resolve() == root or not Path(out).resolve().is_relative_to(root):
        raise ValueError('additional reservation output escapes run root')
    if time_expired(allocation['deadline_unix']):
        raise TimeoutError('additional allocation common deadline expired')
    ledger.mkdir(parents=True, exist_ok=True)
    requested = identities(stage, blocks)
    requested_keys = {tuple(row) for row in requested}
    if len(requested_keys) != len(requested):
        raise ValueError('duplicate additional detector identities')
    with (ledger/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for contract_path in root.glob('*/contract.json'):
            prior = json.loads(contract_path.read_text())
            if prior.get('stage') not in STAGES:
                continue
            reservation = prior.get('ledger', {})
            reservation_path = Path(reservation.get('path', '')).resolve()
            if (reservation_path.parent != ledger or not reservation_path.is_file() or
                    _sha(reservation_path) != reservation.get('sha256')):
                raise ValueError('previous additional contract lost or changed its reservation')
        used = set()
        for path in ledger.glob('reservation-*.json'):
            old = json.loads(path.read_text())
            rows = old.get('identities')
            if (old.get('schema') != RESERVATION_SCHEMA or
                    old.get('campaign_id') != CAMPAIGN_ID or
                    old.get('allocation_sha256') != allocation['_sha256'] or
                    old.get('source_sha256') != source_sha256 or
                    not isinstance(rows, list) or
                    old.get('T') != len(rows)):
                raise ValueError('invalid existing additional reservation')
            if any(not isinstance(row, list) or len(row) != 4 or
                   type(row[1]) is not int or type(row[3]) is not bool for row in rows):
                raise ValueError('invalid existing additional identity')
            keys = {tuple(row) for row in rows}
            expected = identities(old.get('stage'), sorted({row[1] for row in rows}))
            if len(keys) != len(rows) or keys & used or rows != expected:
                raise ValueError('forged or overlapping additional reservation')
            previous_out = Path(old.get('out', '')).resolve()
            expected_name = 'reservation-' + hashlib.sha256(str(previous_out).encode()).hexdigest() + '.json'
            if path.name != expected_name or previous_out == root or not previous_out.is_relative_to(root):
                raise ValueError('additional reservation output binding differs')
            used.update(keys)
        if requested_keys & used:
            raise ValueError('additional detector identity already charged; no retry')
        if len(used | requested_keys) > TOTAL_T:
            raise ValueError('additional detector 400T cap exceeded')
        key = hashlib.sha256(str(Path(out).resolve()).encode()).hexdigest()
        target = ledger/f'reservation-{key}.json'
        if target.exists():
            raise ValueError('additional reservation output already exists')
        value = {'schema':RESERVATION_SCHEMA, 'campaign_id':CAMPAIGN_ID,
            'allocation_sha256':allocation['_sha256'], 'source_sha256':source_sha256,
            'stage':stage, 'identities':requested, 'T':len(requested),
            'out':str(Path(out).resolve()),
            'policy':'immutable; failed and unused calls remain charged; no retry'}
        publish_json(target, value)
    return {'path':str(target), 'sha256':_sha(target), 'T':len(requested)}


@contextmanager
def execution_lock(allocation):
    root = Path(allocation['run_root']).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def output_bytes(run_root):
    return sum(path.stat().st_size for path in Path(run_root).rglob('*')
               if path.is_file())


def unchanged(allocation, source_manifest):
    if source_manifest != allocation['source_manifest']:
        raise ValueError('additional detector source changed')
    if any(_sha(path) != digest
           for path, digest in allocation['_bound_files'].items()):
        raise ValueError('additional detector bound evidence changed')


def prepare(args, caches, ids, source_manifest):
    """Reuse original replay authorization for the same engineering/design caches."""
    from .supplement_detector_run import validate_request
    from .supplement_detector_development import validate_development
    from .supplement_detectors import catalogue

    if (ids != list(ADDITIONAL_IDS) or args.device != 'cuda' or
            not getattr(args, 'allocation', None) or
            not getattr(args, 'allocation_sha256', None)):
        raise ValueError('additional detectors require explicit bound allocation and CUDA')
    allocation = validate_allocation(args.allocation, args.allocation_sha256, source_manifest)
    admission = validate_stage_admission(args, allocation, caches)
    old_ids = [row['id'] for row in catalogue()]
    development = None
    original = allocation['_bodies']['original_development_admission']
    qualification_ref = original.get('qualification')
    _, _, previous = _reference(qualification_ref, 'original qualification result')
    if (previous.get('stage') != 'qualification' or previous.get('calls_attempted') != 64 or
            previous.get('failures') or set(previous.get('qualified_by_detector', {})) != set(old_ids)):
        raise ValueError('original qualification outcome must remain bound')
    allocation['_bound_files'][qualification_ref['path']] = qualification_ref['sha256']
    if args.stage == STAGES[0]:
        original = allocation['_bodies']['original_qualification_admission']
        if len(caches) != 4 or caches != original.get('caches'):
            raise ValueError('additional qualification must retain original four caches')
        old = SimpleNamespace(**vars(args))
        old.stage = 'qualification'
        old.admission = allocation['references']['original_qualification_admission']['path']
        old.max_terminal_calls = 64
        validate_request(old, caches, old_ids)
        quote = original['completed_quote']
        allocation['_bound_files'][quote['path']] = quote['sha256']
        quote_contract = Path(quote['path']).parent / 'contract.json'
        allocation['_bound_files'][str(quote_contract)] = _sha(quote_contract)
    else:
        old = SimpleNamespace(**vars(args))
        old.stage = 'development'
        old.admission = allocation['references']['original_development_admission']['path']
        old.max_terminal_calls = len(caches) * len(old_ids)
        validate_request(old, caches, old_ids)
        development = validate_development(old, caches, old_ids)
        if allocation.get('protocol') == DET01R_PROTOCOL:
            qualified, records = verify_historical_qualification(
                admission.get('qualification'), allocation)
        else:
            qualified, records = verify_qualification(
                admission.get('qualification'), allocation)
        development['qualified_by_detector'] = qualified
        development['historical_frozen_verifier_status'] = (
            allocation['_bodies'].get('dual_status', {}).get(
                'historical_frozen_verifier_status') if allocation.get('protocol') == DET01R_PROTOCOL else None)
        for ref in (development['selection'], development['qualification']):
            allocation['_bound_files'][ref['path']] = ref['sha256']
        # All batches share the original clock; later batches cannot reset it.
        if max(row['seconds'] for row in records) * args.max_terminal_calls > (
                allocation['deadline_unix'] - __import__('time').time()):
            raise ValueError('measured qualification cost exceeds remaining batch time')
        if allocation.get('protocol') == DET01R_PROTOCOL:
            projection = qualification_resources(records, allocation)
            if projection.get('development_resources_fit') is not True:
                raise ValueError('full384T measured resource projection required')
        else:
            projection = admission.get('resource_projection')
            if not isinstance(projection, dict) or projection.get('development_resources_fit') is not True:
                raise ValueError('full384T measured resource projection required')
            if projection != read_json(admission['qualification']['path'])[0].get('resource_projection'):
                raise ValueError('resource projection differs from completed qualification')
    return {'allocation': allocation, 'admission': admission, 'development': development}


def verify_qualification(reference, allocation):
    """Recompute qualification from saved messages, not a stored PASS flag."""
    import numpy as np
    from .supplement_baseline_select import config_hash
    from .supplement_detectors import qualification_pair
    from .supplement_detector_run import qualification_summary, load_cache

    path, digest, summary = _reference(reference, 'additional qualification')
    root = path.parent
    run_root = Path(allocation['run_root']).resolve()
    if root == run_root or not root.is_relative_to(run_root):
        raise ValueError('qualification output escapes allocation root')
    contract_path = root / 'contract.json'
    contract, contract_sha = read_json(contract_path)
    if (summary.get('stage') != STAGES[0] or summary.get('calls_attempted') != 16 or
            len(summary.get('records', [])) != 16 or summary.get('failures') or
            summary.get('status') not in ('complete', 'completed_unqualified') or
            contract.get('config_sha256') != config_hash(contract) or
            summary.get('config_sha256') != contract['config_sha256'] or
            contract.get('stage') != STAGES[0] or
            contract.get('source_sha256') != allocation['source_manifest'] or
            contract.get('allocation_sha256') != allocation['_sha256'] or
            contract.get('detectors') != list(ADDITIONAL_IDS) or
            contract.get('calls_reserved') != {'F': 0, 'T': 16, 'E': 0} or
            (root / 'batch-failure.json').exists() or list(root.glob('failure-*.json'))):
        raise ValueError('complete bound additional16T qualification required')
    bound = allocation['_bound_files']
    bound[str(path)] = digest
    bound[str(contract_path)] = contract_sha
    original = allocation['_bodies']['original_qualification_admission']
    specs = original.get('caches')
    if not isinstance(specs, list) or len(specs) != 4:
        raise ValueError('original four engineering caches required')
    admission_path = Path(contract.get('admission_path', '')).resolve()
    if _sha(admission_path) != contract.get('admission_sha256'):
        raise ValueError('qualification admission changed')
    qargs = SimpleNamespace(stage=STAGES[0], admission=admission_path,
        deadline_unix=allocation['deadline_unix'], max_output_bytes=OUTPUT_CAP,
        max_terminal_calls=16, out=root)
    validate_stage_admission(qargs, allocation, specs, require_live=False)
    proofs = []
    for block, spec in enumerate(specs):
        _, proof = load_cache(spec)
        if proof.get('block') != block or proof.get('baseline') != 'B0-p3-s1' or proof.get('split') != 'engineering':
            raise ValueError('qualification cache differs from original engineering domain')
        proofs.append(proof)
        bound.update(proof['files'])
    if contract.get('caches') != proofs:
        raise ValueError('qualification contract caches differ from original evidence')
    ledger = contract.get('ledger', {})
    ledger_path = Path(ledger.get('path', '')).resolve()
    expected_path = run_root/'supplement-detector-additional-ledger'/(
        'reservation-'+hashlib.sha256(str(root).encode()).hexdigest()+'.json')
    if ledger_path != expected_path or _sha(ledger_path) != ledger.get('sha256'):
        raise ValueError('qualification canonical reservation binding differs')
    reservation, _ = read_json(ledger_path, ledger['sha256'])
    source_sha = hashlib.sha256(json.dumps(allocation['source_manifest'],sort_keys=True).encode()).hexdigest()
    expected_reservation = dict(schema=RESERVATION_SCHEMA,campaign_id=CAMPAIGN_ID,
        allocation_sha256=allocation['_sha256'],source_sha256=source_sha,
        stage=STAGES[0],identities=identities(STAGES[0],range(4)),T=16,out=str(root))
    if any(reservation.get(key) != value for key,value in expected_reservation.items()) or ledger.get('T') != 16:
        raise ValueError('qualification reservation identity differs')
    bound[str(ledger_path)] = ledger['sha256']
    expected = identities(STAGES[0], range(4))
    pairs = {}
    for ordinal, (record, identity) in enumerate(zip(summary['records'], expected), 1):
        current = record['identity']
        if (current.get('attempt') != ordinal or current.get('cache') != identity[1] or
                current.get('block') != identity[1] or current.get('batch_index') != identity[1] or
                current.get('detector') != identity[2] or current.get('doubled') is not identity[3] or
                current.get('config_sha256') != contract['config_sha256'] or
                record.get('truth_access') != 'none' or not math.isfinite(record['seconds']) or
                record['seconds'] <= 0):
            raise ValueError('additional qualification record identity differs')
        record_path = root / f'call-{ordinal:03d}.json'
        saved, saved_sha = read_json(record_path)
        if saved != record:
            raise ValueError('qualification summary differs from immutable record')
        bound[str(record_path)] = saved_sha
        raw = Path(record['terminal']['path']).resolve()
        if (raw.parent != root or raw.stat().st_size != record['terminal']['bytes'] or
                _sha(raw) != record['terminal']['sha256']):
            raise ValueError('qualification raw content differs')
        bound[str(raw)] = record['terminal']['sha256']
        with np.load(raw, allow_pickle=False) as arrays:
            result = {key: arrays[key].copy() for key in ('llr', 'mu', 'decoded')}
            result['bp_message_state'] = {
                key: arrays['bp_message_' + key].copy()
                for key in ('mu_previous', 'mu_current', 'var_previous', 'var_current')}
        result['diagnostics'] = record['diagnostics']
        pairs[tuple(identity[1:])] = result
    stability = [dict(cache=block, detector=detector,
                      result=qualification_pair(pairs[block, detector, False],
                                                pairs[block, detector, True]))
                 for block in range(4) for detector in ADDITIONAL_IDS]
    qualified, passed = qualification_summary(stability, list(ADDITIONAL_IDS), 4)
    if (summary.get('stability') != stability or summary.get('qualified_by_detector') != qualified or
            summary.get('qualification_passed') is not passed or
            summary.get('exitcode') != int(not passed) or
            summary.get('status') != ('complete' if passed else 'completed_unqualified')):
        raise ValueError('qualification flags differ from raw numerical evidence')
    return qualified, summary['records']


def verify_historical_qualification(reference, allocation):
    """Replay closed 16T NPZ with the R1 verifier. Never a 16T rerun."""
    import numpy as np
    from .supplement_baseline_select import config_hash
    from .supplement_detectors import qualification_pair
    from .supplement_detector_run import qualification_summary, load_cache

    if allocation.get('protocol') != DET01R_PROTOCOL:
        raise ValueError('historical 16T replay requires DET-01R')
    path, digest, summary = _reference(reference, 'historical additional qualification')
    root = path.parent
    contract_path = root / 'contract.json'
    contract, contract_sha = read_json(contract_path)
    predecessor_sha = allocation['references']['predecessor_allocation']['sha256']
    if (summary.get('stage') != STAGES[0] or summary.get('calls_attempted') != 16 or
            len(summary.get('records', [])) != 16 or summary.get('failures') or
            contract.get('config_sha256') != config_hash(contract) or
            summary.get('config_sha256') != contract['config_sha256'] or
            contract.get('stage') != STAGES[0] or
            contract.get('allocation_sha256') != predecessor_sha or
            contract.get('detectors') != list(ADDITIONAL_IDS) or
            contract.get('calls_reserved') != {'F': 0, 'T': 16, 'E': 0} or
            (root / 'batch-failure.json').exists() or list(root.glob('failure-*.json'))):
        raise ValueError('historical 16T package is not the closed predecessor')
    bound = allocation['_bound_files']
    bound[str(path)] = digest
    bound[str(contract_path)] = contract_sha
    original = allocation['_bodies']['original_qualification_admission']
    specs = original.get('caches')
    if not isinstance(specs, list) or len(specs) != 4:
        raise ValueError('original four engineering caches required')
    proofs = []
    for block, spec in enumerate(specs):
        _, proof = load_cache(spec)
        if proof.get('block') != block or proof.get('baseline') != 'B0-p3-s1' or proof.get('split') != 'engineering':
            raise ValueError('qualification cache differs from original engineering domain')
        proofs.append(proof)
        bound.update(proof['files'])
    if contract.get('caches') != proofs:
        raise ValueError('historical qualification caches differ from original evidence')
    ledger = contract.get('ledger', {})
    ledger_path = Path(ledger.get('path', '')).resolve()
    if not ledger_path.is_file() or _sha(ledger_path) != ledger.get('sha256'):
        raise ValueError('historical 16T reservation missing or changed')
    reservation, _ = read_json(ledger_path, ledger['sha256'])
    if (reservation.get('allocation_sha256') != predecessor_sha or
            reservation.get('stage') != STAGES[0] or reservation.get('T') != 16 or
            reservation.get('identities') != identities(STAGES[0], range(4))):
        raise ValueError('historical 16T reservation identity differs')
    bound[str(ledger_path)] = ledger['sha256']
    expected = identities(STAGES[0], range(4))
    pairs = {}
    for ordinal, (record, identity) in enumerate(zip(summary['records'], expected), 1):
        current = record['identity']
        if (current.get('attempt') != ordinal or current.get('cache') != identity[1] or
                current.get('block') != identity[1] or
                current.get('detector') != identity[2] or current.get('doubled') is not identity[3] or
                record.get('truth_access') != 'none'):
            raise ValueError('historical qualification record identity differs')
        record_path = root / f'call-{ordinal:03d}.json'
        saved, saved_sha = read_json(record_path)
        if saved != record:
            raise ValueError('historical summary differs from immutable record')
        bound[str(record_path)] = saved_sha
        raw = Path(record['terminal']['path']).resolve()
        if (raw.parent != root or raw.stat().st_size != record['terminal']['bytes'] or
                _sha(raw) != record['terminal']['sha256']):
            raise ValueError('historical raw content differs')
        bound[str(raw)] = record['terminal']['sha256']
        with np.load(raw, allow_pickle=False) as arrays:
            result = {key: arrays[key].copy() for key in ('llr', 'mu', 'decoded')}
            result['bp_message_state'] = {
                key: arrays['bp_message_' + key].copy()
                for key in ('mu_previous', 'mu_current', 'var_previous', 'var_current')}
        result['diagnostics'] = record['diagnostics']
        pairs[tuple(identity[1:])] = result
    stability = [dict(cache=block, detector=detector,
                      result=qualification_pair(pairs[block, detector, False],
                                                pairs[block, detector, True]))
                 for block in range(4) for detector in ADDITIONAL_IDS]
    qualified, passed = qualification_summary(stability, list(ADDITIONAL_IDS), 4)
    dual = allocation['_bodies']['dual_status']
    if (qualified != {'BP80': True, 'BP160': True} or passed is not True or
            dual.get('corrected_revalidation_status') != 'PASS' or
            dual.get('historical_frozen_verifier_status') != 'FAIL'):
        raise ValueError('corrected revalidation did not recover BP80/BP160 without rewriting v2 FAIL')
    return qualified, summary['records']


def qualification_resources(records, allocation):
    if len(records) != QUALIFICATION_T:
        raise ValueError('resource projection requires all16 qualification T')
    seconds = max(row['seconds'] for row in records)
    raw_bytes = max(row['terminal']['bytes'] for row in records)
    remaining_seconds = allocation['deadline_unix'] - __import__('time').time()
    remaining_bytes = OUTPUT_CAP - output_bytes(allocation['run_root'])
    projected_bytes = (raw_bytes + 65536) * DEVELOPMENT_T + 16 * 1024**2
    return {'observed_max_seconds_per_T':seconds,
        'observed_max_raw_bytes_per_T':raw_bytes,
        'projected_development_seconds':seconds*DEVELOPMENT_T,
        'projected_development_raw_bytes':raw_bytes*DEVELOPMENT_T,
        'projected_development_total_bytes':projected_bytes,
        'remaining_seconds':remaining_seconds, 'remaining_bytes':remaining_bytes,
        'development_resources_fit':bool(seconds*DEVELOPMENT_T <= remaining_seconds and
                                         projected_bytes <= remaining_bytes)}
