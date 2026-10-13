#!/usr/bin/env python
"""T0 exploratory screen of EXISTING per-frame C1 rows (task 10-08-doppler-cluster; research/c1-scalar-closure.md, T-1 / T0).
No new simulation, read-only on rows (streamed line by line).  Descriptive only: a SCREEN, not a bistability test.

Inputs : out/c1_boot rows (8/11 dB; rho .2/.3/.5; L 4..32; arms A3, SPg_flat, SPg_slep, SPg_flat03)
         out/c1_map  rows (rho .3; 5/6.5 dB; L 2..32; arms A3, SPg_flat)
Outputs: <out-dir>/T0_SCREEN.md, t0_screen.json, t0_maps.png, t0_hist.png

Definitions (physical units; N = 1024, sigma2 = 10^(-SNR/10), s = (sigma2 + 1 - rho)/(rho N), K = 8 L)
  r1 correct       = (r1_cerr == 0)               (round-1 decision, TRUE coded errors)
  final success    = (info_errors == 0)
  syndrome-zero-but-wrong: (r1_syn == 0 & r1_cerr > 0); (syndrome == 0 & info_errors > 0) [also vs coded_errors > 0 in json]
  old definitions : decode_ok = (final syndrome == 0).  c1_analyze / c1_map_analyze FER = info_errors > 0 (checked in source);
                    here the syndrome-based FER_syn = 1 - mean(decode_ok) is reported next to it.
  eps_pred         = K s / (1 + K s)   (predicted first-pass error, compare with eps_ce1)
  K*               = b / ((1 - b) s), b = (1 - rho)/1.37 - sigma2   (old cliff proxy, g = 1.37)
  bimodality       = Sarle's coefficient BC = (skew^2 + 1)/(excess kurt + 3 (n-1)^2/((n-2)(n-3))) of log10 eps_det2 (BC > 5/9 is the
                     conventional 'possibly bimodal' mark), plus valley/peak ratio of the 3-tap [1,2,1]/4 smoothed 30-bin histogram on
                     log10 eps_det2 in [-3, 0]: highest peak p1, second peak p2 = highest local maximum >= 3 bins away,
                     ratio = min(smoothed between) / min(p1, p2).  Screen flag: ratio < .5 and p2 >= 2% of in-range frames per bin.
  maps             = ~8 equal-count bins on x, conditional medians of y (bins with < 5 samples in a group: median omitted).
usage: c1_t0_screen.py --boot-dir D --map-dir D --out-dir D [--boot-md5 F --map-md5 F]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

N = 1024
G_OLD = 1.37
QS = (10, 25, 50, 75, 90)
STAGES = ('eps_ce1', 'eps_det1', 'eps_ce2', 'eps_det2')
FIELDS = ('info_errors', 'coded_errors', 'syndrome', 'decode_ok', 'r1_cerr', 'r1_syn', 'r1_ll_in', 'r1_ll_app', 'e_real') + STAGES
SP_ARMS = ('SPg_flat', 'SPg_slep', 'SPg_flat03')
PRIMARY = 'SPg_flat'
NBINS = 8
MIN_N = 5
HIST_EDGES = np.linspace(-3., 0., 31)
CLIFF_BAND = (0.5, 1.5)
MAP_BAND = (0.7, 1.3)


# ------------------------------------------------------------------------------------------------ helpers
def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def verify_md5(dirpath, md5file):
    if md5file is None:
        return 'unchecked'
    want = {}
    for line in open(md5file):
        p = line.split()
        if len(p) == 2:
            want[p[1]] = p[0]
    files = sorted(Path(dirpath).glob('rows_shard*.jsonl'))
    bad = [f.name for f in files if want.get(f.name) != md5(f)]
    if bad or len(files) != len(want):
        print(f'MD5 MISMATCH in {dirpath}: {len(bad)} bad of {len(files)} files (expected {len(want)}): {bad[:5]}', flush=True)
        sys.exit(2)
    return f'OK {len(files)} files'


def kstar(g, rho, s2):
    s = (s2 + 1 - rho) / (rho * N)
    b = (1 - rho) / g - s2
    if b <= 0:
        return 0.
    if b >= 1:
        return math.inf
    return b / ((1 - b) * s)


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (float, np.floating)):
        o = float(o)
        return None if math.isnan(o) else ('+inf' if o == math.inf else '-inf' if o == -math.inf else o)
    return o


def fmt(x, p=3):
    if x is None:
        return '-'
    if isinstance(x, (bool, np.bool_)):
        return str(bool(x))
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    x = float(x)
    if math.isnan(x):
        return 'nan'
    if math.isinf(x):
        return 'inf' if x > 0 else '-inf'
    return f'{x:.{p}g}'


def tab(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '|'.join(['---'] * len(head)) + '|']
                     + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])


def spearman(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3:
        return None
    rx, ry = np.argsort(np.argsort(x[ok])).astype(float), np.argsort(np.argsort(y[ok])).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


def med(x):
    return float(np.median(x)) if len(x) else None


def quantiles(x):
    x = x[np.isfinite(x)]
    return {str(q): (float(np.percentile(x, q)) if len(x) else None) for q in QS} | {'n': int(len(x))}


# ------------------------------------------------------------------------------------------------ loading
def load(dirpath):
    """Stream rows; return ({(arm, snr_centi, rho_permille, L): {field: array sorted by frame}}, stats)."""
    cells = collections.defaultdict(list)
    seen, n_rows, n_err, dup = set(), 0, 0, 0
    for f in sorted(Path(dirpath).glob('rows_shard*.jsonl')):
        with open(f) as s:
            for line in s:
                if not line.strip():
                    continue
                r = json.loads(line)
                n_rows += 1
                if r['status'] != 'ok':
                    n_err += 1
                    continue
                key = (r['arm'], r['snr_centi_db'], r['rho_permille'], r['L'], r['frame'])
                if key in seen:
                    dup += 1
                    continue
                seen.add(key)
                vals = []
                for k in FIELDS:
                    v = r.get(k)
                    vals.append(float('nan') if v is None else float(v))
                cells[key[:4]].append((r['frame'], *vals))
    out = {}
    for key, rows in cells.items():
        a = np.array(sorted(rows), float)
        d = {'frame': a[:, 0].astype(int)}
        for i, k in enumerate(FIELDS):
            d[k] = a[:, 1 + i]
        out[key] = d
    return out, dict(rows_total=n_rows, rows_error=n_err, rows_dup=dup, rows_ok=len(seen))


# ------------------------------------------------------------------------------------------------ statistics
def sarle_bc(x):
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 4 or np.std(x) == 0:
        return None
    z = x - x.mean()
    m2, m3, m4 = np.mean(z**2), np.mean(z**3), np.mean(z**4)
    skew, exk = m3 / m2**1.5, m4 / m2**2 - 3.
    return float((skew**2 + 1.) / (exk + 3. * (n - 1)**2 / ((n - 2) * (n - 3))))


def valley_peak(counts):
    c = np.asarray(counts, float)
    n = c.sum()
    if n <= 0:
        return None
    p = np.pad(c, 1, mode='edge')
    sm = (p[:-2] + 2 * p[1:-1] + p[2:]) / 4.
    i1 = int(np.argmax(sm))
    best = None
    for j in range(len(sm)):
        if abs(j - i1) < 3 or sm[j] <= 0:
            continue
        if sm[j] >= (sm[j - 1] if j > 0 else -1) and sm[j] >= (sm[j + 1] if j < len(sm) - 1 else -1):
            if best is None or sm[j] > sm[best]:
                best = j
    if best is None:
        return dict(ratio=None, peak1_bin=i1, peak2_bin=None, peak1_frac=float(sm[i1] / n), peak2_frac=None, flag=False)
    lo, hi = sorted((i1, best))
    ratio = float(sm[lo:hi + 1].min() / min(sm[i1], sm[best]))
    p2 = float(sm[best] / n)
    return dict(ratio=ratio, peak1_bin=i1, peak2_bin=int(best), peak1_frac=float(sm[i1] / n), peak2_frac=p2, flag=bool(ratio < .5 and p2 >= .02))


def hist_log10(eps):
    lx = np.log10(np.clip(eps[np.isfinite(eps)], 1e-300, None))
    cnt, _ = np.histogram(lx[(lx >= -3.) & (lx <= 0.)], bins=HIST_EDGES)
    return dict(counts=cnt.tolist(), under=int((lx < -3.).sum()), over=int((lx > 0.).sum()), n=int(len(lx)), BC=sarle_bc(lx),
                valley_peak=valley_peak(cnt), edges_log10=HIST_EDGES.tolist())


def binned_map(x, y, groups, nb=NBINS):
    """Equal-count bins on x (edges from all finite points); per group: n, median x, median/q25/q75 y."""
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 2 * nb:
        return None
    edges = np.unique(np.quantile(x[ok], np.linspace(0, 1, nb + 1)))
    if len(edges) < 2:
        return None
    idx = np.clip(np.searchsorted(edges, x, side='right') - 1, 0, len(edges) - 2)
    bins = []
    for b in range(len(edges) - 1):
        rec = {}
        for g, gm in groups.items():
            m = ok & (idx == b) & gm
            k = int(m.sum())
            rec[g] = dict(n=k, x_med=med(x[m]) if k else None,
                          y_med=med(y[m]) if k >= MIN_N else None,
                          y_q25=float(np.percentile(y[m], 25)) if k >= MIN_N else None,
                          y_q75=float(np.percentile(y[m], 75)) if k >= MIN_N else None)
        bins.append(rec)
    return dict(edges=edges.tolist(), bins=bins)


def maps_of(d):
    r1c = d['r1_cerr'] == 0
    allm = np.ones(len(r1c), bool)
    return dict(
        ce1_det1=binned_map(d['eps_ce1'], d['eps_det1'], {'all': allm}),
        det1_ce2=binned_map(d['eps_det1'], d['eps_ce2'], {'r1_correct': r1c, 'r1_fail': ~r1c}),
        det1_det2=binned_map(d['eps_det1'], d['eps_det2'], {'all': allm, 'r1_correct': r1c, 'r1_fail': ~r1c}))


# ------------------------------------------------------------------------------------------------ cell analyses
def analyse_a3(d):
    n = len(d['frame'])
    return dict(n=n, mean_r1_ll_in=float(np.mean(d['r1_ll_in'])), mean_r1_ll_app=float(np.mean(d['r1_ll_app'])),
                fer_final=float(np.mean(d['info_errors'] > 0)), fer_r1=float(np.mean(d['r1_cerr'] > 0)),
                n_fail_final=int(np.sum(d['info_errors'] > 0)), n_fail_r1=int(np.sum(d['r1_cerr'] > 0)),
                n_nan=int(np.sum(~np.isfinite(d['r1_ll_in']) | ~np.isfinite(d['r1_ll_app']))))


def analyse_sp(d, a3, snr_c, rho_pm, L, arm):
    n = len(d['frame'])
    rho, s2, K = rho_pm / 1000., 10 ** (-snr_c / 1000.), 8 * L
    s = (s2 + 1 - rho) / (rho * N)
    ks = kstar(G_OLD, rho, s2)
    ratio = (K / ks if ks > 0 else math.inf) if math.isfinite(ks) else 0.
    r1c, fs = d['r1_cerr'] == 0, d['info_errors'] == 0
    dok = d['decode_ok'] == 1
    rec = dict(arm=arm, snr_db=snr_c / 100., rho=rho, L=int(L), K=int(K), sigma2=s2, s=s, kstar_g137=ks, K_over_kstar=ratio,
               near_cliff=bool(CLIFF_BAND[0] <= ratio <= CLIFF_BAND[1]), eps_pred_first_pass=K * s / (1 + K * s), n=n)
    rec['outcomes'] = dict(
        n_r1c_fs=int(np.sum(r1c & fs)), n_r1f_fs_rescued=int(np.sum(~r1c & fs)), n_r1c_ff_regression=int(np.sum(r1c & ~fs)),
        n_r1f_ff=int(np.sum(~r1c & ~fs)), fer_final=float(np.mean(~fs)), fer_r1=float(np.mean(~r1c)),
        n_syn0_wrong_r1=int(np.sum((d['r1_syn'] == 0) & (d['r1_cerr'] > 0))),
        n_syn0_wrong_final=int(np.sum((d['syndrome'] == 0) & (d['info_errors'] > 0))),
        n_syn0_wrong_final_coded=int(np.sum((d['syndrome'] == 0) & (d['coded_errors'] > 0))),
        n_r1_syn0=int(np.sum(d['r1_syn'] == 0)), n_final_syn0=int(np.sum(dok)),
        fer_syndrome_def=float(np.mean(~dok)), n_decode_ok_but_info_err=int(np.sum(dok & ~fs)),
        n_not_decode_ok_but_info_ok=int(np.sum(~dok & fs)),
        n_nan_stage=int(np.sum(~np.isfinite(d['eps_ce1']) | ~np.isfinite(d['eps_det1']) | ~np.isfinite(d['eps_ce2']) | ~np.isfinite(d['eps_det2']))))
    q = {}
    for st in STAGES:
        x = d[st]
        q[st] = dict(overall=quantiles(x), final_success=quantiles(x[fs]), final_fail=quantiles(x[~fs]),
                     r1_correct=quantiles(x[r1c]), r1_fail=quantiles(x[~r1c]))
    rec['quantiles'] = q
    rec['maps'] = maps_of(d)
    rec['hist_log10_eps_det2'] = hist_log10(d['eps_det2'])
    # strata: realised energy tertiles, A3 outcome (paired by frame)
    st = {}
    e = d['e_real']
    t1, t2 = np.percentile(e, [100 / 3., 200 / 3.])
    for name, m in (('E_lo', e <= t1), ('E_mid', (e > t1) & (e <= t2)), ('E_hi', e > t2)):
        st[name] = dict(n=int(m.sum()), e_min=float(e[m].min()) if m.any() else None, e_max=float(e[m].max()) if m.any() else None,
                        sp_fer=float(np.mean(~fs[m])) if m.any() else None, med_eps_det1=med(d['eps_det1'][m]),
                        med_eps_ce1=med(d['eps_ce1'][m]))
    if a3 is not None:
        _, i_sp, i_a3 = np.intersect1d(d['frame'], a3['frame'], return_indices=True)
        a3_ok = a3['info_errors'][i_a3] == 0
        sp_ok = fs[i_sp]
        for name, m in (('A3_ok', a3_ok), ('A3_fail', ~a3_ok)):
            st[name] = dict(n=int(m.sum()), n_paired=int(len(i_sp)), sp_fer=float(np.mean(~sp_ok[m])) if m.any() else None,
                            med_eps_det1=med(d['eps_det1'][i_sp][m]), med_eps_ce1=med(d['eps_ce1'][i_sp][m]))
    rec['strata'] = st
    e_ = d['e_real']
    rec['energy_confound'] = dict(
        spearman_E_ce1=spearman(e_, d['eps_ce1']), spearman_E_det1=spearman(e_, d['eps_det1']), spearman_E_fail=spearman(e_, (~fs).astype(float)),
        med_rel_ce1_success=med((d['eps_ce1'] / e_)[fs]), med_rel_ce1_fail=med((d['eps_ce1'] / e_)[~fs]),
        med_rel_det1_success=med((d['eps_det1'] / e_)[fs]), med_rel_det1_fail=med((d['eps_det1'] / e_)[~fs]),
        med_E_success=med(e_[fs]), med_E_fail=med(e_[~fs]))
    if a3 is not None:
        rec['a3'] = analyse_a3(a3)
    return rec


def pooled(cells, arm, snr, rho):
    keys = sorted(k for k in cells if k[0] == arm and k[1] == snr and k[2] == rho)
    if not keys:
        return None
    d = {f: np.concatenate([cells[k][f] for k in keys]) for f in FIELDS}
    out = maps_of(d)
    out['Ls'] = [k[3] for k in keys]
    out['n'] = int(len(d['eps_ce1']))
    return out


# ------------------------------------------------------------------------------------------------ report
def sf(rec, st):
    q = rec['quantiles'][st]
    return [f"{fmt(q['overall']['50'])} [{fmt(q['overall']['10'])}, {fmt(q['overall']['90'])}]",
            f"{fmt(q['final_success']['50'])} / {fmt(q['final_fail']['50'])}"]


def dataset_md(name, ds):
    recs = [r for r in ds['cells'] if r['arm'] == PRIMARY]
    md = [f'## Dataset {name}  ({PRIMARY}; cells with K/K* in [{CLIFF_BAND[0]}, {CLIFF_BAND[1]}] shown; json has all {len(recs)} cells)\n']
    st = ds['stats']
    md.append(f"rows total {st['rows_total']}, ok {st['rows_ok']}, error {st['rows_error']}, dup {st['rows_dup']}; MD5 {ds['md5_check']}; "
              f"rows per arm {ds['rows_per_arm']}.\n")
    near = [r for r in recs if r['near_cliff']]
    if not near:
        md.append('(no near-cliff cells)\n')
        return md
    key = lambda r: (r['snr_db'], r['rho'], r['L'])
    near.sort(key=key)
    head = lambda r: [fmt(r['snr_db']), fmt(r['rho']), r['L'], fmt(r['K_over_kstar'], 2)]
    md.append('### (a) outcomes (r1 correct = r1_cerr == 0; final success = info_errors == 0; FER_syn = 1 - mean(decode_ok))\n')
    rows = []
    for r in near:
        o = r['outcomes']
        rows.append(head(r) + [r['n'], fmt(o['fer_r1'], 3), fmt(o['fer_final'], 3), fmt(o['fer_syndrome_def'], 3), o['n_r1c_fs'],
                               o['n_r1f_fs_rescued'], o['n_r1c_ff_regression'], o['n_r1f_ff'], f"{o['n_syn0_wrong_r1']}/{o['n_r1_syn0']}",
                               f"{o['n_syn0_wrong_final']}/{o['n_final_syn0']}", f"{o['n_decode_ok_but_info_err']}/{o['n_not_decode_ok_but_info_ok']}"])
    md.append(tab(['SNR', 'rho', 'L', 'K/K*', 'n', 'FER_r1', 'FER_fin', 'FER_syn', 'r1c&fs', 'r1f&fs (rescued)', 'r1c&ff (regress)', 'r1f&ff',
                   'syn0-wrong r1 / r1 syn0', 'syn0-wrong fin / fin syn0', 'dok&ierr / ~dok&iok'], rows) + '\n')
    md.append('### (b) stage errors: median [q10, q90] overall; median final-success / final-fail  (physical units; eps_pred = K s/(1+K s))\n')
    rows = []
    for r in near:
        rows.append(head(r) + [fmt(r['eps_pred_first_pass'])] + [c for s in STAGES for c in sf(r, s)])
    md.append(tab(['SNR', 'rho', 'L', 'K/K*', 'eps_pred'] + [c for s in STAGES for c in (f'{s} med [q10,q90]', f'{s} med succ / fail')], rows) + '\n')
    md.append('### (c) log10 eps_det2 shape (screen only) and A3 reference\n')
    rows = []
    for r in near:
        h = r['hist_log10_eps_det2']
        vp = h['valley_peak'] or {}
        stt = r['strata']
        a3 = r.get('a3', {})
        rows.append(head(r) + [fmt(h['BC'], 3), fmt(vp.get('ratio'), 2), fmt(vp.get('peak2_frac'), 2), 'FLAG' if vp.get('flag') else '',
                               f"{h['under']}/{h['over']}",
                               ' / '.join(fmt(stt[k]['sp_fer'], 2) for k in ('E_lo', 'E_mid', 'E_hi')),
                               ' / '.join(fmt(stt[k]['med_eps_det1'], 2) for k in ('E_lo', 'E_mid', 'E_hi')),
                               f"{fmt(stt['A3_ok']['sp_fer'], 2)} (n {stt['A3_ok']['n']}) / {fmt(stt['A3_fail']['sp_fer'], 2)} (n {stt['A3_fail']['n']})",
                               f"{fmt(stt['A3_ok']['med_eps_det1'], 2)} / {fmt(stt['A3_fail']['med_eps_det1'], 2)}",
                               fmt(a3.get('mean_r1_ll_in'), 5), fmt(a3.get('mean_r1_ll_app'), 5), fmt(a3.get('fer_final'), 3), fmt(a3.get('fer_r1'), 3)])
    md.append(tab(['SNR', 'rho', 'L', 'K/K*', 'BC', 'valley/peak', 'p2 frac', 'flag', 'under/over [-3,0]', 'SP FER by E tertile lo/mid/hi',
                   'med eps_det1 by E tertile', 'SP FER (A3 ok / A3 fail)', 'med eps_det1 (A3 ok / A3 fail)', 'A3 mean r1_ll_in',
                   'A3 mean r1_ll_app', 'A3 FER_fin', 'A3 FER_r1'], rows) + '\n')
    md.append('### (d) realised-energy confound (extra, descriptive): Spearman with E_real, medians of eps/E_real (relative error) and of E_real by final outcome\n')
    rows = []
    for r in near:
        c = r['energy_confound']
        rows.append(head(r) + [fmt(c['spearman_E_ce1'], 2), fmt(c['spearman_E_det1'], 2), fmt(c['spearman_E_fail'], 2),
                               f"{fmt(c['med_rel_ce1_success'], 3)} / {fmt(c['med_rel_ce1_fail'], 3)}",
                               f"{fmt(c['med_rel_det1_success'], 3)} / {fmt(c['med_rel_det1_fail'], 3)}",
                               f"{fmt(c['med_E_success'], 3)} / {fmt(c['med_E_fail'], 3)}"])
    md.append(tab(['SNR', 'rho', 'L', 'K/K*', 'rho_S(E, eps_ce1)', 'rho_S(E, eps_det1)', 'rho_S(E, fail)', 'med eps_ce1/E succ / fail',
                   'med eps_det1/E succ / fail', 'med E succ / fail'], rows) + '\n')
    md.append(f'### (e) stage maps, cells with K/K* in [{MAP_BAND[0]}, {MAP_BAND[1]}] (8 equal-count x bins; entries x_med:y_med (n); "-" = group n < {MIN_N})\n')
    for r in near:
        if not (MAP_BAND[0] <= r['K_over_kstar'] <= MAP_BAND[1]):
            continue
        md.append(f"**SNR {fmt(r['snr_db'])}, rho {fmt(r['rho'])}, L {r['L']}, K/K* {fmt(r['K_over_kstar'], 2)}**\n")
        for mname, groups in (('ce1_det1', ('all',)), ('det1_ce2', ('r1_correct', 'r1_fail')), ('det1_det2', ('all',))):
            m = r['maps'][mname]
            if m is None:
                continue
            for g in groups:
                items = [f"{fmt(b[g]['x_med'], 2)}:{fmt(b[g]['y_med'], 2)} ({b[g]['n']})" for b in m['bins']]
                md.append(f"- {mname} [{g}]: " + '; '.join(items))
        md.append('')
    return md


def flags_md(data):
    out = ['## Flags (automatic, SPg_flat, all cells)\n']
    f_reg, f_syn, f_old, f_bi, f_nan = [], [], [], [], []
    for name, ds in data.items():
        for r in ds['cells']:
            if r['arm'] != PRIMARY:
                continue
            o, tag = r['outcomes'], f"{name} SNR {fmt(r['snr_db'])} rho {fmt(r['rho'])} L {r['L']} (K/K* {fmt(r['K_over_kstar'], 2)})"
            if o['n_r1c_ff_regression'] > 0.02 * r['n']:
                f_reg.append(f"{tag}: r1c&ff = {o['n_r1c_ff_regression']}/{r['n']}")
            if o['n_syn0_wrong_final'] > 0 or o['n_syn0_wrong_r1'] > 0:
                f_syn.append(f"{tag}: syn0-wrong r1 {o['n_syn0_wrong_r1']}, final {o['n_syn0_wrong_final']}")
            if o['n_decode_ok_but_info_err'] > 0 or o['n_not_decode_ok_but_info_ok'] > 0:
                f_old.append(f"{tag}: decode_ok&info_err {o['n_decode_ok_but_info_err']}, ~decode_ok&info_ok {o['n_not_decode_ok_but_info_ok']}")
            if (r['hist_log10_eps_det2']['valley_peak'] or {}).get('flag'):
                f_bi.append(f"{tag}: BC {fmt(r['hist_log10_eps_det2']['BC'], 2)}, valley/peak {fmt(r['hist_log10_eps_det2']['valley_peak']['ratio'], 2)}, p2 {fmt(r['hist_log10_eps_det2']['valley_peak']['peak2_frac'], 2)}")
            if o['n_nan_stage'] > 0:
                f_nan.append(f"{tag}: {o['n_nan_stage']} rows with non-finite stage error")
    for title, lst in (('r1-correct & final-fail > 2% of frames', f_reg), ('syndrome-zero-but-wrong (any count)', f_syn),
                       ('syndrome-based vs info-error-based final outcome differ', f_old), ('eps_det2 bimodality screen flag', f_bi),
                       ('non-finite stage errors', f_nan)):
        out.append(f'**{title}**: ' + ('none' if not lst else f'{len(lst)} cells'))
        out += [f'- {x}' for x in lst[:40]]
        if len(lst) > 40:
            out.append(f'- ... {len(lst) - 40} more (see json)')
        out.append('')
    return out


def secondary_md(data):
    out = ['## Secondary arms (summary only; full cell records in json)\n']
    for name, ds in data.items():
        for arm in SP_ARMS:
            if arm == PRIMARY:
                continue
            rs = [r for r in ds['cells'] if r['arm'] == arm]
            if not rs:
                continue
            nr = [r for r in rs if r['near_cliff']]
            tot = lambda rr, k: sum(r['outcomes'][k] for r in rr)
            nn = sum(r['n'] for r in nr)
            out.append(f"- {name} {arm}: {len(rs)} cells; near-cliff {len(nr)} cells, {nn} frames: FER_fin {fmt(sum(r['outcomes']['fer_final'] * r['n'] for r in nr) / max(nn, 1), 3)}, "
                       f"r1c&fs {tot(nr, 'n_r1c_fs')}, rescued {tot(nr, 'n_r1f_fs_rescued')}, regress {tot(nr, 'n_r1c_ff_regression')}, r1f&ff {tot(nr, 'n_r1f_ff')}, "
                       f"syn0-wrong r1/fin {tot(nr, 'n_syn0_wrong_r1')}/{tot(nr, 'n_syn0_wrong_final')}; "
                       f"eps_det2 bimodality flags {sum(bool((r['hist_log10_eps_det2']['valley_peak'] or {}).get('flag')) for r in nr)}/{len(nr)}")
    out.append('')
    return out


def plots(data, out_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cm = plt.get_cmap('viridis')
    # maps: eps_ce1 -> eps_det1 binned medians per L, one panel per (dataset, SNR, rho)
    panels = sorted({(n, r['snr_db'], r['rho']) for n, ds in data.items() for r in ds['cells'] if r['arm'] == PRIMARY})
    ncol = 4
    nrow = math.ceil(len(panels) / ncol)
    fig, ax = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.6 * nrow), squeeze=False)
    for a, (n, snr, rho) in zip(ax.ravel(), panels):
        rs = sorted([r for r in data[n]['cells'] if r['arm'] == PRIMARY and r['snr_db'] == snr and r['rho'] == rho], key=lambda r: r['L'])
        Lmax = max(r['L'] for r in rs)
        for r in rs:
            m = r['maps']['ce1_det1']
            if m is None:
                continue
            xs = [b['all']['x_med'] for b in m['bins']]
            ys = [b['all']['y_med'] for b in m['bins']]
            a.plot(xs, [np.nan if y is None else y for y in ys], '-o', ms=3, color=cm(r['L'] / Lmax), lw=1.6 if r['near_cliff'] else .7)
        lim = [1e-3, 3]
        a.plot(lim, lim, 'k:', lw=.6)
        a.set_xscale('log')
        a.set_yscale('log')
        a.set_title(f'{n} {snr:g} dB rho {rho:g}', fontsize=9)
        a.set_xlabel('eps_ce1 (bin median)', fontsize=8)
        a.set_ylabel('eps_det1', fontsize=8)
        a.tick_params(labelsize=7)
    for a in ax.ravel()[len(panels):]:
        a.axis('off')
    fig.suptitle('T0 screen: eps_ce1 -> eps_det1 binned medians per L (color = L, thick = K/K* in [.5,1.5], dotted = identity)', fontsize=10)
    fig.tight_layout()
    fig.savefig(out_dir / 't0_maps.png', dpi=110)
    plt.close(fig)
    # histograms of log10 eps_det2 for near-cliff cells
    centres = .5 * (HIST_EDGES[:-1] + HIST_EDGES[1:])
    fig, ax = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.6 * nrow), squeeze=False)
    for a, (n, snr, rho) in zip(ax.ravel(), panels):
        rs = sorted([r for r in data[n]['cells'] if r['arm'] == PRIMARY and r['snr_db'] == snr and r['rho'] == rho
                     and MAP_BAND[0] <= r['K_over_kstar'] <= MAP_BAND[1]], key=lambda r: r['L'])
        for r in rs:
            h = r['hist_log10_eps_det2']
            a.step(centres, np.array(h['counts']) / max(sum(h['counts']), 1), where='mid', label=f"L{r['L']} ({r['K_over_kstar']:.2f})")
        a.set_title(f'{n} {snr:g} dB rho {rho:g}  (K/K* in [{MAP_BAND[0]}, {MAP_BAND[1]}])', fontsize=8)
        a.set_xlabel('log10 eps_det2', fontsize=8)
        a.tick_params(labelsize=7)
        if rs:
            a.legend(fontsize=6)
    for a in ax.ravel()[len(panels):]:
        a.axis('off')
    fig.suptitle('T0 screen: log10 eps_det2 histograms (fraction of frames per bin; screen, not a bistability test)', fontsize=10)
    fig.tight_layout()
    fig.savefig(out_dir / 't0_hist.png', dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--boot-dir', type=Path, required=True)
    ap.add_argument('--map-dir', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--boot-md5', type=Path, default=None)
    ap.add_argument('--map-md5', type=Path, default=None)
    ap.add_argument('--no-plots', action='store_true')
    args = ap.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    data, pooled_maps = {}, {}
    for name, d, m5 in (('c1_boot', args.boot_dir, args.boot_md5), ('c1_map', args.map_dir, args.map_md5)):
        chk = verify_md5(d, m5)
        print(f'[{name}] md5: {chk}', flush=True)
        cells, st = load(d)
        print(f'[{name}] {st}  cells {len(cells)}  ({time.time() - t0:.0f}s)', flush=True)
        per_arm = collections.Counter()
        for k, v in cells.items():
            per_arm[k[0]] += len(v['frame'])
        recs = []
        for (arm, snr, rho, L), v in sorted(cells.items()):
            if arm == 'A3':
                continue
            a3 = cells.get(('A3', snr, rho, L))
            recs.append(analyse_sp(v, a3, snr, rho, L, arm))
        a3_recs = [dict(snr_db=k[1] / 100., rho=k[2] / 1000., L=k[3], **analyse_a3(v)) for k, v in sorted(cells.items()) if k[0] == 'A3']
        pooled_maps[name] = {f'{arm}|{snr / 100:g}|{rho / 1000:g}': pooled(cells, arm, snr, rho)
                             for arm in SP_ARMS for snr in sorted({k[1] for k in cells}) for rho in sorted({k[2] for k in cells})
                             if any(k[0] == arm and k[1] == snr and k[2] == rho for k in cells)}
        data[name] = dict(stats=st, md5_check=chk, rows_per_arm=dict(per_arm), cells=recs, a3_cells=a3_recs)
        print(f'[{name}] analysed {len(recs)} SP cells, {len(a3_recs)} A3 cells ({time.time() - t0:.0f}s)', flush=True)
    res = dict(_argv=sys.argv, _config=dict(boot_dir=str(args.boot_dir), map_dir=str(args.map_dir), out_dir=str(args.out_dir),
                                            boot_md5=str(args.boot_md5), map_md5=str(args.map_md5), N=N, g_old=G_OLD, quantiles=QS,
                                            nbins=NBINS, min_n_median=MIN_N, hist_edges_log10=HIST_EDGES.tolist(), cliff_band=CLIFF_BAND,
                                            map_band=MAP_BAND, primary_arm=PRIMARY, stages=STAGES, fields=FIELDS),
               datasets=data, pooled_maps=pooled_maps)
    (args.out_dir / 't0_screen.json').write_text(json.dumps(clean(res), indent=1))
    md = ['# T0 exploratory screen of existing C1 rows (descriptive; screen, not a bistability test; no new simulation)\n',
          f'Generated by c1_t0_screen.py. Definitions: see the script docstring. Primary arm {PRIMARY}; K* from g = {G_OLD}; '
          'eps in physical units (||H - H^||_F^2 / N, E = 1 expected). Full per-cell records, maps, histograms, other arms and A3 numbers '
          '(full precision): t0_screen.json.\n']
    for name, ds in data.items():
        md += dataset_md(name, ds)
    md += secondary_md(data) + flags_md(data)
    (args.out_dir / 'T0_SCREEN.md').write_text('\n'.join(md))
    if not args.no_plots:
        plots(data, args.out_dir)
    print(f'done ({time.time() - t0:.0f}s)', flush=True)


if __name__ == '__main__':
    main()
