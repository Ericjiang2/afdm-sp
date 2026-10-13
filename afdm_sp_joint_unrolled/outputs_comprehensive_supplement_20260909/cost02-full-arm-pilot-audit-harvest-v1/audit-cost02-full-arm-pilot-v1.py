"""Audit the frozen 11,970F all-method variance pilot without any receiver calls.

The v1 quote auditor is immutable historical evidence. Its common integrity and
telemetry helpers are reused by content hash; this successor retains its full
record checks and replaces quote-only scope/harvesting with bounded pilot output.
Large producer payloads stay remote with an SHA256/MD5 index.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time
import zipfile

HELPER_SHA256 = '77e49c170dbd2a94228ef58425a17b8b3bea22e48fc6e7b10b72c76f34348933'
helper_path = Path(__file__).with_name('audit-cost02-full-arm-v1.py')
if hashlib.sha256(helper_path.read_bytes()).hexdigest() != HELPER_SHA256:
    raise ValueError('immutable audit helper changed')
spec = importlib.util.spec_from_file_location('cost_audit_helpers_v1', helper_path)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
require, digest, read, put = helpers.require, helpers.digest, helpers.read, helpers.put
file_record = helpers.file_record
checked_reference, telemetry_check = helpers.checked_reference, helpers.telemetry_check
source_check = helpers.source_check


def validate_pilot_scope(manifest, design):
    require(manifest['timing_purpose'] == 'timing-pilot' and
            manifest['block_start'] == 257 and len(manifest['arm_ids']) == 15 and
            manifest['requested_snr_cells'] == [7, 8, 9] and
            manifest['n_by_snr'] == {'7': 256, '8': 256, '9': 256} and
            manifest['warmup_by_snr'] == {'7': 10, '8': 10, '9': 10} and
            manifest['calls'] == dict(F=11970, E=0, T=0) and
            design['expected_total_reserved_F'] == 12858,
            'this auditor is bound to the full-arm 256-block variance pilot only')


def check_cross_snr_pairing(seen, block, metadata):
    common = {k: metadata['input_hashes'][k] for k in ('H', 'data', 'info', 'coded')}
    common['rng_words'] = {k: tuple(metadata['rng_words'][k]) for k in ('channel', 'data', 'noise')}
    require(block not in seen or seen[block] == common,
            'cross-SNR exogenous block/normalized-noise stream identity differs')
    seen[block] = common


def compressed_json(path, value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()
    require(len(raw) <= 128 * 1024**2, 'audit JSON exceeds finite in-memory bound')
    payload = gzip.compress(raw, compresslevel=6, mtime=0)
    existing = sum(p.stat().st_size for p in path.parent.rglob('*') if p.is_file())
    require(existing + len(payload) <= 128 * 1024**2, 'audit artifacts exceed publication budget')
    with path.open('xb') as stream:
        stream.write(payload)
    return file_record(path)


def audit(options):
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled import supplement_timing as timing

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    started = time.perf_counter()
    design = read(options.design, options.design_sha256)
    source, source_inventory = source_check(design)
    out = Path(design['output_stem'])
    root = out.parent
    require(out.resolve().is_relative_to('/data/guoyikun/'), 'invalid production root')
    require(Path(str(out) + '.exit').read_text().strip() == '0' and
            not (out / 'failure.json').exists(), 'producer is not complete and successful')
    manifest_path = Path(str(out) + '-admission.json')
    manifest = read(manifest_path, options.manifest_sha256)
    validate_pilot_scope(manifest, design)
    immutable = {k: v for k, v in manifest.items() if k not in
                 ('runtime_admitted_unix', 'runtime_deadline_unix', 'authorization')}
    require(immutable == design['manifest_template'], 'admission changed the frozen design')
    timing.validate_boundary(manifest, manifest_path)
    require(timing.sources() == manifest['source_manifest'], 'imported source differs')
    complete = read(out / 'complete.json')
    contract = read(out / 'contract.json')
    require(complete['status'] == 'complete_collection_only' and
            complete['exitcode'] == 0 and complete['fixture_only'] is False and
            complete['deployment_cost_pass'] is False and contract['fixture_only'] is False,
            'collection receipt has an unsupported completion/claim state')
    require(complete['calls'] == contract['calls_reserved'] == manifest['calls'] and
            complete['measured_n_by_snr'] ==
            {str(s): manifest['n_by_snr'][str(s)] for s in manifest['requested_snr_cells']} and
            complete['admitted_n_by_snr'] == manifest['n_by_snr'] and
            complete['uncollected_snr_cells'] ==
            [s for s in timing.TIMING_SNRS if s not in manifest['requested_snr_cells']],
            'receipt call/sample coverage differs')
    core = {k: v for k, v in contract.items() if k not in ('config_sha256', 'reservation')}
    config_sha = hashlib.sha256(json.dumps(core, sort_keys=True, allow_nan=False).encode()).hexdigest()
    require(config_sha == contract['config_sha256'] == complete['config_sha256'] and
            contract['manifest_sha256'] == options.manifest_sha256 and
            contract['source_sha256'] == manifest['source_manifest'] and
            contract['catalogue'] == complete['catalogue'] == manifest['catalogue'] and
            contract['deadline_unix'] == manifest['runtime_deadline_unix'] and
            contract['measurement_boundary'] == timing.TIMING_BOUNDARY and
            contract['device'] == 'cuda:0', 'runtime contract differs')
    bound_files = {str(Path(p)): h for p, h in contract['files'].items()}
    for path, expected in bound_files.items():
        require(digest(path) == expected, 'bound input changed: ' + path)
    reservation_ref = complete['reservation']
    require(reservation_ref == contract['reservation'], 'reservation references differ')
    reservation = read(reservation_ref['path'], reservation_ref['sha256'])
    require(reservation['identities'] == timing.timing_identities(manifest) and
            reservation['calls_reserved'] == manifest['calls'] and
            reservation['config_sha256'] == config_sha and
            reservation['manifest_sha256'] == options.manifest_sha256 and
            reservation['out'] == str(out), 'reservation does not cover the exact collection')
    history, reserved_f, identity_keys = {}, 0, set()
    reservations = sorted(Path(manifest['ledger_path']).glob('reservation-*.json'))
    for path in reservations:
        row = read(path)
        old = read(row['manifest_path'], row['manifest_sha256'])
        require(row['manifest_path'] not in history and
                row['identities'] == timing.timing_identities(old) and
                row['calls_reserved'] == old['calls'], 'invalid historical reservation')
        history[row['manifest_path']] = row['manifest_sha256']
        keys = {json.dumps(v, sort_keys=True) for v in row['identities']}
        require(len(keys) == len(row['identities']) and not identity_keys.intersection(keys),
                'duplicate reserved timing identity')
        identity_keys.update(keys)
        reserved_f += row['calls_reserved']['F']
    expected_history = {b['path']: b['sha256'] for b in manifest['excluded_manifests']}
    expected_history[str(manifest_path)] = options.manifest_sha256
    require(history == expected_history and reserved_f == design['expected_total_reserved_F'],
            'unaccounted timing history or reservation count')

    options.audit_out.mkdir(parents=True, exist_ok=False)
    args = argparse.Namespace(out=options.audit_out,
        protocol=source / 'inputs/cost-data-protocol.json',
        representative_freeze=source / 'inputs/A02-representatives.json',
        representative_freeze_sha256=manifest['representative_freeze_sha256'],
        timing_manifest=manifest_path, timing_manifest_sha256=options.manifest_sha256)
    manifest['_resolved_prior_paths'] = {int(s): Path(v['path'])
                                        for s, v in manifest['prior_by_snr'].items()}
    manifest['_pilots_path'] = Path(manifest['selection']['inputs']['pilot_npz']['path'])
    hooks = timing.RealHooks()
    context = hooks.prepare_timing(args, manifest)
    require(context['code_sha256'] == contract['code_sha256'], 'regenerated LDPC code differs')

    expected_orders = []
    for snr in manifest['requested_snr_cells']:
        start = manifest['block_start']
        groups = [('warmup', start, i) for i in range(manifest['warmup_by_snr'][str(snr)])]
        groups += [('measured', b, None) for b in range(start, start + manifest['n_by_snr'][str(snr)])]
        for phase, block, repeat in groups:
            expected_orders.append(dict(group=len(expected_orders) + 1, phase=phase, block=block,
                snr_db=snr, repeat=repeat, order=timing.timing_order(snr, block, manifest['arm_ids'])))
    require(len(complete['order_records']) == len(expected_orders), 'missing execution orders')
    expected_schedule = []
    for ref, expected in zip(complete['order_records'], expected_orders):
        require(checked_reference(ref, out) == expected, 'execution order differs from RNG rule')
        for symbol in expected['order']:
            expected_schedule.append({k: v for k, v in expected.items() if k != 'order'} |
                dict(symbol=symbol, ordinal=len(expected_schedule) + 1, purpose=manifest['timing_purpose']))
    telemetries = {}
    stamps = []
    for ref in complete['telemetry_records']:
        path = Path(ref['path'])
        require(path.name not in telemetries, 'duplicate telemetry reference')
        value = checked_reference(ref, out)
        stamps.append(telemetry_check(value, contract, manifest))
        telemetries[path.name] = value
    expected_names = {'telemetry-initial.json'} | {
        f'telemetry-{row["group"]:06d}-{when}.json'
        for row in expected_orders for when in ('before', 'after')}
    require(set(telemetries) == expected_names and stamps == sorted(stamps),
            'incomplete or nonchronological boundary telemetry')

    refs = complete['measured_records'] + complete['warmup_records']
    require(len(refs) == len(expected_schedule) == manifest['calls']['F'], 'missing raw records')
    refs.sort(key=lambda ref: ref['identity']['ordinal'])
    compact_records, pairings, observed_by_pilot, frame_identities = [], {}, {}, {}
    arrays_audited = 0
    group_seconds, cross_snr = {}, {}
    required_files = set()
    for ref, expected in zip(refs, expected_schedule):
        require(ref['identity'] == expected, 'reference schedule differs')
        record = checked_reference(ref, out)
        identity = record['identity']
        require({k: identity[k] for k in expected} == expected and
                identity['config_sha256'] == config_sha and identity['audit'] is False,
                'record identity/configuration differs')
        started_path = out / f'started-F-{expected["ordinal"]:06d}.json'
        require(read(started_path) == identity, 'started/completed identity mismatch')
        for field in ('seconds', 'CPU_seconds', 'generation_seconds', 'model_setup_seconds'):
            require(type(record[field]) in (float, int) and math.isfinite(record[field]) and
                    record[field] > 0, 'invalid elapsed time: ' + field)
        require(record['truth_access'] == 'none' and
                record['block_validity'] == 'requires successful after-block telemetry',
                'record truth/validity scope differs')
        snr, block, symbol = (expected[k] for k in ('snr_db', 'block', 'symbol'))
        frame = hooks.make_timing_frame(args, context, snr, block, symbol, manifest)
        regenerated = timing._timing_frame_identity(frame, args, manifest, snr, block, symbol)
        require(regenerated == identity['frame_identity'], 'regenerated input identity differs')
        meta = regenerated['metadata']
        check_cross_snr_pairing(cross_snr, block, meta)
        pairing, pilot, observation = timing._timing_pairing(regenerated, manifest)
        common_key, pilot_key = (snr, block), (snr, block, pilot)
        require(common_key not in pairings or pairings[common_key] == pairing,
                'exogenous arrays differ between arms')
        require(pilot_key not in observed_by_pilot or observed_by_pilot[pilot_key] == observation,
                'observed arrays differ for a common pilot')
        pairings[common_key], observed_by_pilot[pilot_key] = pairing, observation
        input_key = (snr, block, symbol)
        regenerated_hash = hashlib.sha256(json.dumps(regenerated, sort_keys=True,
                                                       allow_nan=False).encode()).hexdigest()
        require(input_key not in frame_identities or frame_identities[input_key] == regenerated_hash,
                'warmup/measured input identity differs')
        frame_identities[input_key] = regenerated_hash
        raw_ref = record['raw']
        raw_path = Path(raw_ref['path'])
        require(raw_ref == ref['raw'] and raw_path.resolve().parent == out.resolve() and
                not raw_path.is_symlink() and raw_path.stat().st_size == raw_ref['bytes'] and
                digest(raw_path) == raw_ref['sha256'] and digest(raw_path, 'md5') == raw_ref['md5'] and
                raw_ref['fields'] == list(timing.RAW_FIELDS), 'raw descriptor or dual hash differs')
        with np.load(raw_path, allow_pickle=False) as archive:
            require(set(archive.files) == set(timing.RAW_FIELDS), 'raw array field set differs')
            raw = {key: archive[key] for key in archive.files}
        require({k: timing.array_hash(v) for k, v in raw.items()} == record['raw_field_sha256'],
                'dtype/shape/content array hash differs')
        checked = timing._validate_result(dict(raw, support=raw['support'].tolist(),
            graphs=[], support_trace=[], dals=[]), False, frame, context['code'])
        require(all(np.array_equal(checked[k], raw[k]) for k in raw), 'raw validation changed values')
        arrays_audited += len(raw)
        group_seconds[expected['group']] = group_seconds.get(expected['group'], 0) + record['seconds']
        compact_records.append(dict(expected, **{k: record[k] for k in
            ('seconds', 'CPU_seconds', 'generation_seconds', 'model_setup_seconds', 'receiver_qualification')},
            raw_bytes=raw_ref['bytes'], power=regenerated['metadata']['power'],
            group_started_unix=telemetries[f'telemetry-{expected["group"]:06d}-before.json']['observed_unix'],
            group_finished_unix=telemetries[f'telemetry-{expected["group"]:06d}-after.json']['observed_unix']))
        required_files.update((Path(ref['path']), started_path, raw_path))
        del frame, raw, checked
        if len(compact_records) % 250 == 0:
            print(json.dumps(dict(event='pilot_raw_audit_progress', records=len(compact_records),
                                  arrays=arrays_audited, elapsed_seconds=time.perf_counter()-started)), flush=True)
    for group, seconds in group_seconds.items():
        before = telemetries[f'telemetry-{group:06d}-before.json']['observed_unix']
        after = telemetries[f'telemetry-{group:06d}-after.json']['observed_unix']
        require(0 < seconds <= after - before, 'receiver timings exceed their recorded boundary interval')
    for pattern in ('record-F-*.json', 'started-F-*.json', 'raw-F-*.npz'):
        require(set(out.glob(pattern)) == {p for p in required_files if p.match(pattern)},
                'extra or omitted production call artifacts')
    quotes = []
    for snr in manifest['requested_snr_cells']:
        for symbol in manifest['arm_ids']:
            row = dict(snr_db=snr, symbol=symbol)
            for phase in ('warmup', 'measured'):
                values = [v for v in compact_records if v['snr_db'] == snr and
                          v['symbol'] == symbol and v['phase'] == phase]
                row[phase] = dict(n_calls=len(values))
                for field in ('seconds', 'CPU_seconds', 'generation_seconds', 'model_setup_seconds', 'raw_bytes'):
                    samples = [v[field] for v in values]
                    row[phase][field] = dict(sum=sum(samples), mean=float(np.mean(samples)),
                        minimum=min(samples), maximum=max(samples)) if samples else None
            quotes.append(row)
    # Full content verification after every read; do not replace this with stat checks.
    require(source_check(design)[1] == source_inventory, 'source changed during audit')
    for path, expected in bound_files.items():
        require(digest(path) == expected, 'input changed during audit: ' + path)
    for ref in refs + complete['order_records'] + complete['telemetry_records']:
        require(digest(ref['path']) == ref['sha256'], 'production metadata changed during audit')
    for ref in refs:
        require(digest(ref['raw']['path']) == ref['raw']['sha256'], 'production raw changed during audit')

    paths = sorted(p for p in out.rglob('*') if p.is_file())
    controls = [out / 'complete.json', out / 'contract.json']
    controls += [Path(str(out) + suffix) for suffix in ('.log', '.pid', '.exit',
                 '-admission.json', '-authorization.json', '-preflight.json')]
    controls += reservations + [Path(options.design), Path(__file__), helper_path,
        root / 'cost02-full-arm-pilot-launch-v1.json', root / 'cost02-full-arm-pilot-v1.sh']
    paths += [p for p in controls if p not in paths]
    require(len(paths) == len(set(paths)) and all(p.is_file() for p in controls),
            'missing or duplicate pilot control artifact')
    index = [file_record(path) for path in paths]
    compact_ref = compressed_json(options.audit_out / 'records-compact.json.gz', compact_records)
    index_ref = compressed_json(options.audit_out / 'raw-file-index.json.gz',
                                dict(files=index, remote_originals_unchanged=True))
    summary = dict(schema='COST02-full-arm-variance-pilot-raw-audit-v1', status='PASS',
        production_scope='256 independent exogenous blocks shared by three SNRs; variance pilot only; no formal cost verdict',
        auditor_sha256=digest(__file__), audit_helper_sha256=HELPER_SHA256,
        design_sha256=options.design_sha256, manifest_sha256=options.manifest_sha256,
        source_archive_sha256=design['source']['archive_sha256'], source_files=len(source_inventory),
        producer_calls=complete['calls'], audit_calls=dict(F=0, E=0, T=0, MC=0),
        records=len(refs), raw_arrays=arrays_audited, regenerated_input_records=len(refs),
        unique_measured_exogenous_blocks=len({v['block'] for v in compact_records if v['phase'] == 'measured'}),
        cross_snr_exogenous_blocks_verified=len(cross_snr),
        measured_n_by_snr=complete['measured_n_by_snr'], order_groups=len(expected_orders),
        telemetry_records=len(telemetries), telemetry_scope=contract['telemetry_scope'],
        reserved_timing_F=reserved_f,
        excluded_formal_block_range=[0, manifest['block_start'] + max(manifest['n_by_snr'].values())],
        producer_wall_seconds=complete['wall_seconds'], producer_setup_seconds=contract['setup_seconds'],
        raw_bytes=sum(v['raw_bytes'] for v in compact_records), descriptive_by_arm_snr=quotes,
        compact_records=compact_ref, raw_file_index=index_ref,
        aliases=manifest['catalogue']['aliases'], deployment_cost_pass=False, formal_n_selected=False,
        runtime_versions=contract['runtime_versions'], audit_seconds=time.perf_counter() - started,
        original_payload_retention='All producer NPZ/per-frame records stay at indexed remote paths with SHA256 and MD5.',
        review_agent_mode='main-session-fallback', review_independence='weak')
    put(options.audit_out / 'summary.json', summary)
    bundle = root / (options.audit_out.name + '-harvest.zip')
    exported = [options.audit_out / 'summary.json', Path(compact_ref['path']), Path(index_ref['path'])]
    exported += [p for p in controls if p.stat().st_size <= 10 * 1024**2]
    require(len(exported) == len(set(exported)), 'duplicate control export')
    size = sum(p.stat().st_size for p in options.audit_out.rglob('*') if p.is_file())
    # Reserve conservative deflate/header overhead before opening a new bundle.
    bundle_bound = sum(p.stat().st_size for p in exported) * 1.01 + len(exported) * 4096 + 1024**2
    require(size + bundle_bound <= 256 * 1024**2, 'audit bundle would exceed output budget')
    with zipfile.ZipFile(bundle, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in exported:
            require(path.resolve().is_relative_to(root), 'harvest path outside output root')
            require(path.stat().st_size <= 10 * 1024**2, 'individual return artifact exceeds policy')
            archive.write(path, str(path.relative_to(root)))
    require(size + bundle.stat().st_size <= 256 * 1024**2, 'audit output budget exceeded')
    print(json.dumps(dict(status='PASS', audit_and_bundle_seconds=time.perf_counter()-started,
        records=len(refs), raw_arrays=arrays_audited, audit_calls=summary['audit_calls'],
        payloads_retained_remote=len(index), bundle=file_record(bundle))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', type=Path, required=True)
    parser.add_argument('--design-sha256', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--audit-out', type=Path, required=True)
    options = parser.parse_args()
    require(options.audit_out.resolve().is_relative_to('/data/guoyikun/'), 'audit output outside permitted root')
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'audit must not enable CUDA')
    os.nice(10)
    audit(options)


if __name__ == '__main__':
    main()
