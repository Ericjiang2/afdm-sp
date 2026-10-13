"""Versioned, bounded continuation of the existing supplement campaign.

This contract does not relax the original timing contract. The new three-arm
study has its own declared precision limits, while using the old RNG identities,
generator, immutable publication, and canonical reservation directories.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
from pathlib import Path
import time

from .budgeted_frame_store import publish_json

SCHEMA = 'afdm-bounded-supplement-v1'
RESERVATION_SCHEMA = 'afdm-bounded-supplement-reservation-v1'
SCOPE_ID = 'afdm-i1-cost-adjacent-20260911'
CAMPAIGN = 'afdm-supplement-20260909-090115'
ARMS = ('I1', 'A2', 'B_star_1')
CAPS = {'engineering': 54, 'confirm': 18432, 'development': 1536,
        'cost-warmup': 90, 'cost-measurement': 4608}
DOMAINS = {'engineering': ('engineering', None), 'confirm': ('confirm', 'F_I'),
           'development': ('design', None), 'cost-warmup': ('timing', 'F_C'),
           'cost-measurement': ('timing', 'F_C')}
FLOORS = {'engineering': 32, 'design': 192, 'confirm': 0, 'timing': 1537}
DEADLINE = 1789209000.0  # 2026-09-12 10:30 UTC; inherited, never reset by a run.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_scope(manifest):
    if (manifest.get('schema') != SCHEMA or manifest.get('scope_id') != SCOPE_ID
            or manifest.get('campaign_id') != CAMPAIGN
            or manifest.get('status') != 'frozen'
            or manifest.get('physical_N') != 1024):
        raise ValueError('unknown bounded supplement scope or physical configuration')
    deadline = manifest.get('deadline_unix')
    if (not isinstance(deadline, (int, float)) or not math.isfinite(deadline)
            or deadline > DEADLINE or deadline <= time.time()):
        raise ValueError('bounded supplement deadline expired or extended')
    domains = manifest.get('data_scopes')
    if not isinstance(domains, dict) or set(domains) != set(DOMAINS):
        raise ValueError('bounded supplement purposes are incomplete')
    for purpose, (split, family) in DOMAINS.items():
        row = domains[purpose]
        start, stop = row.get('block_start'), row.get('block_stop')
        snrs, arms = row.get('snrs'), row.get('arm_ids')
        if (row.get('split') != split or row.get('family') != family
                or type(start) is not int or type(stop) is not int
                or not FLOORS[split] <= start < stop
                or not isinstance(snrs, list) or snrs != ([7, 8] if purpose == 'development' else [7, 8, 9])
                or not isinstance(arms, list) or not arms or len(arms) != len(set(arms))
                or any(not isinstance(a, str) or not a for a in arms)
                or row.get('max_F') != CAPS[purpose]):
            raise ValueError('bounded supplement domain differs: ' + purpose)
        if purpose != 'development' and set(arms) != set(ARMS):
            raise ValueError('bounded study must retain the three frozen references')
        if purpose == 'confirm' and stop - start != 2048:
            raise ValueError('I1 confirmation requires the prospective fixed 2048 blocks')
        if purpose == 'development' and (stop - start != 128 or len(arms) > 6):
            raise ValueError('development is restricted to 128 blocks and six calls per cell')
        if purpose.startswith('cost-') and stop - start != (10 if purpose == 'cost-warmup' else 512):
            raise ValueError('new cost scope requires 10 warmup / 512 measurement blocks')
    ordered = list(domains.values())
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            if ((left['split'], left['family']) == (right['split'], right['family'])
                    and left['block_start'] < right['block_stop']
                    and right['block_start'] < left['block_stop']):
                raise ValueError('new purpose ranges overlap')
    limits = manifest.get('resource_limits', {})
    if (limits.get('new_peak_bytes') != 200_000_000_000
            or limits.get('cost_wall_seconds') != 36000
            or limits.get('cpu_workers_max') != 32
            or limits.get('cpu_headroom') != 16
            or limits.get('threads_per_worker') != 1
            or limits.get('gpu_workers_max') != 2):
        raise ValueError('bounded resource contract differs from user authorization')
    return domains


def validate_request(manifest, *, split, purpose, family, arm, block, snr, scenario):
    domains = validate_scope(manifest)
    if purpose not in domains or purpose not in manifest.get('admitted_purposes', []):
        raise ValueError('explicit bounded supplement purpose required')
    row = domains[purpose]
    if ((split, family) != (row['split'], row['family']) or scenario != 'G0'
            or arm not in row['arm_ids'] or snr not in row['snrs']
            or type(block) is not int or not row['block_start'] <= block < row['block_stop']):
        raise ValueError('request is outside its frozen purpose, arm or data range')
    return row


def validate_history(manifest):
    """Check all old reservations, including failed and unused allocations."""
    history = manifest.get('history')
    if not isinstance(history, dict) or not history.get('ledger_files'):
        raise ValueError('historical ledger inventory is required')
    for path, expected in history['ledger_files'].items():
        if sha(path) != expected:
            raise ValueError('historical reservation changed: ' + path)
    for directory, expected in history['ledger_inventory'].items():
        found = {str(path.resolve()) for path in Path(directory).glob('*.json')
                 if json.loads(path.read_text()).get('scope_id') != SCOPE_ID}
        if found != set(expected):
            raise ValueError('historical reservation inventory changed: ' + directory)


def identity_key(row):
    return (row['split'], row['family'], row['block'], row['snr_db'],
            row['arm'], row['repeat'])


def reserve(manifest, manifest_path, manifest_sha256, out, purpose, identities, *, bytes_reserved):
    """Append to canonical ledgers, using their locks and one shared scope lock.

    Prior reservations stay charged. New limits are additive user-authorized
    quotas, not a reset of the exhausted original engineering or timing quota.
    """
    if sha(manifest_path) != manifest_sha256:
        raise ValueError('scope manifest changed before reservation')
    validate_scope(manifest)
    if not identities or type(bytes_reserved) is not int or bytes_reserved < 1:
        raise ValueError('finite call and storage reservation required')
    for row in identities:
        validate_request(manifest, split=row['split'], purpose=purpose,
            family=row['family'], arm=row['arm'], block=row['block'],
            snr=row['snr_db'], scenario='G0')
        repeat_limit = 3 if purpose == 'engineering' else 1
        if type(row['repeat']) is not int or not 0 <= row['repeat'] < repeat_limit:
            raise ValueError('unregistered repeat or retry')
    keys = {identity_key(row) for row in identities}
    if len(keys) != len(identities):
        raise ValueError('duplicate requested call identity')
    ledger_paths = {name: Path(path) for name, path in manifest['ledger_paths'].items()}
    if set(ledger_paths) != set(CAPS):
        raise ValueError('every purpose must bind its canonical ledger')
    ledger = ledger_paths[purpose]
    ledger.mkdir(parents=True, exist_ok=True)
    scope_lock = Path(manifest['scope_lock'])
    with scope_lock.open('a') as global_lock, (ledger / '.lock').open('a') as local_lock:
        fcntl.flock(global_lock, fcntl.LOCK_EX)
        fcntl.flock(local_lock, fcntl.LOCK_EX)
        validate_history(manifest)
        used, all_keys, reserved_bytes = 0, set(), 0
        for directory in set(ledger_paths.values()):
            for path in directory.glob('reservation-*.json'):
                row = json.loads(path.read_text())
                if row.get('scope_id') != SCOPE_ID:
                    continue
                if (row.get('schema') != RESERVATION_SCHEMA
                        or row.get('campaign_id') != CAMPAIGN
                        or row['calls_reserved']['F'] != len(row['identities'])):
                    raise ValueError('invalid bounded reservation in canonical ledger')
                if row['purpose'] == purpose:
                    used += row['calls_reserved']['F']
                previous = {identity_key(item) for item in row['identities']}
                if len(previous) != len(row['identities']) or all_keys & previous:
                    raise ValueError('existing bounded reservation identities overlap')
                all_keys |= previous
                reserved_bytes += row['bytes_reserved']
        if keys & all_keys or used + len(keys) > CAPS[purpose]:
            raise ValueError('call identity reused or bounded quota exceeded')
        if reserved_bytes + bytes_reserved + manifest['auxiliary_bytes_reserved'] > 200_000_000_000:
            raise ValueError('all-run disk reservations exceed 200 GB')
        path = ledger / ('reservation-' + hashlib.sha256(str(Path(out).resolve()).encode()).hexdigest() + '.json')
        value = dict(schema=RESERVATION_SCHEMA, scope_id=SCOPE_ID, campaign_id=CAMPAIGN,
            purpose=purpose, out=str(Path(out).resolve()), manifest_path=str(Path(manifest_path).resolve()),
            manifest_sha256=manifest_sha256, calls_reserved={'F': len(keys), 'T': 0, 'E': 0},
            bytes_reserved=bytes_reserved, identities=identities,
            reserved_at_unix=time.time(), deadline_unix=manifest['deadline_unix'],
            policy='additive bounded authorization; failed and unused reservations remain charged; no automatic retry')
        publish_json(path, value)
    return dict(path=str(path), sha256=sha(path), calls_reserved=value['calls_reserved'])
