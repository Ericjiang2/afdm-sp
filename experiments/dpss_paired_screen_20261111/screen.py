"""Paired integer-delay screening of progressive DPSS rescue."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'dpss_block_rescue_20261110'))
from run import bank_for, m2, p1, paired, prefix, score
from analyze import crossing

GRID = {'U': (4., 4.5, 5., 5.5, 6.), 'G': (4., 4.5, 5., 5.5, 6.),
        'J4': (5.5, 6.5, 7.5, 8.5)}
ARMS = ('UNIFIED', 'B', 'WIDE', 'A3')
ENTROPY = hashlib.sha256(b'AFDM-20261111-DPSS-paired-screen-v1').hexdigest()
RHO = .3


def context(out):
    # Linux uses the reviewed directory names. The archived byte identities still apply.
    args = m2.parse_args(['--mode', 'generate', '--out', str(out)])
    if not (HERE.parent / args.native_dir / 'src').is_dir():
        return paired.context(out)
    ctx = m2.load_context(args)
    archived = paired.M2_CONFIG
    assert ctx.sources == archived['source_sha256']
    for name, sha in ctx.sources.items():
        assert paired.P1_CONFIG['source_sha256'].get(name, sha) == sha, name
    for module in (p1, p1.gen_fixed):
        assert m2.base.sha256_file(module.__file__) == paired.P1_CONFIG['source_sha256'][module.__name__]
    for key in ('checkpoint_sha256', 'code_g_sha256'):
        assert ctx.header[key] == paired.P1_CONFIG[key] == archived[key]
    assert {key: vars(flags) for key, flags in p1.SCENARIOS.items()} == paired.P1_CONFIG['scenario_flags']
    ctx.hd = m2.base
    return ctx


class Widening:
    def __init__(self, bank):
        self.bank = bank
        wide = m2.dpss_rx.tap_columns(bank.n, 0., 2.5, 8)[0]
        mods = np.column_stack((bank.modulations, wide))
        self.spectrum = np.fft.ifft(mods[:, :, None].conj() * mods[:, None, :], axis=0)
        self.q = round(2 * bank.n * bank.c1)

    def fit(self, obs, mu, v, taps):
        bank = self.bank
        des = m2.dpss_rx.Design(obs['y'], obs['pilot'], mu, taps, bank.c1, bank.c2)
        ids = np.concatenate([np.arange(15, 23) if t['D'] == 8 else
                              3 * (int(t['c']) + 2) + np.arange(3) for t in taps])
        left, right = des.delays[:, None], des.delays[None, :]
        delta = right - left
        gamma = (np.exp(2j * np.pi * bank.c1 * (left**2 - right**2))
                 * np.fft.fft(v)[delta % bank.n]
                 * self.spectrum[(self.q * delta) % bank.n, ids[:, None], ids[None, :]])
        q = des.BhB + gamma + obs['sigma2'] * np.eye(des.C)
        h = np.linalg.solve((q + q.conj().T) / 2, des.b)
        c = m2.tapchannel.tap_channel_class()(bank.n, bank.c1, bank.c2, des.delays,
                                               np.zeros(des.C), h)
        object.__setattr__(c, 'tap_mods', des.M)
        return float(np.vdot(des.b, h).real), c, gamma


def terminal(ctx, obs, channel, prior):
    out = m2.dpss_rx.scalar_joint_cols(obs['y'], obs['pilot'], channel, obs['sigma2'],
        np.full(channel.p, 1 / channel.p), pd=1 - ctx.system.rho, prior=prior, iterations=20)
    return ctx.native.decoder_messages(ctx.code, np.clip(out['extrinsic'], -20, 20), maxiter=50)


def unified(ctx, bank, widening, obs):
    from messages import moments
    start = time.perf_counter()
    result, refiner = prefix(ctx, obs)
    dec = result.decoder
    initial = tuple(5 * t['delay'] + int(t['c']) + 2 for t in refiner.prev['taps'])
    groups, expanded = initial, []
    syndrome = lambda: ctx.hd.syndrome_weight(ctx, dec['decoded'])
    if syndrome():
        mu, v, _ = moments(np.clip(result.arrays['r1_app'], -20, 20), 1 - ctx.system.rho)
        prior = np.clip(result.arrays['r1_check'], -20, 20)
        prepared = bank.prepare(obs, mu, v)
        groups = bank.exchange(initial, prepared, True)
        dec = terminal(ctx, obs, bank.channel(groups, prepared), prior)
        taps = [dict(delay=int(bank.delay[g]), c=int(bank.center[g]), W=.5, D=3) for g in groups]
        while syndrome() and len(expanded) < len(taps):
            candidates = []
            for i, tap in enumerate(taps):
                if tap['D'] == 8:
                    continue
                trial = [dict(t) for t in taps]
                trial[i].update(c=0, W=2.5, D=8)
                value, channel, _ = widening.fit(obs, mu, v, trial)
                candidates.append((value, i, trial, channel))
            _, i, taps, channel = max(candidates, key=lambda item: item[0])
            expanded.append(taps[i]['delay'])
            dec = terminal(ctx, obs, channel, prior)
    return dec, dict(initial=initial, groups=groups, expanded=expanded,
                     seconds=time.perf_counter() - start)


def pair_hash(obs):
    return hashlib.sha256(obs['y'].tobytes() + obs['pilot'].tobytes()
                          + np.float64(obs['sigma2']).tobytes()).hexdigest()


def row(ctx, bank, widening, family, frame, snr, raw, diag):
    truth = ctx.hd.truth_from_raw(raw, diag)
    obs = ctx.hd.observe(raw, RHO, snr)
    pair = pair_hash(obs)
    reference = p1.compute_arms(ctx, obs, truth, ('B', 'A3'))
    for result in reference.values():
        if result['status'] != 'ok':
            raise RuntimeError(result)
    w = m2.run_m(ctx, obs, 'M_adapt', paired.CFG)
    wide = ctx.hd.score(ctx, w, truth)
    dec, trace = unified(ctx, bank, widening, obs)
    new = score(ctx, dec, truth) | dict(seconds=trace['seconds'])
    assert pair == pair_hash(obs)
    assert len(trace['initial']) == len(trace['groups']) and len(set(trace['expanded'])) == len(trace['expanded'])
    def compact(s):
        return dict(errors=s['info_errors'], syndrome=s['syndrome'],
                    logloss=s['logloss_bits'], seconds=s['seconds'])
    return dict(family=family, frame=frame, snr=snr, pair=pair, trace=trace,
                arms=dict(UNIFIED=new, B=compact(reference['B']), WIDE=compact(wide),
                          A3=compact(reference['A3'])))


def run(args):
    import copy

    ctx = context(args.out)
    bank = bank_for(ctx)
    widening = Widening(bank)
    seed = p1.make_seed_fn(ENTROPY)
    message_ctx = copy.copy(ctx)
    message_ctx.system = copy.copy(ctx.system)
    message_ctx.system.rho = RHO
    with (args.out / f'rows-{args.shard:02d}.jsonl').open('x') as handle:
        for frame in range(args.shard, args.frames, args.shards):
            for family, grid in GRID.items():
                if family == 'J4':
                    geom = ctx.hd.draw_cluster_geometry(ENTROPY, frame)
                    msg = ctx.hd.cluster_message(message_ctx, ENTROPY, frame)
                    base, diag = ctx.hd.cluster_base(ctx, msg, geom, 'J4')
                else:
                    base, diag = p1.generate(ctx, family, RHO, grid[0], frame, seed)
                for snr in (grid[:1] if args.smoke else grid):
                    raw, details = (ctx.hd.cluster_at_snr(base, snr), diag) if family == 'J4' else (
                        ctx.reuse_at_snr(base, diag, snr))
                    item = row(ctx, bank, widening, family, frame, snr, raw, details)
                    print(json.dumps(item, allow_nan=False), file=handle, flush=True)


def summarize(args):
    rows = {}
    for path in sorted(args.out.glob('rows-*.jsonl')):
        for line in path.read_text().splitlines():
            r = json.loads(line)
            key = r['family'], r['frame'], r['snr']
            assert key not in rows
            rows[key] = r
    n = args.frames
    assert len(rows) == n * sum(map(len, GRID.values()))
    rng = np.random.default_rng(417650)
    counts = np.vstack((np.ones(n, int), rng.multinomial(n, np.full(n, 1 / n), size=10000)))
    report = {}
    for family, grid in GRID.items():
        cells = [[rows[family, f, s] for s in grid] for f in range(n)]
        err = {a: np.array([[r['arms'][a]['errors'] > 0 for r in line] for line in cells]) for a in ARMS}
        comp = 'WIDE' if family == 'J4' else 'B'
        cross = {a: crossing(counts @ e / n, np.full((len(counts), len(grid)), n),
                             np.asarray(grid), .1)[0] for a, e in err.items()}
        d = cross['UNIFIED'] - cross[comp]
        paired_delta = counts @ (err['UNIFIED'].astype(int) - err[comp]) / n
        finite = np.isfinite(d[1:])
        ci = np.quantile(d[1:][finite], [.025, .975]).tolist() if finite.mean() >= .95 else None
        report[family] = dict(snr=grid, frames=n, comparator=comp,
            errors={a: e.sum(axis=0).tolist() for a, e in err.items()},
            delta_fer_ci95=np.quantile(paired_delta[1:], [.025, .975], axis=0).tolist(),
            rescue=(err[comp] & ~err['UNIFIED']).sum(axis=0).tolist(),
            harm=(~err[comp] & err['UNIFIED']).sum(axis=0).tolist(),
            undetected={a: sum(r['arms'][a]['errors'] > 0 and r['arms'][a]['syndrome'] == 0
                                for line in cells for r in line) for a in ARMS},
            crossing_db={a: float(x[0]) if np.isfinite(x[0]) else None for a, x in cross.items()},
            delta_db=float(d[0]) if np.isfinite(d[0]) else None, crossing_ci95=ci,
            joint_crossing_fraction=float(finite.mean()), widened=sum(bool(r['trace']['expanded']) for line in cells for r in line),
            terminal_widen_calls=sum(len(r['trace']['expanded']) for line in cells for r in line))
    (args.out / 'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--frames', type=int, default=160)
    parser.add_argument('--shard', type=int, default=0)
    parser.add_argument('--shards', type=int, default=1)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    (summarize if args.summarize else run)(args)
