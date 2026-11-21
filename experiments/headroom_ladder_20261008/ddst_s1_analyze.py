#!/usr/bin/env python
"""DDST Stage-1 analysis (research/ddst-small-run-protocol-20261014.md section 5, FROZEN).  Reads rows only; no tuning.

    python -B ddst_s1_analyze.py --dir out/ddst_s1 [--out out/ddst_s1]          analysis of the merged Stage-1 rows (rows_shard*.jsonl[.gz])
    python -B ddst_s1_analyze.py --selftest                                       synthetic check of the Kc machinery and the decision logic
    python -B ddst_s1_analyze.py --schema-check <dir>                              row schema / counts only (any ddst_driver output)
Outputs <out>/ddst_s1_results.json (with _argv, _config incl. seed, md5s) and <out>/RESULTS.md.

Kc method (identical to the IB2 analysis c1ib2_analyze.py): Kc_Rk = first FER_k = .5 crossing, linear in K = 8 L (c1e_predict.k_cross), FER_k = frac(ierr_k > 0)
per cell (200 frames); a crossing outside the L range is CENSORED at the nearest K of the range and flagged (above_range: all FER < .5; below_range: all FER >= .5).
Percentile 95% CI, paired frame bootstrap: B = 2000 resamples of the 200 frame indices, ONE index matrix shared by all arms, all L and both SNR groups
(frames resampled jointly), seed recorded.  Ratios are arm / SPg_flat.
Assessability (rule fixed here, before the run): a ratio is ASSESSABLE iff the point-estimate crossings of both arms are exact (not censored); otherwise it is
"not assessable" and never counts as a pass.  Bootstrap resamples with a censored crossing use the clamped edge value (counted and reported).
Decision (section 5): P1 = primary cell (6.5 dB rho .3), Kc_R10(DDST-A)/Kc_R10(SPg_flat) >= 1.10 and CI lower bound > 1; P2 = replication cell (8 dB rho .3),
ratio >= 1.05 and CI lower bound > 1 ("not assessable" if a crossing is outside the L range).  PASS iff P1 and P2.  ROUND-1-ONLY iff the primary-cell R1 ratio
(DDST-A) is assessable with CI lower bound > 1 but P1 fails.  KILL otherwise (literal rule; the case P1 pass / P2 not pass is not enumerated by the protocol and is
labelled by the literal rule, KILL, with an explicit note).
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

import c1e_predict as E

HERE = Path(__file__).resolve().parent
B, SEED = 2000, 20261014
RMAX = 10
ROUNDS = (1, 4, 10)
P1_BAR, P2_BAR = 1.10, 1.05
ARMS = ('SPg_flat', 'DDST-A', 'DDST-N', 'DDST-A-blind')
BASE = 'SPg_flat'
CELLS = {6.5: [8, 12, 16, 20, 24, 28, 32], 8.0: [16, 20, 24, 28, 32, 36, 40]}
RHO = 0.3
FRAME0, NF = 5000, 200
NEEDED = ('arm', 'status', 'snr_db', 'rho', 'L', 'frame', 'info_errors', 'seconds', 't_cum', 'channel_seed', 'physical_gains_sha256', 'info_sha256',
          'noise_sha256', 'ddst_r', 'ddst_c', 'ddst_phi', 'ddst_f_resid', 'data_power_ratio', 'papr_db', 'papr_pass_gate', 'peak_power', 'eps_ce1', 'll_in1',
          'sec_tx_M', 'sec_tx_eig') + tuple(f'ierr{r}' for r in range(1, RMAX + 1))


def pct(x):
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ Kc machinery (as c1ib2_analyze)
def kc_cens(Ks, ys):
    """(Kc, code): 0 exact crossing; 1 'above range' (all FER < .5, Kc >= max K); 2 'below range' (all FER >= .5, Kc <= min K)."""
    k = E.k_cross(Ks, list(ys), 0.5)
    if k is not None:
        return k, 0
    if all(y < 0.5 for y in ys):
        return float(Ks[-1]), 1
    if all(y >= 0.5 for y in ys):
        return float(Ks[0]), 2
    raise ValueError('no crossing but mixed FER')


CODE = {0: 'exact', 1: 'above_range', 2: 'below_range'}


class Cond:
    """fail[g][arm][L] -> (n, RMAX) 0/1 array of frame errors per round; one frame-index matrix for everything (joint resampling)."""

    def __init__(self, fail, seed=SEED, nboot=B):
        self.fail = fail
        self.n = next(iter(next(iter(next(iter(fail.values())).values())).values())).shape[0]
        self.nboot = nboot
        self.idx = np.random.default_rng(seed).integers(0, self.n, size=(nboot, self.n))
        self._bm, self._est = {}, {}

    def bmean(self, g, arm, L):
        if (g, arm, L) not in self._bm:
            self._bm[(g, arm, L)] = self.fail[g][arm][L][self.idx].mean(axis=1)  # (B, RMAX)
        return self._bm[(g, arm, L)]

    def est(self, g, arm, R):
        key = (g, arm, R)
        if key not in self._est:
            Ls = sorted(self.fail[g][arm])
            Ks = [8 * L for L in Ls]
            fer = [float(self.fail[g][arm][L][:, R - 1].mean()) for L in Ls]
            point, code = kc_cens(Ks, fer)
            M = np.stack([self.bmean(g, arm, L)[:, R - 1] for L in Ls], axis=1)
            bk, bc = np.empty(self.nboot), np.empty(self.nboot, int)
            for b in range(self.nboot):
                bk[b], bc[b] = kc_cens(Ks, M[b])
            lo, hi = pct(bk)
            self._est[key] = dict(group=g, arm=arm, R=R, Ls=Ls, point=point, code=int(code), status=CODE[code], lo=lo, hi=hi, boot=bk, bcode=bc, fer=fer,
                                  boot_status={CODE[c]: int(np.sum(bc == c)) for c in CODE})
        return self._est[key]

    def ratio(self, g, arm, R):
        a, b = self.est(g, arm, R), self.est(g, BASE, R)
        rb = a['boot'] / b['boot']
        lo, hi = pct(rb)
        rat = a['point'] / b['point']
        return dict(group=g, arm=arm, R=R, ratio=rat, lo=lo, hi=hi, assessable=bool(a['code'] == 0 and b['code'] == 0), ci_lo_gt_1=bool(lo > 1.),
                    status=f"{a['status']}/{b['status']}", n_boot_censored=int(np.sum((a['bcode'] != 0) | (b['bcode'] != 0))))


def strip(e):
    return {k: v for k, v in e.items() if k not in ('boot', 'bcode')}


def decide(cond):
    """Mechanical section-5 decision from a Cond with groups 6.5 (primary) and 8.0 (replication) and arms SPg_flat, DDST-A."""
    p1 = cond.ratio(6.5, 'DDST-A', 10)
    p2 = cond.ratio(8.0, 'DDST-A', 10)
    r1 = cond.ratio(6.5, 'DDST-A', 1)
    p1_pass = bool(p1['assessable'] and p1['ratio'] >= P1_BAR and p1['ci_lo_gt_1'])
    if not p2['assessable']:
        p2_state = 'not assessable'
    else:
        p2_state = 'pass' if (p2['ratio'] >= P2_BAR and p2['ci_lo_gt_1']) else 'fail'
    r1_up = bool(r1['assessable'] and r1['ci_lo_gt_1'])
    if p1_pass and p2_state == 'pass':
        label, note = 'PASS', ''
    elif r1_up and not p1_pass:
        label, note = 'ROUND-1-ONLY', ''
    else:
        label = 'KILL'
        note = ('P1 passes but P2 does not (' + p2_state + '): this case is not enumerated by the protocol; the literal rule gives KILL. Flagged for the coordinator.'
                if p1_pass else '')
    return dict(label=label, note=note, P1=dict(ratio=p1['ratio'], lo=p1['lo'], hi=p1['hi'], bar=P1_BAR, assessable=p1['assessable'], status=p1['status'],
                                                 passed=p1_pass),
                P2=dict(ratio=p2['ratio'], lo=p2['lo'], hi=p2['hi'], bar=P2_BAR, assessable=p2['assessable'], status=p2['status'], state=p2_state),
                R1_primary=dict(ratio=r1['ratio'], lo=r1['lo'], hi=r1['hi'], assessable=r1['assessable'], status=r1['status'], ci_lo_gt_1=r1['ci_lo_gt_1'],
                                round1_only_condition=r1_up))


# ------------------------------------------------------------------------------------------------------------------ rows
def load_rows(d):
    files = sorted(glob.glob(str(Path(d) / 'rows_shard*.jsonl'))) + sorted(glob.glob(str(Path(d) / 'rows_shard*.jsonl.gz')))
    if not files:
        raise FileNotFoundError(f'no rows in {d}')
    rows = []
    for f in files:
        op = gzip.open if f.endswith('.gz') else open
        with op(f, 'rt') as stream:
            rows += [json.loads(x) for x in stream if x.strip()]
    return rows, files


def schema_check(rows):
    miss = {}
    for r in rows:
        if r['status'] != 'ok':
            continue
        for k in NEEDED:
            if k not in r:
                miss[k] = miss.get(k, 0) + 1
    return miss


def build_fail(rows, arms, cells=CELLS, frame0=FRAME0, nf=NF):
    """Complete-design check + the per-(group, arm, L) 0/1 failure arrays; pairing check across arms."""
    bad = [r for r in rows if r['status'] != 'ok']
    if bad:
        raise RuntimeError(f"{len(bad)} error rows, first: {bad[0].get('arm')} L{bad[0].get('L')} f{bad[0].get('frame')} {bad[0].get('error')}")
    miss = schema_check(rows)
    if miss:
        raise RuntimeError(f'rows lack fields: {miss}')
    by = {}
    for r in rows:
        key = (round(r['snr_db'], 4), r['L'], r['frame'], r['arm'])
        if key in by:
            raise RuntimeError(f'duplicate row {key}')
        by[key] = r
    frames = list(range(frame0, frame0 + nf))
    fail = {}
    for g, Ls in cells.items():
        fail[g] = {a: {} for a in arms}
        for L in Ls:
            for f in frames:
                ref = None
                for a in arms:
                    r = by.get((round(g, 4), L, f, a))
                    if r is None:
                        raise RuntimeError(f'missing row snr {g} L {L} frame {f} arm {a}')
                    fp = (r['channel_seed'], r['physical_gains_sha256'], r['info_sha256'], r['noise_sha256'])
                    ref = ref or fp
                    if fp != ref:
                        raise RuntimeError(f'pairing broken snr {g} L {L} frame {f} arm {a}')
            for a in arms:
                fail[g][a][L] = np.array([[float(by[(round(g, 4), L, f, a)][f'ierr{k}'] > 0) for k in range(1, RMAX + 1)] for f in frames])
    return fail, by, frames


def fmt_ci(e, d=0):
    return f"{e['point']:.{d}f} [{e['lo']:.{d}f}, {e['hi']:.{d}f}]"


def report_only(by, arms, cells, frames, law, law_prior):
    out = dict(data_power={}, papr={}, seconds={}, tx={}, rank={}, diag={})
    for g, Ls in cells.items():
        for a in arms:
            rs = [by[(round(g, 4), L, f, a)] for L in Ls for f in frames]
            dp = np.array([r['data_power_ratio'] for r in rs])
            pp = np.array([r['papr_db'] for r in rs])
            out['data_power'][f'{g:g}|{a}'] = dict(mean=float(dp.mean()), min=float(dp.min()), max=float(dp.max()), std=float(dp.std()))
            out['papr'][f'{g:g}|{a}'] = dict(mean_db=float(pp.mean()), p95_db=float(np.percentile(pp, 95)), max_db=float(pp.max()),
                                             peak_power_max=float(max(r['peak_power'] for r in rs)), gate_pass_frac=float(np.mean([r['papr_pass_gate'] for r in rs])))
            out['diag'][f'{g:g}|{a}'] = {str(L): dict(eps_ce1=float(np.mean([by[(round(g, 4), L, f, a)]['eps_ce1'] for f in frames])),
                                                      ll_in1=float(np.mean([by[(round(g, 4), L, f, a)]['ll_in1'] for f in frames])))
                                         for L in Ls}
            sec = {}
            for L in Ls:
                rl = [by[(round(g, 4), L, f, a)] for f in frames]
                secs = np.array([r['seconds'] for r in rl])
                med = float(np.median(secs))
                keep = secs <= 5. * med  # rows whose timed window overlapped a SIGSTOP pause of the shard (concurrency management) are excluded from the timing means
                tc = np.array([r['t_cum'] for r in rl])
                per_round = np.diff(np.concatenate([np.zeros((len(rl), 1)), tc], axis=1), axis=1)[keep]
                sec[str(L)] = dict(total=float(np.mean(secs[keep])), median=med, n_outliers=int((~keep).sum()), per_round=per_round.mean(axis=0).tolist(),
                                   round1=float(per_round[:, 0].mean()), later_rounds=float(per_round[:, 1:].mean()))
            out['seconds'][f'{g:g}|{a}'] = sec
    for g, Ls in cells.items():
        out['rank'][f'{g:g}'] = {str(L): dict(r_genie=int(by[(round(g, 4), L, frames[0], 'DDST-A')]['ddst_r']),
                                             r_blind=int(by[(round(g, 4), L, frames[0], 'DDST-A-blind')]['ddst_r']) if 'DDST-A-blind' in arms else None,
                                             phi_genie_mean=float(np.mean([by[(round(g, 4), L, f, 'DDST-A')]['ddst_phi'] for f in frames])),
                                             phi_blind_mean=float(np.mean([by[(round(g, 4), L, f, 'DDST-A-blind')]['ddst_phi'] for f in frames])) if 'DDST-A-blind' in arms else None)
                                for L in Ls}
    tot = sum(v['total'] * (NF - v['n_outliers']) for sec in out['seconds'].values() for v in sec.values())  # outlier-free sum of row seconds (pauses excluded)
    tx_blocks = {}
    for g, Ls in cells.items():
        for L in Ls:
            for f in frames:
                r = by[(round(g, 4), L, f, 'DDST-A')]
                tx_blocks[(L, f)] = r['sec_tx_M'] + r['sec_tx_eig']  # computed once per (frame, L), shared by both cells containing L
    out['core_seconds_receiver'] = float(tot)
    out['core_seconds_tx'] = float(sum(tx_blocks.values()))
    gl = {}
    for g in cells:
        row = next(x for x in law['groups'] if abs(x['snr_db'] - g) < 1e-9 and abs(x['rho'] - RHO) < 1e-9)
        rp = next(x for x in law_prior['groups'] if abs(x['snr_db'] - g) < 1e-9 and abs(x['rho'] - RHO) < 1e-9) if law_prior else None
        gl[f'{g:g}'] = dict(screen_g_R=row['g_R'], screen_Kc_base=row['Kc_base'], screen_Kc_R=row['Kc_R'], prior_g_R=None if rp is None else rp['g_R'])
    out['screen'] = gl
    return out


def analyze(fail, by, frames, arms, law, law_prior):
    cond = Cond(fail)
    res = dict(estimates={}, ratios={})
    for g in fail:
        for a in arms:
            for R in ROUNDS:
                res['estimates'][f'{g:g}|{a}|R{R}'] = strip(cond.est(g, a, R))
                if a != BASE:
                    res['ratios'][f'{g:g}|{a}|R{R}'] = cond.ratio(g, a, R)
    res['decision'] = decide(cond)
    if by is not None:
        res['report_only'] = report_only(by, arms, CELLS, frames, law, law_prior)
        # measured R1 gain / screen bound (bound looseness)
        loose = {}
        for g in CELLS:
            sc = res['report_only']['screen'][f'{g:g}']
            for a, ref in (('DDST-A', sc['screen_g_R']), ('DDST-A-blind', sc['prior_g_R'])):
                if a in arms and ref:
                    m = res['ratios'][f'{g:g}|{a}|R1']
                    loose[f'{g:g}|{a}'] = dict(measured_R1_ratio=m['ratio'], ci=[m['lo'], m['hi']], bound_g_R=ref, measured_over_bound=m['ratio'] / ref,
                                              gain_fraction=(m['ratio'] - 1.) / (ref - 1.), assessable=m['assessable'])
        res['report_only']['bound_looseness'] = loose
    return res


def write_md(res, arms, path):
    f3 = lambda x: f'{x:.3f}'
    L = ['# DDST Stage 1 results', '',
         'Protocol: `.trellis/tasks/10-08-doppler-cluster/research/ddst-small-run-protocol-20261014.md` (frozen). Analysis: `experiments/headroom_ladder_20261008/ddst_s1_analyze.py`.',
         f'Kc = FER_k = .5 crossing, linear in K = 8L; CI = percentile, paired frame bootstrap (B = {B}, seed {SEED}, frames resampled jointly across L, arms and SNR groups); '
         'a crossing outside the L range is censored at the range edge and the ratio is "not assessable".', '']
    d = res['decision']
    L += ['## Decision (mechanical)', '',
          f"**{d['label']}**" + (f" -- {d['note']}" if d['note'] else ''), '',
          f"- P1 (6.5 dB rho .3, R10, DDST-A/SPg_flat): {f3(d['P1']['ratio'])} [{f3(d['P1']['lo'])}, {f3(d['P1']['hi'])}], bar >= {d['P1']['bar']}, CI lower bound > 1 needed, "
          f"assessable {d['P1']['assessable']} ({d['P1']['status']}) -> {'pass' if d['P1']['passed'] else 'fail'}",
          f"- P2 (8 dB rho .3, R10): {f3(d['P2']['ratio'])} [{f3(d['P2']['lo'])}, {f3(d['P2']['hi'])}], bar >= {d['P2']['bar']}, assessable {d['P2']['assessable']} "
          f"({d['P2']['status']}) -> {d['P2']['state']}",
          f"- R1 primary (6.5 dB, DDST-A): {f3(d['R1_primary']['ratio'])} [{f3(d['R1_primary']['lo'])}, {f3(d['R1_primary']['hi'])}], assessable {d['R1_primary']['assessable']} "
          f"({d['R1_primary']['status']}), CI lower bound > 1: {d['R1_primary']['ci_lo_gt_1']}", '']
    for g in sorted({float(k.split('|')[0]) for k in res['estimates']}):
        L += [f'## {g:g} dB, rho .3 ({"primary" if g == 6.5 else "replication"})', '',
              '| round | arm | Kc [95% CI] | status | ratio vs SPg_flat [95% CI] | ratio status |', '|---|---|---|---|---|---|']
        for R in ROUNDS:
            for a in arms:
                e = res['estimates'][f'{g:g}|{a}|R{R}']
                if a == BASE:
                    L.append(f"| R{R} | {a} | {e['point']:.1f} [{e['lo']:.1f}, {e['hi']:.1f}] | {e['status']} | - | - |")
                else:
                    r = res['ratios'][f'{g:g}|{a}|R{R}']
                    L.append(f"| R{R} | {a} | {e['point']:.1f} [{e['lo']:.1f}, {e['hi']:.1f}] | {e['status']} | {f3(r['ratio'])} [{f3(r['lo'])}, {f3(r['hi'])}] | "
                             f"{'assessable' if r['assessable'] else 'NOT ASSESSABLE'} ({r['status']}) |")
        L.append('')
        Ls = res['estimates'][f'{g:g}|{BASE}|R1']['Ls']
        L += ['FER by L (frac ierr_k > 0):', '', '| round | arm | ' + ' | '.join(f'L{x}' for x in Ls) + ' |', '|---|---|' + '---|' * len(Ls)]
        for R in ROUNDS:
            for a in arms:
                e = res['estimates'][f'{g:g}|{a}|R{R}']
                L.append(f'| R{R} | {a} | ' + ' | '.join(f'{x:.3f}' for x in e['fer']) + ' |')
        L.append('')
    ro = res.get('report_only')
    if ro:
        L += ['## Report-only', '', '### Measured R1 gain vs the zero-simulation bound', '',
              '| cell | arm | measured R1 ratio [95% CI] | bound g_R | measured / bound | (ratio-1)/(g_R-1) |', '|---|---|---|---|---|---|']
        for k, v in ro['bound_looseness'].items():
            L.append(f"| {k.split('|')[0]} dB | {k.split('|')[1]} | {f3(v['measured_R1_ratio'])} [{f3(v['ci'][0])}, {f3(v['ci'][1])}] | {f3(v['bound_g_R'])} | "
                     f"{f3(v['measured_over_bound'])} | {f3(v['gain_fraction'])} |")
        L += ['', '### Realised data power (ratio to nominal) and PAPR', '', '| cell | arm | data power mean [min, max] | PAPR mean / p95 / max dB | peak power max | gate pass |', '|---|---|---|---|---|---|']
        for k in ro['data_power']:
            dp, pp = ro['data_power'][k], ro['papr'][k]
            L.append(f"| {k.split('|')[0]} dB | {k.split('|')[1]} | {dp['mean']:.4f} [{dp['min']:.4f}, {dp['max']:.4f}] | {pp['mean_db']:.2f} / {pp['p95_db']:.2f} / {pp['max_db']:.2f} | "
                     f"{pp['peak_power_max']:.2f} | {pp['gate_pass_frac']:.3f} |")
        L += ['', f"Receiver wall-seconds in the run (sum of row seconds, pause outliers excluded; the shards ran 20-40 concurrently, so these are contended times): {ro['core_seconds_receiver']:.0f} ({ro['core_seconds_receiver'] / 3600:.2f} core-hours); "
              f"Tx side (M + eigh, once per frame and L): {ro['core_seconds_tx']:.0f} s.", '']
        for g in CELLS:
            L += [f'### Receiver seconds, {g:g} dB (mean per frame; in brackets: mean per round over rounds 2-10 / round 1)', '',
                  '| arm | ' + ' | '.join(f'L{x}' for x in CELLS[g]) + ' |', '|---|' + '---|' * len(CELLS[g])]
            for a in arms:
                sec = ro['seconds'][f'{g:g}|{a}']
                L.append(f'| {a} | ' + ' | '.join(f"{sec[str(x)]['total']:.2f} ({sec[str(x)]['later_rounds']:.2f}/{sec[str(x)]['round1']:.2f})" for x in CELLS[g]) + ' |')
            L.append('')
        L += ['### Rank and receiver s2 factor', '', '| cell | L | r genie | r blind | mean phi genie | mean phi blind |', '|---|---|---|---|---|---|']
        for g, d2 in ro['rank'].items():
            for Ls_, v in d2.items():
                L.append(f"| {g} dB | {Ls_} | {v['r_genie']} | {v['r_blind']} | {v['phi_genie_mean']:.3f} | " + (f"{v['phi_blind_mean']:.3f}" if v['phi_blind_mean'] is not None else '-') + ' |')
        L.append('')
        for g in CELLS:
            L += [f'### Round-1 diagnostics, {g:g} dB (mean over frames: eps_ce1 / ll_in1)', '', '| arm | ' + ' | '.join(f'L{x}' for x in CELLS[g]) + ' |', '|---|' + '---|' * len(CELLS[g])]
            for a in arms:
                dg = ro['diag'][f'{g:g}|{a}']
                L.append(f'| {a} | ' + ' | '.join(f"{dg[str(x)]['eps_ce1']:.3f} / {dg[str(x)]['ll_in1']:.3f}" for x in CELLS[g]) + ' |')
            L.append('')
    Path(path).write_text('\n'.join(L) + '\n')


# ---------------------------------------------------------------------------------------------------------------- selftest
def synth_fail(kc_mult, seed=7, n=NF):
    """Synthetic nested frame errors: round-k failure iff u < sigmoid((K - Kc_k)/w) with shared u per (frame, L); Kc_k = base * mult for the arm."""
    base_kc = {6.5: {1: 76., 4: 168., 10: 180.}, 8.0: {1: 120., 4: 230., 10: 250.}}
    rng = np.random.default_rng(seed)
    fail = {}
    for g, Ls in CELLS.items():
        fail[g] = {}
        u = {L: rng.random(n) for L in Ls}
        for a, mults in kc_mult.items():
            fail[g][a] = {}
            for L in Ls:
                arr = np.zeros((n, RMAX))
                for k in range(1, RMAX + 1):
                    ref = base_kc[g][1] if k == 1 else base_kc[g][4] if k <= 4 else base_kc[g][10]
                    kc = ref * mults.get(k if k in (1, 4, 10) else (4 if k <= 4 else 10), 1.)
                    arr[:, k - 1] = u[L] < 1. / (1. + np.exp(-(8 * L - kc) / 12.))
                # nested: success is absorbing
                arr = np.minimum.accumulate(arr, axis=1)
                fail[g][a][L] = arr
    return fail


def selftest():
    one = {1: 1., 4: 1., 10: 1.}
    cases = {
        'PASS': ({BASE: one, 'DDST-A': {1: 1.25, 4: 1.2, 10: 1.2}}, 'PASS'),
        'ROUND-1-ONLY': ({BASE: one, 'DDST-A': {1: 1.25, 4: 1.0, 10: 1.0}}, 'ROUND-1-ONLY'),
        'KILL (no effect)': ({BASE: one, 'DDST-A': one}, 'KILL'),
        'KILL (worse)': ({BASE: one, 'DDST-A': {1: .8, 4: .9, 10: .9}}, 'KILL'),
    }
    ok = True
    for name, (mult, want) in cases.items():
        fail = synth_fail(mult)
        d = decide(Cond(fail, nboot=400))
        print(f"selftest {name}: {d['label']}  P1 {d['P1']['ratio']:.3f}/{d['P1']['lo']:.3f} P2 {d['P2']['ratio']:.3f} ({d['P2']['state']}) R1 {d['R1_primary']['ratio']:.3f}", flush=True)
        if want is not None and d['label'] != want:
            ok = False
            print('  MISMATCH expected', want)
    # out-of-range replication: DDST pushes the 8 dB R10 crossing beyond L40
    fail = synth_fail({BASE: one, 'DDST-A': {1: 1.2, 4: 1.2, 10: 1.35}})
    d = decide(Cond(fail, nboot=400))
    print('selftest out-of-range:', d['label'], d['P1']['passed'], d['P2'], d['note'])
    ok &= d['P2']['state'] == 'not assessable' and d['label'] == 'KILL' and bool(d['note'])
    # known crossing: FER ramp .5 at L = 20 (slope .02 per L) -> Kc 160 exactly
    ramp = {L: np.array([[1. if i < NF * (0.5 + 0.02 * (L - 20)) else 0.] * RMAX for i in range(NF)]) for L in CELLS[6.5]}
    c = Cond({6.5: {BASE: ramp}}, nboot=50)
    e = c.est(6.5, BASE, 10)
    print('selftest crossing:', e['point'], e['status'])
    ok &= abs(e['point'] - 160.) < 1e-6 and e['status'] == 'exact'
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--dir', type=Path, default=HERE / 'out' / 'ddst_s1')
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--law', type=Path, default=HERE / 'out' / 'ddst_screen' / 'law.json')
    ap.add_argument('--law-prior', type=Path, default=HERE / 'out' / 'ddst_s0' / 'law_prior.json')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--schema-check', type=Path, default=None)
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if args.schema_check:
        rows, files = load_rows(args.schema_check)
        miss = schema_check(rows)
        print(f'{len(rows)} rows in {len(files)} files; error rows {sum(r["status"] != "ok" for r in rows)}; missing fields {miss or "none"}')
        sys.exit(1 if miss else 0)
    out = (args.out or args.dir)
    rows, files = load_rows(args.dir)
    arms = [a for a in ARMS if any(r['arm'] == a for r in rows)]
    if set(arms) != set(ARMS):
        raise RuntimeError(f'expected all four arms, found {arms}')
    fail, by, frames = build_fail(rows, arms)
    law = json.loads(args.law.read_text())
    law_prior = json.loads(args.law_prior.read_text())
    res = analyze(fail, by, frames, arms, law, law_prior)
    res['_argv'] = sys.argv
    res['_config'] = dict(B=B, seed=SEED, rounds=ROUNDS, bars=dict(P1=P1_BAR, P2=P2_BAR), cells=CELLS, frames=[frames[0], frames[-1]], n_rows=len(rows),
                          rows_files=[str(Path(f).name) for f in files], rows_files_md5={Path(f).name: md5_file(f) for f in files},
                          law_md5=md5_file(args.law), law_prior_md5=md5_file(args.law_prior), code_md5={n: md5_file(HERE / n) for n in ('ddst_s1_analyze.py', 'c1e_predict.py')},
                          kc_method='c1ib2_analyze.kc_cens (E.k_cross, censored at range edge), FER_k = frac(ierr_k > 0)')
    (out / 'ddst_s1_results.json').write_text(json.dumps(res, indent=1, default=float, allow_nan=False) + '\n')
    write_md(res, arms, out / 'RESULTS.md')
    print((out / 'RESULTS.md').read_text())


if __name__ == '__main__':
    main()
