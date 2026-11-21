#!/usr/bin/env python
"""DDST small-run driver (task 10-08-doppler-cluster; research/ddst-small-run-protocol-20261014.md, FROZEN 2026-10-14).

Question: does a real DDST transmitter with a DDST-aware receiver move the round-10 cliff of the SP-AFDM C1 receiver at equal total power and rate?
Observations are the C1 / driver_c1ib2 observations of the same (entropy 129abc..., frame, L, rho, SNR): channel, info bits and noise streams are
untouched, so every arm pairs frame by frame (asserted).  Only the data block changes:  data' = DAFT( c (I - U U^H) IDAFT(data) ),  c = sqrt(N/(N - r)),
U = top-r eigenvectors of the interference matrix M of the frame's genie delays (Tx-genie) or of M_prior(L) (Tx-blind)  (ddst_core.py).

Arms (one row per frame, cell, arm; every arm = the frozen default schedule R10 T20 through wrappers._instrumented, as driver_c1ib2 R10T20)
  SPg_flat      plain SP transmitter, frozen SPg_flat receiver                      (driver_c1ib2.run_arm_ib2 verbatim)
  DDST-A        DDST Tx-genie U, DDST-aware receiver (protocol 3.3)                 primary
  DDST-N        DDST Tx-genie U, frozen SPg_flat receiver (distortion = noise)      report-only lower bracket
  DDST-A-blind  DDST Tx with U from M_prior(L) (Stage 0), DDST-aware receiver       conditional on Stage 0

r per cell = frozen r_opt at K = 8 L of out/ddst_screen/law.json (6.5 dB rho .3 -> c1_map group, 8 dB rho .3 -> c1_boot group); Tx-blind r from
out/ddst_s0/law_prior.json.  Row fields: the c1ib2 R10T20 fields (per-round cerr/ierr/syn/dsha/ll_in/eps_ce/eps_det, r1_*, timing) plus ddst_r, ddst_c,
ddst_phi (receiver s2 factor from the frame's own spectrum), ddst_f_resid, ddst_s2_eff_r1, data_power (realised, nominal .5), data_power_ratio, papr_db,
papr_pass_gate, peak_power, sec_tx_M, sec_tx_eig (Tx side, per (frame, L)).
Scored Stage-1 invocations are locked to the frozen definition (preset s1, offset 5000, 200 frames); gates / smoke / timing need --unscored.
Run one process per shard, single thread.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

import driver as base
import driver_c1 as c1
import driver_c1i as c1i
import driver_c1ib as ib
import driver_c1ib2 as ib2
import dpss_rx
import ddst_core as core

HERE = base.HERE
ARMS = ('SPg_flat', 'DDST-A', 'DDST-N', 'DDST-A-blind')
DEFAULT_ARMS = ('SPg_flat', 'DDST-A', 'DDST-N')
GENIE_ARMS = ('DDST-A', 'DDST-N')
RT = 'R10T20'
K_GRID = tuple(range(16, 1025, 4))  # ddst_screen.K_GRID (index of r_opt in law.json)
S1_FRAME_OFFSET, S1_FRAMES = 5000, 200
S1_CELLS = [(6.5, 0.3, [8, 12, 16, 20, 24, 28, 32]), (8.0, 0.3, [16, 20, 24, 28, 32, 36, 40])]
PRESETS = {'s1': dict(cells=S1_CELLS, frames=S1_FRAMES, offset=S1_FRAME_OFFSET),
           'primary': dict(cells=S1_CELLS[:1], frames=S1_FRAMES, offset=S1_FRAME_OFFSET),
           'replication': dict(cells=S1_CELLS[1:], frames=S1_FRAMES, offset=S1_FRAME_OFFSET)}
CODE_FILES = ('ddst_driver.py', 'ddst_core.py', 'ddst_screen.py')
DDST_PARAMS = dict(
    tx='data\' = data + DAFT(corr(IDAFT(data))), corr(d) = (c-1) d - c U (U^H d)  == DAFT(c (I - U U^H) IDAFT(data)); pilot unchanged; U = top-r eigenvectors of M',
    M='M = (1/K) sum_j T_j^H A A^H T_j, K = 8 L, SPg_flat column set (W 2.5, D 8, centre 0), frozen ZC pilot; ddst_core.interference_matrix (closed form of the screen construction)',
    rx='DDST-aware: detector xt = IDAFT(pilot+mu) + corr(IDAFT(mu)), data adjoint DAFT(G^H adj_time); refit Design signal IDAFT(pilot)+G IDAFT(mu); '
       'round-1 s2 = noise + phi (s2_frozen - noise), phi = N/(N-r) tr((I-UU^H)M)/tr(M) of the frame; later passes frozen',
    pairing='observations identical to driver_c1ib2 for the same (entropy_hex 129abc..., frame, L, rho, SNR) except the data block',
    data_power='frozen per-frame data-power assertion replaced by an assertion on c and r plus the logged realised data power')


def md5_file(path):
    return ib.md5_file(path)


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--preset', choices=tuple(PRESETS), default=None)
    p.add_argument('--cells', default=None, help="'snr:rho:L,L,...;snr:rho:L,...' (unscored runs only)")
    p.add_argument('--arms', default=','.join(DEFAULT_ARMS), help='comma list of ' + ','.join(ARMS))
    p.add_argument('--rt', default=RT, help='R<rounds>T<updates>; the frozen schedule is R10T20 (other values: unscored runs only)')
    p.add_argument('--frames', type=int, default=None)
    p.add_argument('--frame-offset', type=int, default=None)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--unscored', action='store_true', help='gate / smoke / timing run (any frames, cells, r override)')
    p.add_argument('--r-override', type=int, default=None, help='force r for the DDST arms (unscored runs only; 0 = gate U1)')
    p.add_argument('--law', type=Path, default=HERE / 'out' / 'ddst_screen' / 'law.json')
    p.add_argument('--prior-dir', type=Path, default=HERE / 'out' / 'ddst_s0', help='Stage 0 output (Uprior_L<LL>.npz, law_prior.json)')
    p.add_argument('--entropy-hex', default=c1i.C1_MAP_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'ddst'  # base.fingerprint keys cluster params on 'clustered' only
    return args


def resolve(args):
    pre = PRESETS.get(args.preset, {})
    arms = base.parse_list(args.arms, str)
    if not arms or not set(arms) <= set(ARMS):
        raise ValueError(f'unknown arm in {arms}')
    ib2.arm_RT(args.rt)
    if not args.unscored:
        if args.preset is None or args.cells or args.r_override is not None or args.rt != RT:
            raise ValueError('scored runs are locked: --preset s1/primary/replication, no --cells / --r-override / --rt')
        if args.frames not in (None, S1_FRAMES) or args.frame_offset not in (None, S1_FRAME_OFFSET):
            raise ValueError('scored runs are locked to 200 frames at offset 5000')
    cells = ib2.parse_cells(args.cells) if args.cells else pre.get('cells')
    frames = args.frames if args.frames else pre.get('frames')
    offset = args.frame_offset if args.frame_offset is not None else pre.get('offset')
    if not cells or not frames or offset is None:
        raise ValueError('give --preset or --cells --frames --frame-offset')
    if args.unscored and offset <= S1_FRAME_OFFSET + S1_FRAMES - 1 and offset + frames - 1 >= S1_FRAME_OFFSET:
        raise ValueError('unscored frames must not overlap the Stage-1 scored range 5000..5199')
    if any(L < 1 or L > 101 for (_, _, Ls) in cells for L in Ls):
        raise ValueError('unknown L')
    return cells, arms, int(frames), int(offset)


def code_md5():
    out = ib2.code_md5()
    for name in CODE_FILES:
        out[name] = md5_file(HERE / name)
    return out


# ------------------------------------------------------------------------------------------ r lookup
def r_from_law(law, snr_db, rho, L):
    """Frozen r_opt (variant R) of the law group with this (snr, rho) at K = 8 L."""
    g = [x for x in law['groups'] if abs(x['snr_db'] - snr_db) < 1e-9 and abs(x['rho'] - rho) < 1e-9]
    if len(g) != 1:
        raise ValueError(f'law group for snr {snr_db} rho {rho}: {len(g)} matches')
    return int(g[0]['r_opt'][K_GRID.index(8 * int(L))])


class Priors:
    """Stage-0 M_prior(L) eigenvectors (top 512) loaded on demand, cached per process."""

    def __init__(self, prior_dir):
        self.dir = Path(prior_dir)
        self.cache = {}
        self.law = None

    def U(self, L):
        if L not in self.cache:
            path = self.dir / f'Uprior_L{int(L):02d}.npz'
            if not path.exists():
                raise FileNotFoundError(f'{path} (DDST-A-blind needs Stage 0)')
            self.cache[L] = np.load(path)['U']
        return self.cache[L]

    def r(self, snr_db, rho, L):
        if self.law is None:
            self.law = json.loads((self.dir / 'law_prior.json').read_text())
        return r_from_law(self.law, snr_db, rho, L)


# ------------------------------------------------------------------------ receiver
def run_arm_aware(ctx, obs, truth, genie_delays, cfg, a_true, prec, phi, rt):
    """driver_c1ib2.run_arm_ib2 with the DDST-aware refit and detector (changes marked # DDST)."""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    R, T = ib2.arm_RT(rt)
    refiner = core.refit_class()(genie_delays, cfg, prec, phi)  # DDST
    start = time.perf_counter()
    with core.vector_prior_ddst(ctx.native, prec):  # DDST
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1i_full', rounds=R, iterations=T,
                                            gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != R:
        raise RuntimeError(f'expected {R} refits, got {len(refiner.snaps)}')
    events = result.timing['events']
    inner = [len(ar[f'r{r}_inference_trace']) for r in range(R)]
    infer = [int(e['inference_iterations']) for e in events]
    if inner != [T] * R or infer != [T] * R:
        raise RuntimeError(f'inner-update count differs from T = {T}: trace lengths {inner}, event inference_iterations {infer}')
    log = refiner.log
    diag = c1.reliability(ctx, ar, truth['coded'])
    for r, snap in enumerate(refiner.snaps, start=1):
        diag[f'eps_ce{r}'] = c1.eps_of(snap, snap['h'], a_true, n)
        diag[f'eps_det{r}'] = c1.eps_of(snap, ar[f'r{r - 1}_gains'], a_true, n)
        diag.update(c1i.decision_diag(ctx, ar, truth, r))
    s1 = refiner.snaps[0]
    proj = np.zeros(len(s1['h']), complex)
    for delay, sl in s1['taps']:
        proj[sl] = np.linalg.lstsq(s1['M'][:, sl], a_true[delay], rcond=None)[0]
    diag.update(
        mode='full', lam=None, rounds=R, eps_init=diag['eps_ce1'],
        eps_pilot1=c1.eps_of(s1, s1.get('h_pilot', s1['h']), a_true, n), eps_proj=c1.eps_of(s1, proj, a_true, n),
        first_mu_ms=refiner.first_call['mu_ms'], first_v_mean=refiner.first_call['v_mean'],
        n_cols=int(log[0]['n_cols']), n_taps_kept=int(log[0]['n_taps_kept']), s2_r1=float(log[0]['s2']),
        tau_sum_r1=float(log[0]['tau_sum']), sec_pilot=float(result.trace['acquisition_seconds']),
        sec_ce=float(sum(e['ce'] for e in events)), sec_inference=float(sum(e['inference'] for e in events)),
        R=R, T=T, inner_iters=inner, inference_iterations=infer,
        t_cum=[float(e['ready']) for e in events], sec_ce_r=[float(e['ce']) for e in events],
        sec_inf_r=[float(e['inference']) for e in events], sec_dec_r=[float(e['decoder']) for e in events],
        ddst_s2_eff_r1=float(refiner.s2_eff_first))
    return dict(arm='DDST-A', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, diag=diag)


def _row(ctx, head, name, status_fn):
    try:
        res = status_fn()
        return dict(head, arm=name, status='ok', **res)
    except Exception as error:  # recorded, never silently dropped
        return dict(head, arm=name, status='error', error=repr(error), trace=traceback.format_exc()[-1500:])


def _finish(ctx, res, truth, extra):
    return dict(base.score(ctx, res, truth), **res['diag'], **extra)


def frame_L_rows(ctx, cfg, entropy, frame, L, cells, arms, rt, *, law, priors, r_override):
    """All rows of one (frame, L): list over the (snr, rho) cells containing L.  Returns [(snr_centi, rho, rows)]."""
    n = int(ctx.system.N_total)
    s = ctx.system
    paths = c1.draw_c1_paths(entropy, frame, L)
    H = c1.c1_physical_h(ctx, paths)
    a_true = c1.tap_sequences(paths, n)
    e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
    assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
    want_genie = any(a in arms for a in GENIE_ARMS)
    want_blind = 'DDST-A-blind' in arms
    tx_times = dict(sec_tx_M=0., sec_tx_eig=0.)
    M = lam = V = None
    if want_genie or want_blind:
        pt = getattr(ctx, 'ddst_pt', None)
        if pt is None:
            pt = ctx.ddst_pt = core.pilot_time(ctx)
        t0 = time.perf_counter()
        M = core.interference_matrix(np.array(paths['tap_delays'], int), s.c1, pt)
        tx_times['sec_tx_M'] = time.perf_counter() - t0
        if want_genie:
            t0 = time.perf_counter()
            lam, V = core.spectrum(M)
            tx_times['sec_tx_eig'] = time.perf_counter() - t0
    out = []
    pair = frame_fp = None
    rhos = sorted({r for (_, r, Ls) in cells if L in Ls})
    for rho in rhos:
        msg = c1.c1_message(ctx, entropy, frame, rho)
        raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
        for snr in sorted({sn for (sn, r, Ls) in cells if L in Ls and r == rho}):
            snr_centi = int(round(snr * 100))
            raw = base.cluster_at_snr(raw_base, snr_centi / 100)
            obs = base.observe(raw, rho, snr_centi / 100)
            truth = base.truth_from_raw(raw, diag_base)
            fp = (truth['channel_seed'], truth['physical_gains_sha256'])
            pair = pair or fp
            assert fp == pair, 'pairing across rho/snr broken'
            mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
            frame_fp = frame_fp or mfp
            assert mfp == frame_fp, 'message/noise pairing across L/rho/snr broken'
            genie = sorted(set(int(x) for x in truth['l_i']))
            head = c1.head_fields(paths, truth, rho, snr_centi, frame, L)
            rows = []
            dpow0 = float(np.mean(np.abs(np.asarray(raw['data']) / np.sqrt(2. * (1. - rho))) ** 2))
            plain = dict(ddst_r=0, ddst_c=1., ddst_phi=1., ddst_f_resid=1., data_power=dpow0, data_power_ratio=dpow0 / .5, **tx_times)
            plain['papr_pass_gate'] = bool(diag_base['waveform']['passes_declared_simulation_power_gate'])
            plain['peak_power'] = float(diag_base['waveform']['peak_power'])
            if 'SPg_flat' in arms:
                rows.append(_row(ctx, head, 'SPg_flat', lambda: dict(
                    _finish(ctx, ib2.run_arm_ib2(ctx, obs, truth, rt, genie, cfg, a_true), truth, plain))))

            def ddst_obs(prec, f):
                msg_d = core.ddst_message(ctx, msg, rho, prec)
                raw_base_d, diag_base_d = c1.c1_base(ctx, msg_d, paths, H)
                raw_d = base.cluster_at_snr(raw_base_d, snr_centi / 100)
                obs_d, dpow = core.observe_ddst(raw_d, rho, snr_centi / 100, prec)
                truth_d = base.truth_from_raw(raw_d, diag_base_d)
                assert (truth_d['channel_seed'], truth_d['physical_gains_sha256']) == pair, 'DDST pairing (channel) broken'
                assert (hashlib.sha256(np.ascontiguousarray(truth_d['info']).tobytes()).hexdigest(), truth_d['noise_sha256']) == frame_fp, \
                    'DDST pairing (message/noise) broken'
                head_d = c1.head_fields(paths, truth_d, rho, snr_centi, frame, L)
                extra = dict(ddst_r=int(prec.r), ddst_c=float(prec.c), data_power=float(dpow), data_power_ratio=float(dpow / .5),
                             papr_pass_gate=bool(diag_base_d['waveform']['passes_declared_simulation_power_gate']),
                             peak_power=float(diag_base_d['waveform']['peak_power']), ddst_f_resid=float(f),
                             ddst_phi=float(core.phi_of(f, prec.r)), **tx_times)
                return obs_d, truth_d, head_d, extra

            if want_genie:
                r = r_override if r_override is not None else r_from_law(law, snr, rho, L)
                prec = core.Precoder(V[:, :r])
                f = core.f_genie(lam, r)
                obs_d, truth_d, head_d, extra = ddst_obs(prec, f)
                if 'DDST-A' in arms:
                    rows.append(_row(ctx, head_d, 'DDST-A', lambda: _finish(ctx, run_arm_aware(
                        ctx, obs_d, truth_d, genie, cfg, a_true, prec, extra['ddst_phi'], rt), truth_d, extra)))
                if 'DDST-N' in arms:
                    rows.append(_row(ctx, head_d, 'DDST-N', lambda: _finish(
                        ctx, ib2.run_arm_ib2(ctx, obs_d, truth_d, rt, genie, cfg, a_true), truth_d, extra)))
            if want_blind:
                rb = r_override if r_override is not None else priors.r(snr, rho, L)
                Ub = priors.U(L)[:, :rb] if rb else np.zeros((n, 0), complex)
                prec_b = core.Precoder(Ub)
                f_b = core.f_with(M, Ub)
                obs_b, truth_b, head_b, extra_b = ddst_obs(prec_b, f_b)
                rows.append(_row(ctx, head_b, 'DDST-A-blind', lambda: _finish(ctx, run_arm_aware(
                    ctx, obs_b, truth_b, genie, cfg, a_true, prec_b, extra_b['ddst_phi'], rt), truth_b, extra_b)))
            out.append((snr_centi, rho, rows))
    return out


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    cells, arms_wanted, n_frames, offset = resolve(args)
    base.entropy_words(args.entropy_hex)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    law = json.loads(Path(args.law).read_text())
    priors = Priors(args.prior_dir)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    for name in ('driver_c1i.py', 'driver_c1ib.py', 'driver_c1ib2.py', 'ddst_driver.py', 'ddst_core.py'):
        ctx.sources[name] = base.sha256_file(HERE / name)
    _, config = base.fingerprint(args, ctx, argv)
    prior_files = {}
    if 'DDST-A-blind' in arms_wanted:
        prior_files = {p.name: md5_file(p) for p in sorted(Path(args.prior_dir).glob('Uprior_L*.npz')) + [Path(args.prior_dir) / 'law_prior.json']}
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, c1i=c1i.C1I_PARAMS, c1ib2=ib2.IB2_PARAMS,
                  ddst=DDST_PARAMS, resolved=dict(cells=[[sn, r, Ls] for (sn, r, Ls) in cells], arms=arms_wanted, frames=n_frames,
                                                  frame_offset=offset, rt=args.rt, scored=not args.unscored, r_override=args.r_override),
                  code_md5=code_md5(), entropy_hex=args.entropy_hex, sp_cfg=cfg, m2_config_sha256=m2_digest,
                  dpss_defaults=dpss_rx.CFG_DEFAULT, law_md5=md5_file(args.law), law_path=str(args.law), prior_files_md5=prior_files)
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment',)}
    if config_path.exists():
        previous = json.loads(config_path.read_text())
        if previous.get('_config_cmp') != json.loads(json.dumps(comparable, default=base.to_jsonable)):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable),
                                          indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = c1i.load_done(jsonl, arms_wanted)
    started = time.perf_counter()
    n_cells = 0
    all_L = sorted({L for (_, _, Ls) in cells for L in Ls})
    frames = list(range(offset, offset + n_frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            for L in all_L:
                todo = [(sn, r, [L]) for (sn, r, Ls) in cells if L in Ls
                        and (f'L{L:02d}', int(round(r * 1000)), int(round(sn * 100)), frame) not in done]
                if not todo:
                    continue
                for snr_centi, rho, rows in frame_L_rows(ctx, cfg, args.entropy_hex, frame, L, todo, arms_wanted, args.rt,
                                                         law=law, priors=priors, r_override=args.r_override):
                    base.append_rows(handle, rows)
                    n_cells += 1
                    print(f'[{time.perf_counter() - started:8.1f}s] ddst snr={snr_centi} rho={rho} L={L} frame={frame} '
                          + ' '.join(f"{r['arm']}:{r.get('info_errors', 'E')}(r={r.get('ddst_r')},{r.get('seconds', 0.):.1f}s)" for r in rows),
                          flush=True)
    rows_all = [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    (out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=list(argv), _config=config, shard=args.shard, nshard=args.nshard,
        cells_run_this_invocation=n_cells, n_rows=len(rows_all),
        n_error_rows=sum(r['status'] != 'ok' for r in rows_all),
        rows_sha256=base.sha256_file(jsonl), wall_seconds=time.perf_counter() - started),
        indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    print(f'shard {args.shard} done: {len(rows_all)} rows', flush=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parse_args(argv)
    if args.mode == 'merge':
        base.merge(args, argv)
    else:
        run_shard(args, argv)


if __name__ == '__main__':
    main()
