"""CSTATE structural score by downstream gain-mean update factorial."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
E1 = HERE.parent / 'tf_cstate_e1_20261017'
sys.path.insert(0, str(E1))
import e1_driver as e1

ARMS = ('FULL_NATIVE', 'DIAG_NATIVE', 'FULL_JOINT', 'DIAG_JOINT')
KEY_FILE = E1 / 'out/select/triggered_keys.json'


def units():
    data = json.loads(KEY_FILE.read_text())
    return [u for u in data['units'] if u['rho_permille'] == 300 and u['frame'] < 128
            and u['snr_centi_db'] in (450, 500, 550, 600)]


def replay(ctx, geom, unit, gate=False):
    from joint import expected_mean, replay_joint
    from messages import moments
    from physical import Channel, daft

    family, rho, snr, frame = (unit[k] for k in e1.KEY_FIELDS)
    raw, diag = e1.p1ctx.base(ctx, family, rho / 1000, frame)
    _, obs, truth = e1.gd.observe(ctx, raw, diag, rho / 1000, snr)
    dec, arrays, syn, _ = e1.f0_state(ctx, obs)
    assert syn != 0 and syn == unit['f0_syndrome'] and e1.gd.bits_sha(dec['decoded']) == unit['f0_sha']
    app, check = (np.clip(arrays['r1_' + key], -20, 20) for key in ('app', 'check'))
    mu, v, _ = moments(app, 1 - ctx.system.rho)
    initial = [geom.Path(int(delay), float(doppler))
               for delay, doppler in zip(arrays['r1_delays'], arrays['r1_dopplers'], strict=True)]
    y, pilot, noise = (obs[k] for k in ('y', 'pilot', 'sigma2'))
    system = ctx.system
    Y = daft(y, system.c1, system.c2, True)
    common = dict(c1=system.c1, c2=system.c2, ridge=noise, max_delay=system.l_max_cap,
                  grid_step=.25, chunk_size=64, strategy='compact')
    arms, paths, chosen = {}, {}, {}
    for mode in ('full', 'diag'):
        structural = geom.reopen_geometry(Y, pilot+mu, v, initial, max_edits=2,
                                          local_passes=0, gamma_mode=mode, **common)
        chosen[mode] = [(p.delay, p.doppler) for p in structural.paths]
        refined = geom.reopen_geometry(Y, pilot+mu, v, structural.paths, max_edits=0,
                                       local_passes=2, gamma_mode='full', **common)
        paths[mode] = [(p.delay, p.doppler) for p in refined.paths]
        c = Channel(len(Y), system.c1, system.c2, *zip(*paths[mode]), refined.gains)
        opts = dict(pd=1-system.rho, prior=check, iterations=20, damping=.3, gain_mode='joint')
        native = ctx.native.scalar_joint(y, pilot, c, noise, **opts)
        if gate:
            clone = replay_joint(y, pilot, c, noise, **opts)
            for key in ('extrinsic', 'gains', 'gain_variance'):
                np.testing.assert_array_equal(clone[key], native[key])
            assert clone['trace'] == native['trace']
        joint = replay_joint(y, pilot, c, noise, mean_update=expected_mean, **opts)
        for suffix, out in (('NATIVE', native), ('JOINT', joint)):
            decoded = ctx.native.decoder_messages(ctx.code, np.clip(out['extrinsic'], -20, 20), maxiter=50)
            bits = decoded['decoded']
            arms[mode.upper()+'_'+suffix] = dict(errors=e1.gd.score(ctx, bits, truth),
                sha=e1.gd.bits_sha(bits), syndrome=ctx.hd.syndrome_weight(ctx, bits),
                logloss=ctx.arms.logloss_bits(decoded['incoming_llr'], truth['coded']))
    assert arms['FULL_NATIVE']['sha'] == unit['b_sha']
    assert arms['FULL_NATIVE']['errors'] == unit['b_info_errors']
    if paths['full'] == paths['diag']:
        assert arms['FULL_NATIVE'] == arms['DIAG_NATIVE'] and arms['FULL_JOINT'] == arms['DIAG_JOINT']
    return dict(family=family, snr=snr, frame=frame, arms=arms, chosen=chosen, paths=paths,
                prior_sha256=hashlib.sha256(check.tobytes()).hexdigest(),
                obs_sha256=hashlib.sha256(y.tobytes()+pilot.tobytes()+np.float64(noise).tobytes()).hexdigest())


def run(args):
    ctx = e1.p1ctx.load()
    e1.check_frozen_md5(ctx)
    geom = e1.load_variant()
    selected = units()
    if args.gate:
        selected = [next(u for u in selected if u['scenario'] == s and u['snr_centi_db'] == snr)
                    for s in ('U','G') for snr in (450,600)]
    with (args.out / ('gate.jsonl' if args.gate else f'rows-{args.shard:02d}.jsonl')).open('x') as handle:
        for unit in selected[args.shard::args.shards]:
            print(json.dumps(replay(ctx, geom, unit, args.gate), allow_nan=False), file=handle, flush=True)


def summarize(args):
    rows = {}
    for path in sorted(args.out.glob('rows-*.jsonl')):
        for line in path.read_text().splitlines():
            r = json.loads(line)
            key = r['family'], r['snr'], r['frame']
            assert key not in rows
            rows[key] = r
    assert rows.keys() == {(u['scenario'], u['snr_centi_db'], u['frame']) for u in units()}
    data = list(rows.values())
    frames = sorted({r['frame'] for r in data})
    frame_index = {f:i for i,f in enumerate(frames)}
    indices = np.asarray([frame_index[r['frame']] for r in data])
    rng = np.random.default_rng(71626)
    draws = rng.multinomial(len(frames), np.full(len(frames), 1/len(frames)), size=10000)
    weights = draws[:, indices]
    err = {a:np.asarray([r['arms'][a]['errors'] > 0 for r in data], dtype=int) for a in ARMS}
    loss = {a:np.asarray([r['arms'][a]['logloss'] for r in data]) for a in ARMS}
    def contrast(delta):
        return dict(mean=float(delta.mean()), ci95=np.quantile(
            (weights @ delta) / weights.sum(axis=1), [.025,.975]).tolist())
    def factorial(values):
        native = values['DIAG_NATIVE'] - values['FULL_NATIVE']
        joint = values['DIAG_JOINT'] - values['FULL_JOINT']
        return dict(native=contrast(native), joint=contrast(joint), interaction=contrast(joint-native))
    report = dict(triggered_rows=len(data), frame_clusters=len(frames),
        structural_discordances=sum(r['chosen']['full'] != r['chosen']['diag'] for r in data),
        failures={a:int(e.sum()) for a,e in err.items()},
        failures_by_cell={f'{s}-{snr}':{a:sum(r['arms'][a]['errors']>0 for r in data
            if r['family']==s and r['snr']==snr) for a in ARMS}
            for s in ('U','G') for snr in (450,500,550,600)},
        logloss={a:float(l.mean()) for a,l in loss.items()},
        fer_factorial=factorial(err), logloss_factorial=factorial(loss))
    (args.out/'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--shard', type=int, default=0)
    parser.add_argument('--shards', type=int, default=1)
    parser.add_argument('--gate', action='store_true')
    parser.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    (summarize if args.summarize else run)(args)
