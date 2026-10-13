"""Read frozen Part-B evidence without constructing or calling a receiver."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def write_csv(path, rows):
    if not rows:
        raise ValueError('cannot silently write an empty evidence table')
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, separators=(',', ':'))
                             if isinstance(value, (list, dict)) else value
                             for key, value in row.items()})


def attach(source, baseline):
    sys.path[:0] = [str(Path(source) / 'src'), str(Path(baseline) / 'src'),
                   str(Path(baseline) / 'upstream' / 'spafdm_receiver_handoff')]
    import evidence
    return evidence


def unpack(value):
    packed = np.asarray(value['packed'])
    count = value['length']
    if packed.dtype != np.uint8 or packed.ndim != 1 or packed.size != (count + 7) // 8:
        raise ValueError('invalid saved packed bit vector')
    raw = np.unpackbits(packed)
    if np.any(raw[count:]):
        raise ValueError('nonzero packed padding')
    return raw[:count].copy()


def load_bound(evidence, path, digest):
    if sha256(path) != digest:
        raise ValueError(f'saved artifact hash differs: {path}')
    return evidence.load_artifact(path)[0]


def verify_sources(manifest, source, baseline, evidence):
    for key, root in [('source_hashes', source), ('baseline_source_hashes', baseline)]:
        if evidence.source_hashes(root) != manifest[key]:
            raise ValueError(f'executed {key} differ from Part-B manifest')
    if manifest['source_commit'] != '2d130b4d' or manifest['baseline_commit'] != '31d5ec0d':
        raise ValueError('unexpected numerical source identity')


def read_records(run):
    records = [json.loads(line) for line in (Path(run) / 'ledger.jsonl').read_text().splitlines()]
    keys = [(r['snr_centi_db'], r['frame'], r['arm']) for r in records]
    if len(records) != 9696 or len(set(keys)) != 9696:
        raise ValueError('Part-B attempt allocation differs')
    tf = [r for r in records if r['arm'] == 'TF_J20_R2']
    if {(r['snr_centi_db'], r['frame']) for r in tf} != {
            (snr, frame) for snr in [600, 650, 700] for frame in range(1024)}:
        raise ValueError('3072 frozen TF observations not complete')
    return records, tf


def selected_records(tf):
    cell = sorted((r for r in tf if r['snr_centi_db'] == 650), key=lambda r: r['frame'])
    bad = [r for r in cell if r['info_errors'] is not None and r['info_errors'] > 0][:32]
    good = [r for r in cell if r['info_errors'] == 0][:32]
    if len(bad) != 32 or len(good) != 32:
        raise ValueError('insufficient fixed first32/32 selection')
    return sorted(bad + good, key=lambda r: r['frame'])


def extract(run, source, baseline, out):
    run, out = Path(run), Path(out)
    if out.exists():
        raise FileExistsError('A extraction output already exists; preserve original')
    evidence = attach(source, baseline)
    manifest = json.loads((run / 'manifest.json').read_text())
    verify_sources(manifest, source, baseline, evidence)
    records, tf = read_records(run)
    header = json.loads((run / 'context_header.json').read_text())
    cache = Path(baseline) / 'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    with np.load(cache, allow_pickle=False) as z:
        H, G, free = z['H'], z['G'], z['free_cols']
    if hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest() != header['code_g_sha256']:
        raise ValueError('actual generator differs')
    out.mkdir(parents=True)
    stages, frames = [], []
    for record in records:
        previous = 0.
        for cp in record['checkpoints']:
            e = cp['event']
            total = sum(float(e[k]) for k in ['ce', 'inference', 'decoder'])
            remainder = float(e['ready']) - previous - total
            if remainder < -1e-7:
                raise ValueError('negative stage accounting remainder')
            stages.append(dict(snr_centi_db=record['snr_centi_db'], frame=record['frame'],
                arm=record['arm'], round=cp['round'], status=record['status'],
                refit_seconds=e['ce'], refit_candidate_evaluations=e['ce_evaluations'],
                refit_individual_candidate_seconds=None, tf_or_detector_seconds=e['inference'],
                detector_iterations=e['inference_iterations'], decoder_seconds=e['decoder'],
                actual_ldpc_sweeps=e['decoder_iterations'], receiver_ready_seconds=e['ready'],
                stages_since_previous_ready_seconds=total, unsplit_remainder_seconds=remainder,
                remainder_scope='acquisition+interface' if cp['round'] == 0 else 'previous_checkpoint+interface',
                acquisition_seconds=None, complete_attempt_seconds=record['seconds'],
                after_final_ready_seconds=record['seconds']-record['checkpoints'][-1]['ready'],
                artifact_path=str(run / cp['path']), artifact_sha256=cp['artifact_sha256']))
            previous = float(e['ready'])
    for record in sorted(tf, key=lambda r: (r['snr_centi_db'], r['frame'])):
        snr, frame = record['snr_centi_db'], record['frame']
        stem = f's{snr}_f{frame:04d}'
        truth = load_bound(evidence, run / 'frames' / f'{stem}_truth.npz', record['frame_sha256'])
        obs = load_bound(evidence, run / 'frames' / f'{stem}_input.npz', record['input_sha256'])
        cps = [load_bound(evidence, run / cp['path'], cp['artifact_sha256'])
               for cp in record['checkpoints']]
        if len(cps) != 2:
            raise ValueError('frozen TF frame lacks its two completed checkpoints')
        coded, info = unpack(truth['coded']), unpack(truth['info'])
        states = [cp['snapshot'] for cp in cps]
        counts = []
        for saved, cp in zip(cps, record['checkpoints']):
            decoded = unpack(saved['decoded'])
            values = (int(np.count_nonzero(decoded[free] != info)),
                      int(np.count_nonzero(decoded != coded)),
                      int(np.count_nonzero((H @ decoded) % 2)))
            if values != (cp['info_errors'], cp['coded_errors'], cp['syndrome_weight']):
                raise ValueError(f'saved TF recount differs for {stem}')
            counts.append(values)
        first, final = counts
        ltrue = np.asarray(truth['l_i'], int)
        ls0, ls1 = (np.asarray(s['delays'], int) for s in states)
        nu0, nu1 = (np.asarray(s['dopplers'], float) for s in states)
        centers1 = np.array([nu0[np.flatnonzero(ls0 == delay)[0]] for delay in ls1])
        lo, hi = np.maximum(-3., centers1-.75), np.minimum(3., centers1+.75)
        distance = np.minimum(nu1-lo, hi-nu1)
        guard_data = sum(bool(t['data_precision_floor']) for s in states for t in s['inference_trace'])
        guard_gain = sum(bool(t['gain_precision_floor']) for s in states for t in s['inference_trace'])
        from physical import dkernel
        gains = np.asarray(truth['g_i'])
        nus = np.asarray(truth['k_real'])
        R = (ltrue[:,None] == ltrue[None,:]) * dkernel(nus[None,:]-nus[:,None], len(obs['y']))
        missing = ~np.isin(ltrue, ls1)
        energy = float(np.vdot(gains, R @ gains).real)
        missing_energy = float(np.vdot(gains[missing], R[np.ix_(missing,missing)] @ gains[missing]).real)
        rows = dict(observation_id=stem, snr_centi_db=snr, frame=frame,
            final_error=bool(final[0]), info_errors=final[0], coded_errors=final[1],
            syndrome_weight=final[2], valid_wrong_word=bool(final[0] and final[2] == 0),
            round1_info_errors=first[0], round1_coded_errors=first[1], round1_syndrome_weight=first[2],
            round2_rescue=bool(first[0] and not final[0]), round2_harm=bool(not first[0] and final[0]),
            initial_acquisition_paths=None, refit0_delays=ls0.tolist(), refit0_dopplers=nu0.tolist(),
            refit1_before_delays=ls0.tolist(), refit1_before_dopplers=nu0.tolist(),
            refit1_delays=ls1.tolist(), refit1_dopplers=nu1.tolist(), fitted_path_count=len(ls1),
            refit0_local_boundary_hit=None, refit1_local_boundary_hit=bool(np.any(distance <= .002)),
            refit1_min_boundary_distance=float(distance.min()),
            absolute_doppler_boundary_hit=bool(np.any(3.-np.abs(nu1)<=.002)),
            true_path_count=len(ltrue), true_distinct_delay_count=len(np.unique(ltrue)),
            missed_distinct_delay_count=len(set(ltrue)-set(ls1)),
            missed_distinct_delay_energy_fraction=missing_energy/energy,
            true_same_delay_multiplicity=bool(len(np.unique(ltrue))<len(ltrue)),
            represented_same_delay_underfit=bool(any(np.count_nonzero(ltrue==d)>np.count_nonzero(ls1==d) for d in set(ltrue)&set(ls1))),
            data_precision_floor_count=guard_data, gain_precision_floor_count=guard_gain,
            other_guard_activity=None, first_ready_seconds=record['checkpoints'][0]['ready'],
            final_ready_seconds=record['checkpoints'][-1]['ready'], complete_seconds=record['seconds'],
            first_decision_utc=None, input_sha256=record['input_sha256'],
            truth_sha256=record['frame_sha256'], checkpoint0_sha256=record['checkpoints'][0]['artifact_sha256'],
            checkpoint1_sha256=record['checkpoints'][1]['artifact_sha256'])
        frames.append(rows)
    chosen = selected_records(tf)
    write_json(out / 'selection.json', dict(scope='first32 failures plus first32 successes at6.5dB; not FER sample',
        observations=[dict(observation_id=f"s650_f{r['frame']:04d}", frame=r['frame'],
            baseline_error=bool(r['info_errors']), input_sha256=r['input_sha256'],
            truth_sha256=r['frame_sha256'], baseline_record=r) for r in chosen]))
    write_csv(out / 'frame_diagnosis.csv', frames)
    write_csv(out / 'stage_costs.csv', stages)
    summary = {}
    for snr in [600, 650, 700]:
        cell = [r for r in frames if r['snr_centi_db']==snr]
        summary[str(snr)] = {key:sum(int(r[key]) for r in cell) for key in [
            'final_error','valid_wrong_word','round2_rescue','round2_harm',
            'refit1_local_boundary_hit','absolute_doppler_boundary_hit',
            'true_same_delay_multiplicity','represented_same_delay_underfit',
            'data_precision_floor_count','gain_precision_floor_count']}
        summary[str(snr)]['missing_delay_frames']=sum(r['missed_distinct_delay_count']>0 for r in cell)
    write_json(out / 'summary.json', summary)
    write_json(out / 'unavailable_fields.json', {
        'initial_acquisition_paths':'pilot_front state not retained by PartB producer; A performs no replay',
        'refit0_local_boundary_hit':'initial strongest integer center not saved',
        'acquisition_seconds':'native pilot_seconds not persisted in PartB ledger/attempt/checkpoint',
        'refit_individual_candidate_seconds':'only whole-refit duration and ALL-evaluation count persisted',
        'other_guard_activity':'only two TF precision-floor booleans persisted; cannot reconstruct all clipping/floors',
        'first_decision_utc':'ready offset measured from receiver entry; UTC at that origin not saved',
        'interface_checkpoint_seconds':'measured only as unsplit accounting remainder; no isolated historical timer'})
    write_json(out / 'receipt.json', dict(status='pass', receiver_calls_added=0,
        observations=3072, original_attempts=9696, original_checkpoints=len(stages),
        recounted_tf_checkpoints=6144, original_run=str(run),
        manifest_sha256=sha256(run/'manifest.json'), ledger_sha256=sha256(run/'ledger.jsonl'),
        ldpc_cache_path=str(cache), ldpc_cache_sha256=sha256(cache),
        code_pairwise_zero_mean=np.all(G.any(axis=1)).item(),
        code_pairwise_independent=np.unique(G,axis=0).shape[0]==G.shape[0],
        code_n=int(G.shape[0]),code_k=int(G.shape[1]), sources_verified=True,
        files={p.name:sha256(p) for p in out.iterdir() if p.is_file()}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    for name in ['run','source','baseline','out']:
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    extract(args.run,args.source,args.baseline,args.out)
