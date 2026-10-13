"""Replay two observed-only native TF calls; keep truth outside this producer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    source = project / 'experiments/sp_afdm_native_joint_reviewed_20260921'
    baseline = project / 'experiments/sp_afdm_frozen_reviewed_20260921'
    sys.path[:0] = [str(project / 'experiments/tf_production_gap_audit_20260922')]
    from audit_io import attach, load_bound, sha256
    evidence = attach(source, baseline)
    from receiver import context
    import native_twofft as native
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.mkdir(parents=True)
    env = evidence.bind_runtime_environment()
    start = time.perf_counter()
    system, _, code, header = context()
    evidence.verify_runtime_binding()
    setup = time.perf_counter() - start
    population = project / 'results/tf_cstate_prospective_20260923/population_observed'
    source_row = next(json.loads(line) for line in (population / 'ledger.jsonl').read_text().splitlines()
                      if json.loads(line)['observation_id'] == 's650_f0000')
    payload = load_bound(evidence, population / source_row['observation_path'],
                         source_row['observation_sha256'])
    obs = payload['observation']
    if set(obs) != {'y', 'pilot', 'sigma2'}:
        raise ValueError('unexpected receiver inputs')
    manifest = dict(environment=env, header=header, setup_seconds=setup,
                    source_hashes=evidence.source_hashes(source),
                    baseline_hashes=evidence.source_hashes(baseline),
                    source_row=source_row, argv=sys.argv, pid=os.getpid(),
                    started_epoch=time.time(), producer_sha256=sha256(Path(__file__)),
                    scope='two real full TF/LDPC calls on one archived observed frame; no FER claim')
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    outputs = []
    previous = None
    for repeat in range(2):
        started = time.perf_counter()
        dec, arrays, timing = native.receive(obs, system, code, rounds=2, iterations=20,
                                            ce_mode='soft', gain_mode='joint')
        elapsed = time.perf_counter() - started
        if previous is not None:
            for key in ('r1_decoded', 'r1_input_llr', 'r1_gains', 'r1_dopplers'):
                if not np.array_equal(previous[key], arrays[key]):
                    raise AssertionError(f'repeat differs: {key}')
        previous = arrays
        path = args.out / f'repeat{repeat}.npz'
        digest = evidence.save_artifact(path, dict(decoder=dec, arrays=arrays, timing=timing),
                                       dict(kind='innovation-smoke', repeat=repeat,
                                            observation_sha256=source_row['observation_sha256']))
        outputs.append(dict(repeat=repeat, raw_path=str(path), raw_sha256=digest,
                            seconds=elapsed, rounds=len(timing['events']),
                            decoded_sha256=hashlib.sha256(dec['decoded'].tobytes()).hexdigest(),
                            decoder_iterations=[e['decoder_iterations'] for e in timing['events']]))
    result = dict(status='pass', real_receiver_calls=2, distinct_observations=1,
                  exact_repeat=True, records=outputs, finished_epoch=time.time())
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
