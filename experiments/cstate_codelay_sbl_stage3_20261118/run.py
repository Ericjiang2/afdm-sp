"""Stage 3 receiver qualification and paired-main sharding."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

import numpy as np

import codelay

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP/'tf_cstate_e1_20261017'))
import e1_driver as e1

CELLS = tuple((s, r) for s in ('U', 'G') for r in (300, 500))
GRID = {300: (500, 550, 600, 700, 800, 900, 1000, 1100),
        500: (500, 550, 600, 650, 700, 800, 900, 1000, 1100)}
ARMS = ('F0', 'FULL', 'CODELAY')
MAIN_FRAMES = range(4000, 4400)
HISTORIC_KEYS = EXP/'tf_cstate_e1_20261017/out/select/triggered_keys.json'
P1_MD5 = dict(gen_fixed='9a3a987e0a1aaecde33018da5f38c74c',
              gs_driver='10611942919e1efcf2839ee5c260d22a',
              native_twofft='d47af1373b2f0052e6de078de40711ba',
              p1_driver='e8594ebfe04f490a86fc16ebd5069cd2',
              p1ctx='e66268616035f8111aacb4910d5bc8a2',
              receiver='228411ca9751eecfca2f794ace909dfd')


def dump(value, dst):
    print(json.dumps(value, allow_nan=False), file=dst, flush=True)


def write_json(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def read_rows(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def context():
    ctx = e1.p1ctx.load()
    checked = e1.check_frozen_md5(ctx)
    if any(r['status'] != 'ok' for r in checked.values()):
        raise AssertionError('E-1 source inventory did not pass')
    if {name: ctx.source_md5[name] for name in P1_MD5} != P1_MD5:
        raise AssertionError('P1 imports differ from the historical SBL archives')
    full = e1.load_variant()
    route = codelay.load(full)
    return ctx, full, route, checked


def key_of(row):
    return tuple(row[field] for field in e1.KEY_FIELDS)


def main_keys():
    return {(s, rho, snr, frame) for frame in MAIN_FRAMES for s, rho in CELLS for snr in GRID[rho]}


def inputs(ctx, frame, scenario, rho):
    raw, diag = e1.p1ctx.base(ctx, scenario, rho/1000, frame)
    return raw, diag


def observed(ctx, base, rho, snr):
    raw, obs, truth = e1.gd.observe(ctx, *base, rho/1000, snr)
    return raw, obs, truth


def digest(a):
    a = np.asarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(repr(a.shape).encode())
    h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def truth_record(obs, truth):
    return dict(sigma2=float(obs['sigma2']), delays=truth['l_i'].tolist(),
                dopplers=truth['k_real'].tolist(),
                gains=[[float(g.real), float(g.imag)] for g in truth['g_i']])


def decoded(ctx, output, truth):
    bits = output['decoded']
    errors = e1.gd.score(ctx, bits, truth)
    return dict(errors=int(errors), decoded_sha=e1.gd.bits_sha(bits))


def arm(ctx, kernel, obs, truth, arrays, syndrome, f0):
    if not syndrome:
        return f0, None
    branch = e1.run_branch(ctx, kernel, obs, arrays, 'A1')
    return decoded(ctx, branch['decoder'], truth), branch


def path_records(branch):
    if branch is None:
        return None
    res = branch['result']
    return dict(paths=[[p.delay,p.doppler] for p in res.paths],
                edits=[dict(slot=x['slot'], old=x['old'], new=x['new']) for x in res.edits],
                fallback=bool(res.diagnostics['numerical_fallback']))


def input_record(raw, obs):
    return dict(y=digest(obs['y']), pilot=digest(obs['pilot']), info=digest(raw['info']),
                coded=digest(raw['coded']), noise=digest(raw['noise']), data=digest(raw['data']))


def one(ctx, full, route, base, s, rho, snr, frame):
    raw, obs, truth = observed(ctx, base, rho, snr)
    dec, arrays, syndrome, _ = e1.f0_state(ctx, obs)
    f0 = decoded(ctx, dec, truth)
    a, full_branch = arm(ctx, full, obs, truth, arrays, syndrome, f0)
    b, codelay_branch = arm(ctx, route, obs, truth, arrays, syndrome, f0)
    return dict(scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame,
                syndrome=syndrome, truth=truth_record(obs, truth), inputs=input_record(raw, obs),
                arms=dict(F0=f0, FULL=a, CODELAY=b), full_geometry=path_records(full_branch),
                codelay_geometry=path_records(codelay_branch))


def compare_geometry(reference, candidate, energy):
    if [p.delay for p in reference.paths] != [p.delay for p in candidate.paths]:
        raise AssertionError('Final delays differ from the uniform-variance reference')
    shifts = np.abs(np.array([p.doppler for p in reference.paths])
                    - np.array([p.doppler for p in candidate.paths]))
    if shifts.max() > 2e-5:
        raise AssertionError(f'Refined Doppler shift {shifts.max()} exceeds gate')
    np.testing.assert_allclose(reference.gains, candidate.gains, rtol=2e-4, atol=2e-6)
    np.testing.assert_allclose(candidate.objective_after, reference.objective_after,
                               rtol=1e-10, atol=1e-11*max(1., energy))
    discrepancy = abs(candidate.objective_after - reference.objective_after)
    for ref, got in zip(reference.global_trace, candidate.global_trace, strict=True):
        np.testing.assert_array_equal(got['valid'], ref['valid'])
        np.testing.assert_allclose(got['scores'][got['valid']], ref['scores'][ref['valid']],
                                   rtol=1e-10, atol=1e-11*max(1., energy))
        for field, p in (('selected','replacement'), ('accepted','new')):
            def choice(trace):
                action = trace[field]
                return None if action is None else (action['slot'], action[p])
            assert choice(got) == choice(ref), (field, choice(got), choice(ref))
    return float(shifts.max()), float(discrepancy)


def uniform_kernel(full):
    def reopen(y, x, v, paths, **opts):
        return full.reopen_geometry(y, x, np.full_like(v, v.mean()), paths, **opts)
    return SimpleNamespace(Path=full.Path, reopen_geometry=reopen)


def historic_gate():
    ctx, full, route, checks = context()
    uniform = uniform_kernel(full)
    entries = json.loads(HISTORIC_KEYS.read_text())['units']
    units = [next(r for r in entries if r['scenario'] == s and r['rho_permille'] == 300
                  and r['snr_centi_db'] == g and r['frame'] < 128)
             for s in ('U','G') for g in (450,500,550,600)]
    result = []
    for unit in units:
        s, rho, snr, frame = key_of(unit)
        _, obs, truth = observed(ctx, inputs(ctx, frame, s, rho), rho, snr)
        dec, arrays, syndrome, _ = e1.f0_state(ctx, obs)
        f0 = decoded(ctx, dec, truth)
        assert syndrome and syndrome == unit['f0_syndrome'] and f0['decoded_sha'] == unit['f0_sha']
        legacy, _ = arm(ctx, full, obs, truth, arrays, syndrome, f0)
        assert legacy['errors'] == unit['b_info_errors'] and legacy['decoded_sha'] == unit['b_sha']
        match, a = arm(ctx, uniform, obs, truth, arrays, syndrome, f0)
        got, b = arm(ctx, route, obs, truth, arrays, syndrome, f0)
        assert got == match, (key_of(unit), match, got)
        err, discrepancy = compare_geometry(a['result'], b['result'], np.vdot(obs['y'], obs['y']).real)
        result.append(dict(key=list(key_of(unit)), final_doppler_delta=err,
                           final_objective_delta=discrepancy, decoded_sha=got['decoded_sha']))
        print(f'Historic gate passed {key_of(unit)}', flush=True)
    return dict(source_checks=checks, historic=result, environment=ctx.environment)


def shard(out, shard_index, shards):
    ctx, full, route, _ = context()
    with (out/f'main-{shard_index:02d}.jsonl').open('x') as file:
        for frame in MAIN_FRAMES[shard_index::shards]:
            for s, rho in CELLS:
                base = inputs(ctx, frame, s, rho)
                for snr in GRID[rho]:
                    try:
                        dump(one(ctx, full, route, base, s, rho, snr, frame), file)
                    except Exception as exc:
                        raise RuntimeError(f'Stage 3 key {(s,rho,snr,frame)} failed') from exc
    print(f'main-{shard_index:02d} completed', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('gate','main'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--commit', required=True)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--shards', type=int, default=1)
    args = p.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        p.error('Expected audited pre-run commit')
    if not 0 <= args.shard < args.shards <= 24:
        p.error('Invalid shard coordinate')
    if args.mode == 'gate':
        result = historic_gate()
        args.out.mkdir(parents=True, exist_ok=True)
        write_json(args.out/'gate.json', dict(commit=args.commit, **result))
    else:
        gate = json.loads((args.out/'gate.json').read_text())
        if gate['commit'] != args.commit or len(gate['historic']) != 8:
            raise ValueError('Main must use the producing commit from a complete gate')
        shard(args.out, args.shard, args.shards)
