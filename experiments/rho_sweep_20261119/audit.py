"""Audit contiguous candidate blocks using only stored frame metadata and rows."""

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'sbl_residual_gap_20261119'))
import audit_fresh  # noqa: E402

FIRST, BLOCK = 5000, 400


def audit(last, remote, scratch):
    root = HERE.parents[1]
    receipt = audit_fresh.scan(root, remote, last, first=FIRST)
    own_out = str(HERE.relative_to(root) / 'out') + '/'
    findings = [hit for hit in receipt['unresolved'] if not hit['file'].startswith(own_out)]
    ignored = dict(receipt['ignored'])
    ignored['derived rho-sweep receipt hits'] = len(receipt['unresolved']) - len(findings)
    scratch_files = 0
    if scratch is not None:
        scanner = audit_fresh.archived
        for path in sorted(scratch.rglob('*')):
            if not path.is_file() or not path.name.endswith(scanner.WATCH_SUFFIXES):
                continue
            if path.name.startswith('._'):
                with path.open('rb') as handle:
                    if handle.read(4) == b'\x00\x05\x16\x07':
                        ignored['scratch AppleDouble sidecars'] = ignored.get('scratch AppleDouble sidecars', 0) + 1
                        continue
            scratch_files += 1
            structured = not path.name.endswith(('.jsonl', '.jsonl.gz'))
            try:
                frames, head = scanner.scan_file(path, structured)
            except (OSError, ValueError, EOFError) as exc:
                findings.append(dict(file=str(path), error=type(exc).__name__))
                continue
            overlap = sorted(n for n in frames if FIRST <= n <= last)
            if overlap:
                findings.append(dict(file=str(path), stream=scanner.path_stream(path, head),
                                     frames=scanner.ranges(overlap)))
    # The reused scanner's status fields refer to the older residual-gap intervals.
    candidates = []
    for start in range(FIRST, last + 1, BLOCK):
        count = sum(a[0] < start + BLOCK and a[-1] >= start
                    for hit in findings for a in hit.get('frames', []))
        candidates.append(dict(inclusive=[start, start + BLOCK - 1], overlap_ranges=count))
    errors = sum('error' in hit for hit in findings)
    selected = None if errors else next(
        (candidate['inclusive'] for candidate in candidates if not candidate['overlap_ranges']), None)
    return {name: receipt[name] for name in (
        'scope', 'interval_inclusive', 'p1_identity', 'scanner_sha256', 'scanned',
        'prior_inventory_sha256', 'prior_scanned', 'delta_since_utc',
    )} | dict(findings=findings, scratch_files=scratch_files, ignored=ignored, candidates=candidates,
              selected=selected, unreadable=errors, _argv=sys.argv,
              _config=dict(first=FIRST, last=last, remote=remote,
                           scratch=str(scratch) if scratch is not None else None))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blocks', type=int, default=2)
    parser.add_argument('--remote', action='store_true')
    parser.add_argument('--scratch', type=Path)
    args = parser.parse_args()
    if args.blocks < 1:
        parser.error('At least one candidate block is required')
    print(json.dumps(audit(FIRST + args.blocks * BLOCK - 1, args.remote, args.scratch), indent=2))
