#!/usr/bin/env python3
"""Idea-funnel round 8 (runner l, claude-fable-5.2), Eric-approved margin check (rule candidate 7), 2026-11-24.
Receiver-side Wiener phase noise on the project receiver (F0 + CODELAY, real LDPC): how far does the 10% FER threshold move
against the strongest combination of existing parts?  Criteria: ideas/l2/PREDICTIONS_r8_pn_margin.md.
The frozen receiver is only called (stageA.one_arm, native.pilot_front, e1.f0_state); nothing in it is modified.
Arms per key (same frame, same noise, same phase-noise draw across arms and SNRs):
  CLEAN  no phase noise                      IGN  phase noise, untreated (sanity only)
  BESTGA strongest existing parts with the path search given away: round-0 pilot model built from the TRUE paths, phase tracked on it;
         then one coded round, re-track on pilot + soft data, and after every failed two-round pass again (<= 8); final F0 + CODELAY.
  BEST   the same chain fully blind: segmented non-coherent search + rank-1 segment phases + 3 passes pilot_front <-> tracking, with
         syndrome-driven retry over four variants (single-pole / Kalman smoother x 32 / 64-sample segments).
  OPP    per key the better of BESTGA and BEST (a frame counts as decoded if either decodes).  Criterion 1 uses it.
  ORACLE phase tracked against the true noiseless received signal (uses truth: upper bound only), then F0 + CODELAY
  python l2_r8_pn_margin.py gate|dev|diag|run|read --out out_r8_pn_margin [--workers 16]
Needs OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1 and CUDA_VISIBLE_DEVICES="".
"""
import argparse, json, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
from scipy.signal import lfilter

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1] / 'experiments'
sys.path.insert(0, str(EXP / 'data_pilot_fer_20261121'))
SCEN, RHO, SEED, BOOT = ('U', 'G'), 300, 20261124, 2000
SNRS = (350, 400, 450, 500, 550, 600, 650, 700)
OPP_SNRS = (450, 500, 550, 600, 650, 700)            # the opponent arms are only run from 4.5 dB up (dev: 85-90% FER at 4.5 dB)
SIG2 = (0.0164, 0.0082)
DEV, TEST = range(52000, 52040), range(53000, 53200)
DIAG_SNRS = (450, 550, 650)
DIAG_ARMS = dict(BEST={}, A_genie_acq=dict(genie=True), B_fb8=dict(n_fb=8), C_both=dict(genie=True, n_fb=8))
DEV_SNRS, DEV_GRID = (500, 550), [(m, 'app', infl) for m in ('sp', 'kf') for infl in (3, 5, 8)]   # dev v4 (5.5 / 6.0 dB): errors of 160 fell from 11-13 (x1) to 4-8 (x3), the grid edge; so wider, and one step lower in SNR   # dev v3: detector LLRs as the re-tracking source were far worse (76-118 vs 11-18 of 160); infl multiplies KAP0/KAP1
VARIANTS = (('sp', 32), ('sp', 64), ('kf', 32), ('kf', 64))    # blind retry order
SCALE = float(np.sqrt(2 * (1 - RHO / 1000)))          # headroom_ladder_20261008/driver.py::observe divides y and pilot by this (trial rho, not the receiver's fixed 0.5)
LOW_SNRS, LOWCHK, OFF_SNRS = (350, 400), 50, (350, 400, 450, 500)
KAP0, KAP1, OMODE, SUB = 0.10, 0.05, 'kf', 100        # residual phase variance after round 0 / after re-tracking (diag_v1 medians); ORACLE smoother (dev v2: 1 vs 2 of 160); frames for the reading-only arms
A0, A1, AO = 0.06, 0.2, 0.25                         # single-pole constants (v1 dev readout: the 8 combinations differed little)
CONST = HERE / 'r8_pn_margin_constants.json'          # written by `dev`, read by `run`
FLOOR_SNRS = (700, 800, 900, 1000, 1100, 1200)
FLOOR_FRAMES = range(54000, 54300)
FDIAG_FAIL = (('U', 54058), ('U', 54268), ('G', 54090), ('G', 54094), ('G', 54112), ('G', 54203))
FDIAG_CTRL = (('U', 54000), ('U', 54001), ('U', 54002), ('G', 54000), ('G', 54001), ('G', 54002))
S1_EXTRA = (('sp', 16, 8), ('sp', 128, 8), ('kf', 16, 8), ('kf', 128, 8),
            ('sp', 16, 16), ('sp', 32, 16), ('sp', 64, 16), ('sp', 128, 16),
            ('kf', 16, 16), ('kf', 32, 16), ('kf', 64, 16), ('kf', 128, 16))
FCONFIRM_FRAMES = range(55000, 55300)
FCONFIRM_SNRS = (1000, 1100, 1200)


def smooth(z, a):
    f = lfilter([a], [1, -(1 - a)], z); b = lfilter([a], [1, -(1 - a)], z[::-1])[::-1]
    return f + b - a * z


def tools(C):
    from physical import daft, regressors
    s = C['ctx'].system
    return (lambda x: daft(x, s.c1, s.c2, True)), (lambda x: daft(x, s.c1, s.c2)), (lambda x, l, k: regressors(x, l, k, s.c1, s.c2))


def theta(frame, scen, sig2, n):
    return np.sqrt(sig2) * np.cumsum(np.random.default_rng([SEED, frame, SCEN.index(scen)]).standard_normal(n))


def kalman_phase(yt, m, nv, sig2, a):
    """Reliability-weighted phase smoother (random-walk state, variance sig2 per sample; forward Kalman + RTS).  Pseudo-observation of the
    phase at sample n: the single-pole estimate plus Im(y conj(m) e^{-j phi0}) / |m|^2, variance nv / (2 |m|^2) (weak samples count less)."""
    phi0 = np.unwrap(np.angle(smooth(yt * np.conj(m), a))); p = np.maximum(abs(m) ** 2, 1e-9)
    obs = phi0 + np.imag(yt * np.conj(m) * np.exp(-1j * phi0)) / p; R = nv / (2 * p); n = len(yt)
    xf = np.empty(n); Pf = np.empty(n); xp = np.empty(n); Pp = np.empty(n); x, P = phi0[0], 10.0
    for i in range(n):
        xp[i], Pp[i] = x, P + sig2; K = Pp[i] / (Pp[i] + R[i]); x = xp[i] + K * (obs[i] - xp[i]); P = (1 - K) * Pp[i]; xf[i], Pf[i] = x, P
    xs = xf.copy()
    for i in range(n - 2, -1, -1):
        xs[i] = xf[i] + Pf[i] / Pp[i + 1] * (xs[i + 1] - xp[i + 1])
    return xs


def derotate(yt, model_t, a, mode='sp', sig2=0.0, floor=0.0):
    if mode == 'sp':
        return yt * np.exp(-1j * np.angle(smooth(yt * np.conj(model_t), a)))
    nv = max(float(np.mean(abs(yt) ** 2) - np.mean(abs(model_t) ** 2)), floor)          # everything the model does not explain, from the data
    return yt * np.exp(-1j * kalman_phase(yt, model_t, nv, sig2, a))


def seg_init(C, yt, S, topk=8, Ut=None):
    """Round-0 start under phase noise from existing parts: segmented non-coherent delay-Doppler search on the pilot (segments of S
    samples, powers added across segments), then the common phase of each segment from the leading singular vector of the
    segment-by-path correlation matrix, interpolated to samples.  Returns the derotated time-domain samples."""
    if Ut is None:
        if 'Ut' not in C:
            C['Ut'] = tools(C)[0](C['U'])                                       # unit-norm pilot atoms (delay x 5 integer Dopplers), time domain
        Ut = C['Ut']
    n = len(yt); ns = n // S; Z = (np.conj(Ut) * yt[:, None])[:ns * S].reshape(ns, S, -1).sum(1)   # segments x atoms
    pw = (abs(Z) ** 2).sum(0).reshape(C['lmax'] + 1, 5); d = np.argsort(-pw.max(1))[:topk]; cols = d * 5 + pw[d].argmax(1)
    u = np.linalg.svd(Z[:, cols], full_matrices=False)[0][:, 0]
    ph = np.interp(np.arange(n), (np.arange(ns) + 0.5) * S, np.unwrap(np.angle(u)))
    return yt * np.exp(-1j * ph)


def final(C, o, truth, trace=None):
    """Same steps as stageA.one_arm (F0, then CODELAY if the syndrome is non-zero); also returns the syndrome weight of the final output."""
    ctx, st = C['ctx'], C['stage3']
    dec, arrays, syn, _ = st.e1.f0_state(ctx, o)
    if syn:
        br = st.e1.run_branch(ctx, C['cd'], o, arrays, 'A1')
        decoded = br['decoder']['decoded']
        if trace is not None:
            trace['final_app'] = br['decoder']['raw_app']
    else:
        decoded = dec['decoded']
        if trace is not None:
            trace['final_app'] = dec['raw_app']
    return int(st.e1.gd.score(ctx, decoded, truth)), int(ctx.hd.syndrome_weight(ctx, decoded))


def best(C, obs, truth, mode, S, sig2, n_fb=8, genie=None, src='app', infl=0, trace=None,
         topk=8, seg_Ut=None, init_theta=None, genie_support=None, pilot_ref=None):
    """sig2 (the oscillator's phase-increment variance) is a known device parameter, as in the cited phase-noise receivers.  `truth` is used
    for scoring only, except when `genie` (true paths) is passed for the round-0 pilot model.  Returns (errors, re-tracks, final syndrome)."""
    from messages import moments
    ctx = C['ctx']; to_t, to_a, reg = tools(C); yt = to_t(obs['y']); o = dict(obs); n_re = 0; fl = float(obs['sigma2'])
    psig = max(float(np.mean(abs(yt) ** 2)) - fl, 0.0)
    r0_pilot = obs['pilot'] if pilot_ref is None else pilot_ref
    if genie is not None:
        m_r0 = to_t(reg(obs['pilot'], genie[0], genie[1]) @ genie[2])
        o['y'] = to_a(derotate(yt, m_r0, A0, mode, sig2, fl))
        if trace is not None:
            trace['m_r0'] = m_r0
    elif genie_support is not None:
        o['y'] = to_a(seg_init(C, yt, S, topk=topk, Ut=seg_Ut))
        A_sup = reg(obs['pilot'], genie_support[0], genie_support[1])
        for _ in range(3):
            g_ls, _, _, _ = np.linalg.lstsq(A_sup, o['y'], rcond=None)
            m_r0 = to_t(A_sup @ g_ls)
            o['y'] = to_a(derotate(yt, m_r0, A0, mode, sig2, fl))
        if trace is not None:
            trace['m_r0'] = m_r0; trace['r0_delays'] = genie_support[0]; trace['r0_dopplers'] = genie_support[1]; trace['r0_gains'] = g_ls
    else:
        o['y'] = to_a(yt * np.exp(-1j * init_theta) if init_theta is not None else seg_init(C, yt, S, topk=topk, Ut=seg_Ut))
        for _ in range(3):                                                # round 0: pilot only (or pilot_ref for DA re-acq)
            o_pf = o if pilot_ref is None else dict(o, pilot=r0_pilot)
            s = ctx.native.pilot_front(o_pf, ctx.system, ctx.code)
            m_r0 = to_t(reg(r0_pilot, s['delays'], s['dopplers']) @ np.asarray(s['gains'], complex))
            o['y'] = to_a(derotate(yt, m_r0, A0, mode, sig2, fl))
        if trace is not None:
            trace['m_r0'] = m_r0; trace['r0_delays'] = s['delays']; trace['r0_dopplers'] = s['dopplers']; trace['r0_gains'] = np.asarray(s['gains'], complex)
    if trace is not None:
        trace['r0'] = to_t(o['y'])
    o['sigma2'] = fl + infl * KAP0 * psig                                 # residual phase error counted as extra noise by the detector

    def retrack(arrays, r):
        llr = arrays[f'r{r}_app'] if src == 'app' else arrays[f'r{r}_input_llr']
        mu, _, _ = moments(np.clip(llr, -20, 20), 1 - ctx.system.rho)
        m = reg(obs['pilot'] + mu, arrays[f'r{r}_delays'], arrays[f'r{r}_dopplers']) @ np.asarray(arrays[f'r{r}_gains'], complex)
        o['y'] = to_a(derotate(yt, to_t(m), A1, mode, sig2, fl)); o['sigma2'] = fl + infl * KAP1 * psig
    _, arrays, _ = ctx.native.receive(o, ctx.system, ctx.code, rounds=1, iterations=20, ce_mode='soft', gain_mode='joint')
    retrack(arrays, 0); n_re += 1                                         # re-track right after the first soft-decision round
    for _ in range(n_fb):                                                 # then after every failed two-round pass
        dec, arrays, syn, _ = C['stage3'].e1.f0_state(ctx, o)
        if not syn:
            break
        retrack(arrays, 1); n_re += 1
    if trace is not None:
        trace['end'] = to_t(o['y'])
    e, syn = final(C, o, truth, trace=trace)
    return e, n_re, syn


def best_blind(C, obs, truth, sig2, k):
    """Syndrome-driven retry over the four acquisition variants; stops at the first one whose final output passes the parity check."""
    tot = 0
    for mode, S in VARIANTS:
        e, nre, syn = best(C, obs, truth, mode, S, sig2, src=k['src'], infl=k['infl']); tot += nre
        if syn == 0:
            break
    return e, tot


def genie_paths(truth):
    return np.asarray(truth['l_i'], int), np.asarray(truth['k_real'], float), np.asarray(truth['g_i'], complex)


def oracle(C, obs, raw, truth, mode, sig2):
    import stageA
    to_t, to_a, _ = tools(C); o = dict(obs)
    o['y'] = to_a(derotate(to_t(obs['y']), to_t(raw['noiseless']) / SCALE, AO, mode, sig2, float(obs['sigma2'])))
    return stageA.one_arm(C, o, truth, None)['errors']


def key_inputs(C, base, snr, frame, scen, sig2):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, RHO, snr)
    to_t, to_a, _ = tools(C); o = dict(obs)
    if sig2 > 0:
        o['y'] = to_a(to_t(obs['y']) * np.exp(1j * theta(frame, scen, sig2, len(obs['y']))))
    return raw, obs, o, truth


def shard_job(job):
    import stageA
    idx, frames, out, mode, k = job; C = stageA.setup(); n = 0
    with open(Path(out) / f'{mode}_shard{idx:03d}.jsonl', 'w') as fh:
        for f in frames:
            for s in SCEN:
                base = C['stage3'].inputs(C['ctx'], f, s, RHO)
                for snr in (DEV_SNRS if mode == 'dev' else DIAG_SNRS if mode == 'diag' else SNRS):
                    row = dict(scenario=s, snr=snr, frame=f)
                    if mode == 'diag':                                    # development frames only; uses truth for the genie arms and for the phase residuals
                        raw, obs, o, truth = key_inputs(C, base, snr, f, s, SIG2[0]); th = theta(f, s, SIG2[0], len(obs['y'])); yt = tools(C)[0](o['y'])
                        g = (np.asarray(truth['l_i'], int), np.asarray(truth['k_real'], float), np.asarray(truth['g_i'], complex))

                        def pv(yd):
                            e = np.angle(np.exp(1j * th) * np.conj(yt * np.conj(yd))); e = np.angle(np.exp(1j * (e - np.angle(np.mean(np.exp(1j * e))))))
                            return float(np.var(e[50:-50]))
                        for name, kw in k.items():
                            tr = {}; e, nre, _ = best(C, o, truth, kw.get('mode', 'sp'), kw.get('seg', 32), SIG2[0], n_fb=kw.get('n_fb', 3), genie=g if kw.get('genie') else None, trace=tr)
                            row[name] = dict(errors=e, nre=nre, pv_r0=pv(tr['r0']), pv_end=pv(tr['end']))
                        print(json.dumps(row), file=fh, flush=True); n += 1
                        continue
                    if mode == 'dev':
                        raw, obs, o, truth = key_inputs(C, base, snr, f, s, SIG2[0]); g = genie_paths(truth)
                        row['ga'] = {f'{m}_{src}_{infl}': best(C, o, truth, m, 0, SIG2[0], genie=g, src=src, infl=infl)[0] for m, src, infl in DEV_GRID}
                    else:
                        raw, obs, o, truth = key_inputs(C, base, snr, f, s, 0.0)
                        row['CLEAN'] = stageA.one_arm(C, obs, truth, None)['errors']
                        if f < TEST[0] + SUB and snr in OFF_SNRS:         # like-for-like starting line: the opponent chain with the phase noise switched off
                            row['BESTGA_off'] = best(C, obs, truth, k['mode'], 0, SIG2[0], genie=genie_paths(truth), src=k['src'], infl=k['infl'])[0]
                        for sig2 in SIG2:
                            raw, obs, o, truth = key_inputs(C, base, snr, f, s, sig2); t = f'{sig2}'; sub = f < TEST[0] + SUB or sig2 == SIG2[0]
                            row[f'ORACLE_{t}'] = oracle(C, o, raw, truth, OMODE, sig2)
                            if sig2 == SIG2[0] and f < TEST[0] + 10:
                                row[f'IGN_{t}'] = stageA.one_arm(C, o, truth, None)['errors']
                            low = sig2 == SIG2[0] and snr in LOW_SNRS and f < TEST[0] + LOWCHK      # monotonicity check below the opponents' grid
                            if (snr in OPP_SNRS and sub) or low:
                                row[f'BESTGA_{t}'], row[f'NREGA_{t}'], _ = best(C, o, truth, k['mode'], 0, sig2, genie=genie_paths(truth), src=k['src'], infl=k['infl'])
                            if (snr in OPP_SNRS and sig2 == SIG2[0]) or low:
                                row[f'BEST_{t}'], row[f'NRE_{t}'] = best_blind(C, o, truth, sig2, k)
                    print(json.dumps(row), file=fh, flush=True); n += 1
    return idx, n


def pool_run(out, mode, frames, workers, k=None):
    fr = list(frames); jobs = [(i, fr[i::workers], str(out), mode, k) for i in range(workers)]; t0 = time.time()
    with get_context('spawn').Pool(workers) as pool:
        done = sum(n for _, n in pool.imap_unordered(shard_job, jobs))
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(keys=done, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0)


def rows(out, mode):
    return [json.loads(l) for p in sorted(out.glob(f'{mode}_shard*.jsonl')) for l in open(p)]


def gate(out):
    """Implementation gate on 6 keys of frame 52000: with sigma2 = 0 the tracking arms must not hurt; the pilot model must correlate."""
    import stageA
    C = stageA.setup(); to_t, to_a, reg = tools(C); recs = []
    for s in SCEN:
        base = C['stage3'].inputs(C['ctx'], 52000, s, RHO)
        for snr in (450, 550, 700):
            raw, obs, o, truth = key_inputs(C, base, snr, 52000, s, 0.0)
            sp = C['ctx'].native.pilot_front(obs, C['ctx'].system, C['ctx'].code)
            m = to_t(reg(obs['pilot'], sp['delays'], sp['dopplers']) @ np.asarray(sp['gains'], complex)); yt = to_t(obs['y'])
            ref = to_t(raw['noiseless']) / SCALE; resid = float(np.mean(abs(yt - ref) ** 2) / obs['sigma2'])
            raw2, obs2, o2, _ = key_inputs(C, base, snr, 52000, s, SIG2[0]); th = theta(52000, s, SIG2[0], len(yt))
            e = np.angle(np.exp(1j * th) * np.conj(np.exp(1j * np.angle(smooth(to_t(o2['y']) * np.conj(ref), 0.25)))))
            recs.append(dict(key=[s, snr], clean=stageA.one_arm(C, obs, truth, None)['errors'], best0=best(C, o, truth, 'sp', 32, SIG2[0])[0], final_eq_one_arm=bool(final(C, obs, truth)[0] == stageA.one_arm(C, obs, truth, None)['errors']),
                             oracle0=oracle(C, o, raw, truth, 'kf', SIG2[0]), ign_pn=stageA.one_arm(C, o2, truth, None)['errors'],
                             best_pn=best_blind(C, o2, truth, SIG2[0], dict(src='app', infl=0))[0], bestga_pn=best(C, o2, truth, 'sp', 0, SIG2[0], genie=genie_paths(truth))[0], bestga_llr_infl=best(C, o2, truth, 'kf', 0, SIG2[0], genie=genie_paths(truth), src='llr', infl=1)[0], oracle_pn=oracle(C, o2, raw, truth, 'kf', SIG2[0]),
                             pilot_model_corr=float(abs(np.vdot(m, yt)) / np.linalg.norm(m) / np.linalg.norm(yt)),
                             noise_over_sigma2=resid, oracle_phase_err_var=float(np.var(e[50:-50]))))
            print(recs[-1], flush=True)
    ok = all(0.8 < r['noise_over_sigma2'] < 1.25 for r in recs) and all(r['pilot_model_corr'] > 0.2 for r in recs) \
        and sum(r['best0'] > 0 for r in recs) <= sum(r['clean'] > 0 for r in recs) + 1 and all(r['oracle_phase_err_var'] < 0.1 for r in recs) and all(r['final_eq_one_arm'] for r in recs)
    json.dump(dict(pass_=ok, records=recs), open(out / 'gate.json', 'w'), indent=1); print('GATE', 'PASS' if ok else 'FAIL')


def dev(out, workers):
    info = pool_run(out, 'dev', DEV, workers); R = rows(out, 'dev')
    tb = {k: int(sum(r['ga'][k] > 0 for r in R)) for k in R[0]['ga']}; kb = min(tb, key=tb.get); md, src, infl = kb.split('_')
    k = dict(mode=md, src=src, infl=float(infl), omode=OMODE, a0=A0, a1=A1, ao=AO, kap=[KAP0, KAP1], dev_frame_errors_bestga=tb, dev_keys=len(R), dev_snrs=DEV_SNRS, **info, _argv=sys.argv)
    json.dump(k, open(CONST, 'w'), indent=1); print(json.dumps(k))


def crossing(snr, fer, level=0.1):
    """Interval (lo, hi) in dB for the first SNR where FER falls to `level` (log-linear interpolation).  Below the grid: (-inf, first];
    never reached: [last, +inf)."""
    fer = np.maximum(np.asarray(fer, float), 1e-4)
    if fer[0] <= level:
        return (-np.inf, snr[0] / 100)
    for i in range(1, len(snr)):
        if fer[i] <= level < fer[i - 1]:
            w = (np.log(fer[i - 1]) - np.log(level)) / (np.log(fer[i - 1]) - np.log(fer[i])); v = (snr[i - 1] + w * (snr[i] - snr[i - 1])) / 100; return (v, v)
    return (snr[-1] / 100, np.inf)


def read(out):
    R = rows(out, 'run'); k = json.load(open(CONST)); rng = np.random.default_rng(SEED); KEYS = ('mode', 'src', 'infl', 'omode', 'a0', 'a1', 'ao', 'kap')
    m0, m1 = f'{SIG2[0]}', f'{SIG2[1]}'; T = list(TEST); D = {}
    for r in R:
        key = (r['frame'], r['scenario'], r['snr'])
        if key in D:
            raise ValueError(f'duplicate key {key}')
        if f'BESTGA_{m0}' in r and f'BEST_{m0}' in r:                     # OPP: run both opponents, keep whichever decodes (selection given away)
            r[f'OPP_{m0}'] = min(r[f'BESTGA_{m0}'], r[f'BEST_{m0}'])
        D[key] = r
    SPEC = {'CLEAN': (T, SNRS), f'OPP_{m0}': (T, OPP_SNRS), f'ORACLE_{m0}': (T, SNRS), f'ORACLE_{m1}': (T, SNRS), f'BESTGA_{m0}': (T, OPP_SNRS), f'BEST_{m0}': (T, OPP_SNRS),
            f'BESTGA_{m1}': (T[:SUB], OPP_SNRS), f'IGN_{m0}': (T[:10], SNRS), 'BESTGA_off': (T[:SUB], OFF_SNRS)}
    if len(D) != len(T) * len(SCEN) * len(SNRS):
        raise ValueError(f'expected {len(T) * len(SCEN) * len(SNRS)} keys, found {len(D)}')

    def table(a, fr, sn):                                                 # frames x scenarios x SNRs, 1 = frame error; a missing entry raises
        return np.array([[[D[(f, s, q)][a] > 0 for q in sn] for s in SCEN] for f in fr], float)
    fin = lambda v: None if not np.isfinite(v) else float(v)
    cap = lambda v, sn: float(np.clip(v[0] if np.isfinite(v[0]) else v[1], sn[0] / 100 - 0.5, sn[-1] / 100 + 0.5))
    res = dict(keys=len(D), constants={x: k[x] for x in KEYS}, fer={}, threshold_interval_db={}, shift_db={}, like_for_like={}, verdicts={})
    for a, (fr, sn) in SPEC.items():
        E = table(a, fr, sn); iv = crossing(sn, E.mean((0, 1)))
        res['fer'][a] = dict(frames=len(fr), snrs=list(sn), fer=E.mean((0, 1)).tolist(), per_scenario={s: E[:, i].mean(0).tolist() for i, s in enumerate(SCEN)}); res['threshold_interval_db'][a] = [fin(iv[0]), fin(iv[1])]
        if a == 'CLEAN':
            continue
        Ec = table('CLEAN', fr, SNRS); ic = crossing(SNRS, Ec.mean((0, 1)))                              # CLEAN on the same frames (paired)
        B = rng.integers(0, len(fr), (BOOT, len(fr))); d = [cap(crossing(sn, E[b].mean((0, 1))), sn) - cap(crossing(SNRS, Ec[b].mean((0, 1))), SNRS) for b in B]
        res['shift_db'][a] = dict(lower=fin(iv[0] - ic[1]), upper=fin(iv[1] - ic[0]), censored=bool(iv[0] != iv[1] or ic[0] != ic[1]), clean_threshold_same_frames=[fin(ic[0]), fin(ic[1])],
                                  boot_ci95_capped=np.percentile(d, [2.5, 97.5]).tolist(), boot_frac_ge_1db=float(np.mean(np.array(d) >= 1.0)), frames=len(fr))
    fr, sn0 = SPEC['BESTGA_off']                                          # reading only: same chain with and without phase noise, same frames
    for a in (f'BESTGA_{m0}', f'BESTGA_{m1}'):
        x = crossing(OPP_SNRS, table(a, fr, OPP_SNRS).mean((0, 1))); x0 = crossing(sn0, table('BESTGA_off', fr, sn0).mean((0, 1)))
        res['like_for_like'][a] = dict(threshold=[fin(x[0]), fin(x[1])], off_threshold=[fin(x0[0]), fin(x0[1])], lower=fin(x[0] - x0[1]), upper=fin(x[1] - x0[0]), frames=len(fr))
    low = table(f'OPP_{m0}', T[:LOWCHK], LOW_SNRS).mean((0, 1)); res['opp_low_snr_check'] = dict(frames=LOWCHK, snrs=list(LOW_SNRS), fer=low.tolist(), all_above_10pct=bool((low > 0.1).all()))
    b, o = res['shift_db'][f'OPP_{m0}'], res['shift_db'][f'ORACLE_{m0}']; inf = float('inf')
    lo = lambda x: -inf if x is None else x; hi = lambda x: inf if x is None else x
    c1 = True if lo(b['lower']) >= 1.0 else (False if hi(b['upper']) < 1.0 else None); c2 = True if hi(o['upper']) <= 0.5 else (False if lo(o['lower']) > 0.5 else None)
    if c1 is True and not res['opp_low_snr_check']['all_above_10pct']:   # an earlier crossing below the opponents' grid cannot be excluded
        c1 = None
    res['verdicts'] = dict(OPP_LOSES_1DB=c1, ORACLE_WITHIN_HALF_DB=c2, PASS_PRIMARY=True if (c1 is True and c2 is True) else (False if (c1 is False or c2 is False) else None))
    res['retracks_mean'] = {a: float(np.mean([r[a] for r in R if a in r])) for a in (f'NREGA_{m0}', f'NREGA_{m1}', f'NRE_{m0}')}
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))


_FLOOR_C = None


def _floor_init():
    global _FLOOR_C
    import stageA
    _FLOOR_C = stageA.setup()


def _floor_frame_job(task):
    import stageA
    f, snrs, scenarios, k = task
    C = _FLOOR_C; sig2 = SIG2[0]; ru0 = resource.getrusage(resource.RUSAGE_SELF); out_rows = []
    for s in scenarios:
        base = C['stage3'].inputs(C['ctx'], f, s, RHO)
        for snr in snrs:
            row = dict(scenario=s, snr=snr, frame=f)
            raw, obs, o, truth = key_inputs(C, base, snr, f, s, 0.0)
            row['CLEAN'] = stageA.one_arm(C, obs, truth, None)['errors']
            raw, obs, o, truth = key_inputs(C, base, snr, f, s, sig2)
            row['BESTGA'], row['NREGA'], _ = best(C, o, truth, k['mode'], 0, sig2, genie=genie_paths(truth), src=k['src'], infl=k['infl'])
            row['BEST'], row['NRE'] = best_blind(C, o, truth, sig2, k)
            out_rows.append(row)
    ru1 = resource.getrusage(resource.RUSAGE_SELF)
    return out_rows, (ru1.ru_utime - ru0.ru_utime) + (ru1.ru_stime - ru0.ru_stime)


def floor_read(out, frames=FLOOR_FRAMES, snrs=FLOOR_SNRS, scenarios=SCEN, run_meta=None):
    fr = list(frames); sn = tuple(snrs); sc = tuple(scenarios)
    k = json.load(open(CONST)); KEYS = ('mode', 'src', 'infl', 'omode', 'a0', 'a1', 'ao', 'kap')
    meta_path = out / 'floor_run.json'
    if run_meta is None and meta_path.exists():
        run_meta = json.load(open(meta_path))
    R = [json.loads(l) for l in open(out / 'floor_rows.jsonl')]
    D = {}
    for r in R:
        key = (r['frame'], r['scenario'], r['snr'])
        if key in D:
            raise ValueError(f'duplicate key {key}')
        D[key] = r
    expected = len(fr) * len(sc) * len(sn)
    if len(D) != expected:
        raise ValueError(f'expected {expected} keys, found {len(D)}')
    fer = {}; retracks = {}; checks = {}; n_fr = len(fr)
    for s in sc:
        fer[s] = {}; retracks[s] = {}
        for arm in ('CLEAN', 'BESTGA', 'BEST'):
            errs = [int(sum(D[(f, s, q)][arm] > 0 for f in fr)) for q in sn]
            fer[s][arm] = dict(frames=n_fr, snrs=list(sn), errors=errs, fer=[e / n_fr for e in errs])
        for nr in ('NREGA', 'NRE'):
            retracks[s][nr] = [float(np.mean([D[(f, s, q)][nr] for f in fr])) for q in sn]
        be = fer[s]['BEST']['errors']; bf = fer[s]['BEST']['fer']
        all_ge_1pct = all(e * 100 >= n_fr for e in be)
        if 1200 in sn:
            i12 = sn.index(1200); bga12_e = fer[s]['BESTGA']['errors'][i12]; bga12_f = fer[s]['BESTGA']['fer'][i12]
            bga12_le_0_5pct = (bga12_e * 200 <= n_fr)
            trig = bool(all_ge_1pct and bga12_le_0_5pct)
        else:
            bga12_e = bga12_f = bga12_le_0_5pct = trig = None
        checks[s] = dict(best_min_fer_7_to_12db=float(min(bf)), best_all_ge_1pct=bool(all_ge_1pct),
                         bestga_12db_errors=bga12_e, bestga_12db_fer=bga12_f,
                         bestga_12db_le_0_5pct=bga12_le_0_5pct, scenario_triggers_floor=trig)
    full_grid = (sn == FLOOR_SNRS and sc == SCEN and fr == list(FLOOR_FRAMES))
    if full_grid:
        verdict = 'FLOOR_CANDIDATE' if any(checks[s]['scenario_triggers_floor'] for s in sc) else 'CLOSED'
    else:
        verdict = 'SMOKE_ONLY'
    cfg = dict(frames=[fr[0], fr[-1]], n_frames_per_scenario=n_fr, scenarios=list(sc), rho=RHO, snrs=list(sn),
               sigma2=SIG2[0], arms=['CLEAN', 'BESTGA', 'BEST'], seed=SEED, constants_file=CONST.name,
               constants={x: k[x] for x in KEYS}, criteria=dict(best_min_fer_all_snrs=0.01, bestga_max_fer_12db=0.005))
    res = dict(_argv=(run_meta or {}).get('_argv', sys.argv), _read_argv=sys.argv, _config=cfg, keys=len(D),
               core_hours=(run_meta or {}).get('core_hours'), wall_seconds=(run_meta or {}).get('wall_seconds'),
               fer=fer, retracks_mean=retracks, per_scenario_check=checks, verdict=verdict)
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
    return res


def floor_run(out, workers, frames=FLOOR_FRAMES, snrs=FLOOR_SNRS, scenarios=SCEN, max_core_hours=5.0):
    fr = list(frames); sn = tuple(snrs); sc = tuple(scenarios)
    k = json.load(open(CONST)); KEYS = ('mode', 'src', 'infl', 'omode', 'a0', 'a1', 'ao', 'kap')
    tasks = [(f, sn, sc, k) for f in fr]; t0 = time.time(); cpu_s = 0.0; done_keys = 0; done_frames = 0; stopped = False
    rows_path = out / 'floor_rows.jsonl'
    with open(rows_path, 'w') as fh:
        if workers == 1:
            _floor_init()
            for task in tasks:
                out_rows, dt_cpu = _floor_frame_job(task); cpu_s += dt_cpu; done_frames += 1
                for r in out_rows:
                    print(json.dumps(r), file=fh, flush=True); done_keys += 1
                if cpu_s / 3600.0 > max_core_hours:
                    stopped = True; break
        else:
            with get_context('spawn').Pool(workers, initializer=_floor_init) as pool:
                for out_rows, dt_cpu in pool.imap_unordered(_floor_frame_job, tasks):
                    cpu_s += dt_cpu; done_frames += 1
                    for r in out_rows:
                        print(json.dumps(r), file=fh, flush=True); done_keys += 1
                    if done_frames % 25 == 0 or done_frames == len(fr):
                        print(f'PROGRESS frames={done_frames}/{len(fr)} keys={done_keys} core_hours={cpu_s / 3600.0:.3f} wall_s={time.time() - t0:.1f}', flush=True)
                    if cpu_s / 3600.0 > max_core_hours:
                        stopped = True; pool.terminate(); pool.join(); break
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = dict(_argv=sys.argv,
                _config=dict(frames=[fr[0], fr[-1]], n_frames_per_scenario=len(fr), scenarios=list(sc), rho=RHO, snrs=list(sn),
                             sigma2=SIG2[0], arms=['CLEAN', 'BESTGA', 'BEST'], seed=SEED, constants_file=CONST.name,
                             constants={x: k[x] for x in KEYS}, max_core_hours=max_core_hours),
                status='STOPPED_BUDGET' if stopped else 'DONE',
                frames_done=done_frames, keys=done_keys, core_hours=cpu_s / 3600.0,
                rusage_children_core_hours=(ch.ru_utime + ch.ru_stime) / 3600.0, wall_seconds=time.time() - t0)
    json.dump(meta, open(out / 'floor_run.json', 'w'), indent=1)
    if stopped:
        print('STOPPED BUDGET', meta, flush=True); sys.exit(2)
    floor_read(out, frames=fr, snrs=sn, scenarios=sc, run_meta=meta)
    print('DONE', meta, flush=True)


def _parse_range(spec, default):
    if not spec:
        return default
    a, b = spec.split(':'); return range(int(a), int(b))


def _phase_var(yd, yt, th):
    e = np.angle(np.exp(1j * th) * np.conj(yt * np.conj(yd)))
    e = np.angle(np.exp(1j * (e - np.angle(np.mean(np.exp(1j * e))))))
    return float(np.var(e[50:-50]))


def _path_match(est_delays, est_dopplers, truth):
    lt = np.asarray(truth['l_i'], int); kt = np.asarray(truth['k_real'], float); gt = np.abs(np.asarray(truth['g_i'])) ** 2
    ed = np.asarray(est_delays, int); ek = np.asarray(est_dopplers, float)
    matched = [any((ed[j] == lt[i]) and (abs(ek[j] - kt[i]) <= 0.5) for j in range(len(ed))) for i in range(len(lt))]
    ptot = float(np.sum(gt))
    return dict(matched_count=int(sum(matched)), n_true=int(len(lt)), n_est=int(len(ed)),
                matched_power_ratio=float(np.sum(gt[matched]) / ptot) if ptot > 0 else 0.0)


def _pilot_fit_J(yt, m_t, mode, sig2, fl):
    yd = derotate(yt, m_t, A0, mode, sig2, fl)
    return float(np.mean(abs(yd - m_t) ** 2))


def _run_da_reacq(C, obs, truth, sig2, k, seed, max_passes=2):
    from messages import moments
    ctx = C['ctx']; to_t, _, reg = tools(C)
    dl = np.repeat(np.arange(C['lmax'] + 1), 5); dk = np.tile(np.arange(-2, 3), C['lmax'] + 1)
    app = seed['trace']['final_app']; mode = seed['mode']; S = seed['S']; topk = seed['topk']
    tot_nre = 0; passes = 0; e, syn = seed['errors'], seed['syn']
    for _ in range(max_passes):
        passes += 1
        mu, _, _ = moments(np.clip(app, -20, 20), 1 - ctx.system.rho)
        ref = obs['pilot'] + mu
        U_da = reg(ref, dl, dk.astype(float))
        U_da = U_da / np.maximum(np.linalg.norm(U_da, axis=0, keepdims=True), 1e-12)
        Ut_da = to_t(U_da)
        tr = {}
        e, nre, syn = best(C, obs, truth, mode, S, sig2, src=k['src'], infl=k['infl'],
                           trace=tr, topk=topk, seg_Ut=Ut_da, pilot_ref=ref)
        tot_nre += nre; app = tr['final_app']
        if syn == 0:
            return e, 0, tot_nre, passes
    return e, syn, tot_nre, passes


def _run_variants_trace(C, obs, truth, sig2, k, variants, genie_support=None):
    attempts = []; tot_nre = 0
    for item in variants:
        mode, S, topk = item if len(item) == 3 else (item[0], item[1], 8)
        tr = {}
        e, nre, syn = best(C, obs, truth, mode, S, sig2, src=k['src'], infl=k['infl'],
                           trace=tr, topk=topk, genie_support=genie_support)
        tot_nre += nre
        attempts.append(dict(mode=mode, S=S, topk=topk, errors=e, syn=syn, nre=nre, trace=tr))
        if syn == 0:
            break
    return attempts, tot_nre


def _fdiag_frame_job(task):
    s, f, tag, snrs, k = task
    C = _FLOOR_C; sig2 = SIG2[0]; ru0 = resource.getrusage(resource.RUSAGE_SELF); out_rows = []
    base = C['stage3'].inputs(C['ctx'], f, s, RHO)
    to_t, _, _ = tools(C)
    for snr in snrs:
        raw, obs, o, truth = key_inputs(C, base, snr, f, s, sig2)
        yt = to_t(o['y']); th = theta(f, s, sig2, len(obs['y'])); fl = float(obs['sigma2'])
        g = genie_paths(truth)
        # A0 BEST (upstream 4 variants)
        a0_att, a0_nre = _run_variants_trace(C, o, truth, sig2, k, VARIANTS)
        a0_e, a0_syn = a0_att[-1]['errors'], a0_att[-1]['syn']
        # A1 BESTGA (upstream)
        tr_a1 = {}
        a1_e, a1_nre, a1_syn = best(C, o, truth, k['mode'], 0, sig2, genie=g, src=k['src'], infl=k['infl'], trace=tr_a1)
        # M1 & M2 on A0 and A1 (same tracker k['mode'], A0=0.06 for both m_blind and m_true)
        J_true = _pilot_fit_J(yt, tr_a1['m_r0'], k['mode'], sig2, fl)
        a0_m1 = []
        for a in a0_att:
            tr = a['trace']
            pm = _path_match(tr['r0_delays'], tr['r0_dopplers'], truth)
            jb = _pilot_fit_J(yt, tr['m_r0'], k['mode'], sig2, fl)
            a0_m1.append(dict(mode=a['mode'], S=a['S'], errors=a['errors'], syn=a['syn'],
                              pv_r0=_phase_var(tr['r0'], yt, th), pv_end=_phase_var(tr['end'], yt, th),
                              J_blind=jb, **pm))
        best_j_rec = min(a0_m1, key=lambda x: x['J_blind'])
        J_blind = best_j_rec['J_blind']
        m2 = dict(J_blind=J_blind, J_true=J_true, sigma2=fl, delta=float((J_blind - J_true) / fl),
                  best_variant=[best_j_rec['mode'], best_j_rec['S']])
        m1 = dict(A0_variants=a0_m1,
                  A0_max_power_ratio=max(x['matched_power_ratio'] for x in a0_m1),
                  A0_minJ_power_ratio=best_j_rec['matched_power_ratio'],
                  A1=dict(pv_r0=_phase_var(tr_a1['r0'], yt, th), pv_end=_phase_var(tr_a1['end'], yt, th), J_true=J_true))
        # L1 G_PHASE (true phase init only, single variant k['mode'])
        l1_e, l1_nre, l1_syn = best(C, o, truth, k['mode'], 0, sig2, src=k['src'], infl=k['infl'], init_theta=th)
        # L2 G_SUPPORT (true delays/dopplers only, LS gains, VARIANTS retry matching A0)
        l2_att, l2_nre = _run_variants_trace(C, o, truth, sig2, k, VARIANTS, genie_support=(g[0], g[1]))
        l2_e, l2_syn = l2_att[-1]['errors'], l2_att[-1]['syn']
        # S1 WIDE (A0 -> S1_EXTRA, stop at syn == 0)
        if a0_syn == 0:
            s1_extra_att = []; s1_e, s1_syn, s1_nre = a0_e, 0, a0_nre
        else:
            s1_extra_att, ex_nre = _run_variants_trace(C, o, truth, sig2, k, S1_EXTRA)
            s1_e, s1_syn, s1_nre = s1_extra_att[-1]['errors'], s1_extra_att[-1]['syn'], a0_nre + ex_nre
        # S3 DA_REACQ (A0 -> up to 2 DA passes from min-syndrome attempt of A0)
        if a0_syn == 0:
            s3_e, s3_syn, s3_nre, s3_passes = a0_e, 0, a0_nre, 0
        else:
            seed_a0 = min(a0_att, key=lambda x: x['syn'])
            s3_e, s3_syn, da_nre, s3_passes = _run_da_reacq(C, o, truth, sig2, k, seed_a0, max_passes=2)
            s3_nre = a0_nre + da_nre
        # S_PLUS (A0 -> S1_EXTRA -> up to 2 DA passes from min-syndrome attempt of A0 + S1_EXTRA)
        if s1_syn == 0:
            sp_e, sp_syn, sp_nre, sp_da_passes = s1_e, 0, s1_nre, 0
        else:
            seed_sp = min(a0_att + s1_extra_att, key=lambda x: x['syn'])
            sp_e, sp_syn, da_nre2, sp_da_passes = _run_da_reacq(C, o, truth, sig2, k, seed_sp, max_passes=2)
            sp_nre = s1_nre + da_nre2
        arms = dict(A0=dict(errors=a0_e, syn=a0_syn, nre=a0_nre, tries=len(a0_att)),
                    A1=dict(errors=a1_e, syn=a1_syn, nre=a1_nre),
                    L1=dict(errors=l1_e, syn=l1_syn, nre=l1_nre),
                    L2=dict(errors=l2_e, syn=l2_syn, nre=l2_nre, tries=len(l2_att)),
                    S1=dict(errors=s1_e, syn=s1_syn, nre=s1_nre, tries=len(a0_att) + len(s1_extra_att)),
                    S3=dict(errors=s3_e, syn=s3_syn, nre=s3_nre, da_passes=s3_passes),
                    S_PLUS=dict(errors=sp_e, syn=sp_syn, nre=sp_nre, tries=len(a0_att) + len(s1_extra_att), da_passes=sp_da_passes))
        out_rows.append(dict(scenario=s, frame=f, group=tag, snr=snr, arms=arms, M1=m1, M2=m2))
    ru1 = resource.getrusage(resource.RUSAGE_SELF)
    return out_rows, (ru1.ru_utime - ru0.ru_utime) + (ru1.ru_stime - ru0.ru_stime)


def fdiag_read(out, fail_frames=FDIAG_FAIL, ctrl_frames=FDIAG_CTRL, snrs=FLOOR_SNRS, run_meta=None):
    sn = tuple(snrs); ff = tuple(fail_frames); cf = tuple(ctrl_frames)
    k = json.load(open(CONST)); KEYS = ('mode', 'src', 'infl', 'omode', 'a0', 'a1', 'ao', 'kap')
    meta_path = out / 'diag_run.json'
    if run_meta is None and meta_path.exists():
        run_meta = json.load(open(meta_path))
    R = [json.loads(l) for l in open(out / 'diag_rows.jsonl')]
    D = {}
    for r in R:
        key = (r['scenario'], r['frame'], r['snr'])
        if key in D:
            raise ValueError(f'duplicate key {key}')
        D[key] = r
    expected = (len(ff) + len(cf)) * len(sn)
    if len(D) != expected:
        raise ValueError(f'expected {expected} keys, found {len(D)}')
    ARMS = ('A0', 'A1', 'L1', 'L2', 'S1', 'S3', 'S_PLUS')
    full_grid = (ff == FDIAG_FAIL and cf == FDIAG_CTRL and sn == FLOOR_SNRS)
    per_frame = {}
    for grp, flist in (('fail', ff), ('ctrl', cf)):
        per_frame[grp] = {}
        for s, f in flist:
            fid = f'{s}_{f}'
            per_frame[grp][fid] = {a: [int(D[(s, f, q)]['arms'][a]['errors']) for q in sn] for a in ARMS}
    # Rescue counts on failed frames (>= 5/6 zero-error AND 12 dB zero-error)
    rescued = {}
    for a in ARMS:
        rf = []
        for s, f in ff:
            errs = [D[(s, f, q)]['arms'][a]['errors'] for q in sn]
            ok = (sum(e == 0 for e in errs) >= 5) and (1200 in sn and D[(s, f, 1200)]['arms'][a]['errors'] == 0)
            if ok:
                rf.append(f'{s}_{f}')
        rescued[a] = dict(count=len(rf), total=len(ff), frames=rf)
    ctrl_errors = {a: int(sum(D[(s, f, q)]['arms'][a]['errors'] > 0 for s, f in cf for q in sn)) for a in ARMS}
    fail_errors = {a: int(sum(D[(s, f, q)]['arms'][a]['errors'] > 0 for s, f in ff for q in sn)) for a in ARMS}
    # M1 & M2 summary at 12 dB (plus all SNRs)
    m2_12db = dict(fail={}, ctrl={})
    m1_12db = dict(fail={}, ctrl={})
    if 1200 in sn:
        for grp, flist in (('fail', ff), ('ctrl', cf)):
            for s, f in flist:
                fid = f'{s}_{f}'
                m2_12db[grp][fid] = D[(s, f, 1200)]['M2']
                m1_12db[grp][fid] = D[(s, f, 1200)]['M1']
    ctrl_abs = [abs(m2_12db['ctrl'][f'{s}_{f}']['delta']) for s, f in cf] if (1200 in sn and cf) else []
    thresh = float(max(0.5, 3.0 * max(ctrl_abs))) if ctrl_abs else None
    m2_le = int(sum(m2_12db['fail'][f'{s}_{f}']['delta'] <= thresh for s, f in ff)) if (thresh is not None and ff) else None
    m2_gt = int(sum(m2_12db['fail'][f'{s}_{f}']['delta'] > thresh for s, f in ff)) if (thresh is not None and ff) else None
    prereq = dict(
        A0_fail_all_err=(fail_errors['A0'] == len(ff) * len(sn)),
        A1_fail_all_ok=(fail_errors['A1'] == 0),
        A0_ctrl_all_ok=(ctrl_errors['A0'] == 0),
        A1_ctrl_all_ok=(ctrl_errors['A1'] == 0),
    )
    prereq['passed'] = bool(all(prereq.values()))
    if not full_grid:
        verdict = 'SMOKE_ONLY'; locate = None
    elif not prereq['passed']:
        verdict = 'PREREQ_FAILED'; locate = None
    else:
        r_sp = rescued['S_PLUS']['count']
        if r_sp >= 5 and ctrl_errors['S_PLUS'] <= 1:
            verdict = 'BLIND_RESCUES'
        elif r_sp <= 1 and m2_le >= 4:
            verdict = 'STRUCTURAL_CANDIDATE'
        elif r_sp <= 1 and m2_gt >= 4:
            verdict = 'SEARCH_GAP'
        else:
            verdict = 'MIXED'
        r_l1, r_l2 = rescued['L1']['count'], rescued['L2']['count']
        locate = 'PHASE_INIT' if r_l1 >= 4 else ('SUPPORT' if r_l2 >= 4 else 'CHAIN_COUPLED')
    cfg = dict(fail_frames=[list(x) for x in ff], ctrl_frames=[list(x) for x in cf], snrs=list(sn), rho=RHO,
               sigma2=SIG2[0], seed=SEED, constants_file=CONST.name, constants={x: k[x] for x in KEYS},
               arms=list(ARMS), s1_extra=[list(x) for x in S1_EXTRA], prereq_doc='ideas/l2/PREDICTIONS_r8_pn_floor_diag.md')
    res = dict(_argv=(run_meta or {}).get('_argv', sys.argv), _read_argv=sys.argv, _config=cfg, keys=len(D),
               core_hours=(run_meta or {}).get('core_hours'), wall_seconds=(run_meta or {}).get('wall_seconds'),
               prereq=prereq, rescued=rescued, fail_key_errors=fail_errors, ctrl_key_errors=ctrl_errors,
               per_frame_errors=per_frame, M1_12db=m1_12db,
               M2_12db=dict(threshold=thresh, ctrl_max_abs_delta=max(ctrl_abs) if ctrl_abs else None,
                            fail_le_thresh=m2_le, fail_gt_thresh=m2_gt, **m2_12db),
               verdict=verdict, locate=locate)
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
    return res


def fdiag_run(out, workers, fail_frames=FDIAG_FAIL, ctrl_frames=FDIAG_CTRL, snrs=FLOOR_SNRS, max_core_hours=2.0):
    ff = tuple(fail_frames); cf = tuple(ctrl_frames); sn = tuple(snrs)
    k = json.load(open(CONST)); KEYS = ('mode', 'src', 'infl', 'omode', 'a0', 'a1', 'ao', 'kap')
    tasks = [(s, f, 'fail', sn, k) for s, f in ff] + [(s, f, 'ctrl', sn, k) for s, f in cf]
    t0 = time.time(); cpu_s = 0.0; done_keys = 0; done_frames = 0; stopped = False
    rows_path = out / 'diag_rows.jsonl'
    with open(rows_path, 'w') as fh:
        if workers == 1:
            _floor_init()
            for task in tasks:
                out_rows, dt_cpu = _fdiag_frame_job(task); cpu_s += dt_cpu; done_frames += 1
                for r in out_rows:
                    print(json.dumps(r), file=fh, flush=True); done_keys += 1
                if cpu_s / 3600.0 > max_core_hours:
                    stopped = True; break
        else:
            with get_context('spawn').Pool(workers, initializer=_floor_init) as pool:
                for out_rows, dt_cpu in pool.imap_unordered(_fdiag_frame_job, tasks):
                    cpu_s += dt_cpu; done_frames += 1
                    for r in out_rows:
                        print(json.dumps(r), file=fh, flush=True); done_keys += 1
                    print(f'FDIAG PROGRESS frames={done_frames}/{len(tasks)} keys={done_keys} core_hours={cpu_s / 3600.0:.3f} wall_s={time.time() - t0:.1f}', flush=True)
                    if cpu_s / 3600.0 > max_core_hours:
                        stopped = True; pool.terminate(); pool.join(); break
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = dict(_argv=sys.argv,
                _config=dict(fail_frames=[list(x) for x in ff], ctrl_frames=[list(x) for x in cf], snrs=list(sn),
                             rho=RHO, sigma2=SIG2[0], seed=SEED, constants_file=CONST.name,
                             constants={x: k[x] for x in KEYS}, max_core_hours=max_core_hours),
                status='STOPPED_BUDGET' if stopped else 'DONE',
                frames_done=done_frames, keys=done_keys, core_hours=cpu_s / 3600.0,
                rusage_children_core_hours=(ch.ru_utime + ch.ru_stime) / 3600.0, wall_seconds=time.time() - t0)
    json.dump(meta, open(out / 'diag_run.json', 'w'), indent=1)
    if stopped:
        print('STOPPED_BUDGET', meta, flush=True); sys.exit(2)
    fdiag_read(out, fail_frames=ff, ctrl_frames=cf, snrs=sn, run_meta=meta)
    print('DONE', meta, flush=True)


def _fconfirm_frame_job(task):
    f, snrs, scenarios, k = task
    C = _FLOOR_C; sig2 = SIG2[0]; ru0 = resource.getrusage(resource.RUSAGE_SELF); out_rows = []
    for s in scenarios:
        base = C['stage3'].inputs(C['ctx'], f, s, RHO)
        for snr in snrs:
            raw, obs, o, truth = key_inputs(C, base, snr, f, s, sig2)
            g = genie_paths(truth)
            bga_e, bga_nre, _ = best(C, o, truth, k['mode'], 0, sig2, genie=g, src=k['src'], infl=k['infl'])
            a0_att, a0_nre = _run_variants_trace(C, o, truth, sig2, k, VARIANTS)
            best_e, best_syn = a0_att[-1]['errors'], a0_att[-1]['syn']
            if best_syn == 0:
                sp_e, sp_syn, sp_nre = best_e, 0, a0_nre
            else:
                s1_att, ex_nre = _run_variants_trace(C, o, truth, sig2, k, S1_EXTRA)
                if s1_att[-1]['syn'] == 0:
                    sp_e, sp_syn, sp_nre = s1_att[-1]['errors'], 0, a0_nre + ex_nre
                else:
                    seed_sp = min(a0_att + s1_att, key=lambda x: x['syn'])
                    sp_e, sp_syn, da_nre, _ = _run_da_reacq(C, o, truth, sig2, k, seed_sp, max_passes=2)
                    sp_nre = a0_nre + ex_nre + da_nre
            out_rows.append(dict(scenario=s, snr=snr, frame=f, BESTGA=bga_e, NREGA=bga_nre,
                                 BEST=best_e, NRE=a0_nre, S_PLUS=sp_e, NRE_SPLUS=sp_nre))
    ru1 = resource.getrusage(resource.RUSAGE_SELF)
    return out_rows, (ru1.ru_utime - ru0.ru_utime) + (ru1.ru_stime - ru0.ru_stime)


def fconfirm_read(out, frames=FCONFIRM_FRAMES, snrs=FCONFIRM_SNRS, scenarios=SCEN, run_meta=None):
    fr = list(frames); sn = tuple(snrs); sc = tuple(scenarios)
    k = json.load(open(CONST)); KEYS = ('mode', 'src', 'infl', 'omode', 'a0', 'a1', 'ao', 'kap')
    meta_path = out / 'confirm_run.json'
    if run_meta is None and meta_path.exists():
        run_meta = json.load(open(meta_path))
    R = [json.loads(l) for l in open(out / 'confirm_rows.jsonl')]
    D = {}
    for r in R:
        key = (r['frame'], r['scenario'], r['snr'])
        if key in D:
            raise ValueError(f'duplicate key {key}')
        D[key] = r
    expected = len(fr) * len(sc) * len(sn)
    if len(D) != expected:
        raise ValueError(f'expected {expected} keys, found {len(D)}')
    fer = {}; paired = {}; n_fr = len(fr)
    for s in sc:
        fer[s] = {}; paired[s] = {}
        for arm in ('BEST', 'BESTGA', 'S_PLUS'):
            errs = [int(sum(D[(f, s, q)][arm] > 0 for f in fr)) for q in sn]
            fer[s][arm] = dict(frames=n_fr, snrs=list(sn), errors=errs, fer=[e / n_fr for e in errs])
        for q in sn:
            be_sok = [f for f in fr if D[(f, s, q)]['BEST'] > 0 and D[(f, s, q)]['S_PLUS'] == 0]
            bok_se = [f for f in fr if D[(f, s, q)]['BEST'] == 0 and D[(f, s, q)]['S_PLUS'] > 0]
            both_e = [f for f in fr if D[(f, s, q)]['BEST'] > 0 and D[(f, s, q)]['S_PLUS'] > 0]
            paired[s][str(q)] = dict(best_err_splus_ok=be_sok, best_ok_splus_err=bok_se, both_err=both_e)
    full_grid = (fr == list(FCONFIRM_FRAMES) and sn == FCONFIRM_SNRS and sc == SCEN)
    if not full_grid:
        verdict = 'SMOKE_ONLY'
    else:
        i11, i12 = sn.index(1100), sn.index(1200)
        g_best_12 = fer['G']['BEST']['errors'][i12]
        if g_best_12 < 3:
            verdict = 'FLOOR_NOT_REPRODUCED'
        elif all(fer[s]['S_PLUS']['errors'][idx] <= 1 for s in ('U', 'G') for idx in (i11, i12)):
            verdict = 'CLOSED_IMPL'
        else:
            verdict = 'FLOOR_PERSISTS'
    cfg = dict(frames=[fr[0], fr[-1]], n_frames_per_scenario=n_fr, scenarios=list(sc), rho=RHO, snrs=list(sn),
               sigma2=SIG2[0], arms=['BEST', 'BESTGA', 'S_PLUS'], seed=SEED, constants_file=CONST.name,
               constants={x: k[x] for x in KEYS})
    res = dict(_argv=(run_meta or {}).get('_argv', sys.argv), _read_argv=sys.argv, _config=cfg, keys=len(D),
               core_hours=(run_meta or {}).get('core_hours'), wall_seconds=(run_meta or {}).get('wall_seconds'),
               fer=fer, paired=paired, verdict=verdict)
    json.dump(res, open(out / 'confirm_summary.json', 'w'), indent=1); print(json.dumps(res))
    return res


def fconfirm_run(out, workers, frames=FCONFIRM_FRAMES, snrs=FCONFIRM_SNRS, scenarios=SCEN, max_core_hours=6.0):
    fr = list(frames); sn = tuple(snrs); sc = tuple(scenarios)
    if fr == list(FCONFIRM_FRAMES) and sn == FCONFIRM_SNRS and sc == SCEN:
        s1_path = out / 'summary.json'
        if not s1_path.exists() or json.load(open(s1_path)).get('verdict') != 'BLIND_RESCUES':
            raise RuntimeError('fconfirm requires Stage 1 summary.json verdict == BLIND_RESCUES')
    k = json.load(open(CONST)); KEYS = ('mode', 'src', 'infl', 'omode', 'a0', 'a1', 'ao', 'kap')
    tasks = [(f, sn, sc, k) for f in fr]; t0 = time.time(); cpu_s = 0.0; done_keys = 0; done_frames = 0; stopped = False
    rows_path = out / 'confirm_rows.jsonl'
    with open(rows_path, 'w') as fh:
        if workers == 1:
            _floor_init()
            for task in tasks:
                out_rows, dt_cpu = _fconfirm_frame_job(task); cpu_s += dt_cpu; done_frames += 1
                for r in out_rows:
                    print(json.dumps(r), file=fh, flush=True); done_keys += 1
                if cpu_s / 3600.0 > max_core_hours:
                    stopped = True; break
        else:
            with get_context('spawn').Pool(workers, initializer=_floor_init) as pool:
                for out_rows, dt_cpu in pool.imap_unordered(_fconfirm_frame_job, tasks):
                    cpu_s += dt_cpu; done_frames += 1
                    for r in out_rows:
                        print(json.dumps(r), file=fh, flush=True); done_keys += 1
                    if done_frames % 25 == 0 or done_frames == len(fr):
                        print(f'FCONFIRM PROGRESS frames={done_frames}/{len(fr)} keys={done_keys} core_hours={cpu_s / 3600.0:.3f} wall_s={time.time() - t0:.1f}', flush=True)
                    if cpu_s / 3600.0 > max_core_hours:
                        stopped = True; pool.terminate(); pool.join(); break
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = dict(_argv=sys.argv,
                _config=dict(frames=[fr[0], fr[-1]], n_frames_per_scenario=len(fr), scenarios=list(sc), rho=RHO, snrs=list(sn),
                             sigma2=SIG2[0], arms=['BEST', 'BESTGA', 'S_PLUS'], seed=SEED, constants_file=CONST.name,
                             constants={x: k[x] for x in KEYS}, max_core_hours=max_core_hours),
                status='STOPPED_BUDGET' if stopped else 'DONE',
                frames_done=done_frames, keys=done_keys, core_hours=cpu_s / 3600.0,
                rusage_children_core_hours=(ch.ru_utime + ch.ru_stime) / 3600.0, wall_seconds=time.time() - t0)
    json.dump(meta, open(out / 'confirm_run.json', 'w'), indent=1)
    if stopped:
        print('STOPPED_BUDGET', meta, flush=True); sys.exit(2)
    fconfirm_read(out, frames=fr, snrs=sn, scenarios=sc, run_meta=meta)
    print('DONE', meta, flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('gate', 'dev', 'diag', 'run', 'read', 'floor', 'floor_read', 'fdiag', 'fdiag_read', 'fconfirm', 'fconfirm_read'))
    ap.add_argument('--out', default=None); ap.add_argument('--workers', type=int, default=16)
    ap.add_argument('--frames', default=None); ap.add_argument('--snrs', default=None); ap.add_argument('--scenarios', default=None)
    ap.add_argument('--max-core-hours', type=float, default=None)
    a = ap.parse_args()
    default_out = 'out_r8_pn_floor_diag' if a.cmd in ('fdiag', 'fdiag_read', 'fconfirm', 'fconfirm_read') else ('out_r8_pn_floor' if a.cmd in ('floor', 'floor_read') else 'out_r8_pn_margin')
    out_name = a.out or default_out
    out = Path(out_name) if Path(out_name).is_absolute() else HERE / out_name; out.mkdir(exist_ok=True)
    if a.cmd == 'gate': gate(out)
    elif a.cmd == 'dev': dev(out, a.workers)
    elif a.cmd == 'read': read(out)
    elif a.cmd == 'floor':
        fr = _parse_range(a.frames, FLOOR_FRAMES)
        sn = tuple(int(x) for x in a.snrs.split(',')) if a.snrs else FLOOR_SNRS
        sc = tuple(a.scenarios.split(',')) if a.scenarios else SCEN
        floor_run(out, a.workers, frames=fr, snrs=sn, scenarios=sc, max_core_hours=5.0 if a.max_core_hours is None else a.max_core_hours)
    elif a.cmd == 'floor_read':
        fr = _parse_range(a.frames, FLOOR_FRAMES)
        sn = tuple(int(x) for x in a.snrs.split(',')) if a.snrs else FLOOR_SNRS
        sc = tuple(a.scenarios.split(',')) if a.scenarios else SCEN
        floor_read(out, frames=fr, snrs=sn, scenarios=sc)
    elif a.cmd == 'fdiag':
        sn = tuple(int(x) for x in a.snrs.split(',')) if a.snrs else FLOOR_SNRS
        ff = tuple((x.split(':')[0], int(x.split(':')[1])) for x in a.frames.split(',')) if a.frames else FDIAG_FAIL
        cf = () if a.frames else FDIAG_CTRL
        fdiag_run(out, a.workers, fail_frames=ff, ctrl_frames=cf, snrs=sn, max_core_hours=2.0 if a.max_core_hours is None else a.max_core_hours)
    elif a.cmd == 'fdiag_read':
        sn = tuple(int(x) for x in a.snrs.split(',')) if a.snrs else FLOOR_SNRS
        fdiag_read(out, snrs=sn)
    elif a.cmd == 'fconfirm':
        fr = _parse_range(a.frames, FCONFIRM_FRAMES)
        sn = tuple(int(x) for x in a.snrs.split(',')) if a.snrs else FCONFIRM_SNRS
        sc = tuple(a.scenarios.split(',')) if a.scenarios else SCEN
        fconfirm_run(out, a.workers, frames=fr, snrs=sn, scenarios=sc, max_core_hours=6.0 if a.max_core_hours is None else a.max_core_hours)
    elif a.cmd == 'fconfirm_read':
        fr = _parse_range(a.frames, FCONFIRM_FRAMES)
        sn = tuple(int(x) for x in a.snrs.split(',')) if a.snrs else FCONFIRM_SNRS
        sc = tuple(a.scenarios.split(',')) if a.scenarios else SCEN
        fconfirm_read(out, frames=fr, snrs=sn, scenarios=sc)
    elif a.cmd == 'diag':
        info = pool_run(out, 'diag', DEV, a.workers, DIAG_ARMS); R = rows(out, 'diag'); tab = {}
        for snr in DIAG_SNRS:
            rs = [r for r in R if r['snr'] == snr]
            tab[snr] = {n: dict(fer=float(np.mean([r[n]['errors'] > 0 for r in rs])), pv_r0=float(np.median([r[n]['pv_r0'] for r in rs])), pv_end=float(np.median([r[n]['pv_end'] for r in rs])),
                                nre=float(np.mean([r[n]['nre'] for r in rs]))) for n in DIAG_ARMS}
        json.dump(dict(arms=DIAG_ARMS, table=tab, n_per_snr=len(R) // len(DIAG_SNRS), **info, _argv=sys.argv), open(out / 'diag.json', 'w'), indent=1); print(json.dumps(tab))
    else:
        k = json.load(open(CONST)); info = pool_run(out, 'run', TEST, a.workers, k)
        json.dump(dict(_argv=sys.argv, _config=dict(frames=[TEST[0], TEST[-1]], scenarios=SCEN, rho=RHO, snrs=SNRS, sigma2=SIG2, opp_snrs=OPP_SNRS, sub_frames=SUB, constants={x: k[x] for x in ('mode', 'src', 'infl', 'omode', 'a0', 'a1', 'ao', 'kap')}), **info), open(out / 'run.json', 'w'), indent=1)
        print('DONE', info)
