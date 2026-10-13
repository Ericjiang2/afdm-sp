"""Audit actual S-01 candidate inputs and terminals with zero new F/E/T."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback
from types import SimpleNamespace

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR='/data/guoyikun/tmp',
                  MPLCONFIGDIR='/data/guoyikun/tmp/afdm-mpl-cache', CUDA_VISIBLE_DEVICES='')
ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909')
SOURCE = ROOT/'source-s01-candidate-v2'
RUN = ROOT/'s01-candidates-v1'
sys.path.insert(0, str(SOURCE/'source'))

import numpy as np
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.direction_cancel import transform
from afdm_sp_joint_unrolled.e1_ldpc import build_code, extract_info
from afdm_sp_joint_unrolled.supplement_a01_diagnostics import terminal_diagnostics
from afdm_sp_joint_unrolled.supplement_baselines import recipe_by_id
from afdm_sp_joint_unrolled.supplement_data import SupplementData
from afdm_sp_joint_unrolled.supplement_pilot_frames import pilot_frames
from afdm_sp_joint_unrolled.supplement_profile import score_errors
from afdm_sp_joint_unrolled.supplement_scene_candidates import (
    SCENES, SNRS, SCORE_FIELDS, full_calls, identities, load_contract,
    system_for, validate_baseline, verify_package)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def checked(binding):
    path = Path(binding['path'])
    require(path.resolve().is_relative_to(ROOT), 'evidence path outside task output')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == binding['sha256'], 'evidence SHA256 mismatch: '+str(path))
    if 'bytes' in binding:
        require(len(raw) == binding['bytes'], 'evidence size mismatch')
    if 'md5' in binding:
        require(hashlib.md5(raw).hexdigest() == binding['md5'], 'evidence MD5 mismatch')
    return path


def arrays(binding):
    with np.load(checked(binding), allow_pickle=False) as archive:
        values = {k: archive[k] for k in archive.files}
    require(all(not v.dtype.hasobject and np.isfinite(v).all() for v in values.values()),
            'nonfinite or object evidence array')
    if 'fields' in binding:
        require(sorted(values) == binding['fields'], 'terminal fields changed')
    return values


def close(actual, expected, label='value'):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), 'mapping mismatch: '+label)
        for key, value in expected.items():
            close(actual[key], value, label+'.'+key)
    elif isinstance(expected, list):
        require(len(actual) == len(expected), 'list length mismatch: '+label)
        for i, value in enumerate(expected):
            close(actual[i], value, label+f'[{i}]')
    elif isinstance(expected, float):
        require(np.isclose(actual, expected, rtol=1e-10, atol=1e-12), 'numeric mismatch: '+label)
    else:
        require(actual == expected, 'value mismatch: '+label)


def load_records(batches, frozen, bindings):
    rows, summaries, reserved = {}, [], set()
    for batch in batches:
        require(not (batch/'failure.json').exists(), 'failed batch retained; completion refused')
        contract = json.loads((batch/'contract.json').read_text())
        summary = json.loads((batch/'summary.json').read_text())
        ids = {tuple(x) for x in contract['identities']}
        b = sorted({x[0] for x in ids})
        require(ids == set(identities(b[0], b[-1]+1, frozen['physical_arms'])), 'incomplete batch identities')
        require(not ids & reserved and contract['bindings'] == bindings, 'duplicate or changed batch binding')
        expected_calls = dict(F=full_calls(ids), E=0, T=0)
        require(summary['status'] == 'complete' and summary['exitcode'] == 0
                and summary['active'] is None and contract['calls_reserved'] == expected_calls
                and summary['calls_attempted'] == summary['calls_completed'] == expected_calls
                and summary['reused'] == len(ids)-expected_calls['F'], 'batch accounting mismatch')
        call_paths = list(batch.glob('call-F-*.json'))
        calls = {tuple(json.loads(p.read_text())['identity']) for p in call_paths}
        require(len(call_paths) == len(calls) == expected_calls['F'], 'call receipts incomplete or duplicated')
        expected_new = {x for x in ids if x[3] != 'Bstar' or x[0] < 16}
        require(calls == expected_new, 'call identities differ from the actual F grid')
        require(len(summary['records']) == len(ids) == len(list(batch.glob('frame-*.json'))), 'frame inventory mismatch')
        for binding in summary['records']:
            row = json.loads(checked(binding).read_text())
            key = tuple(row['identity'])
            require(key in ids and key not in rows, 'duplicate or unexpected frame')
            require(row['descriptor'] == frozen['physical_arms'][key[3]]
                    and row['truth_access_level'] == 'none' and not row['independent_confirmation'], 'candidate role/truth scope changed')
            require(row['call_type'] == ('F' if key in expected_new else 'reused'), 'illegal baseline reuse')
            rows[key] = row
        require(set(rows) >= ids, 'batch record coverage incomplete')
        summaries.append(dict(path=str(batch), summary_sha256=sha(batch/'summary.json'),
            contract_sha256=sha(batch/'contract.json'), initialization_seconds=summary['initialization_seconds'],
            groups=summary['groups'], elapsed_seconds=summary['elapsed_seconds']))
        reserved.update(ids)
    ledger_ids = set()
    for path in (RUN/'candidate-ledger').glob('reservation-*.json'):
        row = json.loads(path.read_text())
        ids = {tuple(x) for x in row['identities']}
        require(row['bindings'] == bindings and len(ids) == len(row['identities'])
                and row['F'] == full_calls(ids) and not ids & ledger_ids, 'reservation ledger mismatch')
        ledger_ids.update(ids)
    require(ledger_ids == reserved == set(rows), 'ledger and completed raw grid differ')
    return rows, summaries


def main(stage):
    require(stage == 'complete', 'v3 is the complete audit; executed first-block v2 remains frozen')
    out = ROOT/'s01-candidate-raw-audit-v3'
    out.mkdir()
    started = time.perf_counter()
    counts = dict(states=0, terminal_arrays=0, reused_score_records=0, recaptured_baselines=0,
                  cancellation_arrays=0, legacy_initializer_schema_records=0, calls=dict(F=0, E=0, T=0))
    def timeout(*_):
        raise TimeoutError('S-01 offline raw audit deadline')
    signal.signal(signal.SIGALRM, timeout); signal.alarm(3600)
    try:
        receipt = ROOT/'s01-candidate-remaining-v1.exit'
        require(receipt.read_text().strip() == '0', 'producer queue did not complete')
        args = SimpleNamespace(freeze=SOURCE/'inputs/candidate-freeze.json',
            baseline=SOURCE/'inputs/baseline-manifest.json', inputs=SOURCE/'inputs', source=SOURCE/'source',
            checkpoint=ROOT.parent/'outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk',
            freeze_sha256='a866501e52f4eaf90476b88c9aaf5fec0e072025a7ac8a01553b39d46c4d997e',
            baseline_sha256='199dfe315ca0741c1e571ba990646ed38679eb2aa31485997f2c2f652d466399')
        frozen, arms, baseline = load_contract(args)
        bindings = dict(freeze=args.freeze_sha256, baseline=args.baseline_sha256,
                        sources=sha(args.inputs/'source-sha256.json'), checkpoint=sha(args.checkpoint))
        blocks = range(192)
        batches = [RUN/'batch-000-001']
        batches += [RUN/f'batch-{b:03d}-{min(b+16,192):03d}' for b in range(1,192,16)]
        require(set(batches) == {p for p in RUN.glob('batch-*') if p.is_dir()}, 'unexpected or omitted producer batch')
        records, summaries = load_records(batches, frozen, bindings)
        expected = {(b,s,scene,arm) for b in blocks for s in SNRS for scene in SCENES for arm in arms}
        require(set(records) == expected, 'global candidate grid differs')
        (out/'code-cache').mkdir()
        code = build_code(cache_dir=out/'code-cache')
        data = SupplementData(args.inputs/'data-protocol.json', code)
        systems = {scene: system_for(data.protocol['scenarios'][scene]) for scene in SCENES}
        with np.load(args.inputs/'pilots.npz', allow_pickle=False) as archive:
            pilots = {k: archive[k] for k in archive.files}
        cells, costs, metrics, power, common_blocks = {}, {}, {}, {}, {}
        for block in blocks:
            for scene in SCENES:
                for snr in SNRS:
                    original = data.make_frame(systems[scene], 'counterexample', block, snr, scenario=scene)
                    old_binding = baseline[(block,snr,scene)]
                    old = validate_baseline(original, old_binding)
                    frames = pilot_frames(original, pilots, c1=systems[scene].c1, c2=systems[scene].c2,
                                          preserve_original_p0=True)
                    source_binding = records[(block,snr,scene,'Bstar')]['source_input']
                    truth = arrays(source_binding)
                    require(set(truth) == {'H','data','noise','info','coded'}, 'source array schema differs')
                    for key, value in truth.items():
                        require(np.array_equal(value, original._truth[key]), 'source reconstruction differs: '+key)
                    shared = {k:array_hash(v) for k,v in truth.items()}
                    cluster = (block,scene)
                    require(cluster not in common_blocks or common_blocks[cluster] == shared, 'cross-SNR exogenous pairing changed')
                    common_blocks[cluster] = shared
                    for arm, descriptor in arms.items():
                        key = (block,snr,scene,arm)
                        row = records[key]
                        frame = frames[descriptor['pilot']]
                        require(row['source_input'] == source_binding and row['baseline_record'] == old_binding['record'], 'source record lineage differs')
                        require(row['metadata']['input_hashes'] == frame.metadata['input_hashes'], 'actual pilot input hashes differ')
                        require((row['metadata']['block'],row['metadata']['snr_db'],row['metadata']['scenario']) == key[:3], 'metadata identity differs')
                        close(row['metadata']['power'], frame.metadata['power'], 'regenerated pilot power')
                        power[key] = frame.metadata['power']['passes_declared_simulation_power_gate']
                        score = row['scores']
                        if row['call_type'] == 'reused':
                            close(score, {k:old[k] for k in SCORE_FIELDS}, 'reused historical scores')
                            require('terminal' not in row and not old_binding['recapture'], 'unregistered baseline terminal')
                            counts['reused_score_records'] += 1
                        else:
                            raw = arrays(row['terminal'])
                            for field in ('y','pilot','constellation'):
                                require(np.array_equal(raw[field],frame.observed[field]), 'terminal observed input differs: '+field)
                            for field in ('info','coded'):
                                require(np.array_equal(raw[field],truth[field]), 'terminal truth bit mismatch')
                            require(np.array_equal(raw['info_hat'],extract_info(code,raw['decoded'])), 'decoded information mismatch')
                            require(float(raw['sigma2_thermal']) == float(frame.observed['sigma2']), 'noise power mismatch')
                            require(all(np.all(raw[k] > 0) for k in ('sigma2','sigma2_terminal','var')), 'invalid terminal variance')
                            close(score, score_errors(raw, truth), 'terminal scores')
                            close(row['calibration'], terminal_diagnostics(raw, truth), 'terminal calibration')
                            for trace in row['capacity_trace']:
                                ids = trace['atom_ids']
                                require(len(set(ids)) == len(ids) == trace['unique_count']
                                        and len(ids) <= trace['limit'], 'receiver capacity trace violation')
                            final = row['capacity_trace'][-1]
                            require(final['stage'] == 'final' and set(final['atom_ids']) == set(raw['support'].tolist()), 'final support snapshot differs')
                            initial = row['initial_estimator']
                            recipe = recipe_by_id(descriptor['recipe'])
                            if recipe['stage'] == 'terminal_refit':
                                # The frozen legacy InitialEstimator has no truth_access
                                # field. Its observed-only source/API and SBL parameters
                                # are the authority; do not manufacture that old field.
                                require(initial['family'] == 'sbl' and initial['parameter'] == .001
                                        and initial['nomination_steps'] == 40, 'legacy initializer configuration differs')
                                require('truth_access' not in initial and row['refit']['truth_access'] == 'none',
                                        'legacy/refit evidence schema differs')
                                require(row['refit']['H_after_sha256'] == array_hash(raw['H']), 'refit H snapshot differs')
                                counts['legacy_initializer_schema_records'] += 1
                            else:
                                require(initial['truth_access'] == 'none' and initial['recipe'] == recipe,
                                        'catalogue initializer recipe/truth access changed')
                            if arm == 'I1':
                                schedule = row['bp_schedule']
                                require(schedule['outer_bp_iterations'] == 12 and schedule['final_bp_iterations'] == 20
                                        and schedule['final_ldpc_maxiter'] == 50 and len(schedule['calls']) == 10, 'I1 schedule changed')
                                stages = {name:sum(x['stage'] == name for x in row['feedback'])
                                          for name in ('detector_consume','CE_consume','decoder')}
                                require(stages == dict(detector_consume=10,CE_consume=9,decoder=1), 'I1 consumer trace incomplete')
                            if descriptor['interface'] in ('scalar','diagonal','lowrank'):
                                saved = arrays(row['cancellation_raw'])
                                sigma_base = float(raw['sigma2'])*recipe_by_id(descriptor['recipe'])['terminal_scale']
                                expected_transform = transform(raw['y']-raw['H']@raw['pilot'],raw['H'],saved['B'],sigma_base,arm)
                                for field in ('z','H','sigma_out'):
                                    np.testing.assert_allclose(saved[field],expected_transform[field],rtol=1e-10,atol=1e-10)
                                require(float(saved['sigma_out']) == float(raw['sigma2_terminal']), 'actual cancellation noise differs')
                                counts['cancellation_arrays'] += 1
                            if arm == 'Bstar':
                                close(score, {k:old[k] for k in SCORE_FIELDS}, 'recaptured historical scores')
                                counts['recaptured_baselines'] += 1
                            name = f'{scene}:{arm}'
                            costs.setdefault(name,[]).append(dict(block=block,snr=snr,**row['costs']))
                            metrics[key] = dict(
                                nll=row['calibration']['nll'],brier=row['calibration']['brier'],
                                nmse=float(np.linalg.norm(raw['H']-truth['H'])**2/np.linalg.norm(truth['H'])**2),
                                baseline_eligible=row['baseline_eligible'])
                            counts['terminal_arrays'] += 1
                        cells[key] = score['FER']
                    counts['states'] += 1
            if (block+1)%16 == 0:
                print(json.dumps(dict(event='S01-candidate-raw-audit',block=block,**counts)),flush=True)
        require(counts['terminal_arrays'] == full_calls(expected), 'raw terminal coverage differs')
        path = ROOT/'s01-candidate-analysis-v2.py'
        spec = importlib.util.spec_from_file_location('afdm_sp_joint_unrolled.supplement_scene_analysis',path)
        analysis = importlib.util.module_from_spec(spec); spec.loader.exec_module(analysis)
        inference = analysis.analyze_candidates(cells,frozen,json.loads((args.inputs/'global-contrast-manifest.json').read_text()))
        verify_package(args,bindings)
        index = []
        for path in sorted(RUN.rglob('*')):
            if path.is_file():
                raw = path.read_bytes()
                index.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),md5=hashlib.md5(raw).hexdigest()))
        with (out/'raw-file-index.json.gz').open('xb') as stream:
            with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as compressed:
                compressed.write(json.dumps(index).encode())
        statistics = analysis.summarize_candidate_metrics(cells, metrics, power)
        summary = dict(status='passed',stage=stage,**counts,source_bindings=bindings,batches=summaries,
            costs=costs,statistics=statistics,inference=inference,raw_files=len(index),
            raw_bytes=sum(x['bytes'] for x in index),raw_index_sha256=sha(out/'raw-file-index.json.gz'),
            elapsed_seconds=time.perf_counter()-started,auditor_sha256=sha(__file__),
            analysis_sha256=sha(ROOT/'s01-candidate-analysis-v2.py'),
            limitations=['development only; no independent nonharm or formal cost',
                        'reused legacy baseline scores have no saved terminal arrays',
                        'recaptured baseline cells do not invent original producer hashes',
                        'Bstar FER n=192, terminal diagnostics n=16; power metadata checked on all192 blocks'])
        write(out/'summary.json',summary)
        print(json.dumps({k:summary[k] for k in ('status','stage','states','terminal_arrays','reused_score_records','raw_files','raw_bytes','elapsed_seconds')}),flush=True)
    except BaseException as exc:
        write(out/'failure.json',dict(status='failed',message=str(exc),traceback=traceback.format_exc(),**counts))
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=('complete',),required=True)
    main(parser.parse_args().stage)
