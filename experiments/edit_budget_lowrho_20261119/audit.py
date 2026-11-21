"""Read stored frame metadata and row IDs without running a receiver."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = HERE.parent / 'sbl_residual_gap_20261119/audit_fresh.py'
FIRST, LAST = 6400, 6799
PARTIAL_G3 = 'experiments/gate_sbl_test_20261119/out/phase1_v2_20261119/sbl_g3.json'
PARTIAL_G3_SHA = '6e334689592aaec46ce040bfb9af57a682f68fcfb8f3c25c5895629a0612f2e5'
VERIFY_FRAMES = HERE.parent / 'tf_split_prosp_20261018/verify_frames.py'


def scan(remote):
    for path, expected in (
        (PREVIOUS, 'bac45939e076da46d6a1c5c90e254938d6a495b84f8b8473852dabde35d1e6bf'),
        (VERIFY_FRAMES, '096d880d23388387495e7979557fa312ade1d268c03fcbbda86cbd2e07d3278a'),
    ):
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Frozen audit source mismatch: {path}')
    sys.path.insert(0, str(PREVIOUS.parent))
    import audit_fresh

    receipt = audit_fresh.scan(ROOT, remote, LAST, first=FIRST)
    findings = receipt.pop('unresolved')
    exclusions = []
    partial_g3 = {'file': PARTIAL_G3, 'error': 'JSONDecodeError'}
    if partial_g3 in findings:
        # Its run log records a bool_ serialization failure. The corresponding
        # archived SBL keys are in the configuration and raw rows scanned normally.
        if sha256((ROOT / PARTIAL_G3).read_bytes()).hexdigest() == PARTIAL_G3_SHA:
            findings.remove(partial_g3)
            exclusions.append(dict(file=PARTIAL_G3, sha256=PARTIAL_G3_SHA,
                                   reason='Retained partial G3 diagnostic from failed JSON serialization'))
    # The imported wrapper's decision fields refer to its own older blocks.
    for field in ('status', 'base_status', 'extension_inclusive'):
        del receipt[field]
    archive = audit_fresh.archived
    groups = [PREVIOUS.parent / 'out', ROOT / 'results', ROOT / '_archive',
              ROOT / 'experiments']
    if remote:
        groups.append(Path('/data/guoyikun/tmp'))
    supplements = {}
    for directory in groups:
        counts = Counter()
        for path in sorted(directory.rglob('*')):
            if directory == ROOT / 'experiments':
                # Add root launch scripts separately; experiment outputs are scanned above.
                if path.suffix != '.sh' or 'out' in path.relative_to(directory).parts:
                    continue
            if not path.is_file() or not path.name.lower().endswith(archive.WATCH_SUFFIXES):
                continue
            if not path.stat().st_size:
                counts['empty'] += 1
                continue
            if path.name.startswith('._'):
                with path.open('rb') as handle:
                    if handle.read(4) == b'\x00\x05\x16\x07':
                        counts['appledouble'] += 1
                        continue
            structured = not path.name.lower().endswith(('.jsonl', '.jsonl.gz'))
            counts['metadata' if structured else 'rows'] += 1
            name = str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
            try:
                frames, head = archive.scan_file(path, structured)
                if hit := sorted(frame for frame in frames if FIRST <= frame <= LAST):
                    findings.append(dict(file=name, frames=archive.ranges(hit),
                                         stream=archive.path_stream(path, head)))
            except (OSError, ValueError, EOFError) as error:
                findings.append(dict(file=name, error=type(error).__name__))
        supplements[str(directory)] = dict(exists=directory.is_dir(), scanned=dict(counts))
    return receipt | dict(status='STOP' if findings else 'PASS', findings=findings, exclusions=exclusions,
                          selected=None if findings else [FIRST, LAST], supplements=supplements,
                          _argv=sys.argv, _config=dict(remote=remote, first=FIRST, last=LAST,
                                                     input_root=str(ROOT)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote', action='store_true')
    args = parser.parse_args()
    result = scan(args.remote)
    print(json.dumps(result, indent=2))
    raise SystemExit(result['status'] != 'PASS')
