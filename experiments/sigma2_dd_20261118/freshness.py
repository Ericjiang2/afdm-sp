"""Audit the proposed block with the same P1 row and source scan as slot mismatch."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from receipts import write_receipt

HERE = Path(__file__).resolve().parent
START, STOP = 11000, 12000


def scan(root):
    sys.path.insert(0, str(root / 'slot_mismatch_20261019'))
    from frame_audit import load_scanner

    scanner = load_scanner(root)
    scanner.SKIP_DIRS = {'__pycache__', '_archive', HERE.name}
    files, seconds = scanner.scan_out(root)
    hits = {'p1': {}, 'other': {}}
    for record in files:
        overlap = scanner.overlaps(record['frames'], START, STOP)
        if overlap:
            hits['p1' if record['p1'] else 'other'][record['file']] = scanner.ranges(overlap)
    errors = [r['file'] for r in files if r.get('error')]

    # The old row scanner reads non-config JSON as text. Parse named run configs
    # as well so ranges with no completed per-frame rows are visible.
    run_configs = 0
    for path in root.glob('*/out/**/RUN_CONFIG.json'):
        rel = path.relative_to(root)
        if rel.parts[0] in scanner.SKIP_DIRS:
            continue
        try:
            config = json.loads(path.read_text())['_config']
        except (OSError, ValueError, KeyError):
            errors.append(str(rel))
            continue
        run_configs += 1
        frames = config.get('frame_range')
        if frames and len(frames) == 2 and all(type(n) is int for n in frames):
            lower, upper = max(frames[0], START), min(frames[1], STOP - 1)
            if lower <= upper:
                key = 'p1' if scanner.P1_ENTROPY_PREFIX in config.get('entropy', '') else 'other'
                hits[key][str(rel)] = [[lower, upper]]

    scanner.CAND = (START, STOP + 1)
    scanner.INT_RE = re.compile(r'(?<![\d.\w])(11\d{3}|12000)(?![\d.\w])')
    static = scanner.scan_static(root)
    sources = sum(1 for p in root.rglob('*') if p.suffix in scanner.STATIC_SUFFIX
                  and not set(p.relative_to(root).parts) & (scanner.SKIP_DIRS | {'out'}))
    return dict(scanned=len(files), seconds=round(seconds, 3), run_configs_parsed=run_configs,
                source_files=sources, hits=hits, read_errors=errors, static_hits=static,
                scanner_sha256=hashlib.sha256(Path(scanner.__file__).read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiments', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    report = scan(args.experiments)
    status = 'FAIL' if report['read_errors'] or any(report['hits'].values()) else (
        'REVIEW_STATIC' if report['static_hits'] else 'PASS')
    write_receipt(args.out, dict(experiments=str(args.experiments), candidate_half_open=[START, STOP]),
                  dict(status=status, **report))
    print(status, report['scanned'], report['source_files'], flush=True)
    if status == 'FAIL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
