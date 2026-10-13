#!/usr/bin/env python
"""C1 paired-intervention driver (task 10-08-doppler-cluster; research/c1-scalar-closure.md, section "Paired intervention").

Question: is the SP turbo loop's start-up failure (c1_map, rho .3, 6.5 dB) a property of the pilot-only first estimate, i.e. does the
SAME observation decode when the round-1 channel estimate is moved toward the truth (bistability probe), and does the loop need the
decoder -> estimation feedback at all (FROZEN)?  Mechanism probe only; the warm start is never a receiver-performance claim.

Observations are IDENTICAL to c1_map (same entropy, domain, frame indices, seed streams, rho .3, SNR 6.5 dB): the generator, seeds, head
fields, GenieRefine (genie delays + flat prior, K = 8L), eps_of, reliability and the shard/resume/merge logic are imported from
driver_c1 / driver; nothing frozen (driver_c1.py, dpss_rx.py, ...) is edited.  Defaults are the c1_map values.

Arms (one JSONL row per (L, rho, snr, frame, arm); all genie delays + flat prior exactly as SPg_flat; schedule = frozen native loop
[refit -> scalar_joint(20 inner iterations) -> LDPC50] x rounds, refit r>=2 uses the APP soft symbols of round r-1)
  FULL_R4   SPg_flat with rounds = 4 (rounds 1-2 must reproduce the stored c1_map SPg_flat row).
  FROZEN    the round-1 refit output H^_1 (pilot-only, as SPg_flat) is cached and returned again by every later refit; detector
            gain_mode = 'fixed' (no inner gain update); rounds = 2.  => decoder -> estimation feedback removed entirely.
  WARM_<l>  only the round-1 refit output is replaced by (1 - l) c^_1 + l c_true, c^_1 = normal pilot-only refit coefficients,
            c_true = least-squares projection of the TRUE tap sequences a_l onto the SAME DPSS columns M_l of the round-1 design
            (per tap, lstsq(M_l, a_l)).  TRUTH IS USED ONLY THERE (refiner receives a_true for WARM only).  Everything after
            (inner joint updates, decoding, refits 2..4) is the unmodified algorithm; rounds = 4.  Default l in {.25,.5,.75,1}.
  Smoke only (not in the default grid):  WARM_0.0 (must equal FULL_R4 bit-for-bit)  and  REF (driver_c1.run_sp SPg_flat, rounds 2).
Per row and round r (r = 1..rounds):  eps_ce<r> (channel handed to the detector of round r; for WARM round 1 the injected channel),
  eps_det<r> (detector output gains), cerr<r> / ierr<r> / syn<r> (coded errors / info errors / syndrome weight of the round-r decision),
  dsha<r> (sha256 of that decision), ll_in<r> (logloss of the detector-output LLR); plus the r1_* reliability diagnostics of driver_c1,
  final base.score fields (info_errors, coded_errors, syndrome, decode_ok, logloss_bits, seconds), eps_init (= eps_ce1),
  eps_pilot1 (pilot-only refit, = eps_ce1 except WARM), eps_proj (projection misfit of c_true alone; computed for every arm).
Run one process per shard, single thread (launch_c1i.sh).
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
import dpss_rx
import tapchannel

HERE = base.HERE
C1_MAP_ENTROPY = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'  # out/c1_map/config_shard000.json
DEFAULT_ARMS = ('FULL_R4', 'FROZEN', 'WARM_0.25', 'WARM_0.5', 'WARM_0.75', 'WARM_1.0')
C1I_PARAMS = dict(
    pairing='observations identical to out/c1_map (entropy_hex, c1 domain/streams, rho .3, snr 6.5); arms differ only in the receiver',
    FULL_R4='SPg_flat (genie delays, flat prior tau_d = 1/K) with rounds = 4',
    FROZEN='round-1 refit output cached and returned by every later refit; gain_mode fixed; rounds 2',
    WARM='round-1 refit output := (1-l) c_pilot + l c_true; c_true = lstsq projection of the true tap sequences on the SAME '
         'DPSS columns of the round-1 design (truth used only here); rounds 4; later rounds unmodified',
    eps='eps_of semantics of driver_c1: ||H - H^||_F^2 / N = sum_l ||a_l - M_l h_l||^2 / N')


def arm_spec(arm):
    if arm.startswith('FULL_R'):  # FULL_R<n>: unmodified receiver with n rounds (FULL_R4 = original arm; FULL_R10 for A4)
        return dict(mode='full', lam=None, rounds=int(arm[6:]))
    if arm == 'FROZEN':
        return dict(mode='frozen', lam=None, rounds=2)
    if arm.startswith('WARM_'):
        lam = float(arm[5:])
        if 0. <= lam <= 1.:
            return dict(mode='warm', lam=lam, rounds=4)
    raise ValueError(f'unknown arm {arm}')


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--Ls', default='8,12,16,20,24')
    p.add_argument('--rho-list', default='0.3')
    p.add_argument('--snr-list', default='6.5')
    p.add_argument('--frames', type=int, default=400)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--arms', default=','.join(DEFAULT_ARMS))
    p.add_argument('--entropy-hex', default=C1_MAP_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1i'  # base.fingerprint keys cluster params on 'clustered' only
    return args


# ------------------------------------------------------------------------ receiver
class IntervenedRefine(c1.GenieRefine):
    """GenieRefine (genie delays, flat prior) with one intervention on the refit outputs.
    mode 'full'  : unmodified (any number of rounds).
    mode 'frozen': the round-1 (channel, detail) is returned again by every later call (snaps duplicated => eps_ce<r> = eps_ce1).
    mode 'warm'  : round-1 channel gains replaced by (1 - lam) c_pilot + lam c_true (a_true needed; see _inject)."""

    def __init__(self, delays, cfg, *, mode, lam=None, a_true=None):
        super().__init__(delays, 'flat', cfg)
        if mode not in ('full', 'frozen', 'warm') or (mode == 'warm') != (a_true is not None) or (mode == 'warm') != (lam is not None):
            raise ValueError('mode / lam / a_true inconsistent (truth is allowed for warm only)')
        self.mode, self.lam, self.a_true = mode, lam, a_true
        self.cache = None

    def _inject(self, ch):
        snap = self.snaps[-1]
        c_true = np.zeros(len(snap['h']), complex)
        for delay, sl in snap['taps']:  # per-tap LS projection of the true tap sequence on that tap's DPSS columns
            c_true[sl] = np.linalg.lstsq(snap['M'][:, sl], self.a_true[delay], rcond=None)[0]
        h_pilot = snap['h']
        h_inj = (1. - self.lam) * h_pilot + self.lam * c_true
        new = tapchannel.tap_channel_class()(ch.n, ch.c1, ch.c2, ch.delays, ch.dopplers, h_inj)
        object.__setattr__(new, 'tap_mods', ch.tap_mods)
        object.__setattr__(new, 'prior_var', ch.prior_var)
        snap.update(h=h_inj.copy(), h_pilot=h_pilot, c_true=c_true)
        return new

    def __call__(self, *args, **kwargs):
        if self.mode == 'frozen' and self.cache is not None:
            self.snaps.append(self.snaps[0])
            return self.cache
        ch, detail = super().__call__(*args, **kwargs)
        if self.mode == 'frozen':
            self.cache = (ch, detail)
        elif self.mode == 'warm' and len(self.snaps) == 1:
            ch = self._inject(ch)
        return ch, detail


def decision_diag(ctx, arrays, truth, r):
    """Diagnostics of the round-r decision (r = 1..)."""
    dec = np.asarray(arrays[f'r{r - 1}_decoded'])
    llr = np.clip(np.asarray(arrays[f'r{r - 1}_input_llr'], float), -20., 20.)
    return {f'cerr{r}': int(np.count_nonzero(dec != np.asarray(truth['coded']))),
            f'ierr{r}': int(np.count_nonzero(ctx.extract_info(ctx.code, dec) != truth['info'])),
            f'syn{r}': base.syndrome_weight(ctx, dec), f'dsha{r}': base.decoded_sha(dec),
            f'll_in{r}': ctx.arms.logloss_bits(llr, truth['coded'])}


def run_arm(ctx, obs, truth, arm, genie_delays, cfg, a_true):
    """Count-blind DPSS-BEM SP receiver (genie delay support, flat prior) + the arm's intervention; truth only for WARM / scoring."""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    spec = arm_spec(arm)
    refiner = IntervenedRefine(genie_delays, cfg, mode=spec['mode'], lam=spec['lam'],
                               a_true=a_true if spec['mode'] == 'warm' else None)
    start = time.perf_counter()
    if spec['mode'] == 'frozen':  # frozen twofft.scalar_joint(gain_mode='fixed') on the cached channel; no vector prior needed
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1i_frozen', rounds=spec['rounds'],
                                            iterations=20, gain_mode='fixed', refine_override=refiner)
    else:
        with dpss_rx.vector_prior(ctx.native):
            result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm=f"c1i_{spec['mode']}",
                                                rounds=spec['rounds'], iterations=20, gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - start
    d, ar, R = result.decoder, result.arrays, spec['rounds']
    if len(refiner.snaps) != R:
        raise RuntimeError(f'expected {R} refits, got {len(refiner.snaps)}')
    log = refiner.log
    diag = c1.reliability(ctx, ar, truth['coded'])
    for r, snap in enumerate(refiner.snaps, start=1):
        diag[f'eps_ce{r}'] = c1.eps_of(snap, snap['h'], a_true, n)
        diag[f'eps_det{r}'] = c1.eps_of(snap, ar[f'r{r - 1}_gains'], a_true, n)
        diag.update(decision_diag(ctx, ar, truth, r))
    s1 = refiner.snaps[0]
    proj = s1['c_true'] if 'c_true' in s1 else None
    if proj is None:  # eps_proj for every arm (WARM computes it inside the injection; others recompute it here, post hoc)
        proj = np.zeros(len(s1['h']), complex)
        for delay, sl in s1['taps']:
            proj[sl] = np.linalg.lstsq(s1['M'][:, sl], a_true[delay], rcond=None)[0]
    diag.update(
        mode=spec['mode'], lam=spec['lam'], rounds=R, eps_init=diag['eps_ce1'],
        eps_pilot1=c1.eps_of(s1, s1.get('h_pilot', s1['h']), a_true, n), eps_proj=c1.eps_of(s1, proj, a_true, n),
        first_mu_ms=refiner.first_call['mu_ms'], first_v_mean=refiner.first_call['v_mean'],
        n_cols=int(log[0]['n_cols']), n_taps_kept=int(log[0]['n_taps_kept']), s2_r1=float(log[0]['s2']),
        tau_sum_r1=float(log[0]['tau_sum']), sec_pilot=float(result.trace['acquisition_seconds']),
        sec_ce=float(sum(e['ce'] for e in result.timing['events'])),
        sec_inference=float(sum(e['inference'] for e in result.timing['events'])))
    if spec['mode'] == 'frozen':  # the gains handed to / returned by the detector never move
        h1 = np.asarray(s1['h'])
        diag['frozen_gain_drift'] = float(max(max(np.max(np.abs(np.asarray(ar[f'r{r}_{k}']) - h1)) for k in ('gains', 'ce_gains'))
                                              for r in range(R)))
    return dict(arm=arm, decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, diag=diag)


def run_ref(ctx, obs, truth, genie_delays, cfgs, a_true):
    """Smoke control: the unmodified driver_c1 SPg_flat run (rounds 2), re-run on this observation."""
    res = c1.run_sp(ctx, obs, truth, 'SPg_flat', genie_delays, cfgs, a_true)
    res['diag']['dsha2'] = base.decoded_sha(res['decoded'])
    return dict(res, arm='REF')


def run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfgs):
    rows = []
    genie = sorted(set(int(x) for x in truth['l_i']))
    for arm in arms_wanted:
        try:
            res = (run_ref(ctx, obs, truth, genie, cfgs, a_true) if arm == 'REF'
                   else run_arm(ctx, obs, truth, arm, genie, cfgs['SPg_flat'], a_true))
            rows.append(dict(head, arm=arm, status='ok', **base.score(ctx, res, truth), **res['diag']))
        except Exception as error:  # recorded, never silently dropped
            rows.append(dict(head, arm=arm, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
    return rows


# --------------------------------------------------------------------- shard i/o
def load_done(path, arms_wanted):
    """Completed cells (all wanted arms present).  A cell left half-written by a crash is removed from the file."""
    base.load_done(path)  # drops a partial trailing line
    path = Path(path)
    if not path.exists():
        return set()
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    seen = {}
    for r in rows:
        seen.setdefault(base.cell_key(r), set()).add(r['arm'])
    done = {k for k, a in seen.items() if a >= set(arms_wanted)}
    if len(done) != len(seen):
        path.write_text(''.join(json.dumps(r, sort_keys=True, allow_nan=False, default=base.to_jsonable) + '\n'
                                for r in rows if base.cell_key(r) in done))
    return done


def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    arms_wanted = base.parse_list(args.arms, str)
    for arm in arms_wanted:
        if arm != 'REF':
            arm_spec(arm)
    Ls = base.parse_list(args.Ls, int)
    rhos = base.parse_list(args.rho_list, float)
    if any(L < 1 or L > 101 for L in Ls):
        raise ValueError('unknown L')
    if not args.frames or not args.entropy_hex:
        raise ValueError('--frames and --entropy-hex required')
    base.entropy_words(args.entropy_hex)
    snr_cells = [int(round(float(x) * 100)) for x in base.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    ctx = c1.load_context(args)
    ctx.sources['driver_c1i.py'] = base.sha256_file(HERE / 'driver_c1i.py')
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, c1i=C1I_PARAMS,
                  c1i_default_arms=list(DEFAULT_ARMS), sp_cfgs=cfgs, m2_config_sha256=m2_digest,
                  dpss_defaults=dpss_rx.CFG_DEFAULT)
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
    done = load_done(jsonl, arms_wanted)
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    n = int(ctx.system.N_total)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None  # (info, noise) fingerprint: identical across L, rho, snr
            for L in Ls:
                cfg_name = f'L{L:02d}'
                todo = [(rho, s) for rho in rhos for s in snr_cells
                        if (cfg_name, int(round(rho * 1000)), s, frame) not in done]
                if not todo:
                    continue
                paths = c1.draw_c1_paths(entropy, frame, L)
                H = c1.c1_physical_h(ctx, paths)
                a_true = c1.tap_sequences(paths, n)
                e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                pair = None
                for rho in rhos:
                    todo_r = [s for (r, s) in todo if r == rho]
                    if not todo_r:
                        continue
                    msg = c1.c1_message(ctx, entropy, frame, rho)
                    raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
                    for snr_centi in todo_r:
                        raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                        obs = base.observe(raw, rho, snr_centi / 100)
                        truth = base.truth_from_raw(raw, diag_base)
                        fp = (truth['channel_seed'], truth['physical_gains_sha256'])
                        if pair is None:
                            pair = fp
                        assert fp == pair, 'pairing across rho/snr broken'
                        mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
                        if frame_fp is None:
                            frame_fp = mfp
                        assert mfp == frame_fp, 'message/noise pairing across L/rho/snr broken'
                        head = c1.head_fields(paths, truth, rho, snr_centi, frame, L)
                        rows = run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfgs)
                        base.append_rows(handle, rows)
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] c1i L={L} rho={rho} snr={snr_centi} frame={frame} '
                              f'P={len(truth["l_i"])} ' + ' '.join(f"{r['arm']}:{r.get('info_errors', 'E')}" for r in rows),
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
