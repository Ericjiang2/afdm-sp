"""Run the eight post-hoc readouts from immutable archives."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np
import scipy

import geometry
import pilot
import sbl_dd


ORDER = ('R-A', 'R-B1', 'R-B2', 'R-C1', 'R-C2', 'R-D', 'R-E', 'R-F')
SOURCES = (pilot.SLOT_RUN, sbl_dd.SBL_SOURCE, geometry.RATIO, geometry.CSTATE,
           pilot.P1_RUN, pilot.GS_RUN, geometry.DOUBLET, sbl_dd.DD_SOURCE)
SEED = 20261119
DRAWS = 10_000


def cpu_time():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiments-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = args.experiments_root.resolve()
    manifests = {}
    for run in SOURCES:
        name = 'RAW_SHARDS_MD5.txt' if run == geometry.RATIO else 'REMOTE_ROWS_MD5.txt'
        manifests[f'{run}/{name}'] = sha256((root / run / name).read_bytes()).hexdigest()

    readouts = {}
    for module, seed in zip((pilot, sbl_dd, geometry), np.random.SeedSequence(SEED).spawn(3), strict=True):
        print(f'Reading {module.__name__} archives', flush=True)
        results = module.run(root, np.random.default_rng(seed), DRAWS)
        if readouts.keys() & results.keys():
            raise ValueError('Duplicate readout ID')
        readouts.update(results)
    if readouts.keys() != set(ORDER):
        raise ValueError('Readout IDs differ from the brief')

    config = dict(
        analysis='post hoc', bootstrap_seed=SEED, bootstrap_draws=DRAWS, confidence_level=.95,
        experiments_root=str(root), numpy=np.__version__, scipy=scipy.__version__,
        crossing_sha256=pilot.CROSSING_SHA256,
        source_manifest_sha256=manifests, processes=1, threads=1, core_hour_cap=1,
        receiver_calls=0, detector_calls=0, decoder_calls=0, generated_frames=0,
        cpu_seconds=cpu_time(), elapsed_seconds=time.monotonic() - started,
    )
    result = dict(_argv=sys.argv, _config=config, **{key: readouts[key] for key in ORDER})
    report = [
        '# Saved-row readouts, 2026-11-19', '',
        'All eight analyses are **post hoc**. Claude wrote the decision rules before this batch was computed. '
        'These rules are applied to previously collected data. The batch performs zero receiver, detector '
        'or decoder calls and generates zero frames.', '',
        'The physical frame is the resampling unit wherever a bootstrap is used. The seed, 10,000 draws '
        'per analysis and frozen source manifest fingerprints are recorded in `readouts.json`. '
        'Intervals are two-sided 95% unless the table marks a deterministic count bound.', '',
        'Threshold outcomes describe the specified archived contrasts. Mechanistic explanations remain '
        'untested by interventions in this batch.', '',
    ]
    for key in ORDER:
        row = readouts[key]
        report.extend((f'## {key}', '', f'**Source:** {row["source"]}.', '',
                       f'**Fields:** {row["fields"]}', '', row['report'], '',
                       f'**Rule outcome:** {row["outcome"]}.', ''))
    report.append(f'Aggregation CPU time was {config["cpu_seconds"] / 3600:.6f} core-hours on one CPU process.')
    args.out.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    (args.out / 'readouts.json').write_text(payload, encoding='utf-8')
    (args.out / 'READOUTS.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    for key in ORDER:
        row = readouts[key]
        print(f'{key}: {row["outcome"]} | {row["headline"]}', flush=True)


if __name__ == '__main__':
    main()
