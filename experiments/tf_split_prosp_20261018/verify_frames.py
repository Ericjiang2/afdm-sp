#!/usr/bin/env python
"""Fresh-frame audit for the split-principle prospective test (task 10-18-split-principle-prospective, design.md "frames").

Question: has any frame of the CANDIDATE block (default 7000..7199) ever been observed through the P1 stream (entropy 2261fde3..., domain TCRF), the
stream the prospective test draws from?  Frame ids are only a label: every random draw is keyed by SeedSequence(entropy words, domain, frame, component),
so the same integer under another entropy / domain is an independent realisation.  The audit therefore reports:

  (a) static scan : every .py/.sh/.md under experiments/ (this directory, _archive and generated out/ excluded) that contains an integer in the candidate
                    block -- file, line, text.  Which stream a hit belongs to is classified by hand in PROTOCOL.md.
  (b) out scan    : every config*.json and rows/gate/result file (.jsonl, .jsonl.gz, .json) under experiments/*/out.  A run directory is P1-flagged iff one of
                    its configs names the P1 entropy (a file is also flagged if its first 64 kB do).  Per file: the frame ids it declares ('frame_offset' +
                    'frames', 'frame' fields, [sc, rho, snr, frame] key lists, 'frames' pairs) or contains ('"frame": N' values).

Decision: the block is P1-fresh iff no P1-flagged file declares or contains a frame in it.  Hits in non-P1 files are listed and reported (they do not change the
decision).  If the block is not P1-fresh, ``decision_start`` is the smallest start >= the candidate start whose 200-frame block has no P1-stream use (design
rule).  ``strict_alt`` = smallest start whose block has no integer use in ANY stream (informational only).

Run:  python verify_frames.py --root <.../experiments> --out <dir>      Single-thread, read-only, pure Python.  Never reads stdin.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

P1_ENTROPY_PREFIX = '2261fde33dab09d1'
CAND = (7000, 7200)
N_BLOCK = CAND[1] - CAND[0]
SKIP_DIRS = {'__pycache__', '_archive', 'tf_split_prosp_20261018'}
FRAME_RE = re.compile(rb'"frame"\s*:\s*(\d+)')
ENTROPY_RE = re.compile(r'"(?:entropy|ENTROPY_HEX|entropy_hex)"\s*:\s*"([0-9a-f]{16})')
INT_RE = re.compile(r'(?<![\d.\w])(7[01]\d\d)(?![\d.\w])')
STATIC_SUFFIX = ('.py', '.sh', '.md')
ROWS_SUFFIX = ('.jsonl', '.json', '.jsonl.gz')


def ranges(values):
    values = sorted(set(values))
    out = []
    for v in values:
        if out and v == out[-1][1] + 1:
            out[-1][1] = v
        else:
            out.append([v, v])
    return [[a, b] if a != b else [a] for a, b in out]


def overlaps(frames, lo, hi):
    return sorted(f for f in frames if lo <= f < hi)


def config_frames(doc):
    """Frame ids a parsed config declares: frame_offset+frames pairs, 'frames' [lo, hi) pairs, 'frame' ints, 4-lists (sc, rho, snr, frame)."""
    found = set()

    def walk(x, parent_key=''):
        if isinstance(x, dict):
            off, n = x.get('frame_offset'), x.get('frames')
            if isinstance(off, int) and isinstance(n, int) and n >= 0:
                found.update(range(off, off + n))
            if isinstance(x.get('frame'), int):
                found.add(x['frame'])
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, list):
            if len(x) == 4 and isinstance(x[0], str) and all(isinstance(t, int) for t in x[1:]):
                found.add(x[3])
            elif parent_key in ('frames', 'frame_range', 'smoke_frames') and len(x) == 2 and all(isinstance(t, int) for t in x) and x[0] <= x[1]:
                found.update(range(x[0], x[1]))
            elif parent_key in ('frame_list', 'frames') and x and all(isinstance(t, int) for t in x):
                found.update(x)
            for v in x:
                walk(v, parent_key)
    walk(doc)
    return found


def scan_static(root):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and d != 'out']
        for name in sorted(filenames):
            if not name.endswith(STATIC_SUFFIX):
                continue
            path = Path(dirpath) / name
            try:
                lines = path.read_text(errors='replace').splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                for m in INT_RE.finditer(line):
                    if CAND[0] <= int(m.group(1)) < CAND[1]:
                        hits.append(dict(file=str(path.relative_to(root)), line=i, value=int(m.group(1)), text=line.strip()[:200]))
    return hits


def scan_out(root):
    """Walk experiments/*/out; returns (list of per-file dicts, seconds)."""
    files, t0 = [], time.perf_counter()
    for exp in sorted(p for p in Path(root).iterdir() if p.is_dir() and p.name not in SKIP_DIRS):
        out = exp / 'out'
        if not out.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(out):
            dirnames[:] = [d for d in dirnames if d != '__pycache__']
            cfgs = [n for n in sorted(filenames) if n.startswith('config') and n.endswith('.json')]
            dir_p1, dir_other = False, set()
            for n in cfgs:
                try:
                    text = (Path(dirpath) / n).read_text(errors='replace')
                except OSError:
                    continue
                dir_p1 |= P1_ENTROPY_PREFIX in text
                dir_other |= {e for e in ENTROPY_RE.findall(text) if e != P1_ENTROPY_PREFIX}
            for name in sorted(filenames):
                path = Path(dirpath) / name
                is_cfg = name in cfgs
                if not (is_cfg or name.endswith(ROWS_SUFFIX)):
                    continue
                rec = dict(file=str(path.relative_to(root)), experiment=exp.name, kind='config' if is_cfg else 'rows', frames=set(), p1=bool(dir_p1),
                           other_entropy=sorted(dir_other))
                try:
                    if is_cfg:
                        text = path.read_text(errors='replace')
                        rec['p1'] = bool(dir_p1 or P1_ENTROPY_PREFIX in text)
                        try:
                            rec['frames'] = config_frames(json.loads(text))
                        except json.JSONDecodeError:
                            pass
                    else:
                        op = gzip.open if name.endswith('.gz') else open
                        with op(path, 'rb') as handle:
                            for i, line in enumerate(handle):
                                if i == 0 and P1_ENTROPY_PREFIX.encode() in line[:65536]:
                                    rec['p1'] = True
                                if b'"frame"' in line:
                                    rec['frames'].update(int(m.group(1)) for m in FRAME_RE.finditer(line))
                except (OSError, EOFError):
                    rec['error'] = True
                files.append(rec)
    return files, time.perf_counter() - t0


def hit_table(files, p1):
    """{file: candidate-block frame ranges} for the files whose P1 flag equals ``p1``."""
    out = {}
    for r in files:
        hit = overlaps(r['frames'], *CAND)
        if hit and r['p1'] == p1:
            out[r['file']] = dict(kind=r['kind'], frames=ranges(hit), other_entropy=r['other_entropy'])
    return dict(sorted(out.items()))


def smallest_free_start(used, start, n=N_BLOCK, limit=100000):
    s = start
    while s < limit:
        clash = [f for f in used if s <= f < s + n]
        if not clash:
            return s
        s = max(clash) + 1
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--root', type=Path, required=True, help='.../experiments')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    root = a.root.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    static = scan_static(root)
    files, secs = scan_out(root)
    p1_used, all_used, per_exp = set(), set(), {}
    for r in files:
        all_used |= r['frames']
        e = per_exp.setdefault(r['experiment'], dict(config_files=0, rows_files=0, p1_config=set(), p1_rows=set(), other_config=set(), other_rows=set(),
                                                     other_entropy=set()))
        e['config_files' if r['kind'] == 'config' else 'rows_files'] += 1
        e[('p1' if r['p1'] else 'other') + ('_config' if r['kind'] == 'config' else '_rows')] |= r['frames']
        e['other_entropy'] |= set(r['other_entropy'])
        if r['p1']:
            p1_used |= r['frames']
    p1_hits = overlaps(p1_used, *CAND)
    fresh = not p1_hits
    static_values = {h['value'] for h in static}
    result = dict(
        candidate=list(CAND), script_md5=hashlib.md5(Path(__file__).read_bytes()).hexdigest(), root=str(root), seconds=round(secs, 1), files_scanned=len(files),
        p1_entropy_prefix=P1_ENTROPY_PREFIX, p1_used_frame_ranges=ranges(p1_used), p1_max_used_frame=max(p1_used) if p1_used else None,
        p1_hits_in_candidate=p1_hits, p1_hit_files=hit_table(files, True), p1_fresh=fresh,
        decision_start=CAND[0] if fresh else smallest_free_start(p1_used, CAND[0]), non_p1_hit_files=hit_table(files, False), static_hits=static,
        strict_alt=smallest_free_start(all_used | static_values, CAND[0]),
        per_experiment={d: dict(config_files=e['config_files'], rows_files=e['rows_files'], p1_config_ranges=ranges(e['p1_config']),
                                p1_rows_ranges=ranges(e['p1_rows']), other_config_ranges=ranges(e['other_config']), other_rows_ranges=ranges(e['other_rows']),
                                other_entropy_prefixes=sorted(e['other_entropy'])) for d, e in sorted(per_exp.items())})
    (a.out / 'frames_check.json').write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
    lines = [f"candidate block {CAND[0]}..{CAND[1] - 1}; P1 entropy prefix {P1_ENTROPY_PREFIX}; files scanned {len(files)} in {secs:.1f}s",
             f"P1-stream used frame ranges: {json.dumps(result['p1_used_frame_ranges'])}", f"P1-stream hits in candidate block: {p1_hits or 'NONE'}",
             f"P1 fresh: {fresh}; decision start: {result['decision_start']}", f"static hits (integers in the block, any stream): {len(static)}"]
    lines += [f"  {h['file']}:{h['line']}: {h['text']}" for h in static]
    lines.append(f"P1-flagged hit files: {json.dumps(result['p1_hit_files'])}")
    lines.append(f"non-P1 hit files (other entropy / unflagged): {json.dumps(result['non_p1_hit_files'])}")
    lines.append(f"strict alternative start (no integer use in any stream): {result['strict_alt']}")
    (a.out / 'frames_check.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
