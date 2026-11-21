#!/usr/bin/env python
"""P1 gates before any run (task 10-15-tcom-reference-frame): wiring and reproduction of stored decisions, timing probe.

  g1   wiring: gen_fixed flags OFF + the e_rho entropy/streams; F0, B, A3 reproduce the stored e_rho rows on 64 frames
       (rho .5, SNR 5.5 and 6.5 dB) -- ints, hashes and truth exactly, floats to 1e-9.                      (sharded)
  g2   arm C (and D) reproduce the Stage-A decisions on 32 frames of the prospective population (6.5-dB cell);
       all C-triggered frames are included.
  g3   F0 / B / LOCAL reproduce the five-policy decisions on the 40 original F0-triggered frames.
  g4   timing probe: 16 frames per arm at 5.0 and 7.0 dB in each scenario, rho .3, single quiet process;
       projected full-run core-hours for 30 concurrent shards with the measured x1.5 contention.
  merge  out/p1_gates/p1_gates.json + P1_GATES.md
Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p1_driver as P  # noqa: E402

PROJECT = P.PROJECT
OUT = HERE / 'out' / 'p1_gates'
ERHO_DIR = PROJECT / 'experiments' / 'headroom_ladder_20261008' / 'out' / 'e_rho'
ERHO_ENTROPY = '8588d9b9662647fcb79e210475da8f5c6bc260d4930ba9b4383ec7c024fc754e'
POP_ROOT = PROJECT / 'results' / 'tf_cstate_prospective_20260923'
STAGE_A_DECISIONS = PROJECT / 'results' / 'cstate_necessity_stageA_20260928' / 'observed' / 'decisions'
FIVE_LEDGER = PROJECT / 'results' / 'cstate_necessity_stageB_resume_20260928' / 'population_five_v1' / 'policy_ledger.jsonl'
G1_SNR = (550, 650)
G4_FRAME_BASE = 900000  # frames outside the confirmation (0..1999) and quiet-timing (2000..2099) sets
G4_SNR = (500, 700)
CONTENTION = 1.5
NSH_PROJECTION = 30
GRID_SNR = (450, 500, 550, 600, 650, 700, 750, 800)


def write_json(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, indent=1, sort_keys=True, default=_jsonable, allow_nan=False) + '\n')
    print('wrote', path, flush=True)


def _jsonable(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value))


def provenance(args, ctx):
    return dict(_argv=list(sys.argv), _config=dict(
        args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        erho_entropy=ERHO_ENTROPY, p1_entropy=P.ENTROPY_HEX, p1_domain=P.DOMAIN, source_md5=ctx.source_md5,
        environment=ctx.environment, nu_max_99=P.gen_fixed.UWA_NU_MAX_99),
        _code_md5=dict(p1_gates=P.md5_file(HERE / 'p1_gates.py'), p1_driver=P.md5_file(HERE / 'p1_driver.py'),
                       gen_fixed=P.md5_file(HERE / 'gen_fixed.py')))


def loadavg():
    return [float(x) for x in Path('/proc/loadavg').read_text().split()[:3]]


# ----------------------------------------------------------------------------- G1
def g1_rows(frame):
    """e_rho rows of one frame at rho .5 and the two gate SNRs: {snr_centi: {arm: row}}."""
    path = ERHO_DIR / f'rows_shard{frame % 100:03d}.jsonl'
    out = {}
    with open(path) as stream:
        for line in stream:
            if f'"frame": {frame},' not in line:
                continue
            row = json.loads(line)
            if row['frame'] == frame and row['rho_permille'] == 500 and row['snr_centi_db'] in G1_SNR:
                out.setdefault(row['snr_centi_db'], {})[row['arm']] = row
    return out


G1_INTS = ('info_errors', 'coded_errors', 'syndrome', 'ldpc_iters')
G1_TRUTH_EXACT = ('channel_seed', 'info_sha256', 'noise_sha256', 'physical_gains_sha256', 'n_paths', 'n_distinct_delays',
                  'truth_l')
G1_TRUTH_FLOAT = ('papr_db', 'pdp_total')
G1_TRUTH_LISTS = ('truth_k', 'truth_g2')


def g1_compare(mine, stored):
    mism, floats_inexact, maxdiff = [], 0, 0.
    def fl(name, a, b):
        nonlocal floats_inexact, maxdiff
        d = abs(float(a) - float(b))
        maxdiff = max(maxdiff, d)
        floats_inexact += int(d != 0.)
        if d > 1e-9:
            mism.append(name)
    for key in G1_TRUTH_EXACT:
        if mine[key] != stored['F0'][key]:
            mism.append('truth.' + key)
    for key in G1_TRUTH_FLOAT:
        fl('truth.' + key, mine[key], stored['F0'][key])
    for key in G1_TRUTH_LISTS:
        if len(mine[key]) != len(stored['F0'][key]):
            mism.append('truth.' + key)
        else:
            for a, b in zip(mine[key], stored['F0'][key]):
                fl('truth.' + key, a, b)
    for arm, rarm in (('F0', 'F0'), ('B', 'A0'), ('A3', 'A3')):
        m, r = mine['arms'][arm], stored[rarm]
        if m.get('status') != 'ok':
            mism.append(f'{arm}.status')
            continue
        for key in G1_INTS:
            if m[key] != r[key]:
                mism.append(f'{arm}.{key}')
        fl(f'{arm}.logloss_bits', m['logloss_bits'], r['logloss_bits'])
        if arm == 'B':
            if bool(m['triggered']) != bool(r['triggered']) or m['f0_syndrome'] != r['f0_syndrome']:
                mism.append('B.trigger')
            if m['fit_delays'] != r['fit_delays']:
                mism.append('B.fit_delays')
            if len(m['fit_dopplers']) != len(r['fit_dopplers']):
                mism.append('B.fit_dopplers')
            else:
                for a, b in zip(m['fit_dopplers'], r['fit_dopplers']):
                    fl('B.fit_dopplers', a, b)
    return mism, floats_inexact, maxdiff


def stage_g1(args, ctx):
    seed_fn = lambda frame, component: ctx.hd.seed_words(ERHO_ENTROPY, frame, component)  # noqa: E731
    flags = P.gen_fixed.FLAGS_OFF
    frames = list(range(args.frames))[args.shard::args.nshard]
    cells, bad, details = 0, 0, []
    floats_inexact, maxdiff, triggered = 0, 0., 0
    t0 = time.time()
    for frame in frames:
        stored = g1_rows(frame)
        raw_base, diag_base = P.generate(ctx, flags, .5, 4.5, frame, seed_fn)
        for snr in G1_SNR:
            raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr / 100)
            obs = ctx.hd.observe(raw, .5, snr / 100)
            truth = ctx.hd.truth_from_raw(raw, diag)
            arms = P.compute_arms(ctx, obs, truth, ('F0', 'B', 'A3'))
            mine = dict(P.truth_fields(ctx, truth, diag), arms=arms)
            if snr not in stored or set(stored[snr]) < {'F0', 'A0', 'A3'}:
                raise RuntimeError(f'stored e_rho rows missing: frame {frame} snr {snr}')
            mism, inexact, md = g1_compare(mine, stored[snr])
            cells += 1
            floats_inexact += inexact
            maxdiff = max(maxdiff, md)
            triggered += int(bool(arms['B'].get('triggered')))
            if mism:
                bad += 1
                details.append(dict(frame=frame, snr=snr, mismatches=mism))
            print(f'[{time.time() - t0:6.1f}s] frame={frame} snr={snr} ok={not mism} trig={arms["B"].get("triggered")}', flush=True)
    payload = provenance(args, ctx)
    payload.update(stage='g1', shard=args.shard, nshard=args.nshard, cells=cells, mismatching_cells=bad, details=details,
                   floats_not_bit_identical=floats_inexact, max_float_abs_diff=maxdiff, triggered_cells=triggered)
    write_json(f'g1_shard{args.shard:02d}.json', payload)


# ----------------------------------------------------------------------------- G2 / G3
def population(ctx):
    return ctx.hd.Population(ctx, POP_ROOT, None)


def stage_g2(args, ctx):
    pop = population(ctx)
    stage_a = {}
    for frame in range(1024):
        d = json.loads((STAGE_A_DECISIONS / f's650_f{frame:04d}_C.json').read_text())
        stage_a[frame] = (d['baseline_syndrome_weight'], d['final_decoded_sha256'], d['final_syndrome_weight'])
    trig = [f for f in range(1024) if stage_a[f][0] != 0]
    others = [f for f in range(1024) if stage_a[f][0] == 0]
    frames = sorted(trig + others[:max(0, args.frames - len(trig))])[:max(args.frames, len(trig))]
    rows, bad = [], 0
    t0 = time.time()
    for frame in frames:
        obs, truth = pop.load(650, frame)
        arms = P.compute_arms(ctx, obs, truth, ('C', 'D'))
        c, d = arms['C'], arms['D']
        ref_c = stage_a[frame]
        dref = json.loads((STAGE_A_DECISIONS / f's650_f{frame:04d}_D.json').read_text())
        checks = dict(c_sha=c['decoded_sha256'] == ref_c[1], c_syndrome=c['c_syndrome'] == ref_c[0],
                      c_final_syndrome=c['syndrome'] == ref_c[2],
                      d_sha=d['decoded_sha256'] == dref['final_decoded_sha256'],
                      d_final_syndrome=d['syndrome'] == dref['final_syndrome_weight'],
                      d_triggered=bool(d['triggered']) == bool(dref['triggered']))
        ok = all(checks.values())
        bad += int(not ok)
        rows.append(dict(frame=frame, c_triggered=bool(c['triggered']), ok=ok, checks=checks, c_info_errors=c['info_errors'],
                         d_info_errors=d['info_errors'], seconds_C=c['seconds'], seconds_D=d['seconds']))
        print(f'[{time.time() - t0:6.1f}s] frame={frame} trig={c["triggered"]} ok={ok}', flush=True)
    payload = provenance(args, ctx)
    payload.update(stage='g2', frames=len(frames), c_triggered_frames_in_cohort=len(trig), c_triggered_frames_checked=sum(r['c_triggered'] for r in rows),
                   mismatching_frames=bad, rows=rows, passed=bool(bad == 0 and len(frames) >= 32))
    write_json('g2.json', payload)


def stage_g3(args, ctx):
    pop = population(ctx)
    ledger = [json.loads(x) for x in FIVE_LEDGER.read_text().splitlines()]
    by = {(r['policy'], r['frame']): r for r in ledger}
    frames = sorted(r['frame'] for r in ledger if r['policy'] == 'F0_LOCAL' and r['triggered'])
    if len(frames) != 40:
        raise RuntimeError(f'expected 40 original F0-triggered frames, found {len(frames)}')
    frames = frames[:args.frames] if args.frames else frames
    rows, bad = [], 0
    t0 = time.time()
    for frame in frames:
        obs, truth = pop.load(650, frame)
        arms = P.compute_arms(ctx, obs, truth, ('F0', 'B', 'LOCAL'))
        checks = {}
        for arm, policy in (('F0', 'F0'), ('B', 'B'), ('LOCAL', 'F0_LOCAL')):
            ref = by[(policy, frame)]
            checks[arm + '_sha'] = arms[arm]['decoded_sha256'] == ref['final_decoded_sha256']
            checks[arm + '_syndrome'] = arms[arm]['syndrome'] == ref['final_syndrome_weight']
        ok = all(checks.values())
        bad += int(not ok)
        rows.append(dict(frame=frame, ok=ok, checks=checks, f0_info_errors=arms['F0']['info_errors'], b_info_errors=arms['B']['info_errors'],
                         local_info_errors=arms['LOCAL']['info_errors'], triggered=bool(arms['F0']['triggered'])))
        print(f'[{time.time() - t0:6.1f}s] frame={frame} ok={ok}', flush=True)
    payload = provenance(args, ctx)
    payload.update(stage='g3', frames=len(frames), mismatching_frames=bad, rows=rows,
                   local_final_info_errors=sum(r['local_info_errors'] > 0 for r in rows), b_final_info_errors=sum(r['b_info_errors'] > 0 for r in rows),
                   passed=bool(bad == 0 and len(frames) >= 8))
    write_json('g3.json', payload)


# ----------------------------------------------------------------------------- G4
def stage_g4(args, ctx):
    seed_fn = P.make_seed_fn()
    load0 = loadavg()
    cells, t0 = [], time.time()
    for scenario in ('U', 'G'):
        for snr in G4_SNR:
            for i in range(args.frames):
                frame = G4_FRAME_BASE + i
                g0 = time.perf_counter()
                raw_base, diag_base = P.generate(ctx, scenario, .3, 4.5, frame, seed_fn)
                gen_seconds = time.perf_counter() - g0
                raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr / 100)
                obs = ctx.hd.observe(raw, .3, snr / 100)
                truth = ctx.hd.truth_from_raw(raw, diag)
                c0 = time.perf_counter()
                arms = P.compute_arms(ctx, obs, truth, P.ALL_ARMS)
                cell = time.perf_counter() - c0
                cells.append(dict(scenario=scenario, snr=snr, frame=frame, generate_seconds=gen_seconds, cell_seconds=cell,
                                  arm_seconds={a: r['seconds'] for a, r in arms.items() if r.get('status') == 'ok'},
                                  statuses={a: r.get('status') for a, r in arms.items()},
                                  f0_triggered=bool(arms['F0'].get('triggered')), c_triggered=bool(arms['C'].get('triggered')),
                                  branch_seconds={a: arms[a].get('branch_seconds') for a in ('B', 'LOCAL', 'D')}))
        print(f'[{time.time() - t0:6.1f}s] {scenario} done', flush=True)
    load1 = loadavg()
    summary = {}
    for scenario in ('U', 'G'):
        for snr in G4_SNR:
            sel = [c for c in cells if c['scenario'] == scenario and c['snr'] == snr]
            summary[f'{scenario}_{snr}'] = dict(
                n=len(sel), cell_seconds_mean=float(np.mean([c['cell_seconds'] for c in sel])),
                generate_seconds_mean=float(np.mean([c['generate_seconds'] for c in sel])),
                f0_trigger_rate=float(np.mean([c['f0_triggered'] for c in sel])), c_trigger_rate=float(np.mean([c['c_triggered'] for c in sel])),
                arm_seconds_mean={a: float(np.mean([c['arm_seconds'][a] for c in sel])) for a in P.ALL_ARMS},
                all_arms_ok=bool(all(s == 'ok' for c in sel for s in c['statuses'].values())))
    # projection: per-scenario cost per cell interpolated linearly in SNR between the two probe SNRs (flat outside);
    # generation (one per frame, scenario, rho) is amortised over the 8 SNR cells; rho .5 is charged at the rho .3 cost (conservative)
    grid = np.array(GRID_SNR, float)
    n_frames, n_rho = 2000, 2
    quiet_seconds, per_scenario = 0., {}
    for scenario in ('U', 'G'):
        lo, hi = summary[f'{scenario}_{G4_SNR[0]}'], summary[f'{scenario}_{G4_SNR[1]}']
        cost = np.interp(grid, [G4_SNR[0], G4_SNR[1]], [lo['cell_seconds_mean'] + lo['generate_seconds_mean'] / len(grid),
                                                       hi['cell_seconds_mean'] + hi['generate_seconds_mean'] / len(grid)])
        sec = float(cost.sum() * n_frames * n_rho)
        per_scenario[scenario] = dict(cell_cost_by_snr=[float(x) for x in cost], quiet_core_seconds=sec)
        quiet_seconds += sec
    projection = dict(cells=2 * n_rho * len(grid) * n_frames, quiet_core_hours=quiet_seconds / 3600., contention=CONTENTION,
                      loaded_core_hours=quiet_seconds * CONTENTION / 3600., shards=NSH_PROJECTION,
                      wall_hours_at_shards=quiet_seconds * CONTENTION / 3600. / NSH_PROJECTION, per_scenario=per_scenario,
                      mean_seconds_per_frame_all_arms=quiet_seconds / (2 * n_rho * len(grid) * n_frames),
                      protocol_estimate_core_hours=25., budget_core_hours_p1=25.)
    payload = provenance(args, ctx)
    payload.update(stage='g4', frames_per_arm=args.frames, loadavg_before=load0, loadavg_after=load1, summary=summary,
                   projection=projection, cells=cells, passed=bool(all(v['all_arms_ok'] for v in summary.values())))
    write_json('g4.json', payload)
    print('projected loaded core-hours', projection['loaded_core_hours'], 'wall hours at 30 shards', projection['wall_hours_at_shards'], flush=True)


# ----------------------------------------------------------------------------- merge
def stage_merge(args):
    def load(path):
        return json.loads(Path(path).read_text())
    shards = [load(p) for p in sorted(OUT.glob('g1_shard*.json'))]
    g2, g3, g4 = load(OUT / 'g2.json'), load(OUT / 'g3.json'), load(OUT / 'g4.json')
    cells = sum(s['cells'] for s in shards)
    frames_seen = None
    g1 = dict(shards=len(shards), cells=cells, mismatching_cells=sum(s['mismatching_cells'] for s in shards),
              details=[d for s in shards for d in s['details']], triggered_cells=sum(s['triggered_cells'] for s in shards),
              floats_not_bit_identical=sum(s['floats_not_bit_identical'] for s in shards),
              max_float_abs_diff=max(s['max_float_abs_diff'] for s in shards))
    g1['passed'] = bool(cells == 128 and g1['mismatching_cells'] == 0 and g1['triggered_cells'] >= 8)
    code = {s['_code_md5']['p1_driver'] for s in shards + [g2, g3, g4]} | {s['_code_md5']['gen_fixed'] for s in shards + [g2, g3, g4]}
    now = dict(p1_gates=P.md5_file(HERE / 'p1_gates.py'), p1_driver=P.md5_file(HERE / 'p1_driver.py'), gen_fixed=P.md5_file(HERE / 'gen_fixed.py'))
    consistent = all(s['_code_md5'] == now for s in shards + [g2, g3, g4])
    gates = dict(P1_G1=g1, P1_G2=dict({k: v for k, v in g2.items() if not k.startswith('_') and k != 'rows'}),
                 P1_G3=dict({k: v for k, v in g3.items() if not k.startswith('_') and k != 'rows'}),
                 P1_G4=dict(passed=g4['passed'], loadavg_before=g4['loadavg_before'], loadavg_after=g4['loadavg_after'],
                            summary=g4['summary'], projection=g4['projection']),
                 stage_code_md5_equals_current=bool(consistent))
    gates['all_pass'] = bool(g1['passed'] and g2['passed'] and g3['passed'] and g4['passed'] and consistent)
    payload = dict(_argv=list(sys.argv), _config=dict(stage_files={p.name: P.md5_file(p) for p in sorted(OUT.glob('*.json')) if p.name != 'p1_gates.json'},
                                                      erho_entropy=ERHO_ENTROPY, p1_entropy=P.ENTROPY_HEX, p1_domain=P.DOMAIN,
                                                      source_md5=shards[0]['_config']['source_md5'], environment=shards[0]['_config']['environment']),
                   _code_md5=now, gates=gates)
    write_json('p1_gates.json', payload)
    (OUT / 'P1_GATES.md').write_text(render_md(gates, now))
    print('all_pass =', gates['all_pass'])


def render_md(g, code):
    flag = lambda ok: 'PASS' if ok else 'FAIL'  # noqa: E731
    g1, g2, g3, g4 = g['P1_G1'], g['P1_G2'], g['P1_G3'], g['P1_G4']
    pr = g4['projection']
    L = ['# P1 gates (before any run)\n', f"Overall: **{flag(g['all_pass'])}**. Code md5: {code}. P1 entropy `{P.ENTROPY_HEX}`, domain 0x{P.DOMAIN:08X}.\n",
         '| gate | criterion | result |\n|---|---|---|',
         f"| P1-G1 wiring | flags off + e_rho streams: F0, B, A3 reproduce stored e_rho rows, 64 frames x SNR 5.5, 6.5 (rho .5) | **{flag(g1['passed'])}** "
         f"{g1['cells'] - g1['mismatching_cells']}/{g1['cells']} cells identical ({g1['triggered_cells']} F0-triggered cells exercise CSTATE); "
         f"floats not bit-identical {g1['floats_not_bit_identical']}, max |diff| {g1['max_float_abs_diff']:.1e} |",
         f"| P1-G2 arm C | C (and D) reproduce Stage-A decisions on {g2['frames']} prospective frames (6.5 dB) | **{flag(g2['passed'])}** "
         f"{g2['frames'] - g2['mismatching_frames']}/{g2['frames']} frames identical ({g2['c_triggered_frames_checked']} of {g2['c_triggered_frames_in_cohort']} C-triggered frames included) |",
         f"| P1-G3 LOCAL | F0 / B / LOCAL reproduce the five-policy decisions on the 40 original F0-triggered frames | **{flag(g3['passed'])}** "
         f"{g3['frames'] - g3['mismatching_frames']}/{g3['frames']} frames identical (final errors: B {g3['b_final_info_errors']}, LOCAL {g3['local_final_info_errors']}) |",
         f"| P1-G4 timing | 16 frames per arm, 5.0 and 7.0 dB, U and G, rho .3, single process; loadavg {g4['loadavg_before']} -> {g4['loadavg_after']} | **{flag(g4['passed'])}** "
         f"all arms ok; projection {pr['loaded_core_hours']:.1f} loaded core-hours ({pr['quiet_core_hours']:.1f} quiet x {pr['contention']}), "
         f"{pr['wall_hours_at_shards']:.2f} h wall at {pr['shards']} shards |\n"]
    L.append('## G4 detail (mean seconds per cell; arm columns are per-arm compute incl. shared prefix)\n')
    L.append('| scenario/SNR | n | cell total | gen | F0 | B | LOCAL | C | D | A3 | F0 trig | C trig |\n|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k, v in g4['summary'].items():
        a = v['arm_seconds_mean']
        L.append(f"| {k} | {v['n']} | {v['cell_seconds_mean']:.3f} | {v['generate_seconds_mean']:.3f} | " + ' | '.join(f"{a[x]:.3f}" for x in P.ALL_ARMS)
                 + f" | {v['f0_trigger_rate']:.2f} | {v['c_trigger_rate']:.2f} |")
    L.append(f"\nProjection: {pr['cells']} cells, mean {pr['mean_seconds_per_frame_all_arms']:.3f} quiet seconds per cell (all arms + amortised generation); "
             f"per-SNR cost interpolated between the two probe SNRs, rho .5 charged at the rho .3 cost. Protocol estimate was ~{pr['protocol_estimate_core_hours']:.0f} core-hours.\n")
    return '\n'.join(L) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--stage', choices=('g1', 'g2', 'g3', 'g4', 'merge'), required=True)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--frames', type=int, default=0)
    args = p.parse_args()
    if args.stage == 'merge':
        return stage_merge(args)
    ctx = P.load_context()
    {'g1': stage_g1, 'g2': stage_g2, 'g3': stage_g3, 'g4': stage_g4}[args.stage](args, ctx)


if __name__ == '__main__':
    main()
