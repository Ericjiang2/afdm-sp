"""Offline recount and exact-control comparison after the observed seal is committed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path[:0] = [str(EXPERIMENTS/'tf_geometry_reopen_20260922'),
                str(EXPERIMENTS/'tf_production_gap_audit_20260922'), str(HERE)]
import analyze_reopening as old_analysis  # noqa: E402
import run_reopening as old_runner  # noqa: E402
import run_validation as runner  # noqa: E402
from audit_io import attach, load_bound, sha256, unpack, write_csv, write_json  # noqa: E402

STAGES = ('message_handling','y_transform','geometry_setup',
          'structural_field_build','structural_scoring',
          'structural_selection_trace','structural_refit_refresh',
          'structural_fallback_direct','local_refinement',
          'geometry_finalization','geometry_wrapper_overhead',
          'wrapper_validation','channel_construction','tf','ldpc','checkpoint_write',
          'raw_serialization_hash')
DEADLINES = (.5, 1.)


def _same_continuous(a, b, label, *, atol=2e-10, rtol=0):
    left, right = np.asarray(a), np.asarray(b)
    if left.shape != right.shape or not np.allclose(left, right, rtol=rtol, atol=atol):
        raise ValueError(f'exact-control continuous mismatch: {label}')


def compare_exact_control(global_raw, compact_raw):
    """No truth enters the geometry equivalence check."""
    direct = global_raw['geometry_result']
    compact = compact_raw['geometry_result']
    if len(direct['global_trace']) != len(compact['global_trace']):
        raise ValueError('exact-control global step count differs')
    for i, (d, c) in enumerate(zip(direct['global_trace'], compact['global_trace'])):
        for key in ('entering_paths','candidate_delays','candidate_dopplers','valid',
                    'top_k'):
            if key in ('candidate_delays','candidate_dopplers','valid'):
                if not np.array_equal(d[key], c[key]):
                    raise ValueError(f'exact-control {key} differs at step {i}')
            elif key == 'top_k':
                if len(d[key]) != len(c[key]):
                    raise ValueError(f'exact-control top20 count differs at step {i}')
                for j, (a, b) in enumerate(zip(d[key], c[key])):
                    if (a['rank'], a['slot'], a['replacement'], a['paths']) != (
                            b['rank'], b['slot'], b['replacement'], b['paths']):
                        raise ValueError(f'exact-control top20 geometry differs at {i}/{j}')
                    _same_continuous(a['frozen_score'], b['frozen_score'],
                                     f'top20 score {i}/{j}')
            elif d[key] != c[key]:
                raise ValueError(f'exact-control {key} differs at step {i}')
        if (d['selected'] is None) != (c['selected'] is None):
            raise ValueError(f'exact-control selected candidate presence differs at {i}')
        if d['selected'] is not None:
            for key in ('rank','slot','replacement','paths'):
                if d['selected'][key] != c['selected'][key]:
                    raise ValueError(f'exact-control selected {key} differs at {i}')
            _same_continuous(d['selected']['frozen_score'],
                c['selected']['frozen_score'], f'selected score {i}')
        direct_scores, compact_scores = np.asarray(d['scores']), np.asarray(c['scores'])
        if (direct_scores.shape != compact_scores.shape or
                not np.isfinite(direct_scores).all() or
                not np.isfinite(compact_scores).all()):
            raise ValueError(f'exact-control full candidate scores malformed at {i}')
        _same_continuous(direct_scores[d['valid']], compact_scores[d['valid']],
                         f'full candidate scores {i}')
        if (d['accepted'] is None) != (c['accepted'] is None):
            raise ValueError(f'exact-control accept/hold differs at step {i}')
        if d['accepted'] is not None:
            for key in ('slot','old','new'):
                if d['accepted'][key] != c['accepted'][key]:
                    raise ValueError(f'exact-control accepted {key} differs at step {i}')
            for key in ('frozen_score','direct_score','decrease'):
                _same_continuous(d['accepted'][key], c['accepted'][key],
                                 f'accepted {key} {i}')
    if ([(e['step'],e['slot'],e['old'],e['new']) for e in direct['edits']] !=
            [(e['step'],e['slot'],e['old'],e['new']) for e in compact['edits']]):
        raise ValueError('exact-control discrete replacement sequence differs')
    if len(direct['local_trace']) != len(compact['local_trace']):
        raise ValueError('exact-control local trial schedule differs')
    for i, (d, c) in enumerate(zip(direct['local_trace'], compact['local_trace'])):
        for key in ('pass_index','slot','accepted','trial_count',
                    'rejected_duplicate_trials','local_phase_entering_paths'):
            if d[key] != c[key]:
                raise ValueError(f'exact-control local {key} differs at {i}')
        for key in ('start','endpoint'):
            if d[key]['delay'] != c[key]['delay']:
                raise ValueError(f'exact-control local {key} delay differs at {i}')
            _same_continuous(d[key]['doppler'], c[key]['doppler'],
                             f'local {key} Doppler {i}')
        for key in ('center','bounds','start_objective','endpoint_objective'):
            _same_continuous(d[key], c[key], f'local {key} {i}')
        if len(d['trials']) != len(c['trials']) or len(d['trials']) != d['trial_count']:
            raise ValueError(f'exact-control local trial count differs at {i}')
        for trial_index, (a, b) in enumerate(zip(d['trials'], c['trials'])):
            if a['valid'] != b['valid']:
                raise ValueError(f'exact-control local trial validity differs at {i}/{trial_index}')
            _same_continuous(a['doppler'], b['doppler'],
                             f'local trial Doppler {i}/{trial_index}')
            if a['valid']:
                _same_continuous(a['score'], b['score'],
                                 f'local trial score {i}/{trial_index}')
            elif a['score'] is not None or b['score'] is not None:
                raise ValueError(f'exact-control invalid local trial score differs at {i}/{trial_index}')
    if len(direct['paths']) != len(compact['paths']):
        raise ValueError('exact-control final physical slot count differs')
    for i, (a, b) in enumerate(zip(direct['paths'], compact['paths'])):
        if a['delay'] != b['delay']:
            raise ValueError('exact-control final physical delays differ')
        _same_continuous(a['doppler'], b['doppler'], f'final path Doppler {i}')
    for key in ('gains','objective_before','objective_after'):
        _same_continuous(direct[key], compact[key], f'geometry {key}')
    for key in ('gains','mu','variance','extrinsic','app','gain_variance'):
        _same_continuous(global_raw['detector'][key], compact_raw['detector'][key],
                         f'final TF {key}')
    for key in ('incoming_llr','raw_app','raw_check_extrinsic'):
        _same_continuous(global_raw['decoder'][key], compact_raw['decoder'][key],
                         f'final decoder {key}')
    if not np.array_equal(global_raw['decoder']['decoded'], compact_raw['decoder']['decoded']):
        raise ValueError('exact-control final decoded bits differ')
    return dict(global_steps=len(direct['global_trace']),
                local_endpoints=len(direct['local_trace']),
                discrete_replacements=len(direct['edits']))


def compare_previous_final(previous, current, arm):
    old, new = previous['geometry_result'], current['geometry_result']
    if len(old['paths']) != len(new['paths']):
        raise ValueError(f'{arm} prior final slot count differs')
    for index, (a, b) in enumerate(zip(old['paths'], new['paths'])):
        if a['delay'] != b['delay']:
            raise ValueError(f'{arm} prior final delay differs')
        _same_continuous(a['doppler'], b['doppler'], f'{arm} prior Doppler {index}')
    for key in ('gains','objective_after'):
        _same_continuous(old[key], new[key], f'{arm} prior geometry {key}')
    for key in ('gains','mu','variance','extrinsic','app'):
        _same_continuous(previous['detector'][key], current['detector'][key],
                         f'{arm} prior TF {key}')
    for key in ('incoming_llr','raw_app','raw_check_extrinsic'):
        _same_continuous(previous['decoder'][key], current['decoder'][key],
                         f'{arm} prior decoder {key}')
    if not np.array_equal(previous['decoder']['decoded'], current['decoder']['decoded']):
        raise ValueError(f'{arm} prior final bits differ')


def stage_costs(rows):
    records = []
    for arm in runner.ARMS:
        selected = [r for r in rows if r['arm'] == arm and r['kind'] == 'trigger']
        if len(selected) != 43:
            raise ValueError(f'triggered cost allocation differs for {arm}')
        total = np.array([r['added_complete_branch_seconds'] for r in selected])
        for stage in STAGES:
            values = np.array([r['branch_exclusive_stages'][stage] for r in selected])
            stats = old_analysis.cost_summary(values)
            records.append(dict(arm=arm, stage=stage, **stats,
                mean_share_of_complete_branch=float(np.mean(values)/np.mean(total))))
        for stage in ('setup_seconds','native_two_rounds_seconds',
                      'baseline_parity_seconds','native_checkpoint_write_seconds',
                      'wrapper_bookkeeping_seconds'):
            values = np.array([r[stage] for r in selected])
            records.append(dict(arm=arm, stage=stage, **old_analysis.cost_summary(values),
                                mean_share_of_complete_branch=None))
    return records


def discarded_compact_summary(rows):
    """Report abandoned compact time without adding it twice to branch cost."""
    result = {}
    for arm in runner.ARMS:
        selected = [row for row in rows if row['arm'] == arm]
        if not selected:
            raise ValueError(f'missing discarded-work rows for {arm}')
        reasons = [dict(observation_id=row['observation_id'], reason=row['fallback_reason'])
                   for row in selected if row['numerical_fallback']]
        result[arm] = dict(count=len(reasons),
            seconds=old_analysis.cost_summary([
                row['discarded_compact_seconds'] for row in selected]),
            reasons=reasons, nested_in_exclusive_stages=True)
    return result


def _bound(args):
    """Seal, Git-show receipt, source and stage0 checks precede any truth access."""
    observed, prior, run = args.observed, args.prior_observed, args.run
    seal = runner.verify_seal(observed)
    old_runner.verify_seal(prior)
    binding = old_analysis._check_seal_binding(args.seal_commit,
        args.seal_binding, observed/'observed_seal.json')
    manifest = json.loads((observed/'manifest.json').read_text())
    previous = json.loads((prior/'manifest.json').read_text())
    qualification = json.loads(args.qualification.read_text())
    local_audit = json.loads(args.local_audit.read_text())
    original = json.loads((run/'manifest.json').read_text())
    evidence = attach(args.source, args.baseline)
    from audit_io import verify_sources
    verify_sources(original, args.source, args.baseline, evidence)
    receipt = json.loads(args.a_receipt.read_text())
    if (manifest.get('schema') != runner.SCHEMA or seal.get('completed_checkpoints') != 675
            or manifest.get('original_manifest_sha256') != sha256(run/'manifest.json')
            or manifest.get('original_ledger_sha256') != sha256(run/'ledger.jsonl')
            or manifest.get('original_context_header_sha256') != sha256(run/'context_header.json')
            or manifest.get('previous_observed_seal_sha256') != sha256(prior/'observed_seal.json')
            or manifest.get('previous_selection_sha256') != sha256(prior/'selection.json')
            or manifest.get('selection_sha256') != sha256(observed/'selection.json')
            or manifest.get('previous_kernel_sha256') !=
                previous['code_hashes']['tf_geometry_reopen_20260922/geometry_reopen.py']
            or manifest.get('stage0_receipt_sha256') != sha256(args.qualification)
            or manifest.get('local_trial_audit_sha256') != sha256(args.local_audit)
            or manifest.get('a_receipt_sha256') != sha256(args.a_receipt)
            or manifest.get('common_config_sha256') != evidence.canonical_hash(
                manifest.get('common_config'))
            or manifest.get('source_hashes_sha256') != evidence.canonical_hash(
                manifest.get('source_hashes'))
            or receipt.get('status') != 'pass'
            or receipt.get('ldpc_cache_sha256') != manifest.get('cache_sha256')
            or qualification.get('status') != 'pass'
            or qualification.get('qualified_entered_states') != 145
            or local_audit.get('status') != 'pass'
            or local_audit.get('receiver_calls') != 0
            or local_audit.get('checked_arm_states') != 150
            or local_audit.get('qualification_receipt_sha256') != sha256(args.qualification)
            or local_audit.get('files', {}).get('local_trial_checks.csv') !=
                sha256(args.local_audit.parent/'local_trial_checks.csv')):
        raise ValueError('validation manifest, prior seal or stage0 identity differs')
    if json.loads((observed/'selection.json').read_text()) != \
            json.loads((prior/'selection.json').read_text()):
        raise ValueError('validation selection differs from prior fixed 75')
    if (manifest.get('frozen_source_hashes') != original['source_hashes']
            or manifest.get('frozen_baseline_hashes') != original['baseline_source_hashes']):
        raise ValueError('validation frozen source identity differs')
    for relative, digest in manifest['source_hashes'].items():
        if sha256(EXPERIMENTS/relative) != digest:
            raise ValueError(f'validation source changed: {relative}')
    cache = args.baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    if sha256(cache) != receipt['ldpc_cache_sha256']:
        raise ValueError('actual LDPC cache changed')
    with np.load(cache, allow_pickle=False) as saved:
        code = {key:np.asarray(saved[key]) for key in ('H','G','free_cols')}
    return evidence, code, manifest, binding


def analyze(args):
    args.observed, args.prior_observed, args.run = map(
        lambda p:p.resolve(), (args.observed,args.prior_observed,args.run))
    if args.out.exists():
        raise FileExistsError('validation analysis output already exists')
    evidence, code, manifest, binding = _bound(args)
    original_header = json.loads((args.run/'context_header.json').read_text())
    rho = float(original_header['system']['rho'])
    if not np.isfinite(rho) or not 0 < rho < 1:
        raise ValueError('original APP power split differs')
    # Truth is first opened here, after the complete new and prior observed seals.
    original = old_analysis._selected_original(args.observed, args.run,
        __import__('audit_io'), evidence, code)
    trigger_ids = {stem for stem, item in original.items()
                   if item['selection']['kind']=='trigger'}
    old23, old_b_hash = old_analysis._old_23(args.prior_b,
        sha256(args.run/'manifest.json'), trigger_ids)
    previous_ledger = [json.loads(line) for line in
                       (args.prior_observed/'ledger.jsonl').read_text().splitlines()]
    previous_by_key = {(r['observation_id'],r['arm']):r for r in previous_ledger}
    ledger = [json.loads(line) for line in
              (args.observed/'ledger.jsonl').read_text().splitlines()]
    by_key = {(r['observation_id'],r['arm']):r for r in ledger}
    if len(by_key) != 225:
        raise ValueError('validation ledger key count differs')
    outcomes, timing_rows, equivalence = [], [], []
    mismatches = []
    for stem, item in original.items():
        truth = item['coded'], item['info']
        original_cp = [load_bound(evidence, args.run/cp['path'], cp['artifact_sha256'])
                       for cp in item['record']['checkpoints']]
        original_bits = [unpack(cp['decoded']) for cp in original_cp]
        raws = {}
        for arm in runner.ARMS:
            row = by_key[(stem,arm)]
            if (row['source_hashes_sha256'] != manifest['source_hashes_sha256']
                    or row['common_config_sha256'] != manifest['common_config_sha256']):
                raise ValueError('validation call source/config binding differs')
            raw = load_bound(evidence, args.observed/row['raw_path'], row['raw_sha256'])
            raws[arm] = raw
            if raw['observation_id'] != stem or raw['arm'] != arm:
                raise ValueError('validation raw identity differs')
            old_analysis.check_observed_branch_inputs(raw, rho)
            bits = []
            cp_results = []
            for cp_row in row['checkpoints']:
                cp = load_bound(evidence, args.observed/cp_row['path'],
                                cp_row['artifact_sha256'])
                decoded = np.asarray(cp['decoded'])
                counts = old_analysis.recount(decoded, *truth, code['H'], code['free_cols'])
                if counts['syndrome_weight'] != cp_row['syndrome_weight']:
                    raise ValueError(f'validation syndrome recount differs {stem}/{arm}')
                bits.append(decoded)
                cp_results.append(dict(round=cp_row['round'],
                    ready_seconds=cp_row['decision_ready_seconds'], **counts))
            old_analysis.check_checkpoint_bits(original_bits, bits, raw)
            if not np.array_equal(raw['decoder']['decoded'], bits[-1]):
                raise ValueError('validation raw final decision differs from checkpoint')
            if set(row['branch_exclusive_stages']) != set(STAGES):
                raise ValueError('validation branch stage inventory differs')
            if not np.isclose(sum(row['branch_exclusive_stages'].values()),
                row['added_complete_branch_seconds'], rtol=0, atol=1e-7):
                raise ValueError('validation stage/complete branch sum differs')
            if not np.isclose(row['wrapper_seconds'],
                row['setup_seconds']+row['baseline_bookkeeping_seconds']+
                row['native_two_rounds_seconds']+row['baseline_parity_seconds']+
                row['added_complete_branch_seconds']+row['wrapper_bookkeeping_seconds'],
                rtol=0, atol=1e-7):
                raise ValueError('validation full wrapper stage sum differs')
            for step in raw['geometry_result']['global_trace']:
                old_analysis._check_trace(step)
            if arm == 'LOCAL20' and raw['geometry_result']['global_trace']:
                raise ValueError('LOCAL20 ran structural replacements')
            final = cp_results[-1]
            diagnostics = raw['geometry_result']['diagnostics']
            discarded = diagnostics['discarded_compact_evaluations']
            discarded_count = (sum(int(value) for value in discarded.values()
                                   if isinstance(value, (int, np.integer)))
                               if isinstance(discarded, dict) else 0)
            discarded_seconds = float(diagnostics['stage_timing']['discarded_compact_seconds'])
            fallback = bool(diagnostics['numerical_fallback'])
            if (not np.isfinite(discarded_seconds) or discarded_seconds < 0
                    or fallback != bool(diagnostics['fallback_reason'])
                    or (not fallback and discarded_seconds != 0)):
                raise ValueError('discarded compact work accounting differs')
            outcome = dict(observation_id=stem, kind=item['selection']['kind'],
                arm=arm, old23_member=stem in old23,
                final_info_errors=final['info_errors'],
                final_coded_errors=final['coded_errors'],
                final_syndrome_weight=final['syndrome_weight'],
                final_correct=final['correct'],
                final_valid_but_wrong=final['valid_but_wrong'],
                rescue=bool(stem in trigger_ids and final['correct']),
                forced_control_harm=bool(stem not in trigger_ids and not final['correct']),
                added_complete_branch_seconds=row['added_complete_branch_seconds'],
                branch_decision_seconds=row['branch_decision_seconds'],
                wrapper_seconds=row['wrapper_seconds'],
                numerical_fallback=fallback,
                fallback_seconds=row['branch_exclusive_stages']['structural_fallback_direct'],
                fallback_reason=diagnostics['fallback_reason'],
                discarded_compact_evaluations=discarded_count,
                discarded_compact_seconds=discarded_seconds)
            for deadline in DEADLINES:
                chosen = old_analysis.latest_available(cp_results, deadline)
                label = '0500ms' if deadline == .5 else '1000ms'
                outcome[f'{label}_available_round'] = None if chosen is None else chosen['round']
                outcome[f'{label}_correct'] = None if chosen is None else chosen['correct']
            outcomes.append(outcome)
            timing_rows.append(dict(observation_id=stem, kind=item['selection']['kind'],
                arm=arm, setup_seconds=row['setup_seconds'],
                native_two_rounds_seconds=row['native_two_rounds_seconds'],
                baseline_parity_seconds=row['baseline_parity_seconds'],
                wrapper_bookkeeping_seconds=row['wrapper_bookkeeping_seconds'],
                native_checkpoint_write_seconds=row['native_checkpoint_write_seconds'],
                added_complete_branch_seconds=row['added_complete_branch_seconds'],
                wrapper_seconds=row['wrapper_seconds'],
                discarded_compact_seconds=discarded_seconds,
                branch_exclusive_stages=row['branch_exclusive_stages']))
            if arm in ('LOCAL20','GLOBAL20'):
                previous = previous_by_key[(stem,arm)]
                prev_raw = load_bound(evidence, args.prior_observed/previous['raw_path'],
                                      previous['raw_sha256'])
                try:
                    compare_previous_final(prev_raw, raw, arm)
                except ValueError as error:
                    mismatches.append(dict(observation_id=stem, arm=arm,
                                           reason=str(error)))
        try:
            equivalence.append(dict(observation_id=stem,
                **compare_exact_control(raws['GLOBAL20'], raws['CSTATE20'])))
        except ValueError as error:
            mismatches.append(dict(observation_id=stem, arm='CSTATE20/GLOBAL20',
                                   reason=str(error)))
    trigger = [r for r in outcomes if r['kind']=='trigger']
    controls = [r for r in outcomes if r['kind']=='control']
    summary = dict(status='fail' if mismatches else 'pass',
        evidence_integrity='pass',
        scope='same75 previously examined 6.5dB observations; development evidence',
        receiver_calls_verified=225, checkpoints_recounted=675,
        direct_compact_equivalence_count=len(equivalence), mismatches=mismatches,
        trigger_rescues={arm:sum(r['rescue'] for r in trigger if r['arm']==arm)
                         for arm in runner.ARMS},
        old23_rescues={arm:sum(r['rescue'] and r['old23_member']
                               for r in trigger if r['arm']==arm)
                       for arm in runner.ARMS},
        forced_control_harms={arm:sum(r['forced_control_harm'] for r in controls
                                      if r['arm']==arm) for arm in runner.ARMS},
        forced_control_valid_but_wrong_ids={arm:[r['observation_id'] for r in controls
            if r['arm']==arm and r['final_valid_but_wrong']] for arm in runner.ARMS},
        triggered_complete_branch_cost={arm:old_analysis.cost_summary([
            r['added_complete_branch_seconds'] for r in trigger if r['arm']==arm])
            for arm in runner.ARMS},
        stage_costs=stage_costs(timing_rows),
        fallback_counts={arm:sum(r['numerical_fallback'] for r in outcomes
                                 if r['arm']==arm) for arm in runner.ARMS},
        fallback_costs={arm:old_analysis.cost_summary([
            r['fallback_seconds'] for r in outcomes if r['arm']==arm])
            for arm in runner.ARMS},
        discarded_compact_evaluations={arm:sum(
            r['discarded_compact_evaluations'] for r in outcomes if r['arm']==arm)
            for arm in runner.ARMS},
        discarded_compact_costs=discarded_compact_summary(outcomes),
        prior_observed_seal_sha256=sha256(args.prior_observed/'observed_seal.json'),
        observed_seal_sha256=sha256(args.observed/'observed_seal.json'),
        seal_commit=args.seal_commit, seal_binding=binding,
        prior_b_ledger_sha256=old_b_hash)
    summary['expected_outcomes'] = dict(
        global_trigger_rescues_31=summary['trigger_rescues']['GLOBAL20']==31,
        compact_trigger_rescues_31=summary['trigger_rescues']['CSTATE20']==31,
        compact_old23_rescues_15=summary['old23_rescues']['CSTATE20']==15,
        compact_controls_successful_32=summary['forced_control_harms']['CSTATE20']==0,
        compact_mean_complete_branch_at_most_0p6s=
            summary['triggered_complete_branch_cost']['CSTATE20']['mean_seconds']<=.6)
    summary['paired_trigger_table'] = old_analysis.paired_2x2([
        dict(LOCAL20_correct=next(r['final_correct'] for r in trigger
                                  if r['observation_id']==stem and r['arm']=='GLOBAL20'),
             GLOBAL20_correct=next(r['final_correct'] for r in trigger
                                   if r['observation_id']==stem and r['arm']=='CSTATE20'))
        for stem in sorted(trigger_ids)])
    if not all(summary['expected_outcomes'].values()):
        summary['status'] = 'fail'
    summary['deadline_outcomes'] = {}
    for arm in runner.ARMS:
        summary['deadline_outcomes'][arm] = {}
        for label in ('0500ms','1000ms'):
            subset = [r for r in trigger if r['arm']==arm]
            ready = [r for r in subset if r[f'{label}_available_round'] is not None]
            summary['deadline_outcomes'][arm][label] = dict(
                ready_count=len(ready), correct_count=sum(r[f'{label}_correct'] for r in ready),
                unready_count=len(subset)-len(ready),
                fallback_round0_or1_count=sum(r[f'{label}_available_round'] in (0,1)
                                               for r in ready))
    args.out.mkdir(parents=True)
    write_json(args.out/'summary.json', summary)
    write_csv(args.out/'arm_outcomes.csv', outcomes)
    write_csv(args.out/'stage_costs.csv', summary['stage_costs'])
    write_csv(args.out/'timing_rows.csv', timing_rows)
    analysis_files = {p.name:sha256(p) for p in args.out.iterdir() if p.is_file()}
    write_json(args.out/'receipt.json', dict(
        evidence_integrity='pass', scientific_gate=summary['status'],
        observed_seal_sha256=sha256(args.observed/'observed_seal.json'),
        prior_observed_seal_sha256=sha256(args.prior_observed/'observed_seal.json'),
        git_commit=args.seal_commit, seal_binding_sha256=sha256(args.seal_binding),
        qualification_sha256=sha256(args.qualification),
        local_trial_audit_sha256=sha256(args.local_audit),
        source_hashes=dict(manifest['source_hashes'],
            **{'tf_cstate_validation_20260922/analyze_validation.py':
               sha256(Path(__file__))}),
        receiver_calls_recounted=225, checkpoints_recounted=675,
        files=analysis_files))
    if summary['status'] != 'pass':
        raise ValueError(f'validation failed: {len(mismatches)} paired mismatches; '
                         'inspect expected_outcomes and cost gate')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('observed','prior-observed','run','source','baseline','a-receipt',
                 'qualification','local-audit','prior-b','seal-binding','out'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--seal-commit', required=True)
    analyze(parser.parse_args())
