#!/usr/bin/env python
"""slot_mismatch driver (task 10-19-slot-mismatch; PROTOCOL.md section 2, family M only; family T is not implemented).

Per key and cap s:  F0_s = native_twofft_variant.receive(max_paths=s)  (production F0 otherwise: rounds=2 iterations=20 soft/joint).
Triggered (F0_s final syndrome != 0): A1_s (full Gamma) and A2_s (diag Gamma), guard off, max_edits 2, local passes 2, both from the SAME
captured F0_s state (e2_driver.process_key -> run_branch -> e1_driver.arm_record).  Per key: A3 (true-H receiver, p1_driver.compute_arms).
Generator: P1 frames (gen_fixed through p1ctx.base), P_paths unchanged.

Modes:  gate        G1 (variant max_paths=8 == frozen receive, bit for bit), G2 (A1_8/A2_8/F0_8 reproduce the saved E-2 family R decoded sha),
                    G4 (slot_count == min(s, distinct nominated delays) for s in 6/8/10/12).  G3 (generator P_paths) belongs to family T: not run.
            gate-merge  merge gate shards into gates.json
            pilot       the exploratory slice (defaults below); G4 is asserted on every unit.  Frames must lie in PILOT_FRAMES.
            gate-k4     kernel variant gate: with max_edits=2 the variant reproduces the saved pilot-2 A1/A2 decoded sha (48 triggered keys, caps 8 and 12)
            pilot3      pilot-2 keys again, arms A1e4/A2e4 (= A1/A2 with max_edits=4, kernel geometry_guard_edits_variant) on every F0_s-triggered key;
                        F0_s decoded sha must equal the saved pilot-2 one on every key
            gate4       call-path gate for pilot4: the frozen 10-18 process_key_k reproduces the saved K-diag and K-diag-fullfix decoded sha (>= 20 triggered K units)
            pilot4      detector-clue mini simulation on the pilot-2 cap-8 triggered keys whose A2 final geometry has a co-delay pair: A2-prod (= 10-18 K-diag),
                        A2-fix (= 10-18 K-diag-fullfix, via sp_driver.process_key_k), A2-merge (co-delay atoms merged, production joint continuation)
Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
E2_DIR = EXPERIMENTS / 'tf_cstate_e2_20261017'
sys.path.insert(0, str(E2_DIR))
import e2_lib  # noqa: E402  (puts the frozen math modules and the E-1 directory on sys.path)

e2_lib.prepare_paths()
import e1_driver as e1d  # noqa: E402
import e2_driver as e2d  # noqa: E402
import gs_driver as gd  # noqa: E402
from gs_driver import p1ctx  # noqa: E402

E2_ROWS_R = E2_DIR / 'out' / 'main_R'
ALL_SNR = (450, 500, 550, 600, 650, 700, 750, 800)
G4_CAPS = (6, 8, 10, 12)
G1_UNITS = 40                      # P1 frames 0..39, cells cycled over scenario x rho x SNR (32 cells)
G2_FILES, G2_PER_BUCKET = 8, 3
GK_PER_BUCKET = 8                  # kernel-variant gate: pilot-2 triggered keys, first-seen, <= 8 per (cap, SNR) bucket (6 buckets)     # saved E-2 R triggered keys: first-seen, <= 3 per (scenario, rho, SNR), first 8 shard files
PILOT_FRAMES = (7800, 8000)        # P1-stream free (frame_audit.py); 8000..8199 is not (e3_sbl smoke frames 8000..8007, 8100..8103)
VARIANT_SIG = ('checkpoint_sink=None,record_states=False):', 'checkpoint_sink=None,record_states=False,max_paths=8):')
VARIANT_CALL = ('mode=ce_mode,max_paths=8,rounds=2)', 'mode=ce_mode,max_paths=max_paths,rounds=2)')
KERNEL_EDIT = ('max_edits > 2', 'max_edits > 4')           # the only change of geometry_guard_edits_variant.py vs the E-2 guard kernel
E4_SPECS = {'A1e4': dict(gamma_mode='full', max_edits=4, local_passes=2, guard='off'),
            'A2e4': dict(gamma_mode='diag', max_edits=4, local_passes=2, guard='off')}
e2d.ARM_SPECS.update(E4_SPECS)  # in-memory registration so e2_driver.run_branch can run the 4-edit arms; nothing on disk changes
PILOT2_ROWS = HERE / 'out' / 'pilot2'
SP_DIR = EXPERIMENTS / 'tf_split_prosp_20261018'              # frozen 10-18 split-principle code (imported read-only, lazily)
K_ROWS = SP_DIR / 'out' / 'main'                              # its saved K-family rows (rows_K_shard*.jsonl.gz)
G4_PER_BUCKET = 4                                             # gate4: saved triggered K units, rho .3, SNR 4.5/5.0/5.5, <= 4 per (scenario, SNR) = 24 units


# ----------------------------------------------------------------------------- provenance
def variant_diff_problems(frozen_path, variant_path, edits=(VARIANT_SIG, VARIANT_CALL)):
    """Empty list iff the variant is the frozen file with exactly the listed (old, new) edits, each applied once."""
    frozen, variant = Path(frozen_path).read_text(), Path(variant_path).read_text()
    problems = []
    for old, new in edits:
        if frozen.count(old) != 1 or variant.count(new) != 1 or variant.count(old) != 0:
            problems.append(f'edit not unique: {old!r} -> {new!r}')
        variant = variant.replace(new, old)
    if not problems and variant != frozen:
        problems.append('variant differs from the frozen file beyond the listed edits')
    return problems


def load_all():
    """Frozen context, E-2 geometry kernel (guard module, used with guard off), and the max_paths variant."""
    ctx = p1ctx.load()
    _, k2 = e2d.load_kernels()
    sys.path.insert(0, str(HERE))
    import native_twofft_variant as vr
    problems = variant_diff_problems(ctx.native.__file__, HERE / 'native_twofft_variant.py')
    if problems:
        raise RuntimeError(f'variant diff: {problems}')
    return ctx, k2, vr


def load_k4(k2):
    """E-2 guard kernel with the max_edits <= 4 validation (diff vs the loaded E-2 kernel = that one line)."""
    import geometry_guard_edits_variant as k4
    problems = variant_diff_problems(k2.__file__, HERE / 'geometry_guard_edits_variant.py', (KERNEL_EDIT,))
    if problems:
        raise RuntimeError(f'kernel variant diff: {problems}')
    return k4


def write_config(out, shard, argv, args, ctx, extra=None):
    path = out / f'config_shard{shard:03d}.json'
    if path.exists():
        return
    own = {n: e2_lib.md5_file(HERE / n) for n in ('sm_driver.py', 'native_twofft_variant.py', 'geometry_guard_edits_variant.py', 'PROTOCOL.md') if (HERE / n).exists()}
    cfg = dict(vars(args), out=str(args.out), arm_specs={a: e2d.ARM_SPECS[a] for a in ('A1', 'A2', *E4_SPECS)}, entropy=p1ctx.p1_driver.ENTROPY_HEX,
               domain=p1ctx.p1_driver.DOMAIN, pilot_frames_allowed=PILOT_FRAMES,
               schedule='F0_s = native_twofft_variant.receive(rounds=2 iterations=20 ce_mode=soft gain_mode=joint max_paths=s); branch as E-2 '
                        'run_branch (guard off); A3 = p1_driver.compute_arms true-H; generator P1 gen_fixed, P_paths unchanged',
               variant_native_file=str(ctx.native.__file__), variant_diff_vs_loaded_native=variant_diff_problems(ctx.native.__file__, HERE / 'native_twofft_variant.py'),
               frozen_md5_check=e2d.check_frozen_md5(ctx), own_md5=own, source_md5=ctx.source_md5, environment=ctx.environment, **(extra or {}))
    path.write_text(json.dumps(dict(_argv=list(argv), _config=cfg), indent=1, default=str) + '\n')


# ----------------------------------------------------------------------------- units
def f0_state(ctx, vr, obs, s):
    t0 = time.perf_counter()
    dec, arrays, _ = vr.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20, ce_mode='soft', gain_mode='joint', max_paths=s)
    return dec, arrays, int(ctx.hd.syndrome_weight(ctx, dec['decoded'])), time.perf_counter() - t0


def n_nominated(ctx, vr, obs):
    """Distinct delays nominated by the pilot front (the input of the first time_refine call)."""
    return int(len(np.unique(vr.pilot_front(obs, ctx.system, ctx.code)['delays'])))


def slot_record(arrays, s, n_distinct):
    r0, r1 = len(np.asarray(arrays['r0_delays'])), len(np.asarray(arrays['r1_delays']))
    return dict(cap=int(s), slot_count_r0=r0, slot_count=r1, n_distinct_nominated_delays=int(n_distinct), ok=bool(r0 == r1 == min(s, n_distinct)))


def make_unit(ctx, scenario, rho, snr_centi, frame):
    raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
    return gd.observe(ctx, raw_base, diag_base, rho, snr_centi)[1:]   # (obs, truth)


def jsonable(ctx, value):
    return json.loads(json.dumps(value, default=ctx.hd.to_jsonable))


def key_row(ctx, k2, vr, obs, truth, meta, caps):
    """One row: per cap s the F0_s record (+ slot record) and, iff triggered, A1_s/A2_s from the same F0_s state; plus A3."""
    n_distinct = n_nominated(ctx, vr, obs)
    row = dict(meta, P_true=int(len(np.asarray(truth['l_i']))), n_distinct_nominated_delays=n_distinct,
               truth=dict(delays=[int(x) for x in np.asarray(truth['l_i'])], dopplers=[float(x) for x in np.asarray(truth['k_real'])],
                          gains=[[float(g.real), float(g.imag)] for g in np.asarray(truth['g_i'], complex)]), s={})
    for s in caps:
        pack = f0_state(ctx, vr, obs, s)
        part = e2d.process_key(ctx, k2, obs, truth, {}, pack, arms=('A1', 'A2'))
        slots = slot_record(pack[1], s, n_distinct)
        assert slots['ok'], f'G4 violated at {meta}: {slots}'
        f0 = dict(part['f0'], r1_delays=[int(x) for x in np.asarray(pack[1]['r1_delays'])],
                  r1_dopplers=[float(x) for x in np.asarray(pack[1]['r1_dopplers'])], **{k: slots[k] for k in ('slot_count', 'slot_count_r0')})
        row['s'][str(s)] = dict(f0=f0, triggered=part['triggered'], arms=part['arms'])
    row['A3'] = jsonable(ctx, p1ctx.p1_driver.compute_arms(ctx, obs, truth, ['A3'])['A3'])
    return row


def cells(ctx, frame, scenarios, rhos, snr_cells):
    for scenario in scenarios:
        for rho in rhos:
            g0 = time.perf_counter()
            raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
            gen_seconds = time.perf_counter() - g0
            for k, snr in enumerate(snr_cells):
                raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
                meta = dict(family='M', scenario=scenario, rho=float(rho), rho_permille=int(round(rho * 1000)), snr_centi_db=int(snr),
                            snr_db=snr / 100, frame=int(frame), sigma2=float(raw['sigma2']), gen_seconds=gen_seconds if k == 0 else 0.)
                yield meta, obs, truth


# ----------------------------------------------------------------------------- pilot
def pilot_mode(args, argv):
    lo, hi = PILOT_FRAMES
    f_lo, f_hi = args.frame_offset, args.frame_offset + args.frames
    if not (lo <= f_lo and f_hi <= hi):
        raise ValueError(f'pilot frames must lie in [{lo}, {hi})')
    ctx, k2, vr = load_all()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    caps = [int(x) for x in gd.parse_list(args.s_list, str)]
    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
    rhos = gd.parse_list(args.rho_list, float)
    scenarios = gd.parse_list(args.scenarios, str)
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    started, n_rows = time.perf_counter(), 0
    with jsonl.open('a') as handle:
        for frame in list(range(f_lo, f_hi))[args.shard::args.nshard]:
            for meta, obs, truth in cells(ctx, frame, scenarios, rhos, snr_cells):
                if e2d.key_of(meta) in done:
                    continue
                t0 = time.perf_counter()
                row = key_row(ctx, k2, vr, obs, truth, meta, caps)
                row['key_seconds'] = time.perf_counter() - t0
                e2d.write_row(handle, row)
                n_rows += 1
                print(f"[{time.perf_counter() - started:8.1f}s] {e2d.key_of(meta)} {row['key_seconds']:.1f}s nom={row['n_distinct_nominated_delays']} "
                      + ' '.join(f"s{s}:trig={int(r['triggered'])},f0={r['f0']['info_errors']}" for s, r in row['s'].items()) + f" A3={row['A3'].get('info_errors')}", flush=True)
    print(f'pilot shard {args.shard}/{args.nshard} done: {n_rows} keys in {time.perf_counter() - started:.1f}s', flush=True)


# ----------------------------------------------------------------------------- pilot-2 rows (saved decisions) and pilot 3
def load_pilot2(rows_dir):
    rows = {}
    for path in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl.gz'))):
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                rows[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r
    return rows


def pilot3_mode(args, argv):
    lo, hi = PILOT_FRAMES
    f_lo, f_hi = args.frame_offset, args.frame_offset + args.frames
    if not (lo <= f_lo and f_hi <= hi):
        raise ValueError(f'pilot frames must lie in [{lo}, {hi})')
    ctx, k2, vr = load_all()
    k4 = load_k4(k2)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    saved = load_pilot2(args.pilot2_rows)
    caps = [int(x) for x in gd.parse_list(args.s_list, str)]
    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    started, n_rows = time.perf_counter(), 0
    with jsonl.open('a') as handle:
        for frame in list(range(f_lo, f_hi))[args.shard::args.nshard]:
            for meta, obs, truth in cells(ctx, frame, gd.parse_list(args.scenarios, str), gd.parse_list(args.rho_list, float), snr_cells):
                k = e2d.key_of(meta)
                if k in done:
                    continue
                t0 = time.perf_counter()
                row = dict(meta, s={})
                for s in caps:
                    sv = saved[k]['s'][str(s)]
                    pack = f0_state(ctx, vr, obs, s)
                    part = e2d.process_key(ctx, k4, obs, truth, {}, pack, arms=tuple(E4_SPECS))
                    assert part['f0']['decoded_sha256'] == sv['f0']['decoded_sha256'] and part['triggered'] == sv['triggered'], f'F0_{s} differs from pilot 2 at {k}'
                    row['s'][str(s)] = dict(f0_sha256=part['f0']['decoded_sha256'], triggered=part['triggered'], arms=part['arms'])
                row['key_seconds'] = time.perf_counter() - t0
                e2d.write_row(handle, row)
                n_rows += 1
                print(f"[{time.perf_counter() - started:8.1f}s] {k} {row['key_seconds']:.1f}s " + ' '.join(
                    f"s{s}:trig={int(r['triggered'])}" + ''.join(f",{a}={x.get('info_errors', 'ERR')}" for a, x in r['arms'].items()) for s, r in row['s'].items()), flush=True)
    print(f'pilot3 shard {args.shard}/{args.nshard} done: {n_rows} keys in {time.perf_counter() - started:.1f}s', flush=True)


def gate_k4_mode(args, argv):
    """Kernel-variant gate: with max_edits=2 (A1/A2 specs) k4 must reproduce the saved pilot-2 decoded sha of F0, A1 and A2."""
    ctx, k2, vr = load_all()
    k4 = load_k4(k2)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    saved, buckets, units = load_pilot2(args.pilot2_rows), {}, []
    for k, r in sorted(saved.items(), key=lambda kv: (kv[0][3], kv[0][0], kv[0][2])):
        for s in ('8', '12'):
            b = (s, k[2])
            if r['s'][s]['triggered'] and buckets.get(b, 0) < GK_PER_BUCKET:
                buckets[b] = buckets.get(b, 0) + 1
                units.append((k, s))
    recs, started = [], time.perf_counter()
    for k, s in units[args.shard::args.nshard]:
        obs, truth = make_unit(ctx, k[0], k[1] / 1000, k[2], k[3])
        part = e2d.process_key(ctx, k4, obs, truth, {}, f0_state(ctx, vr, obs, int(s)), arms=('A1', 'A2'))
        sv = saved[k]['s'][s]
        got = dict(F0=part['f0']['decoded_sha256'], **{a: part['arms'][a].get('decoded_sha256') for a in ('A1', 'A2')})
        want = dict(F0=sv['f0']['decoded_sha256'], **{a: sv['arms'][a]['decoded_sha256'] for a in ('A1', 'A2')})
        recs.append(dict(key=list(k), cap=int(s), triggered=part['triggered'], **{f'{a}_match': got[a] == want[a] for a in got}))
        print(f'[{time.perf_counter() - started:8.1f}s] {recs[-1]}', flush=True)
    gates = dict(GK=dict(units=len(recs), per_cap={s: sum(r['cap'] == int(s) for r in recs) for s in ('8', '12')},
                         triggered_now=sum(r['triggered'] for r in recs), **{f'{a}_match': sum(r[f'{a}_match'] for r in recs) for a in ('F0', 'A1', 'A2')}),
                 e2_kernel_md5=e2_lib.md5_file(k2.__file__), kernel_variant_md5=e2_lib.md5_file(HERE / 'geometry_guard_edits_variant.py'))
    g = gates['GK']
    g['pass_'] = bool(g['units'] >= 40 and g['triggered_now'] == g['units'] and all(g[f'{a}_match'] == g['units'] for a in ('F0', 'A1', 'A2')))
    (out / f'gates_k4_shard{args.shard:03d}.json').write_text(json.dumps(dict(gates, records=recs), indent=1) + '\n')
    print(json.dumps(gates, indent=1))


# ----------------------------------------------------------------------------- pilot 4: detector clue (A2 co-delay pairs)
def load_sp():
    """Frozen 10-18 driver (sp_driver.process_key_k = F0, E-1 A1/A2 branches, fixed-gain arms incl. K-diag-fullfix); read-only import."""
    sys.path.insert(0, str(SP_DIR))
    import sp_driver
    return sp_driver


def has_pair(delays):
    return len(set(delays)) < len(delays)


def merge_atoms(paths, gains):
    """One atom per delay.  Delays holding k > 1 atoms: Doppler = |gain|^2-weighted mean, gain = sum of the k gains (initialisation only); singletons unchanged."""
    delays, nus, g = [int(p.delay) for p in paths], [float(p.doppler) for p in paths], np.asarray(gains, complex)
    out_d, out_nu, out_g, groups = [], [], [], []
    for d in dict.fromkeys(delays):
        idx = [i for i, x in enumerate(delays) if x == d]
        if len(idx) == 1:
            out_d.append(d), out_nu.append(nus[idx[0]]), out_g.append(g[idx[0]])
            continue
        w = np.abs(g[idx]) ** 2
        if not w.sum() > 0:
            raise ValueError('co-delay atoms with zero total gain energy')
        out_d.append(d), out_nu.append(float(np.sum(w * np.array([nus[i] for i in idx])) / w.sum())), out_g.append(g[idx].sum())
        groups.append(dict(delay=d, dopplers=[nus[i] for i in idx], gain_energy=[float(x) for x in w], merged_doppler=out_nu[-1]))
    return out_d, out_nu, np.array(out_g), groups


def continue_joint(ctx, obs, delays, dopplers, gains, check):
    """The production continuation of e1_driver.run_branch (Channel -> scalar_joint gain_mode joint, prior = r1 check -> LDPC) on a given path list."""
    from physical import Channel
    s = ctx.system
    channel = Channel(len(obs['y']), s.c1, s.c2, delays, dopplers, gains)
    det = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - s.rho, prior=check, iterations=20, damping=.3, gain_mode='joint')
    return ctx.native.decoder_messages(ctx.code, np.clip(det['extrinsic'], -20, 20), maxiter=50)['decoded']


def arm_summary(ctx, truth, decoded):
    err = gd.score(ctx, decoded, truth)
    return dict(info_errors=int(err), fer=int(err > 0), syndrome=int(ctx.hd.syndrome_weight(ctx, decoded)), decoded_sha256=gd.bits_sha(decoded))


def pilot4_unit(ctx, sp, kvar, obs, truth, meta, sv):
    """sv = saved pilot-2 cap-8 record.  Asserts: F0_8 and A2 reproduce pilot 2; the production continuation on the unmerged A2 paths reproduces A2."""
    dbg = {}
    krow = sp.process_key_k(ctx, kvar, obs, truth, meta, debug=dbg)
    prod, fix = krow['arms']['K-diag'], krow['arms']['K-diag-fullfix']
    saved_a2 = sv['arms']['A2']
    if not (krow['f0']['decoded_sha256'] == sv['f0']['decoded_sha256'] and krow['triggered'] and prod['decoded_sha256'] == saved_a2['decoded_sha256']
            and prod['final_delays'] == saved_a2['final_delays']):
        raise AssertionError(f'pilot-2 A2 not reproduced at {meta}')
    br = dbg['br_diag']
    res, check = br['result'], br['check_prior']
    delays, nus = [int(p.delay) for p in res.paths], [float(p.doppler) for p in res.paths]
    null = gd.bits_sha(continue_joint(ctx, obs, delays, nus, res.gains, check))
    if null != prod['decoded_sha256']:
        raise AssertionError(f'continue_joint does not reproduce A2 at {meta}')
    md, mnu, mg, groups = merge_atoms(res.paths, res.gains)
    merged = arm_summary(ctx, truth, continue_joint(ctx, obs, md, mnu, mg, check))
    return dict(meta, a2_final_delays=delays, a2_final_dopplers=nus, n_codelay_groups=len(groups),
                arms={'A2-prod': {k: prod[k] for k in ('info_errors', 'fer', 'syndrome', 'decoded_sha256')},
                      'A2-fix': {k: fix[k] for k in ('info_errors', 'fer', 'syndrome', 'decoded_sha256')},
                      'A2-merge': dict(merged, merged_slot_count=len(md), merged_delays=md, merged_dopplers=mnu, groups=groups)})


def load_k_rows(rows_dir, keys):
    out = {}
    for path in sorted(glob.glob(str(Path(rows_dir) / 'rows_K_shard*.jsonl.gz'))):
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                k = (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
                if k in keys:
                    out[k] = r
    return out


def gate4_mode(args, argv):
    """The frozen process_key_k (my observation path, my context) reproduces saved 10-18 K-diag and K-diag-fullfix decoded sha on triggered K units."""
    ctx, _, _ = load_all()
    sp = load_sp()
    kvar = e1d.load_variant()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx, extra=dict(sp_sources={n: e2_lib.md5_file(SP_DIR / n) for n in ('sp_driver.py', 'sp_lib.py')}))
    want = {(sc, 300, snr, f) for sc in ('U', 'G') for snr in (450, 500, 550) for f in range(7000, 7200)}
    rows, buckets, units = load_k_rows(args.k_rows, want), {}, []
    for k in sorted(rows, key=lambda k: (k[3], k[0], k[2])):
        r = rows[k]
        b = (k[0], k[2])
        if r['status'] == 'ok' and r['triggered'] and buckets.get(b, 0) < G4_PER_BUCKET:
            buckets[b] = buckets.get(b, 0) + 1
            units.append(k)
    recs, started = [], time.perf_counter()
    for k in units[args.shard::args.nshard]:
        obs, truth = make_unit(ctx, k[0], k[1] / 1000, k[2], k[3])
        row = sp.process_key_k(ctx, kvar, obs, truth, dict(scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3]))
        recs.append(dict(key=list(k), triggered=row['triggered'],
                         **{f'{a}_match': row['arms'][a]['decoded_sha256'] == rows[k]['arms'][a]['decoded_sha256'] for a in ('K-diag', 'K-diag-fullfix')}))
        print(f'[{time.perf_counter() - started:8.1f}s] {recs[-1]}', flush=True)
    g = dict(units=len(recs), triggered_now=sum(r['triggered'] for r in recs), **{f'{a}_match': sum(r[f'{a}_match'] for r in recs) for a in ('K-diag', 'K-diag-fullfix')})
    g['pass_'] = bool(g['units'] >= 20 and g['triggered_now'] == g['units'] and g['K-diag_match'] == g['K-diag-fullfix_match'] == g['units'])
    (out / f'gate4_shard{args.shard:03d}.json').write_text(json.dumps(dict(G4_call_path=g, records=recs), indent=1) + '\n')
    print(json.dumps(g, indent=1))


def pilot4_mode(args, argv):
    ctx, _, _ = load_all()
    sp = load_sp()
    kvar = e1d.load_variant()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    saved = load_pilot2(args.pilot2_rows)
    units = [k for k in sorted(saved, key=lambda k: (k[3], k[0], k[2]))
             if saved[k]['s']['8']['triggered'] and has_pair(saved[k]['s']['8']['arms']['A2']['final_delays'])]
    write_config(out, args.shard, argv, args, ctx, extra=dict(n_units_total=len(units), sp_sources={n: e2_lib.md5_file(SP_DIR / n) for n in ('sp_driver.py', 'sp_lib.py')},
                                                                loaded_project_modules_md5={k: e2_lib.md5_file(v) for k, v in p1ctx.p1_driver.project_module_files().items()}))
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    started, n_rows = time.perf_counter(), 0
    with jsonl.open('a') as handle:
        for k in units[args.shard::args.nshard]:
            if k in done:
                continue
            obs, truth = make_unit(ctx, k[0], k[1] / 1000, k[2], k[3])
            meta = dict(family='M', scenario=k[0], rho=k[1] / 1000, rho_permille=k[1], snr_centi_db=k[2], snr_db=k[2] / 100, frame=k[3])
            t0 = time.perf_counter()
            row = pilot4_unit(ctx, sp, kvar, obs, truth, meta, saved[k]['s']['8'])
            row['unit_seconds'] = time.perf_counter() - t0
            e2d.write_row(handle, jsonable(ctx, row))
            n_rows += 1
            print(f"[{time.perf_counter() - started:8.1f}s] {k} {row['unit_seconds']:.1f}s " + ' '.join(f"{a}={r['info_errors']}" for a, r in row['arms'].items()), flush=True)
    print(f'pilot4 shard {args.shard}/{args.nshard} done: {n_rows} units (of {len(units)} total) in {time.perf_counter() - started:.1f}s', flush=True)


# ----------------------------------------------------------------------------- gate
def g1_units():
    cells_ = [(sc, rho, snr) for sc in ('U', 'G') for rho in (0.3, 0.5) for snr in ALL_SNR]
    return [dict(kind='g1', scenario=cells_[f % len(cells_)][0], rho=cells_[f % len(cells_)][1], snr_centi_db=cells_[f % len(cells_)][2], frame=f)
            for f in range(G1_UNITS)]


def g2_units(rows_dir):
    """Saved E-2 R triggered keys (deterministic: first-seen per bucket) with their saved F0/A1/A2 decoded sha."""
    buckets, units = {}, []
    for path in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl.gz')))[:G2_FILES]:
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if not r['triggered'] or any(r['arms'][a].get('status') != 'ok' for a in ('A1', 'A2')):
                    continue
                b = (r['scenario'], r['rho_permille'], r['snr_centi_db'])
                if buckets.get(b, 0) >= G2_PER_BUCKET:
                    continue
                buckets[b] = buckets.get(b, 0) + 1
                units.append(dict(kind='g2', scenario=r['scenario'], rho=r['rho_permille'] / 1000, snr_centi_db=r['snr_centi_db'], frame=r['frame'],
                                  saved=dict(F0=r['f0']['decoded_sha256'], A1=r['arms']['A1']['decoded_sha256'], A2=r['arms']['A2']['decoded_sha256'])))
    return units


def gate_unit(ctx, k2, vr, u):
    obs, truth = make_unit(ctx, u['scenario'], u['rho'], u['snr_centi_db'], u['frame'])
    rec = dict(kind=u['kind'], scenario=u['scenario'], rho=u['rho'], snr_centi_db=u['snr_centi_db'], frame=u['frame'])
    if u['kind'] == 'g1':
        dec_f, arr_f, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20, ce_mode='soft', gain_mode='joint')
        n_distinct, slots, v8 = n_nominated(ctx, vr, obs), {}, None
        for s in G4_CAPS:
            dec_v, arr_v, _ = vr.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20, ce_mode='soft', gain_mode='joint', max_paths=s)
            slots[str(s)] = slot_record(arr_v, s, n_distinct)
            if s == 8:
                v8 = (dec_v, arr_v)
        diff = e2_lib.deep_equal(dict(decoded=dec_f['decoded'], arrays=arr_f), dict(decoded=v8[0]['decoded'], arrays=v8[1]))
        rec.update(g1_identical=not diff, g1_diff=diff[:3], n_arrays=len(arr_f), triggered=bool(ctx.hd.syndrome_weight(ctx, dec_f['decoded']) != 0), g4=slots)
    else:
        pack = f0_state(ctx, vr, obs, 8)
        part = e2d.process_key(ctx, k2, obs, truth, {}, pack, arms=('A1', 'A2'))
        got = dict(F0=part['f0']['decoded_sha256'], **{a: part['arms'][a].get('decoded_sha256') for a in ('A1', 'A2')})
        rec.update(triggered=part['triggered'], g2={k: got[k] == u['saved'][k] for k in got})
    return rec


def gate_mode(args, argv):
    ctx, k2, vr = load_all()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    units = (g1_units() + g2_units(args.e2_rows))[args.shard::args.nshard]
    started, recs = time.perf_counter(), []
    for u in units:
        recs.append(gate_unit(ctx, k2, vr, u))
        print(f"[{time.perf_counter() - started:8.1f}s] {recs[-1]}", flush=True)
    (out / f'gate_shard{args.shard:03d}.json').write_text(json.dumps(recs) + '\n')


def gate_merge(args):
    recs = [r for p in sorted(args.out.glob('gate_shard*.json')) for r in json.loads(p.read_text())]
    g1, g2 = [r for r in recs if r['kind'] == 'g1'], [r for r in recs if r['kind'] == 'g2']
    cfg = json.loads(sorted(args.out.glob('config_shard*.json'))[0].read_text())['_config']
    gates = dict(
        G1=dict(units=len(g1), identical=sum(r['g1_identical'] for r in g1), triggered_units=sum(r['triggered'] for r in g1),
                variant_diff_problems=cfg['variant_diff_vs_loaded_native'], mismatches=[r['g1_diff'] for r in g1 if not r['g1_identical']][:3]),
        G2=dict(units=len(g2), triggered_now=sum(r['triggered'] for r in g2), **{f'{k}_match': sum(r['g2'][k] for r in g2) for k in ('F0', 'A1', 'A2')}),
        G3=dict(status='not run: P_paths generator check belongs to family T, which is out of scope for this job'),
        G4={str(s): dict(units=len(g1), ok=sum(r['g4'][str(s)]['ok'] for r in g1),
                         slot_count_counts={str(c): sum(r['g4'][str(s)]['slot_count'] == c for r in g1) for c in sorted({r['g4'][str(s)]['slot_count'] for r in g1})})
            for s in G4_CAPS})
    gates['G4']['n_distinct_nominated_delays'] = dict(min=min(r['g4']['8']['n_distinct_nominated_delays'] for r in g1),
                                                      max=max(r['g4']['8']['n_distinct_nominated_delays'] for r in g1))
    gates['G1']['pass_'] = bool(gates['G1']['units'] >= 32 and gates['G1']['identical'] == gates['G1']['units'] and not gates['G1']['variant_diff_problems'])
    gates['G2']['pass_'] = bool(gates['G2']['units'] >= 32 and gates['G2']['triggered_now'] == gates['G2']['units']
                                and all(gates['G2'][f'{k}_match'] == gates['G2']['units'] for k in ('F0', 'A1', 'A2')))
    gates['G4']['pass_'] = bool(all(gates['G4'][str(s)]['ok'] == gates['G4'][str(s)]['units'] >= 32 for s in G4_CAPS))
    gates['source_md5'] = {k: cfg['source_md5'].get(k) for k in ('native_twofft', 'twofft')}
    gates['variant_md5'] = cfg['own_md5']['native_twofft_variant.py']
    (args.out / 'gates.json').write_text(json.dumps(gates, indent=1) + '\n')
    print(json.dumps(gates, indent=1))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('gate', 'gate-merge', 'pilot', 'gate-k4', 'pilot3', 'gate4', 'pilot4'), required=True)
    p.add_argument('--pilot2-rows', type=Path, default=PILOT2_ROWS)
    p.add_argument('--k-rows', type=Path, default=K_ROWS)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--e2-rows', type=Path, default=E2_ROWS_R)
    p.add_argument('--scenarios', default='G,U')
    p.add_argument('--rho-list', default='0.3')
    p.add_argument('--snr-list', default='6.0,6.5,7.0')
    p.add_argument('--s-list', default='8,12')
    p.add_argument('--frame-offset', type=int, default=PILOT_FRAMES[0])
    p.add_argument('--frames', type=int, default=200)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    return p.parse_args(argv)


if __name__ == '__main__':
    A = parse_args()
    {'gate': lambda: gate_mode(A, sys.argv[1:]), 'gate-merge': lambda: gate_merge(A), 'pilot': lambda: pilot_mode(A, sys.argv[1:]),
     'gate-k4': lambda: gate_k4_mode(A, sys.argv[1:]), 'pilot3': lambda: pilot3_mode(A, sys.argv[1:]),
     'gate4': lambda: gate4_mode(A, sys.argv[1:]), 'pilot4': lambda: pilot4_mode(A, sys.argv[1:])}[A.mode]()
