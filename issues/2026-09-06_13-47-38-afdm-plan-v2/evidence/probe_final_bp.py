"""Observe the unchanged final BP call, then repeat its exact inputs in isolation."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('receiver_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.report.exists(): raise FileExistsError(args.report)
    sys.path.insert(0, args.source)
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled import budgeted_support_eval as runner
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    original = runner.afb.mp_detect_bp
    decode_original = runner.decode_llr
    records = []
    def compare(a, b):
        return [dict(equal=bool(np.array_equal(x, y)), max_abs=float(np.max(np.abs(x-y))),
                     relative_norm=float(np.linalg.norm(x-y)/max(np.linalg.norm(x), 1e-30))) for x, y in zip(a, b)]
    def observe(y, H, sigma2, constellation, *pos, **kw):
        output = original(y, H, sigma2, constellation, *pos, **kw)
        values = [y, H, np.asarray(sigma2), constellation]
        row = dict(input_hashes={name: array_hash(value) for name, value in zip(['y_data','H','sigma2','constellation'], values)},
                   input_layout=[dict(shape=list(np.shape(v)), dtype=str(np.asarray(v).dtype), strides=list(np.asarray(v).strides)) for v in values],
                   ordinary_repeats=[], deterministic_repeats=[])
        baseline = tuple(np.copy(v) for v in output)
        for _ in range(4): row['ordinary_repeats'].append(compare(baseline, original(y,H,sigma2,constellation,*pos,**kw)))
        was_enabled = torch.are_deterministic_algorithms_enabled()
        was_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
        try:
            torch.use_deterministic_algorithms(True)
            reference = original(y,H,sigma2,constellation,*pos,**kw)
            row['ordinary_vs_deterministic'] = compare(baseline,reference)
            for _ in range(4): row['deterministic_repeats'].append(compare(reference, original(y,H,sigma2,constellation,*pos,**kw)))
        except RuntimeError as error:
            row['deterministic_error'] = str(error)
        finally:
            torch.use_deterministic_algorithms(was_enabled, warn_only=was_warn_only)
        assert row['input_hashes']=={name: array_hash(value) for name,value in zip(['y_data','H','sigma2','constellation'], values)}
        row['original_output_hashes']=[array_hash(v) for v in output]
        records.append(row)
        return output
    def decode(*pos,**kw):
        output=decode_original(*pos,**kw)
        records[-1]['decoded_bits']=np.asarray(output[0]).astype(int).tolist()
        records[-1]['decode_ok']=bool(output[1])
        return output
    runner.afb.mp_detect_bp=observe
    runner.decode_llr=decode
    receiver_args=args.receiver_args[1:] if args.receiver_args[:1]==['--'] else args.receiver_args
    sys.argv=['budgeted_support_eval',*receiver_args]
    runner.main()
    args.report.write_text(json.dumps(dict(scope='repeatability diagnosis; original outputs returned unchanged; deterministic mode only isolated probes',records=records),indent=2)+'\n')


if __name__=='__main__': main()
