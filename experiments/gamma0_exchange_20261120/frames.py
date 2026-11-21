"""Audit recorded frame IDs before any Phase 1 smoke or future evaluation."""
import argparse
from collections import Counter
import csv
import gzip
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'unified_cov_prospective_20261119'))
from audit_frames import FRAME, WATCH_SUFFIXES, manifest_frames  # noqa: E402
from verify_frames import config_frames, ranges, smallest_free_start  # noqa: E402

START, SIZE = 9400, 400
SMOKE_FIRST = 9300
FIRST = SMOKE_FIRST
NAMED_RANGE = re.compile(
    r'(?i)\b(?:frame(?:s|[-_ ]ids?)?|cohort)\b[^\n\d]{0,35}(\d+)\s*'
    r'(?:\.\.+|[–—-]|:\s*|\bto\b|,\s*)(?:\s*)(\d+)'
)
PYTHON_RANGE = re.compile(
    r'(?i)(?:\b(?:[\w]*frames?|first|start|stop|end|block)\s*(?:=|:)\s*)'
    r'(?:range\(\s*|\(\s*|\[\s*)?(\d+)\s*,\s*(\d+)'
)
FRAME_LIST = re.compile(
    r'(?i)\b(?:frames|frame_ids|[\w]+_frames)\s*["\x27]?\s*[:=]\s*[\[(]'
    r'([\d,\s]+)[\])]'
)
EXTRA_SUFFIXES = ('.md', '.py', '.txt', '.log', '.csv')
LEGACY_STDOUT = 'afdm_sp_joint_unrolled/outputs_dpss_paired_screen_20261111_v2/gate.json'
NUMAX_LAUNCH = 'experiments/tcom_reference_frame_20261015/launch_s0.sh'


def structured_frames(doc):
    """Additional archive schemas, preserving both bounds when unspecified."""
    seen = set()

    def visit(node, in_ranges=False):
        if isinstance(node, dict):
            for key, value in node.items():
                normalized = key.lower()
                visit(value, in_ranges or normalized in ('frame_ranges', 'frame_intervals'))
                if (normalized in ('frame_ids', 'frames_used', 'frames_inclusive', 'inclusive_block')
                        and isinstance(value, list) and all(type(n) is int for n in value)):
                    if normalized in ('frames_inclusive', 'inclusive_block') and len(value) == 2:
                        seen.update(range(max(FIRST, value[0]), value[1] + 1))
                    else:
                        seen.update(n for n in value if n >= FIRST)
            for first, last in (('first_frame', 'last_frame'), ('frame_first', 'frame_last'),
                                ('frame_start', 'frame_stop'), ('start_frame', 'end_frame'),
                                ('frame_lo', 'frame_hi')):
                lo, hi = node.get(first), node.get(last)
                if type(lo) is int and type(hi) is int and lo <= hi <= 1_000_000:
                    seen.update(range(max(FIRST, lo), hi + 1))
        elif isinstance(node, list):
            if in_ranges and len(node) == 2 and all(type(n) is int for n in node):
                seen.update(range(max(FIRST, node[0]), node[1] + 1))
            else:
                for value in node:
                    visit(value, in_ranges)

    visit(doc)
    return seen


def declared_frames(line, *, cli=True):
    seen = {frame for frame in manifest_frames(line) if frame >= FIRST} if cli else set()
    for pattern in (NAMED_RANGE, PYTHON_RANGE):
        for a, b in pattern.findall(line):
            lo, hi = int(a), int(b)
            if lo <= hi <= 1_000_000:
                seen.update(range(max(lo, FIRST), hi + 1))
    for limits in FRAME_LIST.findall(line):
        seen.update(n for n in map(int, re.findall(r'\d+', limits)) if n >= FIRST)
    return seen


def scan_file(path, relative):
    name = path.name.lower()
    if name.endswith(('.jsonl', '.jsonl.gz')):
        opener = gzip.open if name.endswith('.gz') else open
        with opener(path, 'rb') as handle:
            return {int(m[1]) for line in handle if b'"frame' in line
                    for m in FRAME.finditer(line) if int(m[1]) >= FIRST}
    if name.endswith(('.json', '.json.gz')):
        opener = gzip.open if name.endswith('.gz') else open
        with opener(path, 'rt', encoding='utf-8') as handle:
            raw = handle.read()
        if not raw:
            return set()
        if relative == LEGACY_STDOUT and raw.startswith('AFDM System initialized:') and not FRAME.search(raw.encode()):
            return declared_frames(raw)
        doc = json.loads(raw)
        return ({n for n in config_frames(doc) if n >= FIRST}
                | structured_frames(doc)
                | {int(m[1]) for m in FRAME.finditer(raw.encode()) if int(m[1]) >= FIRST}
                | declared_frames(raw))
    if name.endswith('.csv'):
        with path.open(encoding='utf-8', newline='') as handle:
            rows = csv.DictReader(handle)
            field = next((f for f in ('frame', 'frame_id', 'frame_index') if f in (rows.fieldnames or ())), None)
            if field:
                return {int(row[field]) for row in rows if row[field] and int(row[field]) >= FIRST}
    with path.open(encoding='utf-8') as handle:
        seen = set()
        for line in handle:
            if 'frame' in line.lower() or 'cohort' in line.lower():
                # Python usage examples and the nu_max draw count do not
                # declare actual receiver frame IDs.
                cli = not name.endswith('.py') and not (relative == NUMAX_LAUNCH and '--stage numax' in line)
                seen |= declared_frames(line, cli=cli)
        return seen


def scan(root, supplement=False):
    roots = [root / 'experiments', root / 'results', root / '.mission',
             root / '.trellis' / 'tasks', root / 'issues']
    roots.extend(sorted((root / 'afdm_sp_joint_unrolled').glob('outputs_*')))
    scanned, hits, errors = Counter(), {}, {}
    for scope in (p for p in roots if p.is_dir()):
        for path in sorted(scope.rglob('*')):
            rel = path.relative_to(root)
            if (not path.name.lower().endswith(WATCH_SUFFIXES + EXTRA_SUFFIXES)
                    or '__pycache__' in rel.parts
                    or HERE.name in rel.parts or '11-20-gamma0-exchange' in rel.parts
                    or path.name.startswith('._')):
                continue
            if (supplement and rel.parts[0] != 'issues'
                    and not path.name.lower().endswith(('.json', '.json.gz', '.csv'))):
                continue
            if not path.is_file():
                continue
            scanned[str(scope.relative_to(root))] += 1
            try:
                if seen := scan_file(path, str(rel)):
                    hits[str(rel)] = ranges(seen)
            except (OSError, ValueError, EOFError) as exc:
                errors[str(rel)] = f'{type(exc).__name__}: {exc}'
    return dict(scanned=dict(scanned), frame_hits=hits, errors=errors)


def used_frames(*audits):
    return {frame for audit in audits for blocks in audit['frame_hits'].values()
            for block in blocks for frame in range(block[0], block[-1] + 1)}


def select(*audits):
    occupied = used_frames(*audits)
    start = smallest_free_start(occupied, START, n=SIZE)
    smoke = [n for n in range(SMOKE_FIRST, START) if n not in occupied][:3]
    if start is None or len(smoke) != 3:
        raise ValueError('Could not select disjoint evaluation and smoke frames')
    return dict(fresh=[start, start + SIZE - 1], smoke=smoke)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--supplement', action='store_true')
    args = parser.parse_args()
    result = scan(args.root, args.supplement)
    print(json.dumps(result, indent=2, sort_keys=True))
