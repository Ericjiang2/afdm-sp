"""Predeclared paired terminal analysis; refuses partial or unaudited runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from tail_terminal_run_v1 import sha, validate_contract

ARMS = ('ORIGINAL', 'TAIL', 'RIDGE_T')


def paired_analysis(rows):
    index = {}
    for row in rows:
        key = row['block'], row['snr'], row['arm']
        if key in index or row['scores']['FER'] not in (0, 1):
            raise ValueError('duplicate work point or invalid FER flag')
        index[key] = row
    wanted = {(b, s, a) for b in range(32) for s in (7, 8) for a in ARMS}
    if set(index) != wanted:
        raise ValueError('complete 32 physical blocks x 2 SNR x 3 arms required')
    for b in range(32):
        physical = {index[b, s, a]['physical_record_sha256'] for s in (7, 8) for a in ARMS}
        if len(physical) != 1:
            raise ValueError('cross-SNR physical pairing differs')
    names = ('TAIL_minus_ORIGINAL', 'TAIL_minus_RIDGE_T')
    references = ('ORIGINAL', 'RIDGE_T')
    values = np.array([[np.mean([index[b, s, 'TAIL']['scores']['FER']
                                 - index[b, s, a]['scores']['FER'] for s in (7, 8)])
                        for a in references] for b in range(32)])
    draw = np.random.default_rng(202609160701).integers(0, 32, size=(20000, 32))
    bootstrap = values[draw].mean(axis=1)
    endpoints = {name: dict(mean=float(values[:, j].mean()),
        simultaneous_95_percentile=np.quantile(bootstrap[:, j], [.0125, .9875]).tolist(),
        per_physical_block=values[:, j].tolist()) for j, name in enumerate(names)}
    by_snr = {}
    for snr in (7, 8):
        arms = {}
        for arm in ARMS:
            scores = [index[b, snr, arm]['scores'] for b in range(32)]
            arms[arm] = dict(error_blocks=sum(v['FER'] for v in scores), frames=32,
                info_bit_errors=sum(v['info_bit_errors'] for v in scores),
                info_bits=sum(v['info_bits'] for v in scores),
                H_NMSE_mean=float(np.mean([v['H_NMSE'] for v in scores])),
                response_NMSE_mean=float(np.mean([v['response_NMSE'] for v in scores])))
            arms[arm]['FER'] = arms[arm]['error_blocks']/32
            arms[arm]['BER'] = arms[arm]['info_bit_errors']/arms[arm]['info_bits']
        discordance = {}
        for reference in references:
            a = np.array([index[b, snr, 'TAIL']['scores']['FER'] for b in range(32)])
            b = np.array([index[b, snr, reference]['scores']['FER'] for b in range(32)])
            discordance[reference] = dict(rescued=int(np.count_nonzero((b == 1) & (a == 0))),
                                          newly_failed=int(np.count_nonzero((b == 0) & (a == 1))))
        by_snr[str(snr)] = dict(arms=arms, tail_discordance=discordance)
    significant = all(v['simultaneous_95_percentile'][1] < 0 for v in endpoints.values())
    no_snr_worsening = all(by_snr[str(s)]['arms']['TAIL']['error_blocks']
                          <= by_snr[str(s)]['arms'][a]['error_blocks']
                          for s in (7, 8) for a in references)
    return dict(primary_endpoints=endpoints, by_snr=by_snr,
                significant_against_both=significant, no_per_snr_worsening=no_snr_worsening,
                full_feedback_development_GO=bool(significant and no_snr_worsening),
                scope='exposed development; bootstrap is descriptive; not independent confirmation')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    c = json.loads(args.contract.read_text())
    validate_contract(c)
    if sha(__file__) != c['implementation_sha256'][Path(__file__).name]:
        raise ValueError('analysis source changed after freeze')
    rows, transforms, hashes, wall = {}, [], {}, 0.
    engineering_rows, audit_counts = [], {}
    for stage, count in (('engineering', 12), ('development', 120)):
        sp = args.root/'runs'/stage/'producer/summary.json'
        ap = args.root/'runs'/stage/'audit/summary.json'
        producer, audit = json.loads(sp.read_text()), json.loads(ap.read_text())
        if (producer['status'] != 'COMPLETE' or audit['status'] != 'COMPLETE'
                or producer['calls'] != {'T': count} or audit['calls'] != {'D': count}
                or audit['producer_summary_sha256'] != sha(sp)
                or producer['contract_sha256'] != sha(args.contract)
                or audit['contract_sha256'] != sha(args.contract)
                or audit['rows'] != producer['rows'] or audit['original_rows'] != producer['original_rows']):
            raise ValueError('complete bound producer and raw audit required')
        if stage == 'engineering':
            if not audit['engineering_quote']['GO']:
                raise ValueError('development lacks engineering resource admission')
            engineering_rows = producer['rows']
        for key, value in audit['additional_method_counts'].items():
            audit_counts[key] = audit_counts.get(key, 0) + value
        for mode in ('run', 'audit'):
            path = args.root/'evidence'/f'tail-terminal-{stage}-{mode}-v1-exit.json'
            exit_record = json.loads(path.read_text())
            if exit_record['exit_code'] != 0 or exit_record['timed_out']:
                raise ValueError('incomplete or timed-out campaign stage')
            wall += float(exit_record['wall_seconds'])
            hashes[str(path.relative_to(args.root))] = sha(path)
        for path in (sp, ap):
            hashes[str(path.relative_to(args.root))] = sha(path)
        for row in producer['original_rows']:
            key = row['block'], row['snr'], 'ORIGINAL'
            if key in rows:
                raise ValueError('engineering/development ORIGINAL overlap')
            rows[key] = row
        for row in producer['rows']:
            if row['arm'] == 'ORIGINAL':
                if row['scores'] != rows[row['block'], row['snr'], 'ORIGINAL']['scores']:
                    raise ValueError('engineering identity replay changed ORIGINAL scoring')
                continue
            key = row['block'], row['snr'], row['arm']
            if key in rows:
                raise ValueError('duplicate new method terminal')
            rows[key] = dict(block=row['block'], snr=row['snr'], arm=row['arm'], scores=row['scores'],
                             **row['provenance'])
            transforms.append(row)
    if wall > c['limits']['wall_seconds']:
        raise ValueError('campaign exceeded its frozen wall limit')
    result = paired_analysis(list(rows.values()))
    result.update(schema='tail-terminal-results-v1', status='AUDITED',
                  artifact_hashes=hashes, contract_sha256=sha(args.contract),
                  accounting=dict(production_T=132, new_BP=132, new_BP_iterations=2640,
                    production_LDPC=132, audit_D=132, total_LDPC=264, new_receiver_F=0,
                    new_physical_A=0, unique_new_method_terminals=128, reused_originals=64,
                    original_terminal_identity_replays=4, supervisor_seconds=wall),
                  review_independence='main-session self-review; weak')
    costs = {}
    for arm in ('TAIL', 'RIDGE_T'):
        selected = [v for v in transforms if v['arm'] == arm]
        if len(selected) != 64:
            raise ValueError('incomplete method cost matrix')
        totals = [v['preprocessing_seconds']+sum(x['seconds'] for x in v['operator_profile']) for v in selected]
        costs[arm] = dict(instrumented_forward_seconds_median=float(np.median(totals)),
            instrumented_forward_seconds_mean=float(np.mean(totals)),
            actual_edges_mean=float(np.mean([v['actual_edges'] for v in selected])),
            predictor_solves=sum(v['method_counts']['F_matrix_solves'] for v in selected),
            tail_refits=sum(v['method_counts']['tail_refit_solves'] for v in selected))
    result['development_costs'] = costs
    result['audit_method_counts'] = audit_counts
    result['original_graph_edges_mean_64_points'] = float(np.mean([
        rows[b, s, 'ORIGINAL']['actual_edges'] for b in range(32) for s in (7, 8)]))
    result['engineering_costs_four_paired_points_only'] = {
        a: float(np.median([v['preprocessing_seconds']+sum(p['seconds'] for p in v['operator_profile'])
                           for v in engineering_rows if v['arm'] == a])) for a in ARMS}
    result['cost_scope'] = 'Instrumented construction/cancellation + BP + LDPC; excludes I/O/scoring, not isolated formal deployment latency.'
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(output=str(args.output), GO=result['full_feedback_development_GO'])))


if __name__ == '__main__':
    main()
