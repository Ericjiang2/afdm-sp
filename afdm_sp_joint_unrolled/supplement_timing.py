"""COST-02 engineering equivalence and manifest-bound timing collection."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback

# These must be fixed before importing numerical libraries.
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import numpy as np
import torch

from .budgeted_frame_store import publish_json
from .budgeted_support_eval import build_receiver, load_prior
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver, recipe_by_id
from .supplement_baseline_run import validate_frame_identity
from .supplement_data import CAMPAIGN_ID, SupplementData, campaign_rng
from .supplement_profile import A2Model, A2Receiver, reserve_profile
from .direction_run import summarize
from .supplement_run import array_hash, json_value, sources
from .supplement_pilot_frames import pilot_frames
from .supplement_scene_candidates import INPUT_FILES as CANDIDATE_INPUT_FILES
from .supplement_timing_authority import (MANIFEST_V1, MANIFEST_V2,
    PURPOSES as TIMING_PURPOSES, AUTHORIZATION_SCHEMA as TIMING_AUTHORIZATION_SCHEMA,
    timing_request_sha256 as timing_request_sha256, validate_authorization, validate_boundary)
from .supplement_timing_catalogue import resolve_catalogue, TimingReceiver
from .supplement_timing_integrity import BoundFiles, OutputMeter

SYMBOLS = ('A2', 'B_star_1', 'B_star_2')
MODES = (True, False)
RECIPE_IDS = {'B_star_1': 'B0-p2-s0.5',
              'B_star_2': 'bounded-param-p3-s1'}
FROZEN_IDS = {'B_star_1': 'A02-Bstar', 'B_star_2': 'A02-hard'}
RAW_FIELDS = ('H', 'sigma2', 'sigma2_terminal', 'x_soft', 'llr',
              'x_hard', 'decoded', 'info_hat', 'support')
CONTINUOUS = ('H', 'sigma2', 'sigma2_terminal', 'x_soft', 'llr')
EXACT = ('x_hard', 'decoded', 'info_hat', 'support')
TOLERANCE = 1e-6
MIN_OUTPUT_BYTES = 6 * 24 * 1024**2 + 32 * 1024**2
PER_TERMINAL_BYTES = 24 * 1024**2
FAILURE_RESERVE_BYTES = 256 * 1024
NPZ_OVERHEAD_BYTES = 1024**2

TIMING_SYMBOLS = SYMBOLS
TIMING_SNRS = (7, 8, 9)
TIMING_ORDER_RULE = ('campaign_rng(timing, block, order, family=F_C, '
                     'scenario=G0); SNR excluded')
TIMING_BOUNDARY = 'sync; complete receiver.run; sync'
TIMING_GPU_UUID = 'GPU-fe13c694-2050-c9f0-2904-b806f6f6b0c2'
TIMING_MANIFEST_SCHEMA = MANIFEST_V1
PER_TIMING_CALL_ESTIMATE_BYTES = 4 * 1024**2
TIMING_SCRATCH_BYTES = PER_TERMINAL_BYTES
TIMING_AUXILIARY_RESERVE_BYTES = 64 * 1024**2
TIMING_REMOTE_ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/'
    'afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def output_bytes(root):
    return sum(path.stat().st_size for path in Path(root).rglob('*')
               if path.is_file())


def expected_freeze_recipe(symbol):
    return recipe_by_id(FROZEN_IDS[symbol])


def expected_engineering_protocol(protocol_sha, checkpoint_sha, prior_sha,
                                  representative_sha):
    """Minimal accepted protocol, also useful to fake-only tests."""
    return {
        'schema': 'COST02-engineering-equivalence-protocol-v1',
        'status': 'preregistered_not_launch_admission',
        'campaign_id': CAMPAIGN_ID, 'issue': 'COST-02',
        'mode': 'engineering-equivalence', 'split': 'engineering',
        'block': 0, 'snr_db': 8, 'arms': list(SYMBOLS),
        'audit_modes': [True, False], 'calls': {'F': 6, 'T': 0, 'E': 0},
        'ledger': 'supplement-engineering-ledger',
        'global_engineering_cap': {'F': 128, 'T': 256, 'E': 128},
        'sources': {'data_protocol_sha256': protocol_sha,
                    'A02_representative_sha256': representative_sha,
                    'checkpoint_sha256': checkpoint_sha,
                    'A2_prior_sha256': prior_sha},
        'recipes': {
            'A2': ('supplement_profile.A2Receiver/A2Model; direction_cost '
                   'direct40/achievable/M96/two-round F2P'),
            'B_star_1': expected_freeze_recipe('B_star_1'),
            'B_star_2': expected_freeze_recipe('B_star_2')},
        'numeric_acceptance': {
            'continuous_relative_l2_max': TOLERANCE,
            'continuous_arrays': list(CONTINUOUS),
            'exact_arrays': list(EXACT),
            'all_arrays_finite_and_shape_equal': True,
            'hash_identity_reported_separately': True,
            'on_observers_present_off_observers_empty': True},
        'raw_required': list(RAW_FIELDS),
        'execution_limits': {'receiver_workers': 1, 'cpu_threads': 1,
            'cuda_allocator_fraction': .25, 'deadline_seconds': 1800,
            'output_bytes': 512 * 1024**2,
            'minimum_disk_free_bytes': 1024**3},
        'formal_timing_data_generated': False}


def validate_engineering_protocol(value, args):
    expected = expected_engineering_protocol(
        sha(args.protocol), sha(args.checkpoint), sha(args.prior),
        args.representative_freeze_sha256)
    for key in ('schema', 'status', 'campaign_id', 'issue', 'mode', 'split',
                'block', 'snr_db', 'arms', 'audit_modes', 'calls', 'ledger',
                'global_engineering_cap', 'raw_required',
                'formal_timing_data_generated'):
        if value.get(key) != expected[key]:
            raise ValueError('engineering protocol domain differs: ' + key)
    for key, digest in expected['sources'].items():
        if value.get('sources', {}).get(key) != digest:
            raise ValueError('engineering protocol input binding differs: ' + key)
    numeric = value.get('numeric_acceptance', {})
    for key, expected_value in expected['numeric_acceptance'].items():
        if numeric.get(key) != expected_value:
            raise ValueError('engineering numeric gate differs: ' + key)
    limits = value.get('execution_limits', {})
    for key, expected_value in expected['execution_limits'].items():
        if limits.get(key) != expected_value:
            raise ValueError('engineering execution limit differs: ' + key)
    recipes = value.get('recipes')
    if not isinstance(recipes, dict):
        raise ValueError('engineering recipes missing')
    for symbol, expected_recipe in expected['recipes'].items():
        if recipes.get(symbol) != expected_recipe:
            raise ValueError('engineering recipe differs: ' + symbol)
    return value


def validate_freeze(path, expected_sha):
    if sha(path) != expected_sha:
        raise ValueError('representative freeze SHA mismatch')
    value = json.loads(Path(path).read_text())
    mapping, recipes = value.get('symbolic_arm_mapping'), value.get('recipes')
    for symbol, frozen_id in FROZEN_IDS.items():
        if (not isinstance(mapping, dict) or mapping.get(symbol) != frozen_id or
                not isinstance(recipes, dict) or
                recipes.get(symbol) != expected_freeze_recipe(symbol)):
            raise ValueError('representative freeze mapping/recipe differs')
    return value


def validate_request(args, hooks=None):
    if (not math.isfinite(args.deadline_unix) or
            not 0 < args.deadline_unix - time.time() <= 1800):
        raise ValueError('future deadline within 1800 seconds required')
    if args.max_output_bytes != 512 * 1024**2 or args.max_output_bytes < MIN_OUTPUT_BYTES:
        raise ValueError('storage cap must preserve six dense-H raw receipts')
    device_type = str(args.device).split(':', 1)[0]
    if device_type not in ('cuda', 'cpu'):
        raise ValueError('device must be CUDA or explicit CPU')
    if device_type == 'cpu' and not args.allow_cpu:
        raise ValueError('CPU execution requires explicit --allow-cpu')
    if device_type == 'cuda' and not (hooks or RealHooks()).cuda_available():
        raise ValueError('requested CUDA unavailable; no CPU fallback')
    if sha(args.engineering_protocol) != args.engineering_protocol_sha256:
        raise ValueError('engineering protocol SHA mismatch')
    engineering = json.loads(Path(args.engineering_protocol).read_text())
    validate_freeze(args.representative_freeze,
                    args.representative_freeze_sha256)
    validate_engineering_protocol(engineering, args)
    return engineering


def _bounded_json(path, value, root, limit, *, meter=None):
    encoded = json.dumps(json_value(value), sort_keys=True,
                         allow_nan=False).encode()
    if meter is not None:
        meter.require_space(len(encoded))
    elif output_bytes(root) + len(encoded) > limit:
        raise OSError('output publication would exceed frozen storage budget')
    publish_json(path, json_value(value))
    if meter is not None:
        meter.record(path)


def _bounded_npz(path, values, root, limit, *, meter=None):
    raw_bytes = sum(np.asarray(value).nbytes for value in values.values())
    if meter is not None:
        meter.require_space(raw_bytes + NPZ_OVERHEAD_BYTES)
    elif output_bytes(root) + raw_bytes + NPZ_OVERHEAD_BYTES > limit:
        raise OSError('raw publication would exceed frozen storage budget')
    fd, temporary = tempfile.mkstemp(prefix='.timing-', suffix='.npz',
                                     dir=Path(path).parent)
    os.close(fd)
    try:
        np.savez_compressed(temporary, **values)
        size = Path(temporary).stat().st_size
        # output_bytes already includes the temporary file.  The hard link does
        # not allocate a second copy and the temporary name is removed below.
        if meter is not None:
            meter.require_space(size)
        elif output_bytes(root) > limit:
            raise OSError('raw publication would exceed frozen storage budget')
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if meter is not None:
        meter.record(path)
    return {'path': str(path), 'bytes': Path(path).stat().st_size,
            'sha256': sha(path), 'md5': md5(path),
            'fields': list(RAW_FIELDS)}


def _validate_result(value, audit, frame, code):
    arrays = {key: np.asarray(value[key]) for key in RAW_FIELDS
              if key != 'support'}
    support = value.get('support')
    n = int(np.asarray(frame.observed['y']).size)
    info_n, coded_n = int(code['k']), int(code['n'])
    if np.asarray(code['G']).shape != (coded_n, info_n) or coded_n != 2*n:
        raise ValueError('LDPC dimensions differ from observed frame')
    if (n < 1 or arrays['H'].shape != (n, n) or
            arrays['x_soft'].shape != (n,) or arrays['x_hard'].shape != (n,) or
            arrays['llr'].shape != (coded_n,) or arrays['decoded'].shape != (coded_n,) or
            arrays['info_hat'].shape != (info_n,) or
            arrays['sigma2'].shape != () or arrays['sigma2_terminal'].shape != () or
            any(not np.isfinite(array).all() for array in arrays.values()) or
            float(arrays['sigma2']) <= 0 or float(arrays['sigma2_terminal']) <= 0 or
            not isinstance(support, list) or len(support) > 40 or
            len(support) != len(set(support)) or
            any(type(index) is not int or not 0 <= index < 515
                for index in support)):
        raise ValueError('receiver raw finite/shape/support contract differs')
    if (not np.isin(arrays['decoded'], (0, 1)).all() or
            not np.isin(arrays['info_hat'], (0, 1)).all()):
        raise ValueError('receiver decoded/info_hat must be binary')
    graphs, supports = value.get('graphs'), value.get('support_trace')
    dals = value.get('dals')
    if audit:
        if (not isinstance(graphs, list) or not graphs or
                not isinstance(supports, list) or not supports or
                not isinstance(dals, list) or len(dals) != 9):
            raise ValueError('audit-on graph/support/DALS evidence missing')
    elif graphs != [] or supports != [] or dals != []:
        raise ValueError('audit-off observers were not empty')
    return {**arrays, 'support': np.asarray(support, dtype=np.int64)}


def _relative(left, right):
    a, b = np.asarray(left), np.asarray(right)
    difference, reference = float(np.linalg.norm(a-b)), float(np.linalg.norm(b))
    if reference == 0.:
        return 0. if difference == 0. else math.inf
    return difference / reference


def compare_pair(on, off, symbol):
    comparisons = {}
    for key in CONTINUOUS:
        if on[key].shape != off[key].shape or not np.isfinite(on[key]).all() or not np.isfinite(off[key]).all():
            raise ValueError('equivalence shape/finite mismatch: ' + key)
        relative = _relative(on[key], off[key])
        if not math.isfinite(relative) or relative > TOLERANCE:
            raise ValueError('observer equivalence tolerance failed: ' + symbol + '/' + key)
        comparisons[key] = {'relative_l2': relative,
                            'within_1e-6': True,
                            'exact_hash': array_hash(on[key]) == array_hash(off[key])}
    for key in EXACT:
        equal = np.array_equal(on[key], off[key])
        if not equal:
            raise ValueError('observer equivalence exact field failed: ' + symbol + '/' + key)
        comparisons[key] = {'elementwise_exact': True,
                            'exact_hash': array_hash(on[key]) == array_hash(off[key])}
    return {'symbol': symbol, 'continuous_tolerance': TOLERANCE,
            'fields': comparisons,
            'scope': 'engineering observer equivalence; LLR need not be bit-exact'}


def _read_bound_json(path, expected_sha, label):
    if not isinstance(path, (str, Path)):
        raise ValueError(label + ' path missing')
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(label + ' cannot be read') from exc
    if (not isinstance(expected_sha, str) or len(expected_sha) != 64 or
            hashlib.sha256(raw).hexdigest() != expected_sha):
        raise ValueError(label + ' SHA-256 mismatch')
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(label + ' is not valid JSON') from exc
    if not isinstance(value, dict):
        raise ValueError(label + ' must be a JSON object')
    return value


def _manifest_path(manifest_path, value):
    path = Path(value)
    if not path.is_absolute():
        path = Path(manifest_path).parent / path
    return path.resolve()


def _require_real_path(path, label):
    if (not isinstance(path, (str, Path)) or
            not str(path).strip()):
        raise ValueError('real timing ' + label + ' path is missing')
    resolved = Path(path).resolve()
    if not resolved.is_relative_to('/data/guoyikun'):
        raise ValueError('real timing ' + label + ' must stay under /data/guoyikun')
    return resolved


def _validate_global_freeze(path, expected_sha, protocol_sha):
    value = _read_bound_json(path, expected_sha, 'global freeze')
    if (value.get('schema') != 'afdm-supplement-global-freeze-v1' or
            value.get('status') != 'GLOBAL_FROZEN_NOT_FAMILY_ADMISSION' or
            value.get('campaign_id') != CAMPAIGN_ID or
            value.get('alpha_total') != .05 or
            value.get('family_m', {}).get('F_C') != 102 or
            value.get('data_protocol', {}).get('sha256') != protocol_sha):
        raise ValueError('global freeze semantic contract differs')
    return value


def _validate_timing_authorization(manifest, manifest_path, *, real=False):
    path, digest = validate_authorization(manifest, manifest_path)
    if real:
        _require_real_path(path, 'authorization evidence')
    return Path(path), digest


def timing_order(snr, block, symbols=TIMING_SYMBOLS):
    if snr not in TIMING_SNRS or type(block) is not int or block < 0:
        raise ValueError('invalid timing order identity')
    order = list(symbols)
    if (not order or any(not isinstance(symbol, str) or not symbol for symbol in order)
            or len(set(order)) != len(order)):
        raise ValueError('invalid timing order methods')
    campaign_rng('timing', block, 'order', family='F_C',
                 scenario='G0').shuffle(order)
    return order


def _validate_prior_map(manifest, manifest_path, *, real=False):
    requested = manifest['requested_snr_cells']
    mapping = manifest.get('prior_by_snr')
    if not isinstance(mapping, dict) or set(mapping) != {
            str(snr) for snr in requested}:
        raise ValueError('each requested SNR requires one explicit prior binding')
    resolved = {}
    for snr in requested:
        row = mapping[str(snr)]
        if not isinstance(row, dict):
            raise ValueError('SNR prior binding must be an object')
        path = _manifest_path(manifest_path, row.get('path', ''))
        if real:_require_real_path(path, 'prior')
        if sha(path) != row.get('sha256'):
            raise ValueError('prior SHA-256 mismatch for SNR ' + str(snr))
        resolved[snr] = path
    return resolved


def _validate_catalogue(manifest, args, global_freeze, *, real=False):
    selection = manifest.get('selection')
    if (not isinstance(selection, dict) or
            set(selection) != {'candidate_freeze', 'inputs'} or
            not isinstance(selection['inputs'], dict) or
            set(selection['inputs']) != set(CANDIDATE_INPUT_FILES)):
        raise ValueError('full timing selection bindings are incomplete')
    files, paths = {}, {}

    def read(binding, label, *, binary=False):
        if not isinstance(binding, dict):
            raise ValueError('timing selection binding missing: '+label)
        value = binding.get('path')
        if not isinstance(value, str) or not value.strip():
            raise ValueError('timing selection path missing: '+label)
        path = _manifest_path(args.timing_manifest, value)
        if real:
            _require_real_path(path, 'selection '+label)
        if binary:
            if sha(path) != binding.get('sha256'):
                raise ValueError('timing selection SHA-256 mismatch: '+label)
            result = None
        else:
            result = _read_bound_json(path, binding.get('sha256'), 'selection '+label)
        files[str(path)] = binding['sha256']
        paths[label] = path
        return result

    freeze = read(selection['candidate_freeze'], 'candidate_freeze')
    inputs = {}
    for key, binding in selection['inputs'].items():
        if (not isinstance(binding, dict) or
                binding.get('sha256') != freeze.get('bindings', {}).get(key)):
            raise ValueError('timing selection differs from frozen input: '+key)
        value = read(binding, key, binary=key == 'pilot_npz')
        if key != 'pilot_npz':
            inputs[key] = value
    catalogue = resolve_catalogue(freeze, inputs)
    if manifest.get('catalogue') != catalogue or manifest.get('arm_ids') != catalogue['arm_ids']:
        raise ValueError('timing catalogue or actual method order differs')
    if (selection['inputs']['A02_representatives']['sha256'] != args.representative_freeze_sha256 or
            selection['inputs']['global_contrasts']['sha256'] !=
            global_freeze.get('global_manifest', {}).get('sha256')):
        raise ValueError('timing catalogue does not bind original representatives/global freeze')
    return files, paths['pilot_npz']


def _validate_formal_link(manifest, manifest_path, *, real=False):
    v2 = manifest.get('schema') == MANIFEST_V2
    bound_files = validate_boundary(manifest, manifest_path)['files'] if v2 else {}
    if real:
        for path in bound_files:
            _require_real_path(path, 'timing history')
    if manifest['timing_purpose'] == 'timing-pilot':
        if v2:
            return bound_files
        if manifest['block_start'] != 0 or any(key in manifest for key in
                ('pilot_manifest_path', 'pilot_manifest_sha256')):
            raise ValueError('timing pilot must start at zero without a pilot link')
        return {}
    counts = manifest['n_by_snr']
    if any(counts[str(snr)] < 1024 for snr in TIMING_SNRS):
        raise ValueError('formal timing requires at least 1024 blocks per SNR')
    pilot_value = manifest.get('pilot_manifest_path')
    if not isinstance(pilot_value, str) or not pilot_value.strip():
        raise ValueError('formal timing pilot manifest is missing')
    pilot_path = _manifest_path(manifest_path, pilot_value)
    if real:_require_real_path(pilot_path, 'pilot manifest')
    pilot = _read_bound_json(pilot_path,
        manifest.get('pilot_manifest_sha256'), 'formal pilot manifest')
    bound_files[str(pilot_path)] = manifest['pilot_manifest_sha256']
    pilot_authorization_path, pilot_authorization_sha = \
        _validate_timing_authorization(pilot, pilot_path, real=real)
    bound_files[str(pilot_authorization_path)] = pilot_authorization_sha
    if (pilot.get('schema') != manifest['schema'] or
            pilot.get('status') != 'accepted_for_collection' or
            pilot.get('campaign_id') != CAMPAIGN_ID or
            pilot.get('issue') != 'COST-02' or pilot.get('family') != 'F_C' or
            pilot.get('scenario') != 'G0' or pilot.get('proceed_timing') is not True or
            pilot.get('timing_purpose') != 'timing-pilot' or
            (not v2 and pilot.get('block_start') != 0) or
            manifest['block_start'] != pilot.get('block_start', 0) +
                max(pilot.get('n_by_snr', {}).values(), default=-1) or
            manifest.get('source_manifest') != pilot.get('source_manifest') or
            any(manifest.get(key) != pilot.get(key) for key in
                ('ledger_path', 'protocol_sha256', 'global_freeze_sha256',
                 'checkpoint_sha256', 'representative_freeze_sha256',
                 'order_rule', 'measurement_boundary', 'prior_by_snr')) or
            not set(manifest['arm_ids']).issubset(pilot.get('arm_ids', []))):
        raise ValueError('formal timing overlaps or does not bind the complete pilot')
    completion_path = _manifest_path(manifest_path,
                                    manifest.get('pilot_completion_path', ''))
    if real:_require_real_path(completion_path, 'pilot completion')
    completion = _read_bound_json(completion_path,
        manifest.get('pilot_completion_sha256'), 'formal pilot completion')
    bound_files[str(completion_path)] = manifest['pilot_completion_sha256']
    if (completion.get('schema') != 'COST02-timing-receipt-v1' or
            completion.get('status') != 'complete_collection_only' or
            completion.get('exitcode') != 0 or completion.get('calls') != pilot['calls'] or
            completion.get('measured_n_by_snr') != {str(snr): pilot['n_by_snr'][str(snr)]
                for snr in pilot['requested_snr_cells']}):
        raise ValueError('formal timing requires completed pilot observations')
    if v2 and (completion.get('collection_manifest_schema') != MANIFEST_V2 or
               completion.get('catalogue') != pilot['catalogue']):
        raise ValueError('formal timing pilot completion catalogue differs')
    contract_path = completion_path.parent/'contract.json'
    if real:_require_real_path(contract_path, 'pilot contract')
    contract = json.loads(contract_path.read_text())
    bound_files[str(contract_path.resolve())] = sha(contract_path)
    config = {key: value for key, value in contract.items()
              if key not in ('config_sha256', 'reservation')}
    digest = hashlib.sha256(json.dumps(config, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if (digest != contract.get('config_sha256') or digest != completion.get('config_sha256') or
            contract.get('manifest_sha256') != manifest['pilot_manifest_sha256'] or
            contract.get('schema') != 'COST02-timing-contract-v1' or
            contract.get('campaign_id') != CAMPAIGN_ID or
            contract.get('purpose') != 'timing-pilot' or
            contract.get('source_sha256') != pilot.get('source_manifest')):
        raise ValueError('formal pilot completion contract is not content-bound')
    if v2 and (contract.get('collection_manifest_schema') != MANIFEST_V2 or
               contract.get('catalogue') != pilot['catalogue']):
        raise ValueError('formal timing pilot contract catalogue differs')
    if real and (completion.get('fixture_only') is not False or
            contract.get('fixture_only') is not False or
            contract.get('device') not in ('cuda', 'cuda:0')):
        raise ValueError('real formal timing requires a completed real CUDA pilot')
    references = completion.get('measured_records', [])+completion.get('warmup_records', [])
    expected = {_timing_id_key(row) for row in timing_identities(pilot)}
    actual = set()
    for reference in references:
        record_path = _manifest_path(completion_path, reference.get('path', ''))
        if real:_require_real_path(record_path, 'pilot record')
        record = _read_bound_json(record_path, reference.get('sha256'),
                                  'formal pilot record')
        bound_files[str(record_path)] = reference['sha256']
        identity = record['identity']
        actual.add(_timing_id_key({key: identity[key] for key in
            ('purpose', 'phase', 'snr_db', 'block', 'repeat', 'symbol')}))
        raw = record['raw']
        raw_path = _manifest_path(record_path, raw.get('path', ''))
        if real:_require_real_path(raw_path, 'pilot raw output')
        if sha(raw_path) != raw['sha256']:
            raise ValueError('formal pilot raw output changed')
        bound_files[str(raw_path)] = raw['sha256']
    if actual != expected or len(references) != len(expected):
        raise ValueError('formal pilot observation identities are incomplete')
    telemetry = completion.get('telemetry_records', [])
    groups = sum(pilot['n_by_snr'][str(snr)]+pilot['warmup_by_snr'][str(snr)]
                 for snr in pilot['requested_snr_cells'])
    if len(telemetry) != 1+2*groups:
        raise ValueError('formal pilot boundary telemetry is incomplete')
    for reference in telemetry:
        telemetry_path = _manifest_path(completion_path, reference.get('path', ''))
        if real:_require_real_path(telemetry_path, 'pilot telemetry')
        value = _read_bound_json(telemetry_path, reference.get('sha256'),
                                'formal pilot telemetry')
        bound_files[str(telemetry_path)] = reference['sha256']
        if (value.get('status') != 'ok' or value.get('gpu_uuid') != TIMING_GPU_UUID or
                not isinstance(value.get('compute_pids'), list) or
                any(pid != contract.get('pid') for pid in value['compute_pids'])):
            raise ValueError('formal pilot contained foreign or ambiguous telemetry')
    expected_orders=[]
    group=0
    for snr in pilot['requested_snr_cells']:
        start=pilot['block_start']
        rows=[('warmup',start,repeat) for repeat in
              range(pilot['warmup_by_snr'][str(snr)])]
        rows += [('measured',block,None) for block in
                 range(start,start+pilot['n_by_snr'][str(snr)])]
        for phase,block,repeat in rows:
            group+=1
            expected_orders.append({'group':group,'phase':phase,'block':block,
                'snr_db':snr,'repeat':repeat,'order':timing_order(snr,block,pilot['arm_ids'])})
    order_references=completion.get('order_records',[])
    if len(order_references)!=len(expected_orders):
        raise ValueError('formal pilot order evidence is incomplete')
    for reference,expected_order in zip(order_references,expected_orders):
        order_path=_manifest_path(completion_path,reference.get('path',''))
        if real:_require_real_path(order_path,'pilot order record')
        order=_read_bound_json(order_path,reference.get('sha256'),
                               'formal pilot order record')
        bound_files[str(order_path)]=reference['sha256']
        if order!=expected_order:
            raise ValueError('formal pilot order evidence differs')
    return bound_files


def validate_timing_request(args, hooks, *, real=False):
    manifest = _read_bound_json(args.timing_manifest,
        args.timing_manifest_sha256, 'timing manifest')
    schema = manifest.get('schema')
    if schema not in (MANIFEST_V1, MANIFEST_V2):
        raise ValueError('unsupported timing manifest schema')
    maximum_duration = 86400 if schema == MANIFEST_V2 else 3600
    if (not math.isfinite(args.deadline_unix) or
            not 0 < args.deadline_unix - time.time() <= maximum_duration):
        raise TimeoutError(f'future timing deadline within {maximum_duration} seconds required')
    if str(args.device).split(':', 1)[0] != 'cuda':
        if not (str(args.device).split(':', 1)[0] == 'cpu' and
                args.allow_cpu):
            raise ValueError('timing requires CUDA or explicit CPU fixture mode')
    elif not hooks.cuda_available():
        raise ValueError('requested CUDA unavailable; no fallback')
    fixed = {'status': 'accepted_for_collection', 'campaign_id': CAMPAIGN_ID,
        'issue': 'COST-02', 'family': 'F_C', 'scenario': 'G0',
        'proceed_timing': True, 'protocol_sha256': sha(args.protocol),
        'global_freeze_sha256': args.global_freeze_sha256,
        'checkpoint_sha256': sha(args.checkpoint),
        'representative_freeze_sha256': args.representative_freeze_sha256,
        'order_rule': TIMING_ORDER_RULE,
        'measurement_boundary': TIMING_BOUNDARY}
    if schema == MANIFEST_V1:
        fixed['arm_ids'] = list(TIMING_SYMBOLS)
    for key, expected in fixed.items():
        if manifest.get(key) != expected:
            message = 'unsupported timing arms' if key == 'arm_ids' else \
                'timing manifest differs: ' + key
            raise ValueError(message)
    if manifest.get('timing_purpose') not in TIMING_PURPOSES:
        raise ValueError('unsupported timing purpose')
    if manifest['timing_purpose'] != getattr(args, 'mode',
            manifest['timing_purpose']):
        raise ValueError('timing mode and manifest purpose differ')
    global_freeze = _validate_global_freeze(args.global_freeze,
        args.global_freeze_sha256, sha(args.protocol))
    if sha(args.representative_freeze) != args.representative_freeze_sha256:
        raise ValueError('representative freeze SHA-256 mismatch')
    if manifest.get('source_manifest') != hooks.sources():
        raise ValueError('timing source manifest differs')
    if schema == MANIFEST_V2:
        files, pilot_path = _validate_catalogue(manifest, args, global_freeze, real=real)
        boundary = validate_boundary(manifest, args.timing_manifest)
        manifest['_catalogue_files'] = files
        manifest['_pilots_path'] = pilot_path
        manifest['_excluded_manifest_bindings'] = boundary['excluded_manifests']
    requested = manifest.get('requested_snr_cells')
    if (not isinstance(requested, list) or not requested or
            len(set(requested)) != len(requested) or
            any(snr not in TIMING_SNRS for snr in requested)):
        raise ValueError('requested SNR cells are invalid')
    counts, warmups = manifest.get('n_by_snr'), manifest.get('warmup_by_snr')
    keys = {str(snr) for snr in TIMING_SNRS}
    if (not isinstance(counts, dict) or set(counts) != keys or
            any(type(counts[key]) is not int or counts[key] < 1
                for key in keys)):
        raise ValueError('timing sample counts are invalid')
    if (not isinstance(warmups, dict) or set(warmups) != keys or
            any(type(warmups[key]) is not int or warmups[key] < 0
                for key in keys)):
        raise ValueError('timing warmup counts are invalid')
    block_start = manifest.get('block_start')
    if type(block_start) is not int or block_start < 0:
        raise ValueError('timing block start is invalid')
    pilot_bound_files = _validate_formal_link(
        manifest, args.timing_manifest, real=real)
    prior_paths = _validate_prior_map(manifest, args.timing_manifest, real=real)
    expected_F = len(manifest['arm_ids']) * sum(
        counts[str(snr)] + warmups[str(snr)] for snr in requested)
    if (manifest.get('calls') != {'F': expected_F, 'T': 0, 'E': 0} or
            type(manifest.get('timing_family_cap_F')) is not int or
            not expected_F <= manifest['timing_family_cap_F']):
        raise ValueError('finite timing F count or cap is invalid')
    limits = manifest.get('resource_limits')
    expected_limits = {'cpu_threads': 1, 'cuda_allocator_fraction': .25,
        'gpu_uuid': TIMING_GPU_UUID, 'max_output_bytes': args.max_output_bytes,
        'host_cpu_headroom_cores': 16}
    if not isinstance(limits, dict) or any(limits.get(k) != v
            for k, v in expected_limits.items()):
        raise ValueError('timing storage or resource limits differ')
    duration = limits.get('deadline_seconds')
    admitted = manifest.get('runtime_admitted_unix')
    deadline = manifest.get('runtime_deadline_unix')
    if (type(duration) is not int or not 0 < duration <= maximum_duration or
            type(admitted) not in (float, int) or not math.isfinite(admitted) or
            type(deadline) not in (float, int) or not math.isfinite(deadline) or
            deadline != args.deadline_unix or admitted > time.time() or
            not 0 < deadline-admitted <= duration):
        raise ValueError('timing deadline is not bound to its finite admission')
    minimum_disk = limits.get('minimum_disk_free_bytes')
    if type(minimum_disk) is not int or minimum_disk < args.max_output_bytes:
        raise ValueError('timing disk reserve must cover the full output cap')
    if manifest.get('ledger_path') != str(Path(args.timing_ledger).resolve()):
        raise ValueError('timing reservation ledger is not manifest-bound')
    if args.max_output_bytes < (expected_F * PER_TIMING_CALL_ESTIMATE_BYTES +
            TIMING_SCRATCH_BYTES + TIMING_AUXILIARY_RESERVE_BYTES +
            FAILURE_RESERVE_BYTES):
        raise ValueError('timing storage bound cannot retain all outputs')
    _validate_timing_authorization(manifest, args.timing_manifest, real=real)
    manifest['_resolved_prior_paths'] = prior_paths
    manifest['_pilot_bound_files'] = pilot_bound_files
    manifest['_manifest_path'] = str(Path(args.timing_manifest).resolve())
    return manifest


def _timing_id_key(identity):
    return json.dumps(identity, sort_keys=True, separators=(',', ':'))


def _schedule_identity(identity):
    if identity is None:return None
    keys=('ordinal','purpose','phase','group','snr_db','block','repeat','symbol')
    return {key:identity[key] for key in keys if key in identity}


def _compact_references(references, pattern):
    encoded=json.dumps(json_value(references),sort_keys=True,
                       separators=(',',':')).encode()
    return {'count':len(references),'references_sha256':hashlib.sha256(encoded).hexdigest(),
            'last':references[-1] if references else None,
            'complete_originals_preserved_as':pattern}


def timing_identities(manifest):
    identities = []
    start = manifest['block_start']
    for snr in manifest['requested_snr_cells']:
        for repeat in range(manifest['warmup_by_snr'][str(snr)]):
            for symbol in manifest['arm_ids']:
                identities.append({'purpose': manifest['timing_purpose'],
                    'phase': 'warmup', 'snr_db': snr, 'block': start,
                    'repeat': repeat, 'symbol': symbol})
        for block in range(start, start + manifest['n_by_snr'][str(snr)]):
            for symbol in manifest['arm_ids']:
                identities.append({'purpose': manifest['timing_purpose'],
                    'phase': 'measured', 'snr_db': snr, 'block': block,
                    'repeat': None, 'symbol': symbol})
    return identities


def reserve_timing(ledger, out, manifest_sha, manifest, config_sha, *, real=False):
    ledger = Path(ledger)
    ledger.mkdir(parents=True, exist_ok=True)
    requested = timing_identities(manifest)
    requested_keys = {_timing_id_key(row) for row in requested}
    if len(requested_keys) != len(requested):
        raise ValueError('duplicate identities in timing reservation')
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        used, existing_keys, existing_manifests = 0, set(), {}
        for path in ledger.glob('reservation-*.json'):
            row = json.loads(path.read_text())
            if (row.get('campaign_id') != CAMPAIGN_ID or
                    row.get('schema') != 'COST02-timing-reservation-v1'):
                raise ValueError('foreign timing ledger campaign')
            previous_manifest_path = row.get('manifest_path')
            if real:
                _require_real_path(previous_manifest_path,
                                   'reserved timing manifest')
            previous = _read_bound_json(previous_manifest_path,
                row.get('manifest_sha256'), 'reserved timing manifest')
            previous_key = str(Path(previous_manifest_path).resolve())
            if previous_key in existing_manifests:
                raise ValueError('duplicate timing history manifest reservation')
            existing_manifests[previous_key] = row['manifest_sha256']
            prior = row.get('identities')
            if (not isinstance(prior, list) or
                    previous.get('ledger_path') != str(ledger.resolve()) or
                    prior != timing_identities(previous) or
                    row.get('calls_reserved') != previous.get('calls') or
                    row.get('calls_reserved') != {'F': len(prior), 'T': 0,
                                                   'E': 0}):
                raise ValueError('invalid timing reservation')
            keys = {_timing_id_key(identity) for identity in prior}
            if len(keys) != len(prior) or existing_keys & keys:
                raise ValueError('duplicate identities in existing timing ledger')
            existing_keys.update(keys)
            used += len(prior)
        if (manifest.get('schema') == MANIFEST_V2 and
                existing_manifests != manifest.get('_excluded_manifest_bindings')):
            raise ValueError('timing exclusions do not cover exactly the reserved history')
        if existing_keys & requested_keys:
            raise ValueError('timing reservation identity overlap')
        if used + len(requested) > manifest['timing_family_cap_F']:
            raise ValueError('timing family F cap exceeded')
        key = hashlib.sha256(str(Path(out).resolve()).encode()).hexdigest()
        path = ledger / ('reservation-' + key + '.json')
        if path.exists():
            raise ValueError('timing reservation already exists')
        value = {'schema': 'COST02-timing-reservation-v1',
            'campaign_id': CAMPAIGN_ID, 'out': str(Path(out).resolve()),
            'manifest_path': manifest['_manifest_path'],
            'manifest_sha256': manifest_sha,
            'config_sha256': config_sha, 'identities': requested,
            'calls_reserved': {'F': len(requested), 'T': 0, 'E': 0},
            'policy': 'immutable; failed/unused calls remain charged; no retry'}
        publish_json(path, value)
    return {'path': str(path), 'sha256': sha(path)}


class RealHooks:
    def cuda_available(self):
        return torch.cuda.is_available()

    def configure(self, device):
        torch.set_num_threads(1)
        if torch.get_num_interop_threads() != 1:
            torch.set_num_interop_threads(1)
        if torch.device(device).type == 'cuda':
            torch.cuda.set_per_process_memory_fraction(.25, torch.device(device))

    def sources(self):
        return sources()

    def reserve(self, out, contract):
        return reserve_profile(out, contract)

    def prepare(self, args):
        (args.out / 'code-cache').mkdir()
        code = build_code(cache_dir=args.out / 'code-cache')
        system = _make_config_a(1024, 2., 8, 10., 4.)
        frame = SupplementData(args.protocol, code).make_frame(
            system, 'engineering', 0, 8)
        return {'code': code, 'system': system, 'frame': frame,
                'code_sha256': {key: array_hash(code[key])
                                for key in ('G', 'H')}}

    def build(self, symbol, context):
        return self.build_timing(symbol, context, 8, context['args'].prior)

    def build_timing(self, symbol, context, snr, prior_path):
        model = build_receiver(context['args'].checkpoint, context['system'],
                               1024, context['args'].device,
                               receiver_shell='direct40', active_cap=40)
        if symbol == 'A2':
            lookup, _ = load_prior(prior_path, snr, 1024,
                l_max=102, k_max=2, nomination_cap=40,
                receiver_shell='direct40')
            return A2Receiver(A2Model(model, context['system'], lookup),
                              context['code'])
        if 'catalogue' in context:
            return TimingReceiver(model, context['code'], context['system'],
                                  context['catalogue']['methods'][symbol])
        return BaselineReceiver(model, context['code'], RECIPE_IDS[symbol],
                                system=context['system'])

    def prepare_timing(self, args, manifest):
        validate_freeze(args.representative_freeze,
                        args.representative_freeze_sha256)
        (args.out / 'code-cache').mkdir()
        code = build_code(cache_dir=args.out / 'code-cache')
        data = SupplementData(args.protocol, code, freeze_manifests={'F_C': {
            'frozen_manifest_path': str(args.timing_manifest),
            'frozen_manifest_sha256': args.timing_manifest_sha256}})
        for snr, prior_path in manifest['_resolved_prior_paths'].items():
            # Validate calibration domains before any random frame is generated.
            load_prior(prior_path, snr, 1024, l_max=102, k_max=2,
                       nomination_cap=40, receiver_shell='direct40')
            for symbol in manifest['arm_ids']:
                data._request('timing', manifest['block_start'], snr,
                    'F_C', symbol, 'G0', manifest['timing_purpose'])
        context = {'code': code, 'data': data,
                'system': _make_config_a(1024, 2., 8, 10., 4.),
                'code_sha256': {key: array_hash(code[key]) for key in ('G', 'H')}}
        if manifest['schema'] == MANIFEST_V2:
            context['catalogue'] = manifest['catalogue']
            with np.load(manifest['_pilots_path'], allow_pickle=False) as archive:
                if set(archive.files) != {'p0', 'p1', 'p2'}:
                    raise ValueError('timing pilot catalogue is incomplete')
                context['pilots'] = {key: archive[key] for key in archive.files}
        return context

    def make_timing_frame(self, args, context, snr, block, symbol, manifest):
        frame = context['data'].make_frame(context['system'], 'timing', block,
            snr, scenario='G0', family='F_C', arm_id=symbol,
            timing_purpose=manifest['timing_purpose'])
        if manifest['schema'] == MANIFEST_V2:
            system = context['system']
            frames = pilot_frames(frame, context['pilots'], c1=system.c1, c2=system.c2,
                                  preserve_original_p0=True)
            return frames[context['catalogue']['methods'][symbol]['pilot']]
        return frame

    def telemetry(self, device):
        def query(fields, target):
            command = ['nvidia-smi', '--query-' + target + '=' + fields,
                       '--format=csv,noheader,nounits']
            if target == 'gpu':
                command.extend(['--id=' + TIMING_GPU_UUID])
            return subprocess.run(command, check=True, capture_output=True,
                                  text=True, timeout=10).stdout.strip()
        gpu = query('uuid,memory.free,memory.used,utilization.gpu', 'gpu')
        cells = [x.strip() for x in gpu.split(',')]
        if len(cells) != 4 or cells[0] != TIMING_GPU_UUID:
            raise ValueError('ambiguous GPU telemetry')
        processes = query('gpu_uuid,pid,used_gpu_memory', 'compute-apps')
        pids = []
        for line in processes.splitlines():
            row = [x.strip() for x in line.split(',')]
            if len(row) != 3:
                raise ValueError('ambiguous process telemetry')
            if row[0] == TIMING_GPU_UUID:
                pids.append(int(row[1]))
        return {'status': 'ok', 'gpu_uuid': cells[0],
                'memory_free_MiB': int(cells[1]), 'memory_used_MiB': int(cells[2]),
                'utilization_percent': int(cells[3]), 'compute_pids': pids,
                'observed_unix': time.time(), 'cpu_count': os.cpu_count(),
                'load_average': list(os.getloadavg()),
                'cpu_affinity': sorted(os.sched_getaffinity(0)),
                'numerical_threads': torch.get_num_threads(),
                'interop_threads': torch.get_num_interop_threads()}

    def sync(self, device):
        if torch.device(device).type == 'cuda':
            torch.cuda.synchronize(torch.device(device))


def _assert_unchanged(args, contract, hooks):
    if hooks.sources() != contract['source_sha256']:
        raise ValueError('source package changed during execution')
    for name in ('protocol', 'checkpoint', 'prior', 'representative_freeze',
                 'engineering_protocol'):
        if sha(getattr(args, name)) != contract[name + '_sha256']:
            raise ValueError(name + ' changed during execution')


def _check_deadline(args):
    remaining = args.deadline_unix - time.time()
    if not math.isfinite(remaining) or remaining <= 0:
        raise TimeoutError('COST02 engineering deadline reached')
    return remaining


def _validate_frame(frame, args):
    validate_frame_identity(frame, 'engineering', 0, sha(args.protocol))
    return {
        'metadata': json_value(frame.metadata),
        'y_sha256': array_hash(frame.observed['y']),
        'pilot_sha256': array_hash(frame.observed['pilot'])}


def execute(args, *, hooks=None):
    hooks = hooks or RealHooks()
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    calls = {'F': 0, 'T': 0, 'E': 0}
    records, active, outputs = [], None, {}
    previous = signal.getsignal(signal.SIGALRM)
    try:
        engineering = validate_request(args, hooks)

        def timeout(_signal, _frame):
            raise TimeoutError('COST02 engineering deadline reached')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, _check_deadline(args))

        if shutil.disk_usage(args.out.parent).free < max(
                args.max_output_bytes, engineering['execution_limits']['minimum_disk_free_bytes']):
            raise OSError('insufficient disk for frozen output bound')
        input_sha256 = {
            name: sha(getattr(args, name))
            for name in ('protocol', 'checkpoint', 'prior',
                         'representative_freeze', 'engineering_protocol')}
        source_sha256 = hooks.sources()
        hooks.configure(args.device)
        context = hooks.prepare(args)
        context['args'] = args
        frame_identity = _validate_frame(context['frame'], args)
        _check_deadline(args)
        binding_snapshot = {'source_sha256': source_sha256}
        binding_snapshot.update({name + '_sha256': digest
                                 for name, digest in input_sha256.items()})
        _assert_unchanged(args, binding_snapshot, hooks)
        contract = {'schema': 'COST02-engineering-equivalence-contract-v1',
            'campaign_id': CAMPAIGN_ID, 'purpose': 'engineering observer equivalence; not COST02 pass',
            'engineering_protocol_sha256': args.engineering_protocol_sha256,
            'representative_freeze_sha256': args.representative_freeze_sha256,
            'protocol_sha256': input_sha256['protocol'],
            'checkpoint_sha256': input_sha256['checkpoint'],
            'prior_sha256': input_sha256['prior'],
            'source_sha256': source_sha256,
            'code_sha256': context['code_sha256'], 'block': 0, 'snr_db': 8,
            'symbols': list(SYMBOLS), 'audit_modes': list(MODES),
            'calls_reserved': {'F': 6, 'T': 0, 'E': 0}, 'max_full_calls': 6,
            'device': args.device, 'threads': 1, 'cuda_allocator_fraction': .25
                if str(args.device).startswith('cuda') else None,
            'deadline_unix': args.deadline_unix,
            'max_output_bytes': args.max_output_bytes,
            'measurement_boundary': 'sync; receiver.run; sync; IO/hash/system queries excluded',
            'raw_fields': list(RAW_FIELDS), 'tolerance': TOLERANCE,
            'runtime_versions': {'python': sys.version,
                'numpy': np.__version__, 'torch': torch.__version__,
                'cuda_runtime': torch.version.cuda},
            'frame_identity': frame_identity,
            'command': [sys.executable, *sys.argv]}
        contract['config_sha256'] = hashlib.sha256(json.dumps(
            contract, sort_keys=True, allow_nan=False).encode()).hexdigest()
        contract['ledger'] = hooks.reserve(args.out, contract)
        _bounded_json(args.out / 'contract.json', contract, args.out,
                      args.max_output_bytes-FAILURE_RESERVE_BYTES)
        _assert_unchanged(args, contract, hooks)

        for symbol in SYMBOLS:
            for audit in MODES:
                _check_deadline(args)
                _assert_unchanged(args, contract, hooks)
                current_frame_identity = _validate_frame(context['frame'], args)
                if current_frame_identity != frame_identity:
                    raise ValueError('frame metadata or observed input changed')
                receiver = hooks.build(symbol, context)
                _check_deadline(args)
                if output_bytes(args.out) + PER_TERMINAL_BYTES > (
                        args.max_output_bytes - FAILURE_RESERVE_BYTES):
                    raise OSError('insufficient terminal and failure receipt reserve')
                calls['F'] += 1
                active = {'ordinal': calls['F'], 'symbol': symbol,
                          'audit': audit, 'block': 0, 'snr_db': 8,
                          'input_hashes': context['frame'].metadata['input_hashes'],
                          'frame_metadata': frame_identity['metadata'],
                          'config_sha256': contract['config_sha256']}
                _bounded_json(args.out / f"started-F-{calls['F']:03d}.json",
                              active, args.out,
                              args.max_output_bytes-FAILURE_RESERVE_BYTES)
                hooks.sync(args.device)
                wall, cpu = time.perf_counter(), time.process_time()
                value = receiver.run(context['frame'].observed, audit=audit)
                hooks.sync(args.device)
                seconds, cpu_seconds = (time.perf_counter()-wall,
                                        time.process_time()-cpu)
                _assert_unchanged(args, contract, hooks)
                if _validate_frame(context['frame'], args) != frame_identity:
                    raise ValueError('frame metadata or observed input changed')
                raw = _validate_result(value, audit, context['frame'],
                                       context['code'])
                raw_path = args.out / f"raw-F-{calls['F']:03d}.npz"
                descriptor = _bounded_npz(raw_path, raw, args.out,
                    args.max_output_bytes-FAILURE_RESERVE_BYTES)
                observer = None
                if audit:
                    observer_path = args.out / f"observer-F-{calls['F']:03d}.json"
                    evidence = {
                        'graphs': value.get('graphs'),
                        'support_trace': value.get('support_trace'),
                        'capacity_trace': value.get('capacity_trace'),
                        'dals_event_count': len(value['dals']),
                        'dals_source': 'diagnostic_dals_observer',
                        'dals_storage': 'summary_only; raw matrices not persisted',
                        'dals_summaries': [summarize(state)
                                           for state in value['dals']]}
                    _bounded_json(observer_path, evidence, args.out,
                                  args.max_output_bytes-FAILURE_RESERVE_BYTES)
                    observer = {'path': str(observer_path),
                                'sha256': sha(observer_path)}
                record = {'identity': active, 'seconds': seconds,
                          'CPU_seconds': cpu_seconds, 'raw': descriptor,
                          'observer': observer,
                          'raw_field_sha256': {key: array_hash(raw[key])
                                               for key in RAW_FIELDS},
                          'timing_boundary': 'synchronized receiver.run only',
                          'truth_access': 'none'}
                record_path = args.out / f"record-F-{calls['F']:03d}.json"
                _bounded_json(record_path, record, args.out,
                              args.max_output_bytes-FAILURE_RESERVE_BYTES)
                reference = {'path': str(record_path), 'sha256': sha(record_path),
                             'identity': dict(active), 'raw': descriptor}
                records.append(reference)
                outputs[symbol, audit] = raw
                active = None
        comparisons = [compare_pair(outputs[symbol, True],
                                    outputs[symbol, False], symbol)
                       for symbol in SYMBOLS]
        _assert_unchanged(args, contract, hooks)
        if _validate_frame(context['frame'], args) != frame_identity:
            raise ValueError('frame metadata or observed input changed')
        _check_deadline(args)
        receipt = {'schema': 'COST02-engineering-equivalence-receipt-v1',
            'status': 'complete_engineering_equivalence', 'exitcode': 0,
            'calls': calls, 'records': records, 'comparisons': comparisons,
            'config_sha256': contract['config_sha256'],
            'bindings_reverified_after_calls': True,
            'wall_seconds': time.perf_counter()-started,
            'scope': '6 engineering F only; not COST02 timing, latency pass, or scientific confirmation'}
        _bounded_json(args.out / 'complete.json', receipt, args.out,
                      args.max_output_bytes-FAILURE_RESERVE_BYTES)
        signal.setitimer(signal.ITIMER_REAL, 0)
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        failure = {'status': 'failed', 'exitcode': 1,
            'exception': type(exc).__name__, 'message': str(exc),
            'traceback': traceback.format_exc(), 'calls': calls,
            'active_attempt': active, 'records': records,
            'policy': 'failed and unused reservations remain charged; no retry'}
        try:
            _bounded_json(args.out / 'failure.json', failure, args.out,
                          args.max_output_bytes)
        except Exception as publication_error:
            print('failure receipt publication also failed: ' +
                  repr(publication_error), file=sys.stderr)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _timing_files(args, manifest):
    expected = {args.protocol: manifest['protocol_sha256'],
        args.checkpoint: manifest['checkpoint_sha256'],
        args.representative_freeze: manifest['representative_freeze_sha256'],
        args.global_freeze: manifest['global_freeze_sha256'],
        args.timing_manifest: args.timing_manifest_sha256}
    for snr, path in manifest['_resolved_prior_paths'].items():
        expected[path] = manifest['prior_by_snr'][str(snr)]['sha256']
    authorization = manifest['authorization']
    expected[_manifest_path(args.timing_manifest, authorization['evidence_path'])] = authorization['evidence_sha256']
    expected.update(manifest['_pilot_bound_files'])
    expected.update(manifest.get('_catalogue_files', {}))
    if any(sha(path) != digest for path, digest in expected.items()):
        raise ValueError('timing bound input changed after validation')
    return {str(Path(path).resolve()): digest for path, digest in expected.items()}


def _timing_unchanged(contract, hooks, guard=None):
    if hooks.sources() != contract['source_sha256']:
        raise ValueError('timing source changed during collection')
    if guard is not None:
        guard.check()
    elif any(sha(path) != digest for path, digest in contract['files'].items()):
        raise ValueError('timing bound input file changed during collection')


def _timing_frame_identity(frame, args, manifest, snr, block, symbol):
    meta = frame.metadata
    expected = {'campaign_id': CAMPAIGN_ID, 'split': 'timing', 'block': block,
        'snr_db': snr, 'family': 'F_C', 'arm_id': symbol, 'scenario': 'G0',
        'protocol_sha256': sha(args.protocol)}
    if any(meta.get(key) != value for key, value in expected.items()):
        raise ValueError('timing frame identity differs from admitted request')
    authority = meta.get('confirmation_authority', {})
    if (authority.get('manifest_sha256') != args.timing_manifest_sha256 or
            authority.get('timing_purpose') != manifest['timing_purpose']):
        raise ValueError('timing frame lacks the requested data authority')
    hashes = {key: array_hash(value) for key, value in frame.observed.items()}
    if (set(hashes) != {'y', 'pilot', 'sigma2', 'constellation'} or
            any(hashes[key] != meta.get('input_hashes', {}).get(key)
                for key in ('y', 'pilot'))):
        raise ValueError('timing observed input hashes differ')
    if manifest.get('schema') == MANIFEST_V2:
        if (meta.get('pilot_id') != manifest['catalogue']['methods'][symbol]['pilot'] or
                not isinstance(meta.get('power'), dict) or
                type(meta['power'].get('passes_declared_simulation_power_gate')) is not bool):
            raise ValueError('timing pilot identity or power evidence differs')
        for key in ('H', 'data', 'noise', 'info', 'coded'):
            if array_hash(frame._truth[key]) != meta['input_hashes'].get(key):
                raise ValueError('timing exogenous input hashes differ')
    return {'metadata': json_value(meta), 'observed_hashes': hashes}


def _timing_pairing(identity, manifest):
    observed, meta = identity['observed_hashes'], identity['metadata']
    if manifest.get('schema') != MANIFEST_V2:
        return (observed, meta['input_hashes']), 'p0', observed
    common = ({key: meta['input_hashes'][key] for key in
               ('H', 'data', 'noise', 'info', 'coded')},
              {key: observed[key] for key in ('sigma2', 'constellation')})
    return common, meta['pilot_id'], {key: observed[key] for key in ('y', 'pilot')}


def _check_telemetry(value, *, real):
    if (not isinstance(value, dict) or value.get('status') != 'ok' or
            value.get('gpu_uuid') != TIMING_GPU_UUID or
            not isinstance(value.get('compute_pids'), list) or
            any(type(pid) is not int or pid < 1 for pid in value['compute_pids']) or
            len(set(value['compute_pids'])) != len(value['compute_pids'])):
        raise ValueError('unavailable or ambiguous GPU telemetry')
    if any(pid != os.getpid() for pid in value['compute_pids']):
        raise ValueError('foreign GPU process; timing collection stopped')
    stamp = value.get('observed_unix')
    if type(stamp) not in (float, int) or not 0 <= time.time()-stamp <= 30:
        raise ValueError('GPU telemetry timestamp is unavailable or stale')
    if real:
        cores, load = value.get('cpu_count'), value.get('load_average')
        affinity = value.get('cpu_affinity')
        numerical = value.get('numerical_threads')
        interop = value.get('interop_threads')
        if (type(cores) is not int or cores <= 16 or not isinstance(load, list)
                or len(load) != 3 or any(not math.isfinite(x) for x in load)
                or load[0] >= cores-16 or not isinstance(affinity,list) or
                not affinity or len(set(affinity))!=len(affinity) or
                any(type(cpu) is not int or cpu<0 or cpu>=cores for cpu in affinity) or
                numerical != 1 or interop != 1):
            raise ValueError('CPU telemetry cannot verify one thread, affinity, and approximately16-core host headroom')
        free = value.get('memory_free_MiB')
        used, util = value.get('memory_used_MiB'), value.get('utilization_percent')
        if (any(type(x) is not int for x in (free, used, util)) or free < 6144
                or used < 0 or not 0 <= util <= 100 or
                (used > 18*1024 and util > 90)):
            raise ValueError('GPU memory/contamination telemetry gate failed')


def _real_timing_paths(args):
    if (os.environ.get('CUDA_VISIBLE_DEVICES') != TIMING_GPU_UUID or
            args.device not in ('cuda', 'cuda:0') or args.allow_cpu):
        raise ValueError('real timing requires the explicitly isolated frozen CUDA UUID')
    for key in ('out', 'protocol', 'checkpoint', 'representative_freeze',
                'global_freeze', 'timing_manifest', 'timing_ledger'):
        if not Path(getattr(args, key)).resolve().is_relative_to('/data/guoyikun'):
            raise ValueError('real timing paths must stay under /data/guoyikun')
    if Path(args.timing_ledger).resolve() != TIMING_REMOTE_ROOT/'cost02-timing-ledger':
        raise ValueError('real timing must use the canonical campaign timing ledger')


def execute_timing(args, *, hooks=None):
    real = hooks is None or isinstance(hooks, RealHooks)
    hooks = hooks or RealHooks()
    if real:
        _real_timing_paths(args)
    manifest = validate_timing_request(args, hooks, real=real)
    bound_files = _timing_files(args, manifest)
    guard = BoundFiles(bound_files)
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    calls = {'F': 0, 'T': 0, 'E': 0}
    measured, warmups, active, reservation = [], [], None, None
    last_started = None
    telemetry_records, order_records = [], []
    previous = signal.getsignal(signal.SIGALRM)
    lock = None
    limit = args.max_output_bytes-FAILURE_RESERVE_BYTES
    meter = OutputMeter(args.out, limit)

    def publish(name, value):
        _bounded_json(args.out/name, value, args.out, limit, meter=meter)

    def telemetry(name):
        value = hooks.telemetry(args.device)
        # Persist even rejected observations; a stop cannot erase contamination.
        publish(name, value)
        telemetry_records.append({'path': str(args.out/name), 'sha256': sha(args.out/name)})
        _check_telemetry(value, real=real)
        return value

    try:
        def timeout(_signal, _frame):
            raise TimeoutError('finite timing collection deadline reached')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, _check_deadline(args))
        if shutil.disk_usage(args.out.parent).free < manifest['resource_limits']['minimum_disk_free_bytes']:
            raise OSError('insufficient timing disk reserve')
        Path(args.timing_ledger).mkdir(parents=True, exist_ok=True)
        lock = (Path(args.timing_ledger)/'collection.lock').open('a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('another timing collection owns the device lane') from exc
        hooks.configure(args.device)
        telemetry('telemetry-initial.json')
        setup = time.perf_counter()
        context = hooks.prepare_timing(args, manifest)
        context['args'] = args
        meter.adopt_tree(args.out/'code-cache')
        contract = {'schema': 'COST02-timing-contract-v1',
            'campaign_id': CAMPAIGN_ID, 'source_sha256': manifest['source_manifest'],
            'files': bound_files,
            'manifest_sha256': args.timing_manifest_sha256,
            'purpose': manifest['timing_purpose'], 'code_sha256': context['code_sha256'],
            'calls_reserved': manifest['calls'], 'device': args.device, 'pid': os.getpid(),
            'runtime_versions': {'python': sys.version, 'numpy': np.__version__,
                'torch': torch.__version__, 'cuda_runtime': torch.version.cuda},
            'fixture_only': not real, 'measurement_boundary': TIMING_BOUNDARY,
            'setup_seconds': time.perf_counter()-setup,
            'model_policy': 'fresh independent receiver per call; static loading timed separately',
            'warmup_policy': 'charged repeats of first admitted block; excluded from n',
            'deadline_unix': args.deadline_unix,
            'max_output_bytes': args.max_output_bytes,
            'storage_policy': {'per_call_retained_bytes': PER_TIMING_CALL_ESTIMATE_BYTES,
                'single_call_scratch_bytes': TIMING_SCRATCH_BYTES,
                'auxiliary_reserve_bytes': TIMING_AUXILIARY_RESERVE_BYTES},
            'cpu_policy': ('one numerical thread; recorded affinity and host load '
                'must leave approximately16-core shared-machine headroom; no exclusive CPU reservation claim'),
            'telemetry_scope': 'actual occupancy at block boundaries; no continuous guarantee'}
        if manifest['schema'] == MANIFEST_V2:
            contract.update(catalogue=manifest['catalogue'],
                            collection_manifest_schema=MANIFEST_V2)
        _timing_unchanged(contract, hooks, guard)
        contract['config_sha256'] = hashlib.sha256(json.dumps(
            contract, sort_keys=True, allow_nan=False).encode()).hexdigest()
        reservation = reserve_timing(args.timing_ledger, args.out,
            args.timing_manifest_sha256, manifest, contract['config_sha256'],
            real=real)
        contract['reservation'] = reservation
        publish('contract.json', contract)
        measured_n = {str(snr): 0 for snr in manifest['requested_snr_cells']}
        group = 0
        for snr in manifest['requested_snr_cells']:
            start = manifest['block_start']
            groups = [('warmup', start, repeat) for repeat in
                      range(manifest['warmup_by_snr'][str(snr)])]
            groups += [('measured', block, None) for block in
                       range(start, start+manifest['n_by_snr'][str(snr)])]
            for phase, block, repeat in groups:
                group += 1
                _check_deadline(args)
                _timing_unchanged(contract, hooks, guard)
                order = timing_order(snr, block, manifest['arm_ids'])
                order_name = f'order-{group:06d}.json'
                publish(order_name, {'group': group, 'phase': phase,
                    'block': block, 'snr_db': snr, 'repeat': repeat, 'order': order})
                order_records.append({'path': str(args.out/order_name), 'sha256': sha(args.out/order_name)})
                telemetry(f'telemetry-{group:06d}-before.json')
                paired, pilot_pairs = None, {}
                for symbol in order:
                    _check_deadline(args)
                    generation = time.perf_counter()
                    frame = hooks.make_timing_frame(args, context, snr, block, symbol, manifest)
                    generation_seconds = time.perf_counter()-generation
                    identity = _timing_frame_identity(frame, args, manifest, snr, block, symbol)
                    pairing, pilot_id, pilot_pair = _timing_pairing(identity, manifest)
                    if paired is not None and pairing != paired:
                        raise ValueError('timing paired input changed across methods')
                    if pilot_id in pilot_pairs and pilot_pairs[pilot_id] != pilot_pair:
                        raise ValueError('timing paired observation changed within the same pilot')
                    paired = pairing
                    pilot_pairs[pilot_id] = pilot_pair
                    setup = time.perf_counter()
                    receiver = hooks.build_timing(symbol, context, snr,
                                      manifest['_resolved_prior_paths'][snr])
                    setup_seconds = time.perf_counter()-setup
                    _timing_unchanged(contract, hooks, guard)
                    remaining = manifest['calls']['F']-calls['F']-1
                    if (remaining < 0 or meter.used+TIMING_SCRATCH_BYTES+
                            (remaining+1)*PER_TIMING_CALL_ESTIMATE_BYTES+
                            TIMING_AUXILIARY_RESERVE_BYTES > limit):
                        raise OSError('timing output storage exhausted before receiver call')
                    call_output_before = meter.used
                    calls['F'] += 1
                    active = {'ordinal': calls['F'], 'purpose': manifest['timing_purpose'],
                        'phase': phase, 'group': group, 'snr_db': snr, 'block': block,
                        'repeat': repeat, 'symbol': symbol, 'audit': False,
                        'frame_identity': identity, 'config_sha256': contract['config_sha256']}
                    publish(f'started-F-{calls["F"]:06d}.json', active)
                    started_path=args.out/f'started-F-{calls["F"]:06d}.json'
                    last_started={'path':str(started_path),'sha256':sha(started_path),
                                  'identity':_schedule_identity(active)}
                    hooks.sync(args.device)
                    wall, cpu = time.perf_counter(), time.process_time()
                    result = receiver.run(frame.observed, audit=False)
                    hooks.sync(args.device)
                    seconds, cpu_seconds = time.perf_counter()-wall, time.process_time()-cpu
                    _timing_unchanged(contract, hooks, guard)
                    if _timing_frame_identity(frame, args, manifest, snr, block, symbol) != identity:
                        raise ValueError('timing frame input mutated by receiver')
                    raw = _validate_result(result, False, frame, context['code'])
                    descriptor = _bounded_npz(args.out/f'raw-F-{calls["F"]:06d}.npz',
                                             raw, args.out, limit, meter=meter)
                    if descriptor['bytes'] > PER_TIMING_CALL_ESTIMATE_BYTES:
                        raise OSError('timing raw output exceeded admitted per-call retention bound')
                    record = {'identity': active, 'seconds': seconds, 'CPU_seconds': cpu_seconds,
                        'generation_seconds': generation_seconds, 'model_setup_seconds': setup_seconds,
                        'raw': descriptor, 'raw_field_sha256': {key: array_hash(value)
                            for key, value in raw.items()}, 'truth_access': 'none',
                        'block_validity': 'requires successful after-block telemetry'}
                    if manifest['schema'] == MANIFEST_V2:
                        record['receiver_qualification'] = {key: json_value(result[key])
                            for key in ('baseline_eligible', 'deployment_eligible',
                                        'baseline_stationary', 'baseline_eligibility_scope')
                            if key in result}
                    name = f'record-F-{calls["F"]:06d}.json'
                    publish(name, record)
                    if (meter.used-call_output_before >
                            PER_TIMING_CALL_ESTIMATE_BYTES):
                        raise OSError('timing call output exceeded admitted retention bound')
                    reference = {'path': str(args.out/name), 'sha256': sha(args.out/name),
                                 'identity': _schedule_identity(active), 'raw': descriptor}
                    (measured if phase == 'measured' else warmups).append(reference)
                    active = None
                    del receiver, frame, result, raw
                telemetry(f'telemetry-{group:06d}-after.json')
                if phase == 'measured':
                    measured_n[str(snr)] += 1
        _timing_unchanged(contract, hooks, guard)
        guard.verify()
        meter.verify()
        _check_deadline(args)
        if calls != manifest['calls']:
            raise ValueError('timing completed identities do not match reservation')
        complete = {'schema': 'COST02-timing-receipt-v1',
            'status': 'complete_collection_only', 'exitcode': 0, 'calls': calls,
            'measured_n_by_snr': measured_n, 'measured_records': measured,
            'warmup_records': warmups, 'uncollected_snr_cells': [snr for snr in
                TIMING_SNRS if snr not in manifest['requested_snr_cells']],
            'telemetry_records': telemetry_records, 'order_records': order_records,
            'admitted_n_by_snr': manifest['n_by_snr'],
            'config_sha256': contract['config_sha256'], 'reservation': reservation,
            'wall_seconds': time.perf_counter()-started, 'fixture_only': not real,
            'storage_policy': {'per_call_retained_bytes': PER_TIMING_CALL_ESTIMATE_BYTES,
                'single_call_scratch_bytes': TIMING_SCRATCH_BYTES,
                'auxiliary_reserve_bytes': TIMING_AUXILIARY_RESERVE_BYTES},
            'cpu_policy': ('one numerical thread; recorded affinity and host load '
                'must leave approximately16-core shared-machine headroom; no exclusive CPU reservation claim'),
            'deployment_cost_pass': False,
            'scope': 'collection only; simultaneous cost analysis outstanding'}
        if manifest['schema'] == MANIFEST_V2:
            complete.update(catalogue=manifest['catalogue'], collection_manifest_schema=MANIFEST_V2)
        publish('complete.json', complete)
        meter.verify()
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        record_references=measured+warmups
        failure = {'status': 'invalid_incomplete', 'exitcode': 1, 'calls': calls,
            'active_attempt': _schedule_identity(active), 'last_started':last_started,
            'reservation': reservation,
            'telemetry_records': _compact_references(telemetry_records,'telemetry-*.json'),
            'order_records': _compact_references(order_records,'order-*.json'),
            'records': _compact_references(record_references,'record-F-*.json and raw-F-*.npz'),
            'preserved_output_root':str(args.out), 'failure_receipt_compacted':True,
            'exception': type(exc).__name__,
            'message': str(exc)[:4096], 'traceback': traceback.format_exc()[-16384:],
            'policy': 'all reservations remain charged; no retry or substitute blocks'}
        try:
            _bounded_json(args.out/'failure.json', failure, args.out, args.max_output_bytes)
        except Exception as publication_error:
            print('timing failure publication failed: '+repr(publication_error), file=sys.stderr)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if lock is not None:
            lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'checkpoint', 'representative-freeze', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('prior', 'engineering-protocol', 'timing-manifest', 'timing-ledger',
                 'global-freeze'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--mode', choices=('engineering', *TIMING_PURPOSES), default='engineering')
    parser.add_argument('--representative-freeze-sha256', required=True)
    parser.add_argument('--engineering-protocol-sha256')
    parser.add_argument('--timing-manifest-sha256')
    parser.add_argument('--global-freeze-sha256')
    parser.add_argument('--deadline-unix', type=float, required=True)
    parser.add_argument('--max-output-bytes', type=int, required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--allow-cpu', action='store_true')
    args = parser.parse_args()
    return execute(args) if args.mode == 'engineering' else execute_timing(args)


if __name__ == '__main__':
    sys.exit(main())
