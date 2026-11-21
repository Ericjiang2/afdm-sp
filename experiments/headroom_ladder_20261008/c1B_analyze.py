#!/usr/bin/env python
"""Evaluate the frozen B1/B2 screen; no data generation or B3/B4 decisions.

Reads remote evidence rows before compression. Outputs compact aggregates only.
Missing/error/matching-failure evidence is explicit and cannot count as a pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from driver_c1B import ARMS, CELLS, SPEC


ORIGINAL_SHA256 = {
    'dpss_rx.py': '800aa51a8f81dfd1aca6eb5ab5fa81ac1bff79716875187b8f89d8a5994595af',
    'driver_c1.py': '6d39b41c5cb158bebd84edcb1a61de9a0b89346cb9bfdc8d3c1cb362cb8cba24',
    'tapchannel.py': 'bcf3597782da42d94ff37f09010b45e5effe79a231493489ccbc829c6a3414bc',
}


def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def compact_write(path, value):
    content = json.dumps(value, indent=1, allow_nan=False)+'\n'
    if len(content.encode()) >= 1_000_000:
        raise ValueError(f'compact artifact too large: {path}')
    path.write_text(content)


def load_campaign(out):
    result = json.loads((out/'results.json').read_text())
    if result['manifest']['spec'] != json.loads(json.dumps(SPEC)):
        raise ValueError('registered specification mismatch')
    rows, md5s = {}, {}
    for receipt in result['shard_receipts']:
        shard = receipt['shard']
        rp, cp = out/f'rows_shard{shard:03d}.jsonl', out/f'config_shard{shard:03d}.json'
        if digest(rp) != receipt['rows_sha256'] or digest(cp) != receipt['manifest_sha256']:
            raise ValueError(f'evidence hash mismatch: shard {shard}')
        if json.loads(cp.read_text()) != result['manifest']:
            raise ValueError('manifest disagreement')
        md5s[str(rp)] = digest(rp, 'md5')
        count = 0
        with rp.open() as stream:
            for line in stream:
                row = json.loads(line)
                key = row['cell'], row['frame'], row['arm']
                if key in rows:
                    raise ValueError(f'duplicate row {key}')
                rows[key] = row
                count += 1
        if count != receipt['rows']:
            raise ValueError('receipt row count differs')
    arms = ('OFF20','DIR20') if result['mode'] == 'b0' else ARMS
    frames = (0,) if result['mode'] == 'b0' else range(32)
    if set(rows) != {(c,f,a) for c in range(1,7) for f in frames for a in arms}:
        raise ValueError('registered allocation differs')
    fields = ('physical_gains_sha256','info_sha256','noise_sha256',
              'observation_y_sha256','observation_pilot_sha256','observation_sigma2')
    for c in range(1,7):
        for f in frames:
            if len({tuple(rows[c,f,a][k] for k in fields) for a in arms}) != 1:
                raise ValueError('arm observation pairing differs')
    for f in frames:
        if len({(rows[c,f,arms[0]]['info_sha256'], rows[c,f,arms[0]]['noise_sha256'])
                for c in range(1,7)}) != 1:
            raise ValueError('cross-cell message/noise pairing differs')
        if rows[2,f,arms[0]]['physical_gains_sha256'] != rows[3,f,arms[0]]['physical_gains_sha256']:
            raise ValueError('cross-rho physical path pairing differs')
    for name, frozen in ORIGINAL_SHA256.items():
        if result['manifest']['sources'][name] != frozen or digest(Path(__file__).parent/name) != frozen:
            raise ValueError(f'frozen source modified: {name}')
    errors = [dict(cell=c,frame=f,arm=a,error=r.get('error'))
              for (c,f,a),r in rows.items() if r['status'] != 'ok']
    if result['mode'] != 'b0':
        for (c,f,a),r in rows.items():
            if r['status'] != 'ok':
                continue
            expected_steps = 40 if a == 'BASE40' else 20
            selected = {'10','20','40'} if a == 'BASE40' else {'10','20'}
            if r['n_cols'] != 8*CELLS[c-1][2] or len(r['trace']) != expected_steps:
                raise ValueError('actual channel dimension/inner budget differs from registration')
            if not selected.issubset(r['selected_states']):
                raise ValueError('registered replay states missing')
    return rows, result, md5s, errors


def matched_aggregate(sample):
    missing = [r['frame'] for r in sample if r['status'] != 'ok'
               or r.get('matched_refit',{}).get('status') != 'ok']
    if missing:
        return dict(available=False, expected=len(sample), unavailable_frames=missing,
                    matching_failures=sum(r.get('matched_refit',{}).get('status') == 'matching_failure'
                                          for r in sample))
    diagnostics = [r['matched_refit'] for r in sample]
    z2 = sum(d['z2'] for d in diagnostics)
    if z2 <= 0:
        return dict(available=False, expected=len(sample), reason='zero denominator')
    numerator = sum(d['zu2']+d['u2'] for d in diagnostics)
    closure = []
    for d in diagnostics:
        own = d['z2']+d['zu2']+d['u2']
        receiver = own+d['zw2']+d['w2']+d['uw2']
        closure.append(max(abs(own-d['own_orthogonal_risk']),
                           abs(receiver-d['receiver_orthogonal_risk'])))
    if max(closure) > 1e-9:
        raise ValueError('J12 algebra does not close')
    return dict(available=True, frames=len(sample), sum_z2=z2, sum_excess=numerator,
                D_reg=numerator/z2, mean_symbol_mse=float(np.mean([d['true_symbol_mse'] for d in diagnostics])),
                mean_reported_ce_variance=float(np.mean([d['reported_ce_variance'] for d in diagnostics])),
                mean_variance_to_true_mse=float(np.mean([d['variance_to_true_mse'] for d in diagnostics])),
                mean_own_refit_risk=float(np.mean([d['own_orthogonal_risk'] for d in diagnostics])),
                mean_independent_refit_risk=z2/len(sample),
                mean_receiver_risk=float(np.mean([d['receiver_orthogonal_risk'] for d in diagnostics])),
                max_matching_relative_error=max(d['matching']['relative_error'] for d in diagnostics),
                max_closure_error=max(closure))


def probe_aggregate(sample, relative=1e-5, recompute=True):
    values, unavailable, steps = [], [], {5:[],10:[],20:[]}
    for r in sample:
        if r['status'] != 'ok':
            unavailable.extend((r['frame'],t) for t in steps)
            continue
        for t in steps:
            selected = [p for p in r.get('probes',[]) if p['step'] == t
                        and p['relative_step'] == relative and p['recompute_coefficients'] == recompute]
            if len(selected) != 1:
                raise ValueError('registered probe is missing or duplicated')
            p = selected[0]
            if p['rank_zero'] or p['ratio'] is None or p['raw_norm'] <= 0:
                unavailable.append((r['frame'],t))
            else:
                values.append(p['ratio'])
                steps[t].append(p['ratio'])
    return dict(available=len(unavailable) == 0, expected=len(sample)*3,
                usable=len(values), unavailable=unavailable,
                median=float(np.median(values)) if values else None,
                medians_by_step={str(t):float(np.median(v)) if v else None for t,v in steps.items()})


def metrics(sample):
    errors = sum(r['status'] != 'ok' for r in sample)
    value = dict(frames=len(sample), errors=errors,
                 mean_seconds=float(np.mean([r['seconds'] for r in sample])))
    if errors:
        value.update(fer=None, mean_orthogonal_risk=None)
        return value
    value.update(frame_errors=sum(r['info_errors'] > 0 for r in sample),
                 fer=float(np.mean([r['info_errors'] > 0 for r in sample])),
                 mean_orthogonal_risk=float(np.mean([r['orthogonal_risk'] for r in sample])),
                 mean_eps_det1=float(np.mean([r['eps_det1'] for r in sample])),
                 mean_logloss_bits=float(np.mean([r['logloss_bits'] for r in sample])),
                 mean_inference_seconds=float(np.mean([r['sec_inference'] for r in sample])))
    return value


def transient_summary(sample, references):
    reached, costs = [], []
    for r, reference in zip(sample,references):
        if r['status'] != 'ok' or reference['status'] != 'ok':
            continue
        risk = r['orthogonal_trajectory']
        threshold = 1.10*reference['orthogonal_risk']
        t = next((i for i in range(len(risk)) if all(x <= threshold for x in risk[i:])), None)
        if t is not None:
            reached.append(t+1)
            # Actual cumulative core timer; no iteration-fraction extrapolation.
            costs.append(r['sec_pilot']+r['sec_ce']+r['trace'][t]['elapsed_kernel_seconds'])
    return dict(reached=len(reached), censored=len(sample)-len(reached),
                median_step_reached=float(np.median(reached)) if reached else None,
                mean_measured_cost_reached=float(np.mean(costs)) if costs else None,
                scope='descriptive only; registered B3 not run')


def count_gate(outcomes, need=4):
    passed = sum(x is True for x in outcomes)
    unavailable = sum(x is None for x in outcomes)
    verdict = 'PASS' if passed >= need else ('KILL' if passed+unavailable < need else 'INCONCLUSIVE')
    return dict(verdict=verdict, passed_cells=passed, unavailable_cells=unavailable, required=need)


def analyze(rows, result, errors):
    cells, b1, excess, risk_gate, harm = [], [], [], [], []
    for c, physical in enumerate(CELLS,1):
        cell = dict(cell=c, snr_db=physical[0], rho=physical[1], L=physical[2], K=8*physical[2])
        samples = {a:[rows[c,f,a] for f in range(32)] for a in ARMS}
        cell['arms'] = {a:metrics(sample) for a,sample in samples.items()}
        for a,sample in samples.items():
            cell['arms'][a]['transient'] = transient_summary(sample,samples['BASE40'])
        primary = probe_aggregate(samples['DIR20'][:8])
        sensitivity = probe_aggregate(samples['DIR20'][:8],relative=1e-6)
        locked = probe_aggregate(samples['DIR20'][:8],recompute=False)
        cell['B1'] = dict(primary=primary, sensitivity_1e6=sensitivity, locked_algebra_only=locked)
        b1.append(primary['median'] <= .70 if primary['available'] else None)
        cell['B1']['passes'] = b1[-1]
        matched = {a:matched_aggregate(samples[a][:16]) for a in ('BASE20','RAW20','DIR20')}
        cell['matched_refits'] = matched
        dreg_drop = matched['RAW20']['D_reg']-matched['DIR20']['D_reg'] if all(
            matched[a]['available'] for a in ('RAW20','DIR20')) else None
        excess.append(dreg_drop >= .10 if dreg_drop is not None else None)
        risks = cell['arms']
        raw_risk, dir_risk = risks['RAW20']['mean_orthogonal_risk'], risks['DIR20']['mean_orthogonal_risk']
        ratio = dir_risk/raw_risk if dir_risk is not None and raw_risk is not None and raw_risk > 0 else None
        risk_gate.append(ratio <= .90 if ratio is not None else None)
        harm.append(ratio > 1.10 if ratio is not None else None)
        cell['B2'] = dict(D_reg_drop_RAW_minus_DIR=dreg_drop, excess_passes=excess[-1],
                          orthogonal_risk_DIR_over_RAW=ratio, risk_passes=risk_gate[-1], harm=harm[-1])
        cell['comparison'] = {}
        for a in ('RAW20','GLOB20','BASE20','BASE40','DAMP20'):
            m = risks[a]
            cell['comparison'][a] = dict(
                risk_DIR_over_control=dir_risk/m['mean_orthogonal_risk'] if dir_risk is not None
                    and m['mean_orthogonal_risk'] is not None and m['mean_orthogonal_risk'] > 0 else None,
                time_DIR_over_control=risks['DIR20']['mean_seconds']/m['mean_seconds'],
                FER_DIR_minus_control=risks['DIR20']['fer']-m['fer'] if m['fer'] is not None
                    and risks['DIR20']['fer'] is not None else None)
        cells.append(cell)
    no_harm = dict(verdict='KILL' if any(x is True for x in harm) else
                   ('INCONCLUSIVE' if any(x is None for x in harm) else 'PASS'),
                   harmed_cells=[i+1 for i,x in enumerate(harm) if x is True],
                   unavailable_cells=[i+1 for i,x in enumerate(harm) if x is None], threshold=1.10)
    gates = dict(B1=count_gate(b1), B2_excess=count_gate(excess),
                 B2_risk=count_gate(risk_gate), B2_no_harm=no_harm)
    verdicts = [g['verdict'] for g in gates.values()]
    overall = 'KILL' if 'KILL' in verdicts else ('PASS' if all(v == 'PASS' for v in verdicts) else 'INCONCLUSIVE')
    pooled = {a:metrics([rows[c,f,a] for c in range(1,7) for f in range(32)]) for a in ARMS}
    actual_updates = sum(len(r.get('trace',[])) for r in rows.values())
    actual_ffts = sum(1+sum(t['fft_count'] for t in r['trace']) for r in rows.values() if r['status'] == 'ok')
    if not errors and (actual_updates != 26880 or actual_ffts != 70272):
        raise ValueError('actual update/transform budget differs from frozen registration')
    return dict(schema=SPEC['schema'], kind='B1-B2-frozen-screen', overall=overall,
                gates=gates, cells=cells, pooled_descriptive=pooled,
                integrity=dict(rows=len(rows),error_rows=len(errors),errors=errors,
                               source_hashes=result['manifest']['sources'], paired_observations=True),
                compute=dict(full_receiver_calls=len(rows), inner_updates=actual_updates,
                             expected_transform_count=70272, actual_transform_count=actual_ffts,
                             sum_receiver_wall_seconds=sum(r['seconds'] for r in rows.values()),
                             sum_shard_wall_seconds=sum(r['wall_seconds'] for r in result['shard_receipts']),
                             matching_failures=sum(r.get('matched_refit',{}).get('status') == 'matching_failure'
                                                   for r in rows.values()),
                             refit_pairs_registered=288, B3_B4_run=False),
                limitations=[
                    'R=1 known-support mechanism screen, 32 paired frames per cell; no Kc/B3/B4 evidence.',
                    'Cell point gates are frozen screening rules, not confirmatory significance tests.',
                    'Receiver clock includes capture overhead; excludes post-call truth refits/probes/serialization.',
                    'Concurrent single-thread CPU wall time is descriptive, not an isolated deployment benchmark.',
                    'DIR matched control is a conditional frozen export map; not independent of the observed state.',
                    'Pooled six-cell numbers are descriptive; decisions use individual cell gates.',
                ])


def render(report):
    lines = ['# C1-B frozen B1/B2 screen', '', f"Verdict: **{report['overall']}**. R=1; 6 cells × 32 frames × 6 arms. B3/B4 not run.", '',
             '| Gate | Verdict | Evidence |', '|---|---|---|']
    for name,g in report['gates'].items():
        evidence = (f"{g['passed_cells']}/6 pass, {g['unavailable_cells']} unavailable; require 4/6"
                    if 'passed_cells' in g else f"harm cells {g['harmed_cells']}; unavailable {g['unavailable_cells']}")
        lines.append(f"| {name} | {g['verdict']} | {evidence} |")
    lines.extend(['','| Cell (SNR/rho/L) | B1 full median | Dreg RAW−DIR | Risk DIR/RAW | Risk DIR/GLOB | Risk DIR/BASE40 |',
                  '|---|---:|---:|---:|---:|---:|'])
    def fmt(v):
        return 'unavailable' if v is None else f'{v:.6g}'
    for c in report['cells']:
        lines.append(f"| {c['cell']} ({c['snr_db']}/{c['rho']}/{c['L']}) | {fmt(c['B1']['primary']['median'])} | "
                     f"{fmt(c['B2']['D_reg_drop_RAW_minus_DIR'])} | {fmt(c['B2']['orthogonal_risk_DIR_over_RAW'])} | "
                     f"{fmt(c['comparison']['GLOB20']['risk_DIR_over_control'])} | {fmt(c['comparison']['BASE40']['risk_DIR_over_control'])} |")
    lines.extend(['', 'Per-cell endpoints (32 frames; FER is raw count/32):', '',
                  '| Cell | Arm | FER | Orthogonal risk | Full receiver seconds |', '|---|---|---:|---:|---:|'])
    for c in report['cells']:
        for a,m in c['arms'].items():
            lines.append(f"| {c['cell']} | {a} | {fmt(m['fer'])} | {fmt(m['mean_orthogonal_risk'])} | {fmt(m['mean_seconds'])} |")
    lines.extend(['', 'Pooled descriptive endpoints (192 frames; not the gate):', '',
                  '| Arm | FER | Orthogonal risk | Full receiver seconds |', '|---|---:|---:|---:|'])
    for a,m in report['pooled_descriptive'].items():
        lines.append(f"| {a} | {fmt(m['fer'])} | {fmt(m['mean_orthogonal_risk'])} | {fmt(m['mean_seconds'])} |")
    lines.extend(['', f"Integrity: {report['integrity']['rows']} rows; {report['integrity']['error_rows']} errors. "
                  f"Matching failures: {report['compute']['matching_failures']}. Original source hashes unchanged; observation pairing checked.",
                  '', 'Facts: measured endpoints and registered gate results above. Derivation checks are B0, not mechanism evidence.',
                  'Inference: failure of any registered mechanism gate kills this frozen candidate’s corresponding claim; it does not disprove every decorrelated JED method.',
                  '', *['- '+x for x in report['limitations']], ''])
    return '\n'.join(lines)


def self_check():
    def diagnostic(z2, numerator):
        return dict(frame=int(z2),status='ok',matched_refit=dict(status='ok',z2=z2,zu2=numerator,u2=0.,
            zw2=0.,w2=0.,uw2=0.,own_orthogonal_risk=z2+numerator,
            receiver_orthogonal_risk=z2+numerator,true_symbol_mse=.2,reported_ce_variance=.3,
            variance_to_true_mse=1.5,matching=dict(relative_error=0.)))
    aggregate = matched_aggregate([diagnostic(1.,1.),diagnostic(9.,0.)])
    assert abs(aggregate['D_reg']-.1) < 1e-14
    assert count_gate([True]*4+[False]*2)['verdict'] == 'PASS'
    assert count_gate([True]*3+[False]*3)['verdict'] == 'KILL'
    assert count_gate([True]*3+[False]*2+[None])['verdict'] == 'INCONCLUSIVE'
    failed = dict(frame=0,status='ok',matched_refit=dict(status='matching_failure'))
    assert not matched_aggregate([failed])['available']
    probes = [dict(step=t,relative_step=1e-5,recompute_coefficients=True,
                   rank_zero=True,ratio=None,raw_norm=0.) for t in (5,10,20)]
    unusable = probe_aggregate([dict(frame=0,status='ok',probes=probes)])
    assert not unusable['available'] and unusable['median'] is None
    return dict(passed=True, checks=['ratio_of_sums_not_mean_ratios','gate_boundary_4of6',
                'missing_evidence_not_pass','matching_failure_not_dropped','zero_response_not_pass'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--self-check',action='store_true')
    args = p.parse_args()
    if args.self_check:
        compact_write(args.out,self_check())
        return
    rows,result,md5s,errors = load_campaign(args.out)
    if result['mode'] == 'b0':
        report = dict(kind='B0-smoke',passed=not errors,calls=len(rows),errors=errors,
                      paired_observations=True,sources=result['manifest']['sources'],
                      summary=result['summary'])
    else:
        report = analyze(rows,result,errors)
        (args.out/'analysis.md').write_text(render(report))
    compact_write(args.out/'analysis.json',report)
    (args.out/'REMOTE_ROWS_MD5.txt').write_text(''.join(f'{md5}  {path}\n' for path,md5 in md5s.items()))
    compact_write(args.out/'analysis_provenance.json',dict(
        analyzer_sha256=digest(Path(__file__)), results_sha256=digest(args.out/'results.json'),
        rows_md5=md5s, gates_frozen_before_generation=True))
    print(json.dumps({k:report[k] for k in ('passed','calls','overall','gates') if k in report},indent=1))


if __name__ == '__main__':
    main()
