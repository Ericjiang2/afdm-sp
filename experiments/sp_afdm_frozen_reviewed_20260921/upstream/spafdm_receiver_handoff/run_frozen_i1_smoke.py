#!/usr/bin/env python3
"""Frozen I1 receiver smoke: a handful of production-like frames, one command.

Runs ``--frames`` independent G0 development frames (fixed replicate/index
seeds, split=2) through the frozen receiver shell with support repair disabled
(arm ``a0``): actual 10 outer iterations / 20 BP detection iterations / LDPC
maxiter 50, using the frozen C2-rel checkpoint and the frozen 2048-bit LDPC.

Prints per-frame FER / LLR summaries and writes a JSON fixture that holds the
input hashes and the expected outputs.  ``--check`` recomputes a saved fixture
and compares (hash and integer fields are expected to match on the same
environment; float fields are compared with a tolerance).

CPU-only by design (CUDA is hidden before torch import, matching the project
convention for CPU runs).  Requires numpy / scipy / torch / matplotlib.

Usage (from the repository root):

    python run_frozen_i1_smoke.py                       # 4 frames @ 8 dB
    python run_frozen_i1_smoke.py --frames 16 --snr 7
    python run_frozen_i1_smoke.py --check frozen-i1-smoke-fixture-v1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')  # must precede the torch import

import numpy as np  # noqa: E402
import torch  # noqa: E402

ROOT = Path(__file__).resolve().parent
CHECKPOINT_CANDIDATES = (
    ROOT / '.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/frozen-c2rel-checkpoint.pt',
    ROOT / '07_checkpoint/frozen-c2rel-checkpoint.pt',
    ROOT / 'frozen-c2rel-checkpoint.pt',
)
CODE_G_SHA256 = 'bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af'
FIXTURE_SCHEMA = 'frozen-i1-smoke-fixture-v1'

CHECKED_HASH_FIELDS = ('final_llr_sha256', 'final_bp_mu_sha256', 'final_bp_var_sha256',
                       'output_h_sha256', 'output_x_sha256')
CHECKED_INT_FIELDS = ('info_errors', 'raw_errors', 'decode_ok', 'fer')
CHECKED_FLOAT_FIELDS = ('final_bit_nll', 'final_bit_brier', 'nmse')


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_one(model, system, code, replicate, index, snr):
    """One frozen frame: make -> full receiver -> scored record. Truth is used only by the scorer."""
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame, run_frame
    frame = make_frame(system, code, replicate, index, snr, split=2)
    record = run_frame(model, system, code, frame, None, ['a0'], replicate, index, snr,
                       active_cap=40, receiver_shell='direct40')
    arm = record['arms']['a0']
    return frame, record, arm


def summarize(replicate, index, snr, frame, record, arm):
    return dict(
        replicate=replicate, frame_index=index, frame_snr=snr, split=2,
        channel_seed=int(record['channel_seed']),
        input_hashes=record['input_hashes'],
        info_errors=int(arm['info_errors']),
        raw_errors=int(arm['raw_errors']),
        decode_ok=bool(arm['decode_ok']),
        fer=int(arm['info_errors'] > 0),
        final_bit_nll=float(arm['final_bit_nll']),
        final_bit_brier=float(arm['final_bit_brier']),
        nmse=float(arm['nmse']),
        final_llr_sha256=arm['final_llr_sha256'],
        final_bp_mu_sha256=arm['final_bp_mu_sha256'],
        final_bp_var_sha256=arm['final_bp_var_sha256'],
        output_h_sha256=arm['output_h_sha256'],
        output_x_sha256=arm['output_x_sha256'],
        decoded_bits_sha256=arm.get('decoded_bits_sha256'),
        receiver_seconds=float(arm['receiver_seconds']),
    )


def build(args):
    """Frozen environment construction with identity checks; CPU only."""
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.direction_receiver import CHECKPOINT_HASH
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a

    if torch.cuda.is_available():
        raise RuntimeError('CPU smoke requires a hidden CUDA device (unset CUDA_VISIBLE_DEVICES override)')
    checkpoint = (Path(args.checkpoint).resolve() if args.checkpoint
                  else next((p for p in CHECKPOINT_CANDIDATES if p.is_file()), CHECKPOINT_CANDIDATES[0]))
    if file_sha256(checkpoint) != CHECKPOINT_HASH:
        raise ValueError('checkpoint differs from the frozen receiver identity: ' + str(checkpoint))
    checkpoint_sha = file_sha256(checkpoint)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    system = _make_config_a(1024, 2., 8, 10., 4.)
    if (system.l_max_cap, system.k_max_cap) != (102, 2) or system.N_total != 1024:
        raise ValueError('dictionary/system configuration changed')
    model = build_receiver(checkpoint, system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
    code = build_code(2048, d_v=3, d_c=6, seed=20260726)
    code_sha = hashlib.sha256(code['G'].tobytes()).hexdigest()
    if code_sha != CODE_G_SHA256:
        raise ValueError('frozen actual LDPC generator changed')
    header = dict(
        schema=FIXTURE_SCHEMA,
        checkpoint_path=str(checkpoint),
        checkpoint_sha256=checkpoint_sha,
        code_g_sha256=code_sha,
        receiver=dict(arm='a0', receiver_shell='direct40', active_cap=40, repair='disabled',
                      outer_iterations=10, bp_iterations=20, ldpc_maxiter=50),
        system=dict(n_total=1024, l_max_cap=102, k_max_cap=2,
                    rho=float(system.rho), c1=float(system.c1), c2=float(system.c2)),
        environment=dict(python=sys.version.split()[0], numpy=np.__version__, torch=torch.__version__),
        truth_access='input hashes and offline scoring only; the receiver never reads H',
    )
    return system, model, code, header


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=4, help='number of independent frames (default 4)')
    parser.add_argument('--snr', type=float, default=8., help='frame SNR in dB (default 8)')
    parser.add_argument('--replicate', type=int, default=30, help='frozen dev replicate id (default 30)')
    parser.add_argument('--checkpoint', type=Path, default=None,
                        help='override the frozen checkpoint path (default: auto-discover)')
    parser.add_argument('--out', type=Path, default=ROOT / 'frozen-i1-smoke-fixture-v1.json')
    parser.add_argument('--check', type=Path, help='recompute and compare against a saved fixture')
    args = parser.parse_args()
    if args.check and args.check == args.out:
        raise ValueError('do not overwrite the fixture being checked')
    if args.frames < 1:
        raise ValueError('frame count must be positive')

    started = time.time()
    system, model, code, header = build(args)
    frames = []
    for index in range(args.frames):
        frame, record, arm = run_one(model, system, code, args.replicate, index, args.snr)
        row = summarize(args.replicate, index, args.snr, frame, record, arm)
        frames.append(row)
        print('frame {i:03d}  FER={f}  info_errors={e:4d}  raw_errors={r:5d}  '
              'nll={n:.6f}  fer_rate={rate:.4f}  receiver_seconds={s:.3f}'.format(
                  i=index, f=row['fer'], e=row['info_errors'], r=row['raw_errors'],
                  n=row['final_bit_nll'], rate=np.mean([f['fer'] for f in frames]),
                  s=row['receiver_seconds']), flush=True)
    result = dict(header, frames=frames, run=dict(wall_seconds=time.time() - started,
                                                  frames=args.frames, replicate=args.replicate, snr=args.snr))

    if args.check:
        saved = json.loads(Path(args.check).read_text())
        problems = []
        if saved['checkpoint_sha256'] != header['checkpoint_sha256']:
            problems.append('checkpoint identity differs')
        if saved['code_g_sha256'] != header['code_g_sha256']:
            problems.append('LDPC identity differs')
        if len(saved['frames']) != len(frames):
            problems.append('frame count differs (%d vs %d)' % (len(saved['frames']), len(frames)))
        for old, new in zip(saved['frames'], frames):
            tag = 'frame %d' % new['frame_index']
            if old['input_hashes'] != new['input_hashes']:
                problems.append(tag + ': input hashes differ')
            for key in CHECKED_HASH_FIELDS:
                if old.get(key) != new.get(key):
                    problems.append(tag + ': ' + key + ' differs')
            for key in CHECKED_INT_FIELDS:
                if old.get(key) != new.get(key):
                    problems.append(tag + ': %s differs (%s vs %s)' % (key, old.get(key), new.get(key)))
            for key in CHECKED_FLOAT_FIELDS:
                if abs(old.get(key, 0.) - new.get(key, 0.)) > 1e-12:
                    problems.append(tag + ': %s differs (%r vs %r)' % (key, old.get(key), new.get(key)))
        if problems:
            print('CHECK FAILED (%d differences)' % len(problems))
            for problem in problems:
                print('  -', problem)
            raise SystemExit(1)
        print('CHECK PASS: %d frames match %s' % (len(frames), args.check))
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=False) + '\n')
    print('fixture written: %s' % args.out)


if __name__ == '__main__':
    main()
