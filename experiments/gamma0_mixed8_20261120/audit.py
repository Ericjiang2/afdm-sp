"""Audit S8D2 frame allocation from archived artifacts without importing a receiver."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ENTROPY = 'fedc6f5c81c7acbbb2c0d4652b47e8e82b0767d3bde61797e58475853bb5df12'
DOMAIN = 0x53384432
# Before the first source registration, 8860dd4f at 2026-11-18 03:34 UTC.
CUTOFF = datetime(2026, 11, 18, tzinfo=timezone.utc)
KNOWN = {'cstate_sparse_doublet_screen_20261118', 'doublet_conflict_20261119',
         'gate_screen_20261119', 'gate_sbl_test_20261119', 'readout_batch_20261119'}
REGISTERED = ((0, 11), (100, 195), (200, 207), (1000, 1599), (1600, 2199))
MARKERS = (b'mixed8', b's8d2', ENTROPY.encode(), b'mixed8_receiver',
           b'cstate_sparse_doublet_screen_20261118')
FIELD = re.compile(rb'"(?:frame|frame_id|frame_index)"\s*:\s*(\d+)')
DECLARATION = re.compile(rb'(?i)\b(?:frame(?:s|_ids?|[-_ ]block))\b\W{0,12}(\d+)\s*(?:\.\.+|[-:]|\xe2\x80[\x93\x94]|to)\s*(\d+)')
CLI_FRAME = re.compile(rb'--(frame-offset|frame-start|start-frame|frame-stop|frame-end|end-frame|n-frames|frames)(?:=|[\s"\x27,]+)(\d+)')
OUT_SUFFIXES = ('.json', '.json.gz', '.jsonl', '.jsonl.gz', '.yaml', '.yml', '.toml', '.sh', '.txt')
MANIFEST = re.compile(r'config|manifest|scope|schedule|registration|protocol|receipt|status', re.I)


LEGACY_SBL_G3 = 'experiments/gate_sbl_test_20261119/out/phase1_v2_20261119/sbl_g3.json'
LEGACY_SHA256 = '6e334689592aaec46ce040bfb9af57a682f68fcfb8f3c25c5895629a0612f2e5'
LEGACY_BASIS = 'experiments/gamma0_exchange_20261120/out/frame_audit_deinlab_resolved.json'


def ranges(ids):
    blocks = []
    for frame in sorted(set(ids)):
        if blocks and frame == blocks[-1][1] + 1:
            blocks[-1][1] = frame
        else:
            blocks.append([frame, frame])
    return blocks


def interval(a, b):
    a, b = int(a), int(b)
    if b < a or b > 1_000_000:
        raise ValueError(f'Invalid frame interval: {a}–{b}')
    return set(range(a, b + 1))

def has_marker(raw):
    lowered = raw.lower()
    return any(marker in lowered for marker in MARKERS)

def cli_frames(raw):
    opts = {key: int(n) for key, n in CLI_FRAME.findall(raw)}
    if not opts:
        return set()
    lo = next((opts[k] for k in (b'frame-offset', b'frame-start', b'start-frame') if k in opts), 0)
    hi = next((opts[k] for k in (b'frame-stop', b'frame-end', b'end-frame') if k in opts), None)
    count = opts.get(b'n-frames', opts.get(b'frames', 0))
    return interval(lo, hi if hi is not None else lo + count - 1) if hi is not None or count else set()


def structured(node, key=''):
    out = set()
    if isinstance(node, dict):
        for field, values in node.items():
            k = field.lower()
            # The gate-SBL receipts also describe unrelated P1 segments.
            if k == 's' or k.startswith('s_') or k in ('source_sha256', 'frozen_source_sha256'):
                continue
            if k in ('_argv', 'argv') and isinstance(values, list):
                out |= cli_frames(' '.join(map(str, values)).encode())
            elif k in ('frame', 'frame_id', 'frame_index') and type(values) is int:
                out.add(values)
            else:
                out |= structured(values, key if key.endswith(('frame_ranges', 'frame_intervals')) else k)
        for a, b in (('frame_start', 'frame_stop'), ('first_frame', 'last_frame'),
                     ('frame_first', 'frame_last'), ('frame_lo', 'frame_hi')):
            if type(node.get(a)) is int and type(node.get(b)) is int:
                out |= interval(node[a], node[b])
        if type(node.get('frame_offset')) is int and type(node.get('frames')) is int and node['frames'] > 0:
            out |= interval(node['frame_offset'], node['frame_offset'] + node['frames'] - 1)
    if isinstance(node, list):
        range_suffix = ('frames_inclusive', 'inclusive_block', 'frame_block', 'frame_range', 'frame_ranges',
                        'frame_intervals', 'frames')
        if key.endswith(range_suffix) and len(node) == 2 and all(type(n) is int for n in node):
            return interval(*node)
        if key.endswith(('frame_ids', 'frames_used', 'frames')) and all(type(n) is int for n in node):
            return set(node)
        if key == 'key' and len(node) == 4 and node[0] in ('MIXED8', 'SINGLE8') and type(node[3]) is int:
            return {node[3]}
        for item in node:
            out |= structured(item, key)
    return out


def read_metadata(raw, name):
    if name.endswith(('.json', '.json.gz')):
        return structured(json.loads(raw))
    frames = {int(match[1]) for match in FIELD.finditer(raw)}
    for a, b in DECLARATION.findall(raw):
        frames |= interval(a, b)
    for line in raw.splitlines():
        frames |= cli_frames(line)
    return frames


def open_bytes(path):
    return (gzip.open if path.name.endswith('.gz') else open)(path, 'rb')


def read_rows(path, relevant):
    # Only frame fields are extracted. Archived receiver outputs are never loaded.
    frames = set()
    with open_bytes(path) as handle:
        for line in handle:
            if relevant or has_marker(line):
                frames.update(int(match[1]) for match in FIELD.finditer(line))
    return frames


def discover(root):
    lineage = set(KNOWN)
    sources = 0
    for project in sorted((root/'experiments').iterdir()):
        if not project.is_dir() or project.name == HERE.name:
            continue
        for source in project.iterdir():
            if source.suffix not in ('.py', '.sh') or not source.is_file():
                continue
            sources += 1
            if has_marker(source.read_bytes()):
                lineage.add(project.name)
    return lineage, sources


def known_nonmanifests(root, errors):
    if LEGACY_SBL_G3 not in errors:
        return {}
    path = root/LEGACY_SBL_G3
    basis = root/LEGACY_BASIS
    if not basis.is_file() or sha256(path.read_bytes()).hexdigest() != LEGACY_SHA256:
        return {}
    raw = basis.read_bytes()
    prior = json.loads(raw)['resolved_errors'][LEGACY_SBL_G3]
    if prior['artifact_sha256'] != LEGACY_SHA256 or prior['input_frame_bounds'] != [4401, 4599]:
        return {}
    errors.pop(LEGACY_SBL_G3)
    return {LEGACY_SBL_G3: dict(**prior, basis=LEGACY_BASIS, basis_sha256=sha256(raw).hexdigest())}


def scan(root, site):
    lineage, source_count = discover(root)
    scanned, hits, errors = Counter(sources=source_count), {}, {}
    roots = [root/'experiments', *sorted((root/'afdm_sp_joint_unrolled').glob('outputs_*'))]
    roots += [root/'results', root/'issues', root/'.mission']
    for directory in (path for path in roots if path.is_dir() and path.parent.name != HERE.name):
        for folder, dirs, files in os.walk(directory):
            dirs[:] = [name for name in dirs if name not in ('__pycache__', '.git', HERE.name)]
            # Read run declarations before rows that inherit a namespace.
            attributed = False
            for name in sorted(files, key=lambda item: item.endswith(('.jsonl', '.jsonl.gz'))):
                name_lower = name.lower()
                if name.startswith('._') or not name_lower.endswith(OUT_SUFFIXES):
                    continue
                path = Path(folder)/name
                label = str(path.relative_to(root))
                known = bool(lineage.intersection(path.relative_to(root).parts[:-1]))
                raw_rows = name_lower.endswith(('.jsonl', '.jsonl.gz'))
                if not known and not MANIFEST.search(name) and not raw_rows:
                    continue
                # Dated outputs are eligible for the S8D2 namespace only after
                # its first registration. Known-lineage and named manifests
                # are always read, independent of timestamps.
                if not (known or attributed) and raw_rows and path.stat().st_ctime < CUTOFF.timestamp():
                    scanned['pre_namespace_rows'] += 1
                    continue
                try:
                    if raw_rows:
                        scanned['row_files'] += 1
                        only_mixed = 'gate_sbl_test_20261119' not in path.parts or name_lower.startswith('x_')
                        ids = read_rows(path, (known or attributed) and only_mixed)
                    else:
                        scanned['metadata_files'] += 1
                        with open_bytes(path) as handle:
                            raw = handle.read()
                        declared_namespace = has_marker(raw)
                        if name_lower.startswith('config') and declared_namespace and (b'"MIXED8"' in raw or ENTROPY.encode() in raw):
                            attributed = True
                        if not raw or not (known or declared_namespace):
                            continue
                        if name_lower.startswith(('fresh_', 'audit_')) and b'"overlaps"' in raw:
                            continue  # Archive audits describe candidate IDs, not run allocations.
                        ids = read_metadata(raw, name_lower)
                    if ids:
                        hits[label] = ranges(ids)
                except (OSError, EOFError, ValueError) as exc:
                    # A malformed JSON outside this lineage that contains no
                    # namespace marker cannot bear on coverage.
                    errors[label] = f'{type(exc).__name__}: {exc}'
    nonmanifests = known_nonmanifests(root, errors)
    return dict(scope=site, entropy=ENTROPY, domain=DOMAIN, epoch_cutoff=CUTOFF.isoformat(),
                lineage=sorted(lineage), scanned=dict(scanned), hits=hits, errors=errors, nonmanifests=nonmanifests)


def select(*records):
    sites = {r['scope'] for r in records}
    if sites != {'local', 'deinlab'} or len(records) != 2:
        raise ValueError('Expected separate local and deinlab audit receipts')
    used = set().union(*(interval(*block) for block in REGISTERED))
    for receipt in records:
        if ((receipt['entropy'], receipt['domain']) != (ENTROPY, DOMAIN) or receipt['errors']):
            raise ValueError(f'Unresolved audit evidence from {receipt["scope"]}: {receipt["errors"]}')
        for blocks in receipt['hits'].values():
            used.update(set().union(*(interval(*block) for block in blocks)))
    start = 1600
    while overlaps := used.intersection(range(start, start + 600)):
        start = max(overlaps) + 1
    smoke = sorted(set(range(208, 1000)) - used)[:3]
    if len(smoke) != 3:
        raise ValueError('No three disjoint smoke IDs remain below the main reservations')
    return dict(status='PASS', entropy=ENTROPY, domain=DOMAIN, registered=[list(b) for b in REGISTERED],
                fresh=[start, start + 599], smoke=smoke, occupied=ranges(used))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', choices=('local', 'deinlab'))
    parser.add_argument('--merge', nargs=2, type=Path, metavar=('LOCAL', 'DEINLAB'))
    parser.add_argument('--root', type=Path, default=EXP.parent)
    args = parser.parse_args()
    if (args.site is None) == (args.merge is None):
        parser.error('supply exactly one of --site or --merge')
    if args.merge:
        evidence = [path.read_bytes() for path in args.merge]
        result = select(*map(json.loads, evidence))
        result['audit_sha256'] = {path.name: sha256(data).hexdigest() for path, data in zip(args.merge, evidence, strict=True)}
    else:
        result = scan(args.root, args.site)
    print(json.dumps(result, indent=2, sort_keys=True))
    return bool(result.get('errors'))


if __name__ == '__main__':
    sys.exit(main())
