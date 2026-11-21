#!/usr/bin/env python3
"""Complete the same-case all-step LLR gate with a return-preserving observer."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__gram_llr_probe', HERE/'gram_block_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    observer_md5 = hashlib.md5(Path(__file__).read_bytes()).hexdigest()
    original = probe.block.scalar_point
    observed, differences = [], []

    def record(*positional, **kwargs):
        if kwargs['gain_block'] != 'full':
            return original(*positional, **kwargs)
        native = kwargs['native']
        marginal = native.marginal
        values = []

        def capture(*a, **kw):
            result = marginal(*a, **kw)
            values.append((result[0].copy(), result[1].copy()))
            return result

        native.marginal = capture
        try:
            result = original(*positional, **kwargs)
        finally:
            native.marginal = marginal
        if len(values) != 20:
            raise AssertionError('exactly20 symbol updates required')
        observed.append(values)
        if len(observed) % 2 == 0:
            pair = []
            for i, (reference, copied) in enumerate(zip(observed[-2], values)):
                for name, actual, expected in zip(('extrinsic', 'app'), copied, reference):
                    probe.rep.close(actual, expected, f'full step{i} {name} duplicate parity')
                pair.append({name:probe.rep.difference(actual, expected)
                             for name, actual, expected in zip(('extrinsic', 'app'), copied, reference)})
            differences.append(pair)
        return result

    probe.block.scalar_point = record
    try:
        probe.run(argparse.Namespace(out=args.out, old_rows=probe.rep.OLD))
    finally:
        probe.block.scalar_point = original
    if len(observed) != 4 or len(differences) != 2:
        raise AssertionError('only the two fixed full original/duplicate pairs')
    receipt = dict(status='ok', observer_md5=observer_md5,
        scope='Return-preserving marginal observer; same two cases and unchanged source/algorithm/tolerances.',
        full_allstep_llr_differences=dict(zip(('synthetic', 'real'), differences)))
    (args.out/'llr_gate.json').write_text(json.dumps(receipt,indent=1,allow_nan=False)+'\n')
    print('all-step extrinsic/APP LLR duplicate parity qualified', flush=True)


if __name__ == '__main__':
    main()
