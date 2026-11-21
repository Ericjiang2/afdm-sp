#!/usr/bin/env python3
"""Frozen-project adapter and bounded audit runner. Never calls a receiver/decoder."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import importlib.util
import json
import os
import resource
from pathlib import Path
import sys
import time
import traceback

import numpy as np
from scipy import stats

import independent as ind

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
EXP = PROJECT / 'experiments'
RTOL = 1e-10
PTOL = 1e-9


class Blocker(RuntimeError):
    pass


def md5(path):
    h = hashlib.md5()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def put(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def energy(x):
    return float(np.vdot(x, x).real / len(x))


def require(ok, message):
    if not ok:
        raise Blocker(message)


def relative(a, b):
    return float(np.linalg.norm(a - b) / max(np.linalg.norm(b), 1e-300))


def import_frozen(directory, module):
    sys.path.insert(0, str(EXP / directory))
    return importlib.import_module(module)


def truth_rows(directory, quotas, snr_db=None):
    """First stored full-truth frame per scenario, stable filename/line ordering."""
    selected, seen, sources = [], set(), {}
    files = sorted(Path(directory).glob('rows*.jsonl*'))
    for path in files:
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt') as stream:
            for line_no, line in enumerate(stream, 1):
                row = json.loads(line)
                sc = row.get('scenario', 'J4')
                qkey = (sc, float(row['rho'])) if any(isinstance(k, tuple) for k in quotas) else sc
                if qkey not in quotas or quotas[qkey] == 0 or not row.get('truth') or (snr_db is not None and row['snr_db'] != snr_db):
                    continue
                key = (sc, int(row['frame']))
                if key in seen:
                    continue
                t = row['truth']
                if not all(k in t for k in ('delays', 'dopplers')):
                    continue
                sources[str(path.resolve())] = None
                selected.append(dict(row=row, path=str(path.resolve()), line=line_no))
                seen.add(key)
                quotas[qkey] -= 1
                if not any(quotas.values()):
                    break
        if not any(quotas.values()):
            break
    if any(quotas.values()):
        raise RuntimeError(f'insufficient saved truth rows in {directory}: missing {quotas}')
    for path in sources:
        sources[path] = md5(path)
    return selected, sources


def saved_paths(row, gains=None):
    t = row['truth']
    g = np.array([complex(*g) for g in t['gains']]) if 'gains' in t else gains
    return np.asarray(t['delays'], int), np.asarray(t['dopplers']), g


def ledger_rows(entries):
    wanted = {(x['row']['scenario'], int(x['row']['frame']), int(x['row']['rho_permille']), int(x['row']['snr_centi_db'])) for x in entries}
    found, sources = {}, {}
    for path in sorted((EXP / 'tcom_reference_frame_20261015/out/p1').glob('rows*.jsonl*')):
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt') as stream:
            for line_no, line in enumerate(stream, 1):
                r = json.loads(line)
                key = (r['scenario'], int(r['frame']), int(r['rho_permille']), int(r['snr_centi_db']))
                if key in wanted:
                    found[key] = dict(row=r, path=str(path.resolve()), line=line_no)
                    sources[str(path.resolve())] = None
        if wanted <= found.keys():
            break
    if not wanted <= found.keys():
        raise RuntimeError(f'missing {len(wanted - found.keys())} P1 ledger truth hashes')
    return found, {p: md5(p) for p in sources}


def path_laws(ctx, p1, p2b, ch, out, result, checkpoint):
    tests = []
    refs, samples = {}, {}
    for sc in ('U', 'G', 'S'):
        flag = p2b.FLAGS_S if sc == 'S' else p1.SCENARIOS[sc]
        seed_fn = p1.make_seed_fn(p2b.ENTROPY_TEST, p2b.DOMAIN_TEST) if sc == 'S' else p1.make_seed_fn()
        rows = []
        for frame in range(2000):
            seed = p1.gen_fixed.expected_channel_seed(seed_fn, frame)
            d = p1.gen_fixed.draw_paths(ctx.system, np.random.RandomState(seed), flag)
            l = p1.gen_fixed.delay_bins(ctx.system, d['delay_idx_bar'], flag)
            k = p1.gen_fixed.doppler_k_real(ctx.system, d['doppler_a'], flag, p1.gen_fixed.geo_rng_for(seed))
            require(l.max() <= (25 if sc == 'S' else 102) and len(np.unique(l)) == 8, f'{sc} D1/D2 geometry violated frame={frame}')
            require(abs(np.vdot(d['gain_tap'], d['gain_tap']).real - 1) <= PTOL, f'{sc} A1 path energy violated frame={frame}')
            rows.append(dict(delays=l, dopplers=k, gains=d['gain_tap'], variance=d['path_var'], attempts=d['attempts']))
        sample = {k: np.array([r[k] for r in rows]) for k in rows[0]}
        ref = ind.reference(20000, sc, 2026101900 + ord(sc))
        samples[sc], refs[sc] = sample, ref
        # One statistic per frame preserves independence; path positions are tested separately.
        features = {'max_delay': lambda x: x['delays'].max(axis=1),
                    'span': lambda x: np.ptp(x['delays'], axis=1),
                    'attempts': lambda x: x['attempts']}
        for j in range(8):
            features[f'delay_{j}'] = lambda x, j=j: x['delays'][:, j]
            features[f'doppler_{j}'] = lambda x, j=j: x['dopplers'][:, j]
            features[f'gain_power_{j}'] = lambda x, j=j: abs(x['gains'][:, j])**2
            # Dividing by the conditional PDP removes its delay-dependent Rayleigh scale.
            def conditional(x, j=j):
                q = abs(x['gains'])**2 / x['variance']
                return (q / q.sum(axis=1, keepdims=True))[:, j]
            features[f'conditional_gain_{j}'] = conditional
            phase = np.mod(np.angle(sample['gains'][:, j]), 2 * np.pi) / (2 * np.pi)
            ks = stats.kstest(phase, 'uniform')
            tests.append(dict(scenario=sc, name=f'phase_uniform_{j}', statistic=float(ks.statistic), p=float(ks.pvalue)))
        for name, fn in features.items():
            ks = stats.ks_2samp(fn(sample), fn(ref), method='asymp')
            tests.append(dict(scenario=sc, name=name, statistic=float(ks.statistic), p=float(ks.pvalue)))
        reject = int((sample['attempts'] > 1).sum())
        ref_reject = int((ref['attempts'] > 1).sum())
        _, p = stats.fisher_exact([[reject, 2000 - reject], [ref_reject, 20000 - ref_reject]])
        tests.append(dict(scenario=sc, name='first_rejection_rate', p=float(p)))
        result.setdefault('parameter_laws', {})[sc] = dict(n=2000, reference_n=20000,
            first_rejection_rate=reject / 2000, independent_first_rejection_rate=ref_reject / 20000,
            historical_approximate_rate=.582 if sc == 'S' else .486,
            max_delay=int(sample['delays'].max()), max_power_error=float(np.max(abs((abs(sample['gains'])**2).sum(axis=1) - 1))))
        ci = stats.binomtest(reject, 2000).proportion_ci(confidence_level=.99)
        historic = .582 if sc == 'S' else .486
        se = np.sqrt(historic * (1-historic) / 2000)
        result['parameter_laws'][sc].update(first_rejection_99pct_interval=[float(ci.low), float(ci.high)],
            historical_three_se=float(3*se), historical_within_three_se=bool(abs(reject/2000-historic) <= 3*se))
        checkpoint()
    c_rays, c_spacing, c_first_nu = [], [], []
    for frame in range(2000):
        geom = ch.draw_cluster_geometry(ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, frame)
        paths = ch.cluster_paths(geom)
        require(np.array_equal(paths['rays_per_tap'], 1 + stats.poisson.ppf(geom['u_rays'], 3).astype(int)), f'C Poisson mapping frame={frame}')
        require(np.allclose(paths['k_real'], 2*np.cos(np.concatenate([geom['uth'][t, :r] for t, r in enumerate(paths['rays_per_tap'])])), atol=1e-14, rtol=0), f'C angular mapping frame={frame}')
        c_rays.extend(paths['rays_per_tap'])
        c_spacing.append(np.diff(paths['tap_delays']))
        c_first_nu.append([paths['k_real'][np.flatnonzero(paths['tap_of'] == t)[0]] for t in range(4)])
    observed = np.bincount(np.minimum(c_rays, 9), minlength=10)[1:]
    expected = 8000*np.r_[stats.poisson.pmf(np.arange(8), 3), stats.poisson.sf(7, 3)]
    chi = stats.chisquare(observed, expected)
    tests.append(dict(scenario='C', name='rays_1_plus_poisson3', statistic=float(chi.statistic), p=float(chi.pvalue)))
    actual_spacing, reference_spacing = np.asarray(c_spacing), ind.cluster_reference(20000)
    for j in range(3):
        a = np.bincount(np.minimum(actual_spacing[:, j], 21), minlength=22)[1:]
        b = np.bincount(np.minimum(reference_spacing[:, j], 21), minlength=22)[1:]
        chi = stats.chi2_contingency(np.array([a, b]))
        tests.append(dict(scenario='C', name=f'truncated_geometric_spacing_{j}', statistic=float(chi.statistic), p=float(chi.pvalue)))
    for t in range(4):
        z = np.clip(np.asarray(c_first_nu)[:, t]/2, -1, 1)
        ks = stats.kstest(1-np.arccos(z)/np.pi, 'uniform')
        tests.append(dict(scenario='C', name=f'uniform_angle_first_ray_tap_{t}', statistic=float(ks.statistic), p=float(ks.pvalue)))
    result['C_parameter_laws'] = dict(frames=2000, mean_rays_per_tap=float(np.mean(c_rays)),
                                      max_rays_per_tap=int(max(c_rays)), spacing_reference_frames=20000)
    order = np.argsort([t['p'] for t in tests])
    adjusted = 0.
    for rank, index in enumerate(order):
        adjusted = max(adjusted, min(1., tests[index]['p'] * (len(tests) - rank)))
        tests[index]['p_holm'] = adjusted
        tests[index]['severity'] = 'MAJOR' if adjusted < .01 else 'OK'
    result['law_tests'] = tests
    path = out / 'parameter_draws.npz'
    np.savez_compressed(path, **{f'{sc}_{k}': v for sc, sample in samples.items() for k, v in sample.items()})
    result.setdefault('remote_artifacts', []).append(dict(path=str(path.resolve()), md5=md5(path), bytes=path.stat().st_size))
    checkpoint()


def compare_truth(raw, stored):
    l, nu, g = saved_paths(stored, raw['params']['g_i'])
    p = raw['params']
    errors = dict(delay=int(np.max(abs(l-p['l_i']))), doppler=float(np.max(abs(nu-p['k_real']))), gain=float(np.max(abs(g-p['g_i']))))
    require(errors['delay'] == 0 and errors['doppler'] <= 1e-12 and errors['gain'] <= 1e-12,
            f'saved truth mismatch frame={stored["frame"]} errors={errors}')
    return l, nu, g


def physical(ctx, p1, ch, result, checkpoint):
    saved, sources = truth_rows(EXP / 'tf_cstate_e1_20261017/out/main', {(sc,rho):100 for sc in ('U','G') for rho in (.3,.5)}, snr_db=4.5)
    csaved, csources = truth_rows(EXP / 'tf_cstate_e2_20261017/out/main_C', {'J4': 50})
    sources.update(csources)
    ledger, lsources = ledger_rows(saved)
    sources.update(lsources)
    result['stored_truth_sources'] = sources
    result['physical_operator'] = []
    result['E1_snr_rows'] = []
    seed_fn = p1.make_seed_fn()
    for family, entries in (('P1', saved), ('C', csaved)):
        errors, powers = [], []
        for item in entries:
            row = item['row']
            f, rho = int(row['frame']), float(row['rho'])
            if family == 'P1':
                raw, diag = p1.generate(ctx, row['scenario'], rho, float(row['snr_db']), f, seed_fn)
            else:
                fg = ch.frame_geometry(ctx, ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f)
                msg = ch.cluster_message(ctx, ch.make_seed_fn(), rho, f)
                raw, diag = ch.cluster_base(ctx, fg, msg)
                raw = ch.at_snr(raw, float(row['snr_db']))
                require(len(np.unique(raw['params']['l_i'])) == 4, f'C tap geometry frame={f}')
                require(np.array_equal(np.bincount(fg['paths']['tap_of']), fg['paths']['rays_per_tap']), f'C rays-per-tap frame={f}')
            l, nu, g = compare_truth(raw, row)
            phase_source = 'stored full complex gains'
            ledger_receipt = None
            if family == 'P1':
                key = (row['scenario'], f, int(row['rho_permille']), int(row['snr_centi_db']))
                ledger_receipt = ledger[key]
                lr = ledger_receipt['row']
                require(ctx.array_hash(g) == lr['physical_gains_sha256'], f'P1 stored gain hash mismatch frame={f}')
                require(hashlib.sha256(np.ascontiguousarray(raw['noise']).tobytes()).hexdigest() == lr['noise_sha256'], f'P1 stored noise hash mismatch frame={f}')
                require(hashlib.sha256(np.ascontiguousarray(raw['info']).tobytes()).hexdigest() == lr['info_sha256'], f'P1 stored info hash mismatch frame={f}')
                require(int(raw['channel_seed']) == int(lr['channel_seed']), f'P1 stored channel seed mismatch frame={f}')
                order = np.argsort(-abs(g)**2, kind='stable')
                require(np.array_equal(l[order], lr['truth_l']) and np.allclose(nu[order], lr['truth_k'], atol=1e-12, rtol=1e-12)
                        and np.allclose(abs(g[order])**2, lr['truth_g2'], atol=1e-12, rtol=1e-12), f'P1 stored truth mismatch frame={f}')
                phase_source = 'regenerated complex gains; bitwise SHA256 authenticated by saved P1 ledger; E1 saved delays/Dopplers'
                result['E1_snr_rows'].append(dict(snr_record('E1',raw), scenario=row['scenario'], rho=rho, frame=f))
            rebuilt = ind.apply(raw['pilot'] + raw['data'], l, nu, g)
            err = relative(rebuilt, raw['noiseless'])
            power = ind.operator_power(l, nu, g)
            receipt = dict(family=family, scenario=row['scenario'], frame=f, rho=rho,
                snr_db=row['snr_db'], stored_path=item['path'], stored_line=item['line'], relative_error=err, power=power,
                complex_gain_source=phase_source, ledger_path=None if ledger_receipt is None else ledger_receipt['path'],
                ledger_line=None if ledger_receipt is None else ledger_receipt['line'])
            result['physical_operator'].append(receipt)
            require(err <= RTOL, f'wrong operator family={family} frame={f} rel={err}')
            require(abs(power - 1) <= PTOL, f'wrong operator power family={family} frame={f} power={power}')
            errors.append(err)
            powers.append(power)
            checkpoint()
        result.setdefault('physical_summary', {})[family] = dict(n=len(entries), max_relative_error=max(errors),
            max_power_error=float(max(abs(np.array(powers) - 1))), doppler_sign='+2pi*j*nu*n/N; specified unambiguously')
        checkpoint()


def snr_record(label, raw, x=None, noiseless=None, pilot=None, data=None):
    x = raw['pilot'] + raw['data'] if x is None else x
    noiseless = raw['noiseless'] if noiseless is None else noiseless
    noise = np.sqrt(raw['sigma2']) * raw['noise']
    record = dict(label=label, tx_power=energy(x), received_signal_power=energy(noiseless),
                scaled_noise_power=energy(noise), nominal_snr_db=-10 * float(np.log10(raw['sigma2'])),
                empirical_snr_db=10 * float(np.log10(energy(noiseless) / energy(noise))))
    pilot = raw['pilot'] if pilot is None else pilot
    data = raw['data'] if data is None else data
    p = raw['params']
    hx = ind.apply(data, p['l_i'], p['k_real'], p['g_i'])
    record.update(tx_pilot_power=energy(pilot), tx_data_power=energy(data),
                  received_data_power=energy(hx),
                  empirical_data_snr_db=10*float(np.log10(energy(hx) / energy(noise))))
    return record


def invariants_and_snr(ctx, p1, p2b, ch, historical, out, result, checkpoint):
    zport = import_frozen('tcom_reference_frame_20261015', 'zport_driver')
    ep_rx = import_frozen('tcom_reference_frame_20261015', 'ep_rx')
    e3 = import_frozen('tf_e3_sbl_20261017', 'e3_driver')
    result['_config']['comparison_source_contracts'] = [saved_contract(EXP / directory / 'config_shard000.json', module)
        for directory, module in (('tcom_reference_frame_20261015/out/zport',zport),
                                  ('tcom_reference_frame_20261015/out/p2b_test',p2b),
                                  ('tcom_reference_frame_20261015/out/p2b_test',ep_rx),
                                  ('tf_e3_sbl_20261017/out/main',e3))]
    (out / 'ep_code').mkdir(exist_ok=True)
    ep = ep_rx.EP(ctx.system, ep_rx.build_ep_code(out / 'ep_code'))
    rows = list(result['E1_snr_rows'])
    cgrid_path = EXP / 'tf_cstate_e2_20261017/out/calibrate/GRID.json'
    cgrid = json.loads(cgrid_path.read_text())['rho']
    result['_config']['C_grid'] = dict(path=str(cgrid_path), md5=md5(cgrid_path))
    seed_fn = p1.make_seed_fn()
    grid = p1.gen_fixed.effective_grid(ctx.system, p1.SCENARIOS['U'])
    require(grid['delta_f'] == ctx.system.fs / 1024 and grid['delay_res'] == ctx.system.Ts, 'D2 grid violated')
    result['invariants'] = dict(D2_grid=grid, deterministic_frames=0, rho_shared_frames=0, snr_shared_frames=0,
                                UG_shared_frames=0, ep_n=int(ep.code['n']), ep_k=int(ep.k))
    inv = result['invariants']
    for f in range(50):
        for sc in ('U', 'G'):
            raw, diag = p1.generate(ctx, sc, .3, 6., f, seed_fn)
            again, _ = p1.generate(ctx, sc, .3, 6., f, seed_fn)
            oldflag = historical.Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='uwa' if sc == 'U' else 'geometric', fix_energy=True)
            archived, _ = historical.generate_base(ctx, .3, 6., f, seed_fn, oldflag)
            other, _ = p1.generate(ctx, sc, .5, 6., f, seed_fn)
            for key in ('y', 'noiseless', 'H', 'data', 'pilot', 'noise', 'info', 'coded'):
                require(np.array_equal(raw[key], again[key]), f'determinism failed {sc} frame={f} key={key}')
                require(np.array_equal(raw[key], archived[key]), f'historical P1 generator mismatch {sc} frame={f} key={key}')
            inv['deterministic_frames'] += 1
            for key in ('H', 'noise', 'info', 'coded'):
                require(np.array_equal(raw[key], other[key]), f'rho frame sharing failed {sc} frame={f} key={key}')
            inv['rho_shared_frames'] += 1
            newer, _ = ctx.reuse_at_snr(raw, diag, 8.)
            for key in ('noiseless', 'H', 'noise', 'info', 'coded', 'data', 'pilot'):
                require(np.array_equal(raw[key], newer[key]), f'SNR frame sharing failed {sc} frame={f} key={key}')
            require(relative(newer['y'], raw['noiseless'] + np.sqrt(newer['sigma2']) * raw['noise']) <= RTOL, 'wrong SNR reuse')
            inv['snr_shared_frames'] += 1
            if sc == 'U':
                uraw = raw
            else:
                for key in ('noise', 'coded', 'info'):
                    require(np.array_equal(raw[key], uraw[key]), f'U/G claimed sharing failed {f} {key}')
                for key in ('l_i', 'g_i'):
                    require(np.array_equal(raw['params'][key], uraw['params'][key]), f'U/G truth sharing failed {f} {key}')
                inv['UG_shared_frames'] += 1
            for rho, r in ((.3, raw), (.5, other)):
                require(abs(energy(r['pilot']) - rho) <= 1e-12 and abs(energy(r['data']) - (1-rho)) <= 1e-12, 'wrong pilot/data split')
                obs = ctx.hd.observe(r, rho, 6.)
                scale = np.sqrt(2 * (1-rho))
                rx_snr = energy(r['noiseless'] / scale) / (r['sigma2'] / scale**2 * energy(r['noise']))
                db = abs(10 * np.log10(rx_snr / (energy(r['noiseless']) / (r['sigma2'] * energy(r['noise'])))))
                require(db < .1 and abs(obs['sigma2'] / (r['sigma2'] / scale**2) - 1) <= 1e-12, 'receiver/physical SNR mismatch')
                rows.append(dict(snr_record('P1+CRB+genie', r), scenario=sc, rho=rho, frame=f,
                                 internal_scale=scale, internal_data_power=energy(r['data'] / scale),
                                 internal_sigma2=obs['sigma2'], physical_internal_snr_difference_db=float(db)))
            for rho, r in ((.3, raw), (.5, other)):
                x, yn = zport.impulse_frame(ctx, r, rho)
                require(abs(energy(x-r['data'])-rho) <= 1e-12, f'P2a pilot power={energy(x-r["data"])} expected={rho}')
                require(relative(ind.apply(x, r['params']['l_i'], r['params']['k_real'], r['params']['g_i']), yn) <= RTOL, 'P2a wrong operator')
                rows.append(dict(snr_record('P2a', r, x, yn, pilot=x-r['data']), scenario=sc, rho=rho, frame=f))
        # Actual later comparisons use the same P1 pipeline but distinct accepted frame IDs.
        for offset, label, rhos in ((3000, 'E2-R', (.3, .5)), (4000, 'E3/E3b/E3c/GSO', (.3, .5)),
                                   (7000, 'prospective-S/K', (.3, .5))):
            for sc in ('U', 'G'):
                for rho in rhos:
                    r, d = p1.generate(ctx, sc, rho, 6., f + offset, seed_fn)
                    obs = ctx.hd.observe(r, rho, 6.)
                    scale = np.sqrt(2 * (1-rho))
                    require(abs(obs['sigma2'] * scale**2 / r['sigma2'] - 1) <= 1e-12, f'{label} sigma mismatch')
                    if offset == 4000:
                        _, eo, data_true, _ = e3.observe_key(ctx, r, d, sc, int(rho*1000), 600, f+offset)
                        require(np.array_equal(eo['y'], obs['y']) and eo['sigma2'] == obs['sigma2']
                                and np.array_equal(data_true, r['data']/scale), 'E3 receiver coordinate mismatch')
                    actual_label = label
                    if offset == 4000 and rho == .5:
                        actual_label = 'E3'
                    if offset == 7000 and rho == .5:
                        actual_label = 'prospective-K'
                    rows.append(dict(snr_record(actual_label, r), scenario=sc, rho=rho, frame=f + offset,
                                     internal_scale=scale, internal_data_power=energy(r['data'] / scale)))
        fg = ch.frame_geometry(ctx, ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f)
        fg_repeat = ch.frame_geometry(ctx, ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f)
        require(np.array_equal(fg['h'],fg_repeat['h']), f'C channel determinism frame={f} rel={relative(fg["h"],fg_repeat["h"])}')
        cprevious = None
        for rho in (.3, .5):
            msg = ch.cluster_message(ctx, ch.make_seed_fn(), rho, f)
            rawc, _ = ch.cluster_base(ctx, fg, msg)
            repeatc, _ = ch.cluster_base(ctx, fg, ch.cluster_message(ctx, ch.make_seed_fn(), rho, f))
            snrc = float(cgrid[str(rho)]['grid_db'][0])
            rawc = ch.at_snr(rawc, snrc)
            require(abs(energy(rawc['pilot'])-rho) <= 1e-12 and abs(energy(rawc['data'])-(1-rho)) <= 1e-12,
                    f'C split frame={f} pilot={energy(rawc["pilot"])} data={energy(rawc["data"])} expected={rho}/{1-rho}')
            cobs = ctx.hd.observe(rawc, rho, snrc)
            require(abs(cobs['sigma2']*(2*(1-rho))/rawc['sigma2']-1) <= 1e-12, f'C sigma2 frame={f} receiver={cobs["sigma2"]} physical={rawc["sigma2"]}')
            for key in ('noiseless','pilot','data','noise','coded','info'):
                require(np.array_equal(rawc[key], repeatc[key]), f'C determinism frame={f} key={key}')
            cnew = ch.at_snr(rawc, snrc+2)
            for key in ('noiseless','pilot','data','noise','coded','info'):
                require(np.array_equal(rawc[key], cnew[key]), f'C SNR sharing frame={f} key={key}')
            if cprevious is not None:
                for key in ('noise','coded','info'):
                    require(np.array_equal(rawc[key], cprevious[key]), f'C rho sharing frame={f} key={key}')
            cprevious = rawc
            rows.append(dict(snr_record('E2-C', rawc), scenario='J4', rho=rho, frame=f))
        sf = p1.make_seed_fn(p2b.ENTROPY_TEST, p2b.DOMAIN_TEST)
        sprevious = None
        for rho in (.3, .5):
            sraw, sd = p1.generate(ctx, p2b.FLAGS_S, rho, 6., f, sf)
            require(abs(energy(sraw['pilot'])-rho) <= 1e-12 and abs(energy(sraw['data'])-(1-rho)) <= 1e-12,
                    f'S split frame={f} pilot={energy(sraw["pilot"])} data={energy(sraw["data"])} expected={rho}/{1-rho}')
            sobs = ctx.hd.observe(sraw, rho, 6.)
            require(abs(sobs['sigma2']*(2*(1-rho))/sraw['sigma2']-1) <= 1e-12, f'S sigma2 frame={f} receiver={sobs["sigma2"]} physical={sraw["sigma2"]}')
            srepeat, _ = p1.generate(ctx, p2b.FLAGS_S, rho, 6., f, sf)
            snew, _ = ctx.reuse_at_snr(sraw, sd, 8.)
            for key in ('H','noiseless','pilot','data','noise','coded','info'):
                require(np.array_equal(sraw[key], srepeat[key]), f'S determinism frame={f} key={key}')
                require(np.array_equal(sraw[key], snew[key]), f'S SNR sharing frame={f} key={key}')
            if sprevious is not None:
                for key in ('H','noise','coded','info'):
                    require(np.array_equal(sraw[key], sprevious[key]), f'S rho sharing frame={f} key={key}')
            sprevious = sraw
            rows.append(dict(snr_record('P2b-SP', sraw), scenario='S', rho=rho, frame=f))
        info = p1.gen_fixed.make_rng_factory(sf, f)(0, f, 2, split=2).integers(0, 2, size=ep.k).astype(np.uint8)
        x, sym, coded = ep_rx.make_frame(ep, info, p2b.RHO_EP)
        require(abs(energy(x) - 1) <= 1e-12 and abs(abs(x[ep_rx.PILOT])**2 / 1024 - .2) <= 1e-12, 'P2b wrong power split')
        pp = sraw['params']
        ep_h = ep_rx.channel_matrix(ep, pp['l_i'], pp['k_real'], pp['g_i'])
        require(np.array_equal(ep_h,sraw['H']), f'EP/SP claimed channel sharing frame={f} rel={relative(ep_h,sraw["H"])}')
        yp = ep_h @ x
        actual_y = ep_rx.observe(ep, ep_h, x, sraw['noise'], sraw['sigma2'])
        require(relative(actual_y, yp + np.sqrt(sraw['sigma2'])*sraw['noise']) <= RTOL, 'EP noise convention mismatch')
        ep_pilot = np.zeros(1024, complex)
        ep_pilot[ep_rx.PILOT] = x[ep_rx.PILOT]
        rows.append(dict(snr_record('P2b-EP/EPG', sraw, x, yp, pilot=ep_pilot, data=x-ep_pilot), scenario='S', rho=.2, frame=f,
                         ep_data_symbol_energy=energy(sym), code_n=len(coded), code_k=ep.k))
        result['snr_rows'] = rows
        checkpoint()
    inv.update(C_channel_determinism_frames=50, C_rho_sharing_frames=50, C_snr_sharing_frames=100,
               S_determinism_frames=100, S_rho_sharing_frames=50, S_snr_sharing_frames=100, EP_SP_channel_noise_sharing_frames=50)
    result['snr_summary'] = {}
    for label, sc, rho in sorted(set((r['label'], r['scenario'], r['rho']) for r in rows)):
        rr = [r for r in rows if (r['label'], r['scenario'], r['rho']) == (label, sc, rho)]
        result['snr_summary'][f'{label}/{sc}/rho{rho}'] = dict(n=len(rr), nominal_snr_db=rr[0]['nominal_snr_db'],
            mean_tx_power=float(np.mean([r['tx_power'] for r in rr])),
            empirical_snr_from_pooled_energies_db=float(10*np.log10(sum(r['received_signal_power'] for r in rr) / sum(r['scaled_noise_power'] for r in rr))),
            empirical_data_snr_from_pooled_energies_db=float(10*np.log10(sum(r['received_data_power'] for r in rr) / sum(r['scaled_noise_power'] for r in rr))),
            mean_per_frame_snr_db=float(np.mean([r['empirical_snr_db'] for r in rr])))
    checkpoint()


def fingerprint(p1):
    paths = p1.project_module_files()
    return {name: dict(path=path, md5=md5(path)) for name, path in paths.items()}


def saved_contract(path, module):
    cfg = json.loads(path.read_text())['_config']
    actual = md5(module.__file__)
    expected = cfg.get('source_md5',{}).get(module.__name__) or cfg.get('own_md5',{}).get(Path(module.__file__).name)
    if expected is None or actual != expected:
        raise RuntimeError(f'frozen comparison source contract {module.__name__}: actual={actual} expected={expected} config={path}')
    return dict(config_path=str(path), config_md5=md5(path), module_path=module.__file__, md5=actual)


def source_contract(p1, historical_path):
    """Verify loaded generator dependencies against their recorded P1 runtime."""
    path = EXP / 'tcom_reference_frame_20261015/out/p1/config_shard000.json'
    cfg = json.loads(path.read_text())['_config']
    current = fingerprint(p1)
    checked = {}
    names = ('gen_fixed', 'p1_driver', 'receiver',
             'afdm_sp_joint_unrolled.afdm_env', 'afdm_sp_joint_unrolled.supplement_g1',
             'afdm_sp_joint_unrolled.supplement_pilots', 'afdm_sp_joint_unrolled.e1_ldpc',
             'afdm_sp_joint_unrolled.budgeted_support_diagnostics',
             'afdm_sp_joint_unrolled.budgeted_support_eval')
    for name in names:
        expected = cfg['source_md5'].get(name)
        if expected is None or name not in current:
            raise RuntimeError(f'missing saved/loaded source contract {name}')
        actual = current[name]['md5']
        evidence_path = current[name]['path']
        if name == 'gen_fixed':
            actual, evidence_path = md5(historical_path), str(historical_path)
        if actual != expected:
            raise RuntimeError(f'source mismatch {name}: saved={expected} actual={actual} path={evidence_path}')
        checked[name] = dict(expected_md5=expected, evidence_path=evidence_path, checked_md5=actual,
                             current=current[name], historical_path=cfg['source_paths'].get(name))
    return dict(config_path=str(path.resolve()), config_md5=md5(path), checked=checked)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--freeze-revision', required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out/'runtime.json').exists():
        raise RuntimeError('refusing to overwrite an existing audit run')
    start = time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (21600, 21600))
    result = dict(status='RUNNING', _argv=list(sys.argv), _config=dict(out=str(out), alpha=.01,
        multiplicity='Holm across every law test; frame-independent tests by path coordinate', operator_rtol=RTOL,
        power_atol=PTOL, snr_systematic_offset_blocker_db=.1, P1_operator_frames_per_scenario=200,
        C_operator_frames=50, law_frames_per_scenario=2000, reference_frames_per_scenario=20000,
        sharing_frames=50, nominal_snr_db=6., cost_cap_core_hours=6,
        environment={k: os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','TMPDIR')},
        independent_md5=md5(HERE/'independent.py'), audit_md5=md5(__file__)))
    def checkpoint():
        result['cpu_seconds'] = time.process_time() - start
        if result['cpu_seconds'] >= 6 * 3600:
            raise RuntimeError('six core-hour audit cost cap')
        put(out / 'runtime.json', result)
    try:
        p1 = import_frozen('tcom_reference_frame_20261015', 'p1_driver')
        p2b = import_frozen('tcom_reference_frame_20261015', 'p2b_driver')
        ch = import_frozen('tf_cstate_e2_20261017', 'e2_channels')
        result['_config']['seed_coordinates'] = dict(P1=dict(entropy=p1.ENTROPY_HEX, domain=p1.DOMAIN),
            S=dict(entropy=p2b.ENTROPY_TEST, domain=p2b.DOMAIN_TEST),
            C=dict(entropy=ch.E2CJ_ENTROPY, domain=ch.E2CJ_DOMAIN), components=dict(channel=1,message=2,noise=3),
            independent_reference_seeds={sc:2026101900+ord(sc) for sc in ('U','G','S')}, C_reference_seed=2026101942)
        result['_config']['scenario_flags'] = dict({sc:vars(flag) for sc,flag in p1.SCENARIOS.items()}, S=vars(p2b.FLAGS_S))
        ctx = p1.load_context()
        historical_path = EXP / 'tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py'
        if md5(historical_path) != 'cb9be5ea91c0a9b1863758ed598de1c6':
            raise RuntimeError('historical P1 generator snapshot fingerprint differs')
        spec = importlib.util.spec_from_file_location('historical_p1_gen', historical_path)
        historical = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = historical
        spec.loader.exec_module(historical)
        result['_config']['historical_P1_generator'] = dict(path=str(historical_path), md5=md5(historical_path), equivalence_frames_per_scenario=50)
        result['_config']['P1_saved_source_contract'] = source_contract(p1, historical_path)
        result['_config']['freeze_revision'] = args.freeze_revision
        result['_config']['versions'] = dict(python=sys.version, numpy=np.__version__, scipy=importlib.import_module('scipy').__version__)
        ccpath = EXP / 'tf_cstate_e2_20261017/out/main_C/config_shard000.json'
        cc = json.loads(ccpath.read_text())['_config']
        if cc['source_md5']['e2_channels'] != md5(ch.__file__):
            raise RuntimeError('family C historical channel source mismatch')
        result['_config']['C_source_contract'] = dict(config_path=str(ccpath), config_md5=md5(ccpath),
                                                      channel_path=ch.__file__, channel_md5=md5(ch.__file__))
        result['_config']['source_fingerprints'] = fingerprint(p1)
        result['_config']['system'] = {k: float(getattr(ctx.system,k)) for k in ('N_total','fs','Ts','c1','c2','l_max_cap','P_paths','tau_mean','tau_spread','att_dB')}
        checkpoint()
        physical(ctx, p1, ch, result, checkpoint)
        invariants_and_snr(ctx, p1, p2b, ch, historical, out, result, checkpoint)
        path_laws(ctx, p1, p2b, ch, out, result, checkpoint)
        result['status'] = 'COMPLETE'
        result['_config']['source_fingerprints'] = fingerprint(p1)
        checkpoint()
    except Exception as error:
        result['status'] = 'BLOCKER' if isinstance(error, Blocker) else 'INCOMPLETE'
        result['blocker'] = str(error)
        result['traceback'] = traceback.format_exc()
        result['cpu_seconds'] = time.process_time() - start
        put(out / 'runtime.json', result)
        print(result['status'] + ':', error, flush=True)
        return 2
    print('COMPLETE', json.dumps(result['physical_summary']), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
