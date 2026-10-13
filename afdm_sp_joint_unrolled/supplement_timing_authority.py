"""Shared signed historical-range boundary for COST-02 collector and generator."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

MANIFEST_V1 = 'COST02-timing-collection-manifest-v1'
MANIFEST_V2 = 'COST02-timing-collection-manifest-v2'
AUTHORIZATION_SCHEMA = 'COST02-timing-authorization-v1'
PURPOSES = ('timing-pilot', 'timing-confirmation')
SCOPE_KEYS = ('campaign_id', 'protocol_sha256', 'global_freeze_sha256',
              'family', 'scenario', 'ledger_path')
PILOT_BINDINGS = ('source_manifest', 'arm_ids', 'ledger_path',
    'protocol_sha256', 'global_freeze_sha256', 'checkpoint_sha256',
    'representative_freeze_sha256', 'order_rule', 'measurement_boundary',
    'prior_by_snr')


def timing_request_sha256(manifest):
    request = {key: value for key, value in manifest.items()
               if key != 'authorization' and not key.startswith('_')}
    return hashlib.sha256(json.dumps(request, sort_keys=True,
        allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def _read(binding, parent, files):
    if (not isinstance(binding, dict) or not isinstance(binding.get('path'), str)
            or not binding['path'].strip()):
        raise ValueError('timing history binding path missing')
    path = Path(binding['path'])
    if not path.is_absolute():
        path = Path(parent).parent/path
    path = path.resolve()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError('timing history file cannot be read') from exc
    digest = binding.get('sha256')
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('timing history SHA-256 mismatch')
    if str(path) in files and files[str(path)] != digest:
        raise ValueError('timing history has conflicting content bindings')
    files[str(path)] = digest
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('timing history must contain JSON objects')
    return value, path


def _authorization(manifest, path, files):
    auth = manifest.get('authorization')
    if not isinstance(auth, dict) or auth.get('status') != 'accepted':
        raise ValueError('timing history authorization is not accepted')
    evidence, _ = _read({'path': auth.get('evidence_path'),
                        'sha256': auth.get('evidence_sha256')}, path, files)
    if (evidence.get('schema') != AUTHORIZATION_SCHEMA or
            evidence.get('status') != 'accepted' or
            not isinstance(evidence.get('source'), str) or not evidence['source'].strip() or
            not isinstance(evidence.get('authorized'), list) or
            'F_C:'+manifest['timing_purpose'] not in evidence['authorized'] or
            evidence.get('request_sha256') != timing_request_sha256(manifest)):
        raise ValueError('timing history authorization does not bind the request')


def validate_authorization(manifest, manifest_path):
    files = {}
    _authorization(manifest, manifest_path, files)
    return next(iter(files.items()))


def _shape(manifest, scope):
    counts = manifest.get('n_by_snr')
    arms = manifest.get('arm_ids')
    requested = manifest.get('requested_snr_cells')
    warmups = manifest.get('warmup_by_snr')
    if (manifest.get('schema') not in (MANIFEST_V1, MANIFEST_V2) or
            manifest.get('status') != 'accepted_for_collection' or
            manifest.get('issue') != 'COST-02' or manifest.get('family') != 'F_C' or
            manifest.get('scenario') != 'G0' or manifest.get('proceed_timing') is not True or
            manifest.get('timing_purpose') not in PURPOSES or
            any(manifest.get(key) != scope.get(key) for key in SCOPE_KEYS) or
            type(manifest.get('block_start')) is not int or manifest['block_start'] < 0 or
            not isinstance(counts, dict) or set(counts) != {'7', '8', '9'} or
            any(type(n) is not int or n < 1 for n in counts.values()) or
            not isinstance(arms, list) or not arms or
            any(not isinstance(a, str) or not a for a in arms) or len(set(arms)) != len(arms) or
            not isinstance(requested, list) or not requested or
            any(type(snr) is not int or snr not in (7, 8, 9) for snr in requested) or
            len(set(requested)) != len(requested) or
            not isinstance(warmups, dict) or set(warmups) != {'7', '8', '9'} or
            any(type(n) is not int or n < 0 for n in warmups.values())):
        raise ValueError('timing history scope, schema or range differs')


def _range(manifest, path, scope, files, trail):
    key = str(Path(path).resolve())
    if key in trail:
        raise ValueError('timing history contains a cycle')
    trail = (*trail, key)
    _shape(manifest, scope)
    _authorization(manifest, path, files)
    start = manifest['block_start']
    stop = start+max(manifest['n_by_snr'].values())
    v2 = manifest['schema'] == MANIFEST_V2
    if manifest['timing_purpose'] == 'timing-pilot':
        if any(k in manifest for k in ('pilot_manifest_path', 'pilot_manifest_sha256')):
            raise ValueError('timing pilot cannot link another pilot')
        references = manifest.get('excluded_manifests') if v2 else []
        if not isinstance(references, list):
            raise ValueError('v2 pilot requires explicit excluded_manifests')
        if not v2 and 'excluded_manifests' in manifest:
            raise ValueError('legacy pilot cannot change its historical boundary')
        excluded, ranges = {}, []
        for reference in references:
            previous, previous_path = _read(reference, path, files)
            if str(previous_path) in excluded:
                raise ValueError('duplicate timing history manifest')
            left, right, _ = _range(previous, previous_path, scope, files, trail)
            if any(left < b and a < right for a, b in ranges):
                raise ValueError('timing history reserved ranges overlap')
            ranges.append((left, right))
            excluded[str(previous_path)] = reference['sha256']
        if start != max((right for _, right in ranges), default=0):
            raise ValueError('timing pilot start does not exclude the whole history')
        return start, stop, excluded

    if any(n < 1024 for n in manifest['n_by_snr'].values()):
        raise ValueError('formal timing requires at least 1024 samples per SNR')
    if 'excluded_manifests' in manifest:
        raise ValueError('formal timing history must come from its pilot')
    pilot, pilot_path = _read({'path': manifest.get('pilot_manifest_path'),
        'sha256': manifest.get('pilot_manifest_sha256')}, path, files)
    _, pilot_stop, excluded = _range(pilot, pilot_path, scope, files, trail)
    bindings = (*PILOT_BINDINGS, 'catalogue', 'selection') if v2 else PILOT_BINDINGS
    if (pilot.get('schema') != manifest['schema'] or
            pilot.get('timing_purpose') != 'timing-pilot' or start != pilot_stop or
            any(key not in manifest or manifest[key] != pilot.get(key) for key in bindings) or
            not set(manifest.get('requested_snr_cells', [])).issubset(
                pilot.get('requested_snr_cells', []))):
        raise ValueError('formal timing does not bind the same complete pilot')
    return start, stop, {**excluded, str(pilot_path): manifest['pilot_manifest_sha256']}


def validate_boundary(manifest, manifest_path):
    """Validate ranges and authorization, without generating or admitting calls.

    Expired reservations still exclude their complete original ranges. A formal
    run derives its history from its pilot. Actual ledger coverage is checked
    under the collector's reservation lock, not inferred from this JSON graph.
    """
    if manifest.get('schema') != MANIFEST_V2:
        raise ValueError('shared timing boundary requires the v2 manifest')
    files = {}
    start, stop, excluded = _range(manifest, manifest_path, manifest, files, ())
    return {'block_start': start, 'block_stop': stop, 'files': files,
            'excluded_manifests': excluded}
