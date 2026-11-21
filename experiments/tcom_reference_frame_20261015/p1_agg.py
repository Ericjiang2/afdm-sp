#!/usr/bin/env python
"""P1 aggregation: protocol.md section 3.3 (H1-H4), frozen rules.  Reads rows only.  numpy + scipy.

    python -B p1_agg.py --rows DIR [DIR ...] --out DIR [--timing DIR [DIR ...]] [--boot 20000] [--seed N]
    python -B p1_agg.py --selftest

Unit of analysis: one (scenario, rho) cell = 8 SNR points x n frames; the frame is the resampling unit (channel, bits and
noise are shared over SNR and rho).  FER = fraction of frames with info_errors > 0.
  H1  eligible SNR points: F0 FER in [1e-3, .5].  Per eligible point: one-sided exact paired McNemar (B better than F0),
      Holm over the eligible points of the cell, alpha .05.  Gain @FER 1e-2 = x(F0) - x(B) dB with a frame-block bootstrap
      (default B = 20000, percentile 95% CI).  Cell PASS iff >= 75% of the eligible points are Holm-significant AND the
      conservative CI of the gain (censored draws against B) excludes 0 from below.  FAIL iff the CI lower end is <= 0 even
      with every censored draw resolved in B's favour (clipped bounds; unidentified draws +inf).  INCONCLUSIVE otherwise
      (e.g. positive gain with < 75% significant points, or a gain left unidentified by censoring).  NO-ELIGIBLE if the cell
      has no eligible point.  Overall: FAIL if any cell FAILs (checked first); INCOMPLETE if a cell is missing; PASS iff all
      four cells PASS; else INCONCLUSIVE.
  H2  gap x(B) - x(A3) @1e-2 with CI; "within .5 dB" may be written for a cell only if the CI upper bound <= .5.
  H3  x(B) - x(C) @1e-2: PASS iff CI upper bound <= +.1 AND quiet mean time(B) <= .65 time(C) (--timing rows; PENDING-TIMING if absent).
  H4  B vs LOCAL: per-SNR paired counts / exact two-sided McNemar and x(LOCAL) - x(B); report only.
Crossing x(target): log-linear interpolation of log10 FER versus SNR (dB), first FER <= target scanning upward (the
analyze.py convention); FER == 0 uses the floor 0.5/n.  A crossing outside the grid is censored: it is clipped to the grid edge
and flagged; for the one-sided claims the bootstrap draw is set to the unfavourable infinity whenever the clipping could
inflate the claim (H1: F0 censored low or B censored high -> gain = -inf; H2/H3: first arm censored high or second arm
censored low -> difference = +inf), so a censored claim can only be weakened, never strengthened.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

ARMS = ('F0', 'B', 'LOCAL', 'C', 'D', 'A3')
CELLS = tuple((s, r) for s in ('U', 'G') for r in (300, 500))
TARGET = 1e-2
ELIGIBLE = (1e-3, .5)
ALPHA = .05
SIG_FRACTION = .75
H2_BOUND = .5
H3_BOUND = .1
H3_RATIO = .65
OK, LOW, HIGH = 0, 1, 2
STATUS = {OK: 'ok', LOW: 'censored-low (FER <= target at the lowest SNR)', HIGH: 'censored-high (FER > target at every SNR)'}


# ----------------------------------------------------------------------------- statistics
def mcnemar_one_sided(b, c):
    """b = frames the first arm got wrong and the second right; c = the reverse.  H1: second arm better, P(X >= b | b + c)."""
    n = int(b) + int(c)
    return 1.0 if n == 0 else float(stats.binom.sf(int(b) - 1, n, .5))


def mcnemar_two_sided(b, c):
    n = int(b) + int(c)
    return 1.0 if n == 0 else float(min(1., 2 * stats.binom.sf(max(int(b), int(c)) - 1, n, .5)))


def holm(pvals, alpha=ALPHA):
    """Holm step-down; returns reject flags in the input order."""
    order = np.argsort(pvals, kind='stable')
    m = len(pvals)
    reject = np.zeros(m, bool)
    for rank, i in enumerate(order):
        if pvals[i] <= alpha / (m - rank):
            reject[i] = True
        else:
            break
    return reject


def crossing(fer, n, snr, target=TARGET):
    """fer (R, S) with snr ascending; returns x (R,) clipped to the grid and status (R,) in {OK, LOW, HIGH}."""
    fer = np.atleast_2d(fer)
    R, S = fer.shape
    snr = np.asarray(snr, float)
    below = fer <= target
    has = below.any(1)
    j = below.argmax(1)
    status = np.zeros(R, int)
    status[~has] = HIGH
    status[has & (j == 0)] = LOW
    x = np.where(status == HIGH, snr[-1], snr[0])
    idx = np.flatnonzero(has & (j > 0))
    if idx.size:
        jj = j[idx]
        f = np.where(fer == 0, .5 / n, fer)
        y0, y1, yt = np.log10(f[idx, jj - 1]), np.log10(f[idx, jj]), math.log10(target)
        res = (fer[idx, jj] == 0) & (y1 >= yt)  # zero-FER floor above the target: resolution-limited
        t = np.where(res, 1., (yt - y0) / np.where(res, 1., y1 - y0))
        x[idx] = snr[jj - 1] + t * (snr[jj] - snr[jj - 1])
    return x, status


def diff_gain(xa, sa, xb, sb):
    """H1 gain = x_a - x_b (a = F0, b = B); lower-bound claim: -inf where clipping could inflate it."""
    d = xa - xb
    return np.where((sa == LOW) | (sb == HIGH), -np.inf, d)


def diff_gain_fav(xa, sa, xb, sb):
    """H1 gain, most favourable to B (an upper bound per draw), used only to decide FAIL.  Clipped crossings are bounds:
    F0 censored low -> x_F0 <= grid start, so the clipped difference is an upper bound unless B is also censored low (then
    unknown, +inf); B censored high -> x_B >= grid end, so the clipped difference is an upper bound unless F0 is also censored
    high (then unknown, +inf); F0 censored high with B uncensored -> the clipped difference is a lower bound only (+inf)."""
    d = xa - xb
    unknown = ((sa == LOW) & (sb == LOW)) | ((sa == HIGH) & (sb == HIGH)) | ((sa == HIGH) & (sb != HIGH))
    return np.where(unknown, np.inf, d)


def diff_gap(xa, sa, xb, sb):
    """H2/H3 gap = x_a - x_b (a = B, b = A3 or C); upper-bound claim: +inf where clipping could shrink it."""
    d = xa - xb
    return np.where((sa == HIGH) | (sb == LOW), np.inf, d)


def diff_plain(xa, sa, xb, sb):
    return xa - xb


def nearest_rank(draws, q):
    d = np.sort(draws)
    return float(d[min(len(d) - 1, max(0, int(math.ceil(q * len(d))) - 1))])


def summarize(values):
    """values[0] = point estimate on the full sample, values[1:] = bootstrap draws."""
    v = np.asarray(values, float)
    draws = v[1:]
    return dict(point=v[0], lo=nearest_rank(draws, .025), hi=nearest_rank(draws, .975),
                frac_unbounded=float(np.mean(~np.isfinite(draws))))


def jf(x):
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else ('inf' if x > 0 else ('-inf' if x < 0 else 'nan'))


def jsum(s):
    return {k: jf(v) for k, v in s.items()}


# ----------------------------------------------------------------------------- loading
def load_rows(dirs):
    rows, files = [], []
    for d in dirs:
        found = sorted(glob.glob(str(Path(d) / 'rows_shard*.jsonl'))) + sorted(glob.glob(str(Path(d) / 'rows_shard*.jsonl.gz')))
        if not found:
            raise FileNotFoundError(d)
        for f in found:
            opener = gzip.open if f.endswith('.gz') else open
            with opener(f, 'rt') as stream:
                rows += [json.loads(x) for x in stream if x.strip()]
            files.append(f)
    return rows, files


def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def build_cells(rows, min_snr_points=2):
    """{(scenario, rho_permille): dict(snr, frames, fail{arm}(n,S), sec{arm}(n,S), trig{arm}(n,S), dropped, errors)}."""
    raw = {}
    for r in rows:
        key = (r['scenario'], int(r['rho_permille']))
        cell = raw.setdefault(key, {})
        k2 = (int(r['frame']), int(r['snr_centi_db']))
        if k2 in cell:
            raise ValueError(f'duplicate row {key} {k2}')
        cell[k2] = r['arms']
    out = {}
    for key, cell in raw.items():
        snrs = sorted({k[1] for k in cell})
        frames_all = sorted({k[0] for k in cell})
        arms = [a for a in ARMS if any(a in v for v in cell.values())]
        keep, dropped, errors = [], 0, 0
        for f in frames_all:
            ok = all((f, s) in cell and all(a in cell[(f, s)] and cell[(f, s)][a].get('status', 'ok') == 'ok' for a in arms)
                     for s in snrs)
            errors += int(any((f, s) in cell and any(a in cell[(f, s)] and cell[(f, s)][a].get('status', 'ok') != 'ok' for a in arms)
                              for s in snrs))
            keep.append(f) if ok else None
            dropped += 0 if ok else 1
        fail = {a: np.array([[cell[(f, s)][a]['fer'] for s in snrs] for f in keep], np.int8) for a in arms}
        sec = {a: np.array([[cell[(f, s)][a]['seconds'] for s in snrs] for f in keep], float) for a in arms}
        trig = {a: np.array([[bool(cell[(f, s)][a].get('triggered')) for s in snrs] for f in keep], bool) for a in arms}
        out[key] = dict(snr=np.array(snrs) / 100., frames=keep, fail=fail, sec=sec, trig=trig, dropped=dropped,
                        error_frames=errors, arms=arms)
    return out


# ----------------------------------------------------------------------------- bootstrap
def boot_fer(cell, B, rng, chunk=500):
    """{arm: (B + 1, S) FER}; row 0 is the full sample; one shared set of frame-block weights for all arms."""
    n = len(cell['frames'])
    fers = {a: np.empty((B + 1, len(cell['snr']))) for a in cell['arms']}
    mats = {a: cell['fail'][a].astype(float) for a in cell['arms']}
    for a in cell['arms']:
        fers[a][0] = mats[a].mean(0)
    start = 1
    while start <= B:
        c = min(chunk, B + 1 - start)
        W = rng.multinomial(n, np.full(n, 1. / n), size=c).astype(float)
        for a in cell['arms']:
            fers[a][start:start + c] = (W @ mats[a]) / n
        start += c
    return fers


# ----------------------------------------------------------------------------- one cell
def analyze_cell(key, cell, B, rng, timing=None):
    snr = cell['snr']
    n = len(cell['frames'])
    S = len(snr)
    arms = cell['arms']
    res = dict(scenario=key[0], rho=key[1] / 1000., n_frames=n, frames_dropped=cell['dropped'],
               frames_with_arm_errors=cell['error_frames'], snr_db=[float(x) for x in snr], arms=arms)
    res['fer'] = {a: [float(x) for x in cell['fail'][a].mean(0)] for a in arms}
    res['errors'] = {a: [int(x) for x in cell['fail'][a].sum(0)] for a in arms}
    res['triggered_fraction'] = {a: [float(x) for x in cell['trig'][a].mean(0)] for a in arms if cell['trig'][a].any()}
    res['mean_seconds_loaded_run'] = {a: float(cell['sec'][a].mean()) for a in arms}
    if n < 2 or S < 2 or 'F0' not in arms:
        res['label_H1'] = 'NO-DATA'
        return res
    fers = boot_fer(cell, B, rng)
    X, ST = {}, {}
    for a in arms:
        X[a], ST[a] = crossing(fers[a], n, snr)
    res['crossing_1e-2'] = {a: dict(point=jf(X[a][0]), status=STATUS[int(ST[a][0])], ci=[jf(nearest_rank(X[a][1:], .025)), jf(nearest_rank(X[a][1:], .975))],
                                    frac_censored_low=float(np.mean(ST[a][1:] == LOW)), frac_censored_high=float(np.mean(ST[a][1:] == HIGH)))
                            for a in arms}
    # ---------------- H1
    if 'B' in arms:
        f0, b_ = cell['fail']['F0'].astype(bool), cell['fail']['B'].astype(bool)
        fer0 = f0.mean(0)
        elig = (fer0 >= ELIGIBLE[0]) & (fer0 <= ELIGIBLE[1])
        pairs = [dict(snr_db=float(snr[s]), n_f0_wrong_b_right=int((f0[:, s] & ~b_[:, s]).sum()),
                      n_f0_right_b_wrong=int((~f0[:, s] & b_[:, s]).sum()), eligible=bool(elig[s])) for s in range(S)]
        idx = np.flatnonzero(elig)
        pv = np.array([mcnemar_one_sided(pairs[s]['n_f0_wrong_b_right'], pairs[s]['n_f0_right_b_wrong']) for s in idx])
        rej = holm(pv) if len(idx) else np.zeros(0, bool)
        for k, s in enumerate(idx):
            pairs[s].update(p_one_sided=float(pv[k]), holm_reject=bool(rej[k]))
        gain = summarize(diff_gain(X['F0'], ST['F0'], X['B'], ST['B']))
        gain_fav = summarize(diff_gain_fav(X['F0'], ST['F0'], X['B'], ST['B']))
        n_el, n_sig = len(idx), int(rej.sum())
        frac = n_sig / n_el if n_el else None
        if n_el == 0:
            label = 'NO-ELIGIBLE'
        else:
            # protocol 3.3 + I1 (revised after the Codex review): FAIL iff the gain CI includes 0 or is negative even when every
            # censored draw is resolved in B's favour (lower end of diff_gain_fav <= 0); PASS iff the conservative CI (censored
            # draws against B) has lower end > 0 and >= 75% of the eligible points are significant; otherwise INCONCLUSIVE.
            if gain_fav['lo'] <= 0:
                label = 'FAIL'
            elif gain['lo'] > 0:
                label = 'PASS' if frac >= SIG_FRACTION else 'INCONCLUSIVE'
            else:
                label = 'INCONCLUSIVE'
        raw_gain = X['F0'] - X['B']
        res['H1'] = dict(label=label, n_eligible=n_el, n_significant=n_sig, fraction_significant=jf(frac), per_snr=pairs,
                         gain_db=jsum(gain), gain_unclipped_rule='-inf if F0 censored low or B censored high',
                         gain_db_favourable_for_fail=jsum(gain_fav),
                         gain_db_clipped_only=jsum(summarize(raw_gain)), f0_censored_high_point=bool(ST['F0'][0] == HIGH),
                         b_status=STATUS[int(ST['B'][0])],
                         harm_frames_total=int(sum(p['n_f0_right_b_wrong'] for p in pairs)),
                         rescue_frames_total=int(sum(p['n_f0_wrong_b_right'] for p in pairs)))
        res['label_H1'] = label
    # ---------------- H2
    if 'B' in arms and 'A3' in arms:
        gap = summarize(diff_gap(X['B'], ST['B'], X['A3'], ST['A3']))
        res['H2'] = dict(gap_db=jsum(gap), claim_within_0p5=bool(math.isfinite(gap['hi']) and gap['hi'] <= H2_BOUND),
                         rule='+inf if B censored high or A3 censored low', gap_db_clipped_only=jsum(summarize(X['B'] - X['A3'])))
    # ---------------- H3
    if 'B' in arms and 'C' in arms:
        diff = summarize(diff_gap(X['B'], ST['B'], X['C'], ST['C']))
        cond1 = bool(math.isfinite(diff['hi']) and diff['hi'] <= H3_BOUND)
        ratio = None
        if timing is not None:
            tb, tc = timing.get('B'), timing.get('C')
            ratio = None if (tb is None or tc is None or tc == 0) else float(tb / tc)
        if not cond1:
            label3 = 'FAIL'
        elif ratio is None:
            label3 = 'PENDING-TIMING'
        else:
            label3 = 'PASS' if ratio <= H3_RATIO else 'FAIL'
        res['H3'] = dict(label=label3, crossing_diff_B_minus_C_db=jsum(diff), cond1_ci_upper_le_0p1=cond1, quiet_time_ratio_B_over_C=jf(ratio),
                         cond2_ratio_le_0p65=(None if ratio is None else bool(ratio <= H3_RATIO)),
                         crossing_diff_clipped_only=jsum(summarize(X['B'] - X['C'])),
                         loaded_run_time_ratio_B_over_C=float(cell['sec']['B'].mean() / cell['sec']['C'].mean()))
    # ---------------- H4 (report only) and extra reports
    if 'B' in arms and 'LOCAL' in arms:
        bf, lf = cell['fail']['B'].astype(bool), cell['fail']['LOCAL'].astype(bool)
        per = [dict(snr_db=float(snr[s]), n_local_wrong_b_right=int((lf[:, s] & ~bf[:, s]).sum()),
                    n_local_right_b_wrong=int((~lf[:, s] & bf[:, s]).sum())) for s in range(S)]
        for s in range(S):
            per[s]['p_two_sided'] = mcnemar_two_sided(per[s]['n_local_wrong_b_right'], per[s]['n_local_right_b_wrong'])
        res['H4'] = dict(label='REPORT-ONLY', per_snr=per, crossing_diff_LOCAL_minus_B_db=jsum(summarize(diff_plain(X['LOCAL'], ST['LOCAL'], X['B'], ST['B']))))
    extra = {}
    for name, a, b_ in (('F0_minus_A3', 'F0', 'A3'), ('C_minus_A3', 'C', 'A3'), ('D_minus_C', 'D', 'C'), ('D_minus_B', 'D', 'B'), ('D_minus_A3', 'D', 'A3')):
        if a in arms and b_ in arms:
            extra[name] = jsum(summarize(diff_plain(X[a], ST[a], X[b_], ST[b_])))
    res['report_only_crossing_differences_db'] = extra
    return res


# ----------------------------------------------------------------------------- timing hook
def quiet_timing(rows):
    """Quiet-subset mean seconds per (scenario, rho) cell (pooled over SNR and frames) and overall, per arm."""
    acc = {}
    for r in rows:
        key = (r['scenario'], int(r['rho_permille']))
        for a, v in r['arms'].items():
            if v.get('status', 'ok') != 'ok':
                continue
            s = acc.setdefault(key, {}).setdefault(a, [0., 0])
            s[0] += v['seconds']
            s[1] += 1
    out = {k: {a: s[0] / s[1] for a, s in v.items()} for k, v in acc.items()}
    pooled = {}
    for v in acc.values():
        for a, s in v.items():
            p = pooled.setdefault(a, [0., 0])
            p[0] += s[0]
            p[1] += s[1]
    return out, {a: s[0] / s[1] for a, s in pooled.items()}


# ----------------------------------------------------------------------------- driver
def analyze(rows, B=20000, seed=20261015, timing_rows=None):
    cells = build_cells(rows)
    timing, timing_pooled = (None, None) if timing_rows is None else quiet_timing(timing_rows)
    rng = np.random.default_rng(seed)
    results = {}
    for key in sorted(cells):
        results[f'{key[0]}_rho{key[1]}'] = analyze_cell(key, cells[key], B, rng, None if timing is None else timing.get(key))
    labels = {k: v.get('label_H1') for k, v in results.items()}
    present = {(v['scenario'], int(round(v['rho'] * 1000))) for v in results.values()}
    if any(l == 'FAIL' for l in labels.values()):
        overall = 'FAIL'
    elif present != set(CELLS):
        overall = 'INCOMPLETE'
    elif all(l == 'PASS' for l in labels.values()):
        overall = 'PASS'
    else:
        overall = 'INCONCLUSIVE'
    h3 = [v['H3']['label'] for v in results.values() if 'H3' in v]
    h3_overall = 'FAIL' if 'FAIL' in h3 else ('PASS' if h3 and all(l == 'PASS' for l in h3) and len(h3) == 4 else ('PENDING-TIMING' if 'PENDING-TIMING' in h3 else 'INCOMPLETE'))
    h2 = {k: v['H2']['claim_within_0p5'] for k, v in results.items() if 'H2' in v}
    return dict(cells=results, H1_cell_labels=labels, H1_overall=overall, H2_claim_within_0p5=h2, H3_overall=h3_overall,
                quiet_timing=None if timing is None else {f'{k[0]}_rho{k[1]}': v for k, v in timing.items()},
                quiet_timing_pooled=timing_pooled)


def render_md(result):
    L = ['# P1 results (protocol section 3.3)\n', f"H1 overall: **{result['H1_overall']}**; H3 overall: **{result['H3_overall']}**; "
         f"H2 within .5 dB claims: {result['H2_claim_within_0p5']}\n"]
    for name, c in result['cells'].items():
        L.append(f"## {name}  (n = {c['n_frames']} frames, dropped {c['frames_dropped']})\n")
        L.append('| SNR | ' + ' | '.join(c['arms']) + ' |\n|---|' + '---|' * len(c['arms']))
        for i, s in enumerate(c['snr_db']):
            L.append(f'| {s:g} | ' + ' | '.join(f"{c['errors'][a][i]}" for a in c['arms']) + ' |')
        L.append('\n(frame errors per arm)\n')
        if 'H1' in c:
            h = c['H1']
            L.append(f"- H1 **{h['label']}**: {h['n_significant']}/{h['n_eligible']} eligible points Holm-significant; gain @1e-2 = {h['gain_db']['point']} dB "
                     f"[{h['gain_db']['lo']}, {h['gain_db']['hi']}] (F0 censored high: {h['f0_censored_high_point']}); rescues {h['rescue_frames_total']}, harms {h['harm_frames_total']}")
        if 'H2' in c:
            L.append(f"- H2: B - A3 = {c['H2']['gap_db']['point']} dB [{c['H2']['gap_db']['lo']}, {c['H2']['gap_db']['hi']}]; within .5 dB claim: {c['H2']['claim_within_0p5']}")
        if 'H3' in c:
            h = c['H3']
            L.append(f"- H3 **{h['label']}**: B - C = {h['crossing_diff_B_minus_C_db']['point']} dB [{h['crossing_diff_B_minus_C_db']['lo']}, {h['crossing_diff_B_minus_C_db']['hi']}]; "
                     f"quiet time ratio B/C = {h['quiet_time_ratio_B_over_C']}")
        if 'H4' in c:
            L.append(f"- H4 (report only): LOCAL - B = {c['H4']['crossing_diff_LOCAL_minus_B_db']['point']} dB "
                     f"[{c['H4']['crossing_diff_LOCAL_minus_B_db']['lo']}, {c['H4']['crossing_diff_LOCAL_minus_B_db']['hi']}]")
        L.append('')
    return '\n'.join(L) + '\n'


# ----------------------------------------------------------------------------- self test
def synth_rows(scenario, rho_pm, fer_curves, n, rng, snrs=(450, 500, 550, 600, 650, 700, 750, 800), seconds=None):
    """Nested synthetic frames: frame f carries one latent u ~ U(0,1); arm fails at SNR s iff u < p_arm(s)."""
    u = rng.random(n)
    rows = []
    for f in range(n):
        for i, s in enumerate(snrs):
            arms = {}
            for a, curve in fer_curves.items():
                arms[a] = dict(status='ok', fer=int(u[f] < curve[i]), seconds=(seconds or {}).get(a, 0.3), triggered=bool(u[f] < fer_curves['F0'][i]))
            rows.append(dict(scenario=scenario, rho_permille=rho_pm, snr_centi_db=s, frame=f, arms=arms))
    return rows


def loglin(slope, s0, snr):
    return np.minimum(1., 10. ** (-slope * (np.asarray(snr) / 100. - s0)))


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(('PASS ' if cond else 'FAIL ') + name)
        ok &= bool(cond)

    # primitives
    check('mcnemar b=10,c=0 -> 2^-10', abs(mcnemar_one_sided(10, 0) - 2. ** -10) < 1e-15)
    check('mcnemar b=0,c=0 -> 1', mcnemar_one_sided(0, 0) == 1.0)
    check('mcnemar b=5,c=5 -> P(X>=5|10)', abs(mcnemar_one_sided(5, 5) - 0.623046875) < 1e-12)
    check('mcnemar two-sided symmetric', abs(mcnemar_two_sided(10, 0) - 2. ** -9) < 1e-15)
    check('holm all rejected', holm(np.array([.001, .02, .04])).all())
    check('holm none rejected (.02 > .05/3)', not holm(np.array([.02, .03, .04])).any())
    check('holm step-down stops at the first failure', list(holm(np.array([.04, .001, .03]))) == [False, True, False])
    x, st = crossing(np.array([[.1, .001]]), 2000, [5., 7.])
    check('crossing log-linear midpoint = 6.0', abs(x[0] - 6.0) < 1e-12 and st[0] == OK)
    x, st = crossing(np.array([[.1, 0.]]), 2000, [5., 7.])
    exp = 5. + (-2. + 1.) / (math.log10(.5 / 2000) + 1.) * 2.
    check('crossing zero-FER floor 0.5/n', abs(x[0] - exp) < 1e-12 and st[0] == OK)
    x, st = crossing(np.array([[.5, .3, .2]]), 2000, [5., 6., 7.])
    check('crossing censored high', st[0] == HIGH and x[0] == 7.)
    x, st = crossing(np.array([[.005, .001]]), 2000, [5., 6.])
    check('crossing censored low', st[0] == LOW and x[0] == 5.)
    check('gain rule: B censored high -> -inf', diff_gain(np.array([7.]), np.array([OK]), np.array([8.]), np.array([HIGH]))[0] == -np.inf)
    check('gain rule: F0 censored high stays finite (conservative)', np.isfinite(diff_gain(np.array([8.]), np.array([HIGH]), np.array([6.]), np.array([OK]))[0]))
    check('gap rule: B censored high -> +inf', diff_gap(np.array([8.]), np.array([HIGH]), np.array([7.]), np.array([OK]))[0] == np.inf)

    # synthetic end-to-end: four cells -> PASS, FAIL (B == F0), NO-ELIGIBLE (F0 FER > .5 everywhere), PASS
    rng = np.random.default_rng(5)
    snrs = (450, 500, 550, 600, 650, 700, 750, 800)
    grid = np.array(snrs) / 100.
    f0 = np.array([.40, .15, .05, .025, .012, .006, 0., 0.])           # 6 eligible points, 2 error-free (ineligible) tail points
    good = {'F0': f0, 'B': .2 * f0, 'LOCAL': .5 * f0, 'C': .22 * f0, 'D': .16 * f0, 'A3': .14 * f0}
    xt = {a: float(crossing(v[None, :], 10 ** 9, grid)[0][0]) for a, v in good.items()}   # exact-curve crossings
    tied = {a: (f0 if a in ('F0', 'B') else good[a]) for a in good}
    hopeless = {a: np.full(8, .8) for a in good}
    n = 2000
    rows = (synth_rows('U', 300, good, n, rng, seconds={'B': .35, 'C': .7}) + synth_rows('U', 500, tied, n, rng) +
            synth_rows('G', 300, hopeless, n, rng) + synth_rows('G', 500, good, n, rng, seconds={'B': .6, 'C': .7}))
    t_rows = (synth_rows('U', 300, good, 20, rng, seconds={'B': .35, 'C': .7}) + synth_rows('U', 500, good, 20, rng, seconds={'B': .35, 'C': .7}) +
              synth_rows('G', 300, good, 20, rng, seconds={'B': .35, 'C': .7}) + synth_rows('G', 500, good, 20, rng, seconds={'B': .6, 'C': .7}))
    res = analyze(rows, B=2000, seed=1, timing_rows=t_rows)
    labels = res['H1_cell_labels']
    check('cell labels PASS/FAIL/NO-ELIGIBLE/PASS', [labels['U_rho300'], labels['U_rho500'], labels['G_rho300'], labels['G_rho500']] == ['PASS', 'FAIL', 'NO-ELIGIBLE', 'PASS'])
    check('overall H1 = FAIL when any cell FAILs', res['H1_overall'] == 'FAIL')
    g = res['cells']['U_rho300']['H1']['gain_db']
    true_gain = xt['F0'] - xt['B']
    check('gain CI covers the exact-curve gain %.3f dB and excludes 0' % true_gain, g['lo'] < true_gain < g['hi'] and g['lo'] > 0 and abs(g['point'] - true_gain) < .2)
    check('FAIL cell: all McNemar p = 1, zero rescues', all(p.get('p_one_sided', 1.) == 1. for p in res['cells']['U_rho500']['H1']['per_snr'] if p['eligible']) and res['cells']['U_rho500']['H1']['rescue_frames_total'] == 0)
    check('NO-ELIGIBLE cell has zero eligible points', res['cells']['G_rho300']['H1']['n_eligible'] == 0)
    c = res['cells']['U_rho300']
    check('eligible points are exactly the 6 low-SNR points', [p['eligible'] for p in c['H1']['per_snr']] == [True] * 6 + [False] * 2)
    true_gap = xt['B'] - xt['A3']
    check('H2 gap B-A3 ~ %.3f dB, within .5 claim allowed' % true_gap, abs(c['H2']['gap_db']['point'] - true_gap) < .2 and c['H2']['claim_within_0p5'])
    check('H3 U300: B ~ C, ratio .5 -> PASS', c['H3']['label'] == 'PASS' and abs(c['H3']['quiet_time_ratio_B_over_C'] - .5) < 1e-9)
    check('H3 G500: ratio .857 -> FAIL', res['cells']['G_rho500']['H3']['label'] == 'FAIL')
    check('H4 reported', c['H4']['label'] == 'REPORT-ONLY')
    res2 = analyze([r for r in rows if not (r['scenario'] == 'U' and r['rho_permille'] == 500)] +
                   synth_rows('U', 500, good, n, rng), B=500, seed=2)
    check('three PASS + one NO-ELIGIBLE -> INCONCLUSIVE', res2['H1_overall'] == 'INCONCLUSIVE')
    rows3 = (synth_rows('U', 300, good, n, rng) + synth_rows('U', 500, good, n, rng) + synth_rows('G', 300, good, n, rng) + synth_rows('G', 500, good, n, rng))
    res3 = analyze(rows3, B=500, seed=3)
    check('four PASS -> overall PASS, H3 pending without timing', res3['H1_overall'] == 'PASS' and res3['H3_overall'] == 'PENDING-TIMING')
    res4 = analyze(rows3[:len(rows3) // 2], B=300, seed=4)
    check('missing cells -> INCOMPLETE', res4['H1_overall'] == 'INCOMPLETE')
    res4b = analyze(synth_rows('U', 500, tied, n, rng), B=300, seed=41)
    check('missing cells but one FAIL -> overall FAIL', res4b['H1_overall'] == 'FAIL')
    # censored B (never reaches 1e-2): gain claim must not pass
    cens = dict(good, B=np.full(8, .05))
    res5 = analyze(synth_rows('U', 300, cens, n, rng), B=300, seed=5)
    check('B censored high -> cell FAIL (gain lower bound -inf)', res5['cells']['U_rho300']['H1']['label'] == 'FAIL' and res5['cells']['U_rho300']['H2']['claim_within_0p5'] is False)
    # F0 censored high (rho .5-like: F0 never reaches 1e-2 on the grid), B does: finite lower-bound gain
    f0c = dict(good, F0=np.array([.45, .30, .20, .12, .08, .05, .03, .02]))
    res6 = analyze(synth_rows('U', 300, f0c, n, rng), B=500, seed=6)
    h = res6['cells']['U_rho300']['H1']
    check('F0 censored high: finite conservative gain', h['f0_censored_high_point'] and math.isfinite(h['gain_db']['lo']) and h['gain_db']['point'] > 0)
    # positive gain at the target but only 2 of 6 eligible points improved -> INCONCLUSIVE, not FAIL
    part = dict(good, B=np.array([.40, .15, .05, .025, .0024, .0012, 0., 0.]))
    res7 = analyze(synth_rows('U', 300, part, n, rng), B=500, seed=7)
    h7 = res7['cells']['U_rho300']['H1']
    check('gain CI > 0 with < 75%% significant points -> INCONCLUSIVE (n_sig %d / %d)' % (h7['n_significant'], h7['n_eligible']),
          h7['label'] == 'INCONCLUSIVE' and h7['gain_db']['lo'] > 0 and h7['fraction_significant'] < SIG_FRACTION)
    # F0 already below the target at the lowest SNR -> gain unidentified -> INCONCLUSIVE
    low = dict(good, F0=np.array([.008, .004, .002, .001, 0., 0., 0., 0.]), B=np.array([.0016, .0008, .0004, .0002, 0., 0., 0., 0.]))
    res8 = analyze(synth_rows('U', 300, low, n, rng), B=500, seed=8)
    check('F0 and B both censored low -> INCONCLUSIVE', res8['cells']['U_rho300']['H1']['label'] == 'INCONCLUSIVE')
    # F0 censored low, B worse and crossing inside the grid -> gain <= grid start - x_B < 0 -> FAIL (Codex review item 1)
    worse = dict(good, F0=np.array([.008, .004, .002, .001, 0., 0., 0., 0.]), B=np.array([.03, .012, .004, .002, 0., 0., 0., 0.]))
    res9 = analyze(synth_rows('U', 300, worse, n, rng), B=500, seed=9)
    check('F0 censored low, B worse inside the grid -> FAIL', res9['cells']['U_rho300']['H1']['label'] == 'FAIL')
    json.dumps(res, allow_nan=False)
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', nargs='+', type=Path)
    p.add_argument('--timing', nargs='+', type=Path, default=None, help='quiet timing subset run dir(s) (H3 time ratio)')
    p.add_argument('--out', type=Path)
    p.add_argument('--boot', type=int, default=20000)
    p.add_argument('--seed', type=int, default=20261015)
    p.add_argument('--selftest', action='store_true')
    args = p.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if not args.rows or not args.out:
        p.error('--rows and --out are required')
    rows, files = load_rows(args.rows)
    trows, tfiles = (None, []) if args.timing is None else load_rows(args.timing)
    result = analyze(rows, B=args.boot, seed=args.seed, timing_rows=trows)
    args.out.mkdir(parents=True, exist_ok=True)
    payload = dict(_argv=sys.argv[:], _config=dict(
        boot=args.boot, seed=args.seed, target_fer=TARGET, eligible_fer=ELIGIBLE, alpha=ALPHA, significant_fraction=SIG_FRACTION,
        h2_bound_db=H2_BOUND, h3_bound_db=H3_BOUND, h3_time_ratio=H3_RATIO, n_rows=len(rows),
        rows_md5={str(Path(f)): md5_file(f) for f in files}, timing_rows_md5={str(Path(f)): md5_file(f) for f in tfiles},
        p1_agg_md5=md5_file(__file__)), results=result)
    (args.out / 'p1_results.json').write_text(json.dumps(payload, indent=1, allow_nan=False, default=float) + '\n')
    (args.out / 'P1_RESULTS.md').write_text(render_md(result))
    print('H1 overall:', result['H1_overall'], '| cells:', result['H1_cell_labels'], '| H3:', result['H3_overall'])


if __name__ == '__main__':
    main()
