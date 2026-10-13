"""Fixed F1 bank/Gram primitive check; never calls acquisition or receiver."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys

import numpy as np

OBS_SHA = 'f1594455bf48f7d59ac4671ad7d7ec571b164e51c347c3aa0f7140e17c71bfab'
RAW_SHA = '959a8045cc70b7fb33b66b5ed81c9de1ee8b58b9e762d48bb82a7706e8b11cd1'
MODS = (0, 16, 32, 48)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def aligned_copy(value: np.ndarray, residue: int) -> np.ndarray:
    arr = np.asarray(value)
    order = 'F' if arr.flags.f_contiguous and not arr.flags.c_contiguous else 'C'
    raw = np.empty(arr.nbytes + 64, np.uint8)
    offset = (residue - raw.ctypes.data % 64) % 64
    if offset % arr.dtype.itemsize:
        raise AssertionError('requested alignment is incompatible with dtype')
    copied = raw[offset:offset+arr.nbytes].view(arr.dtype).reshape(arr.shape, order=order)
    copied[...] = arr
    if (copied.ctypes.data % 64 != residue or copied.strides != arr.strides or
            copied.tobytes(order=order) != arr.tobytes(order=order)):
        raise AssertionError('aligned copy changed element bytes or layout')
    return copied


def comparison(reference: np.ndarray, candidate: np.ndarray) -> dict:
    left = np.asarray(reference)
    right = np.asarray(candidate)
    if left.shape != right.shape or left.dtype != right.dtype:
        raise AssertionError('fixed primitive shape/dtype differs')
    exact = left.tobytes() == right.tobytes()
    if exact:
        return dict(bitwise_equal=True, max_abs=0., first_difference=None)
    flat_left, flat_right = left.ravel(), right.ravel()
    index = next(i for i, (a, b) in enumerate(zip(flat_left, flat_right, strict=True))
                 if np.asarray(a).tobytes() != np.asarray(b).tobytes())
    a, b = complex(flat_left[index]), complex(flat_right[index])
    return dict(bitwise_equal=False, max_abs=float(np.max(np.abs(left-right))),
                first_difference=dict(index=index,
                    reference=(a.real.hex(), a.imag.hex()),
                    candidate=(b.real.hex(), b.imag.hex())))


def run(args: argparse.Namespace) -> None:
    if args.out.exists():
        raise FileExistsError('primitive result root exists; no rerun')
    if sha(args.plan) != args.plan_sha256 or sha(args.observation) != OBS_SHA or sha(args.raw) != RAW_SHA:
        raise ValueError('fixed plan/observation/raw SHA differs')
    registration = json.loads(args.stage_a_registration.read_text())
    if (registration.get('status') != 'locked' or
            sha(args.stage_a_source / 'f1.py') != registration['source_hashes']['f1.py']):
        raise ValueError('frozen F1 source differs')
    for relative, digest in registration['baseline_source_hashes'].items():
        if sha(args.baseline / relative) != digest:
            raise ValueError(f'frozen baseline source differs: {relative}')
    sys.path[:0] = [str(args.stage_a_source), str(args.baseline / 'src'),
                    str(args.baseline / 'upstream/spafdm_receiver_handoff')]
    import evidence  # type: ignore[import-not-found]
    from f1 import response  # type: ignore[import-not-found]
    from physical import daft  # type: ignore[import-not-found]
    from afdm_sp_joint_unrolled.loop9_cache_features import (  # type: ignore[import-not-found]
        _make_config_a)
    if (Path(evidence.__file__).resolve() != (args.baseline / 'src/evidence.py').resolve()
            or Path(response.__code__.co_filename).resolve() !=
            (args.stage_a_source / 'f1.py').resolve()):
        raise ValueError('imported operator source differs')
    payload = evidence.load_artifact(args.observation)[0]
    old = evidence.load_artifact(args.raw)[0]
    if payload['observation_id'] != 's650_f0197' or old['observation_id'] != 's650_f0197':
        raise ValueError('fixed observation identity differs')
    observed = payload['observation']
    y, pilot, noise = observed['y'], observed['pilot'], float(observed['sigma2'])
    # These are the frozen linear operator and response primitives, not acquisition.
    system = _make_config_a(1024, 2., 8, 10., 4.)
    n, c1, c2, lmax = 1024, system.c1, system.c2, system.l_max_cap
    if system.N_total != 1024 or lmax != 102:
        raise ValueError('source-bound AFDM geometry differs')
    z = daft(y, c1, c2, True)
    time_pilot = daft(pilot, c1, c2, True)
    sample = np.arange(n)
    base = np.column_stack([response(time_pilot, delay, 0., c1)
                            for delay in range(lmax+1)])
    modulation = np.exp(2j*np.pi*sample[:, None]*np.arange(-3., 3.00001, .25)/n)
    bank = (base[:, :, None]*modulation[:, None, :]).reshape(n, -1)
    acquisition = old['acquisition']
    delays, dopplers, gains = (np.asarray(acquisition[key]) for key in
                                ('delays', 'dopplers', 'gains'))
    selected = np.column_stack([response(time_pilot, int(delay), float(nu), c1)
                                for delay, nu in zip(delays, dopplers, strict=True)])
    final_residual = z - selected @ gains
    baseline = {}
    for name, residual in (('initial', z), ('final_proxy', final_residual)):
        baseline[name] = bank.conj().T @ residual
    selected_h = selected.conj().T
    gram = selected_h @ selected
    rhs = selected_h @ z
    solution = np.linalg.solve(gram + noise*np.eye(len(delays)), rhs)
    rows = []
    for mod in MODS:
        bank_copy = aligned_copy(bank, mod)
        held_h = aligned_copy(bank.conj().T, mod)
        selected_copy = aligned_copy(selected, mod)
        selected_h_copy = aligned_copy(selected_h, mod)
        row = dict(pointer_mod64=mod,
                   bank_shape=list(bank_copy.shape), bank_strides=list(bank_copy.strides),
                   bank_c=bool(bank_copy.flags.c_contiguous),
                   bank_h_strides=list(held_h.strides), bank_h_f=bool(held_h.flags.f_contiguous),
                   selected_strides=list(selected_copy.strides),
                   selected_h_strides=list(selected_h_copy.strides))
        for name, residual in (('initial', z), ('final_proxy', final_residual)):
            row[f'bank_fresh_{name}'] = comparison(
                baseline[name], bank_copy.conj().T @ residual)
            row[f'bank_held_{name}'] = comparison(
                baseline[name], held_h @ residual)
        gram_copy = selected_h_copy @ selected_copy
        rhs_copy = selected_h_copy @ z
        row['gram'] = comparison(gram, gram_copy)
        row['rhs'] = comparison(rhs, rhs_copy)
        row['solve'] = comparison(solution,
                                  np.linalg.solve(gram_copy + noise*np.eye(len(delays)), rhs_copy))
        rows.append(row)
    args.out.mkdir(parents=True)
    receipt = dict(schema='stage-b-f1-primitive-alignment/1', status='complete',
        acquisition_calls=0, receiver_calls=0, decoder_calls=0, truth_reads=0,
        observation_sha256=OBS_SHA, stage_a_raw_sha256=RAW_SHA,
        plan_sha256=sha(args.plan), script_sha256=sha(Path(__file__)),
        source_hashes=dict(f1=sha(args.stage_a_source/'f1.py'),
                           physical=sha(args.baseline/'src/physical.py')),
        numpy_version=np.__version__, fixed_pointer_residues=list(MODS),
        note='Final residual is a saved-final-state proxy, not an earlier bank scan.',
        rows=rows)
    (args.out/'receipt.json').write_text(json.dumps(receipt, sort_keys=True,
        indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('plan', 'observation', 'raw', 'stage-a-registration',
                 'stage-a-source', 'baseline', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    signal.signal(signal.SIGALRM,
                  lambda *_: (_ for _ in ()).throw(TimeoutError('primitive cap')))
    signal.alarm(55)
    try:
        run(parser.parse_args())
    finally:
        signal.alarm(0)
