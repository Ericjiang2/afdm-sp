#!/usr/bin/env python
"""Evaluate the frozen ACC cell gate; reads evidence, never runs a receiver."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

import driver_c1ACC as harness
from c1B_analyze import compact_write, digest, metrics


CANDIDATES = ('AA2', 'AA4', 'ADPT')
FROZEN_SOURCES = {
    'dpss_rx.py': '800aa51a8f81dfd1aca6eb5ab5fa81ac1bff79716875187b8f89d8a5994595af',
    'c1B_rx.py': '7a945331d55d722d253ad2a2b4b168b9a66bc23c1039f9f4893118306af60b52',
    'driver_c1B.py': '71d451ed4baa8256f992679251c48015f519256a6adb376921418a8d19fe6960',
    'driver_c1.py': '6d39b41c5cb158bebd84edcb1a61de9a0b89346cb9bfdc8d3c1cb362cb8cba24',
    'tapchannel.py': 'bcf3597782da42d94ff37f09010b45e5effe79a231493489ccbc829c6a3414bc',
}


def read_campaign(out):
    result = json.loads((out/'results.json').read_text())
    if result['manifest']['spec'] != harness.SPEC:
        raise ValueError('frozen ACC specification differs')
    rows, md5s = {}, {}
    for receipt in result['shard_receipts']:
        shard = receipt['shard']
        cp = out/f'config_shard{shard:03d}.json'
        rp = out/f'rows_shard{shard:03d}.jsonl'
        if digest(cp) != receipt['manifest_sha256'] or digest(rp) != receipt['rows_sha256']:
            raise ValueError('shard evidence hash differs')
        if json.loads(cp.read_text()) != result['manifest']:
            raise ValueError('shard manifest differs')
        part = harness.read_rows(rp, shard, receipt['nshard'], require_complete=True)
        if set(rows) & set(part):
            raise ValueError('duplicate rows across shards')
        rows.update(part)
        md5s[str(rp)] = digest(rp, 'md5')
    expected = {(c,f,a) for c in range(6) for f in range(32) for a in harness.ARMS}
    if set(rows) != expected:
        raise ValueError('registered 1536-row allocation differs')
    for name,frozen in FROZEN_SOURCES.items():
        if result['manifest']['sources'][name] != frozen or digest(harness.HERE/name) != frozen:
            raise ValueError(f'frozen source changed: {name}')
    for c in range(6):
        for f in range(32):
            if len({tuple(rows[c,f,a][k] for k in harness.PAIR_FIELDS) for a in harness.ARMS}) != 1:
                raise ValueError('arm observation pairing differs')
    for (c,f,a),r in rows.items():
        if r['status'] != 'ok':
            continue
        steps = harness.arm_spec(a)[1]
        if r['n_cols'] != 8*harness.CELLS[c][2] or r['committed_iterations'] != steps:
            raise ValueError('actual column/iteration budget differs')
        if len(r['trace']) != steps or len(r['per_step_overhead_seconds']) != steps:
            raise ValueError('step accounting missing')
        if r['map_evaluations'] != sum(t['map_evaluations'] for t in r['trace']):
            raise ValueError('map-evaluation accounting differs')
        if r['fft_count'] != 1+sum(t['fft_count'] for t in r['trace']):
            raise ValueError('transform accounting differs')
        if r['fft_count'] != 1+2*r['map_evaluations']:
            raise ValueError('unexpected ACC map transform charge')
        if r['map_evaluations'] < steps or (a not in CANDIDATES and r['map_evaluations'] != steps):
            raise ValueError('invalid plain/accelerated map budget')
    return rows,result,md5s


def compare_archived_b(rows, b_out):
    """Verify actual observation hashes against the completed B campaign."""
    original = {}
    for path in sorted(b_out.glob('rows_shard*.jsonl*')):
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path,'rt') as stream:
            for line in stream:
                r = json.loads(line)
                if r['arm'] in ('BASE20','BASE40'):
                    key = r['cell']-1,r['frame'],r['arm']
                    if key in original:
                        raise ValueError('duplicate archived B reference')
                    original[key] = r
    if len(original) != 384:
        raise ValueError('archived B references unavailable/incomplete')
    max_diff = 0.
    for c in range(6):
        for f in range(32):
            old = original[c,f,'BASE20']
            for a in harness.ARMS:
                if any(rows[c,f,a][k] != old[k] for k in harness.PAIR_FIELDS):
                    raise ValueError(f'ACC observation differs from B at {c+1}/{f}/{a}')
            for a in ('BASE20','BASE40'):
                old,new = original[c,f,a],rows[c,f,a]
                if old['status'] == new['status'] == 'ok':
                    if old['info_errors'] != new['info_errors'] or old['coded_errors'] != new['coded_errors']:
                        raise ValueError('frozen reference decoder result differs from B')
                    max_diff = max(max_diff,abs(old['orthogonal_risk']-new['orthogonal_risk']))
    if max_diff > 1e-10:
        raise ValueError('frozen reference risk differs from B')
    return dict(observation_blocks=192, matched_reference_rows=384,
                max_reference_risk_difference=max_diff, passed=True)


def aggregate(sample):
    value = metrics(sample)
    if value['errors']:
        return value
    value.update(mean_committed_iterations=float(np.mean([r['committed_iterations'] for r in sample])),
                 mean_map_evaluations=float(np.mean([r['map_evaluations'] for r in sample])),
                 mean_fft_count=float(np.mean([r['fft_count'] for r in sample])),
                 mean_acceleration_overhead_seconds=float(np.mean([r['overhead_seconds'] for r in sample])),
                 accepted_proposals=sum(t.get('accepted',False) for r in sample for t in r['trace']),
                 rejected_proposals=sum(t.get('rejected',False) for r in sample for t in r['trace']))
    return value


def cell_gate(candidate, base40, damp20, base25):
    if any(m['errors'] for m in (candidate,base40,damp20,base25)):
        return dict(available=False, quality_cost_pass=None, beats_both_controls=None)
    risk,fer,seconds = candidate['mean_orthogonal_risk'],candidate['fer'],candidate['mean_seconds']
    risk_pass = risk <= 1.10*base40['mean_orthogonal_risk']
    fer_pass = fer <= base40['fer']+.02
    time_pass = seconds <= .80*base40['mean_seconds']
    beats_damp = risk < damp20['mean_orthogonal_risk']
    beats_base25 = risk < base25['mean_orthogonal_risk']
    return dict(available=True, risk_pass=risk_pass, FER_pass=fer_pass, time_pass=time_pass,
                quality_cost_pass=risk_pass and fer_pass and time_pass,
                beats_DAMP20=beats_damp, beats_BASE25=beats_base25,
                beats_both_controls=beats_damp and beats_base25,
                risk_over_BASE40=risk/base40['mean_orthogonal_risk'],
                seconds_over_BASE40=seconds/base40['mean_seconds'],
                FER_minus_BASE40=fer-base40['fer'])


def summarize_gate(cells, arm):
    values = [c['gates'][arm] for c in cells]
    quality = sum(g['quality_cost_pass'] is True for g in values)
    both = sum(g['beats_both_controls'] is True for g in values)
    unavailable = sum(not g['available'] for g in values)
    verdict = ('PASS' if quality >= 4 and both >= 4 else
               'KILL' if quality+unavailable < 4 or both+unavailable < 4 else 'INCONCLUSIVE')
    return dict(verdict=verdict, required_cells=4, quality_cost_pass_cells=quality,
                beats_both_controls_cells=both, unavailable_cells=unavailable,
                quality_cost_cell_ids=[c['cell'] for c in cells if c['gates'][arm]['quality_cost_pass'] is True],
                beats_both_cell_ids=[c['cell'] for c in cells if c['gates'][arm]['beats_both_controls'] is True],
                marginal_pass_counts={key:sum(g.get(key) is True for g in values)
                    for key in ('risk_pass','FER_pass','time_pass','beats_DAMP20','beats_BASE25')})


def analyze(rows,result,b_binding):
    cells = []
    for ci,physical in enumerate(harness.CELLS):
        arms = {a:aggregate([rows[ci,f,a] for f in range(32)]) for a in harness.ARMS}
        gates = {a:cell_gate(arms[a],arms['BASE40'],arms['DAMP20'],arms['BASE25']) for a in CANDIDATES}
        cells.append(dict(cell=ci+1,snr_db=physical[0],rho=physical[1],L=physical[2],arms=arms,gates=gates))
    gates = {a:summarize_gate(cells,a) for a in CANDIDATES}
    overall = ('PASS' if any(g['verdict'] == 'PASS' for g in gates.values()) else
               'KILL' if all(g['verdict'] == 'KILL' for g in gates.values()) else 'INCONCLUSIVE')
    pooled = {a:aggregate([rows[c,f,a] for c in range(6) for f in range(32)]) for a in harness.ARMS}
    errors = [dict(cell=c+1,frame=f,arm=a,error=r['error']) for (c,f,a),r in rows.items() if r['status'] != 'ok']
    return dict(schema=harness.SPEC['schema'],overall=overall,candidate_gates=gates,cells=cells,
                pooled_descriptive=pooled,integrity=dict(rows=len(rows),errors=errors,
                    n_error_rows=len(errors),source_sha256=result['manifest']['sources'],
                    archived_B_binding=b_binding,shuffled_order_checked=True),
                compute=dict(receiver_calls=len(rows),
                    registered_committed_updates=37440,
                    observed_committed_updates=sum(r.get('committed_iterations',0) for r in rows.values()),
                    observed_map_evaluations=sum(r.get('map_evaluations',0) for r in rows.values()),
                    map_transform_charges=sum(r.get('fft_count',0) for r in rows.values()),
                    sum_receiver_wall_seconds=sum(r['seconds'] for r in rows.values()),
                    sum_shard_wall_seconds=sum(r['wall_seconds'] for r in result['shard_receipts']),
                    load_screen_calls=0),
                gate_interpretation='One candidate must pass risk/FER/time jointly in >=4 cells AND beat both risk controls jointly in >=4 cells; the two sets need not coincide.',
                limitations=['Headroom screen uses the B observations: six cells, 32 frames each, R=1, known support; no independent confirmation.',
                    'Cell point counts decide; pooled endpoints are descriptive.',
                    'Full receiver wall time includes acceleration, rejected maps and cheap h observation; excludes post-call truth scoring.',
                    'Per-step overhead excludes map time; full seconds includes every rejected-trial map.',
                    'Concurrent single-thread wall time on one host; not an isolated CPU process-time benchmark.',
                    'No load screen, Kc inference or hyperparameter retuning.'])


def render(d):
    lines = ['# Frozen ACC headroom screen','',f"Gate verdict: **{d['overall']}**. 1536 registered receiver calls; no load screen.", '',
             '| Candidate | Joint risk/FER/time cells | Beats both risk controls | Verdict |','|---|---:|---:|---|']
    for a,g in d['candidate_gates'].items():
        lines.append(f"| {a} | {g['quality_cost_pass_cells']}/6 | {g['beats_both_controls_cells']}/6 | {g['verdict']} |")
    lines += ['',d['gate_interpretation'],'','| Cell | Candidate | Risk / BASE40 | FER − BASE40 | Seconds / BASE40 | Joint pass | Beats both |',
              '|---|---|---:|---:|---:|---|---|']
    def fmt(v):
        return 'unavailable' if v is None else f'{v:.6g}'
    for c in d['cells']:
        for a,g in c['gates'].items():
            lines.append(f"| {c['cell']} | {a} | {fmt(g.get('risk_over_BASE40'))} | {fmt(g.get('FER_minus_BASE40'))} | "
                         f"{fmt(g.get('seconds_over_BASE40'))} | {g['quality_cost_pass']} | {g['beats_both_controls']} |")
    lines += ['','Pooled across six cells (192 frames per arm, descriptive):','','| Arm | Risk | FER | Seconds/frame | Maps/frame | Accel overhead/frame |',
              '|---|---:|---:|---:|---:|---:|']
    for a,m in d['pooled_descriptive'].items():
        lines.append(f"| {a} | {fmt(m.get('mean_orthogonal_risk'))} | {fmt(m.get('fer'))} | {fmt(m['mean_seconds'])} | "
                     f"{fmt(m.get('mean_map_evaluations'))} | {fmt(m.get('mean_acceleration_overhead_seconds'))} |")
    lines += ['',f"Integrity: {d['integrity']['rows']} rows; {d['integrity']['n_error_rows']} errors. "
              f"All 192 observation blocks match archived B; maximum BASE20/40 risk difference {d['integrity']['archived_B_binding']['max_reference_risk_difference']:.3g}.",
              '', 'Facts: measured endpoints and frozen cell counts above. No later candidate choice or tuning enters the gate.',
              'Inference: KILL closes this frozen acceleration route; it is not a theorem about every possible accelerator.',
              '',*['- '+x for x in d['limitations']],'']
    return '\n'.join(lines)


def self_check():
    def m(risk,fer,seconds):
        return dict(errors=0,mean_orthogonal_risk=risk,fer=fer,mean_seconds=seconds)
    ref,damp,base25 = m(1.,.25,1.),m(1.2,.2,.6),m(1.1,.2,.7)
    good = cell_gate(m(1.05,.25,.8),ref,damp,base25)
    bad_fer = cell_gate(m(1.05,.28125,.8),ref,damp,base25)
    assert good['quality_cost_pass'] and good['beats_both_controls']
    assert not bad_fer['quality_cost_pass'] and not bad_fer['FER_pass']
    cells = [dict(cell=i+1,gates={'AA2':good if i<4 else bad_fer}) for i in range(6)]
    assert summarize_gate(cells,'AA2')['verdict'] == 'PASS'
    cells[3]['gates']['AA2'] = bad_fer
    assert summarize_gate(cells,'AA2')['verdict'] == 'KILL'
    invalid = cell_gate(dict(good,errors=1),ref,damp,base25)
    assert not invalid['available'] and invalid['quality_cost_pass'] is None
    # Passing the three marginal predicates in different cells must not count
    # as four joint cells; a pooled gain is not the registered cell gate.
    x = dict(good,quality_cost_pass=False,time_pass=False)
    y = dict(good,quality_cost_pass=False,risk_pass=False)
    mixed = [dict(cell=i+1,gates={'AA2':x if i<3 else y}) for i in range(6)]
    assert summarize_gate(mixed,'AA2')['quality_cost_pass_cells'] == 0
    return dict(passed=True,checks=['inclusive_frozen_boundaries','FER_1of32_exceeds_margin',
                '4of6_not3of6','failure_not_dropped','joint_not_marginal_or_pooled'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--b-out',type=Path,default=harness.HERE/'out/c1B/b1b2')
    p.add_argument('--self-check',action='store_true')
    args = p.parse_args()
    if args.self_check:
        compact_write(args.out,self_check())
        return
    out = args.out.resolve()
    rows,result,md5s = read_campaign(out)
    binding = compare_archived_b(rows,args.b_out)
    report = analyze(rows,result,binding)
    compact_write(out/'analysis.json',report)
    (out/'analysis.md').write_text(render(report))
    (out/'REMOTE_ROWS_MD5.txt').write_text(''.join(f'{md5}  {path}\n' for path,md5 in md5s.items()))
    compact_write(out/'analysis_provenance.json',dict(analyzer_sha256=digest(Path(__file__)),
                  merged_result_sha256=digest(out/'results.json'),rows_md5=md5s))
    print(json.dumps(dict(overall=report['overall'],candidate_gates=report['candidate_gates']),indent=1))


if __name__ == '__main__':
    main()
