"""Extend deinlab's checksum-bound frame inventory after the full scan timeout."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from frames import FIRST, LEGACY_STDOUT, WATCH_SUFFIXES, ranges, scan_file

BASE = 'experiments/unified_cov_prospective_20261119/out/phase1_20261119/frames_deinlab_raw.json'
BASE_SHA256 = '0b06f38b0928ab87eed949b155b0dc49c0928ed66425fc6cbe30373f02e2323d'
CONFIG_AUDIT = BASE.replace('_raw.json', '_configs.json')
CONFIG_AUDIT_SHA256 = 'b083e5df7a36bf27f35606bb199f6a00b856cbbb7698ce5a13aa0b05131bd69e'
# This is before the archived scan started, so later changes are checked twice.
SINCE = datetime(2026, 11, 19, 2, 0, tzinfo=timezone.utc)
NUMAX = 'experiments/tcom_reference_frame_20261015/out/s0/numax.json'
NUMAX_SHA256 = '3349c542e44a8fbbf6c1cbbdc10881f2550f58e7554d010ac7aa2946305be9e1'
STOPPED_DIAGNOSTIC = 'experiments/gate_sbl_test_20261119/out/phase1_v2_20261119/sbl_g3.json'
STOPPED_SHA256 = '6e334689592aaec46ce040bfb9af57a682f68fcfb8f3c25c5895629a0612f2e5'
SCREEN = 'experiments/gate_screen_20261119/out/screen.json'
SCREEN_SHA256 = '86f0b012adfd0ab4697d6ef130f92a6aca59bba9f45e90c4640498bcd8e6f02f'


def checked_json(path, expected):
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected:
        raise ValueError(f'Frozen audit evidence differs: {path}')
    return json.loads(data)


def covered(path):
    parts = path.parts
    return ((len(parts) > 3 and parts[0] == 'experiments' and parts[2] == 'out')
            or (len(parts) > 2 and parts[0] == 'afdm_sp_joint_unrolled'
                and parts[1].startswith('outputs_')))


def combine(target, additional):
    for name, blocks in additional.items():
        if name not in target:
            target[name] = blocks
        elif target[name] != blocks:
            target[name] = ranges(n for block in [*target[name], *blocks]
                                  for n in range(block[0], block[-1] + 1))


def audit(root):
    prior = checked_json(root/BASE, BASE_SHA256)
    numax = checked_json(root/NUMAX, NUMAX_SHA256)
    if numax['_config']['args']['stage'] != 'numax':
        raise ValueError('Expected the S0 Doppler Monte Carlo calibration record')
    # S0's --frames specifies the size of a sequential RNG draw, with no P1 frame IDs.
    hits, errors, scanned = {}, {}, Counter()
    for item in prior['hits']:
        if item['file'] != NUMAX:
            blocks = [[max(FIRST, b[0]), b[-1]] for b in item['frames'] if b[-1] >= FIRST]
            if blocks:
                hits[item['file']] = blocks
    for item in prior['errors']:
        name = item['file']
        if not (Path(name).name.startswith('._') or name == LEGACY_STDOUT):
            errors[name] = item['error']

    roots = [root/'experiments', root/'issues', root/'.mission', root/'results', root/'.trellis/tasks']
    roots.extend((root/'afdm_sp_joint_unrolled').glob('outputs_*'))
    for scope in (p for p in roots if p.is_dir()):
        for folder, dirs, files in os.walk(scope):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'gamma0_exchange_20261120', '11-20-gamma0-exchange')]
            for name in files:
                suffix = name.lower()
                if name.startswith('._') or not suffix.endswith(WATCH_SUFFIXES + ('.py', '.md', '.txt', '.log')):
                    continue
                path = Path(folder)/name
                relative = path.relative_to(root)
                rel = str(relative)
                if rel in (BASE, NUMAX) or relative.parts[0] == 'issues' or suffix.endswith(('.json', '.json.gz')):
                    continue  # Covered by the additional manifest scan.
                if covered(relative) and suffix.endswith(WATCH_SUFFIXES):
                    if path.stat().st_ctime < SINCE.timestamp():
                        continue  # Covered by the checksum-bound historical scan.
                try:
                    scanned[str(scope.relative_to(root))] += 1
                    if frame_ids := scan_file(path, rel):
                        combine(hits, {rel: ranges(frame_ids)})
                except (OSError, ValueError, EOFError) as exc:
                    errors[rel] = f'{type(exc).__name__}: {exc}'
    return dict(scanned={'prior_archive': sum(v for k, v in prior['scanned'].items() if not k.endswith('_roots')),
                         **dict(scanned)},
                frame_hits=hits, errors=errors, prior_receipt_sha256=BASE_SHA256, cutoff=SINCE.isoformat(),
                non_frame_artifacts={NUMAX: NUMAX_SHA256})


def merge(root, delta, supplement):
    record = json.loads(delta.read_bytes())
    if (record['prior_receipt_sha256'] != BASE_SHA256
            or record['non_frame_artifacts'] != {NUMAX: NUMAX_SHA256}):
        raise ValueError('Unexpected historical audit evidence')
    checked_json(root/BASE, BASE_SHA256)
    checked_json(root/CONFIG_AUDIT, CONFIG_AUDIT_SHA256)
    # Audit reports repeat the Monte Carlo artifact's numerical range and
    # cannot themselves consume frame IDs.
    record['non_frame_artifacts'].update({BASE: BASE_SHA256, CONFIG_AUDIT: CONFIG_AUDIT_SHA256})
    supplemental = json.loads(supplement.read_bytes())
    combine(record['frame_hits'], {name: blocks for name, blocks in supplemental['frame_hits'].items()
                                   if name not in record['non_frame_artifacts']})
    record['errors'].update(supplemental['errors'])
    if STOPPED_DIAGNOSTIC in record['errors']:
        diagnostic = root/STOPPED_DIAGNOSTIC
        if (sha256(diagnostic.read_bytes()).hexdigest() != STOPPED_SHA256
                or (diagnostic.parent/'STATUS').read_text().strip() != 'STOPPED (1)'):
            raise ValueError('Unexpected contents or status of the stopped SBL diagnostic')
        # The producer selects these 24 construction-only keys from its
        # sealed archival screen. Serialization stopped before its smoke stage.
        pool = checked_json(root/SCREEN, SCREEN_SHA256)['S2']['keys']
        frame_ids = {row['key'][3] for row in pool}
        if len(pool) != 200 or not frame_ids or not frame_ids <= set(range(4400, 4600)):
            raise ValueError('Unexpected historical input pool for the stopped SBL diagnostic')
        record['resolved_errors'] = {STOPPED_DIAGNOSTIC: dict(
            original_error=record['errors'].pop(STOPPED_DIAGNOSTIC),
            artifact_sha256=STOPPED_SHA256, status='STOPPED (1)',
            reason='Truncated archival diagnostic output, with producer inputs bound to the sealed S2 pool',
            input_frame_bounds=[min(frame_ids), max(frame_ids)], input_sha256=SCREEN_SHA256)}
    record['scanned']['manifest_supplement'] = sum(supplemental['scanned'].values())
    record['delta_sha256'] = sha256(delta.read_bytes()).hexdigest()
    record['supplement_sha256'] = sha256(supplement.read_bytes()).hexdigest()
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--combine', type=Path, nargs=2, metavar=('DELTA', 'SUPPLEMENT'))
    args = parser.parse_args()
    result = merge(args.root, *args.combine) if args.combine else audit(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
