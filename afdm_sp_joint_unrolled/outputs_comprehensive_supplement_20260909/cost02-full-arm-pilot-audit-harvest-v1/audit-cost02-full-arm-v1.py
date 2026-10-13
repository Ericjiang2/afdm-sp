"""Audit a completed, design-bound F_C collection without running a receiver.

This validates historical telemetry against its producer PID and admission time;
it does not pretend that historical observations are a fresh resource admission.
Input regeneration and LDPC cache construction are offline audit work (0F/E/T).
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path, kind='sha256'):
    h = hashlib.new(kind)
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path, expected=None):
    if expected is not None:
        require(digest(path) == expected, 'file SHA256 differs: ' + str(path))
    return json.loads(Path(path).read_text())


def put(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def file_record(path):
    path = Path(path)
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=digest(path), md5=digest(path, 'md5'))


def checked_reference(reference, parent):
    path = Path(reference['path'])
    require(not path.is_symlink() and path.resolve().parent == parent.resolve(),
            'reference is not an original direct child: ' + str(path))
    return read(path, reference['sha256'])


def telemetry_check(value, contract, manifest):
    require(value.get('status') == 'ok' and
            value.get('gpu_uuid') == manifest['resource_limits']['gpu_uuid'],
            'missing GPU telemetry')
    pids = value.get('compute_pids')
    require(isinstance(pids, list) and len(set(pids)) == len(pids) and
            all(type(pid) is int and pid == contract['pid'] for pid in pids),
            'foreign or invalid process in historical telemetry')
    stamp = value.get('observed_unix')
    require(type(stamp) in (float, int) and math.isfinite(stamp) and
            manifest['runtime_admitted_unix'] <= stamp <= manifest['runtime_deadline_unix'],
            'telemetry outside the original finite admission')
    cores, load = value.get('cpu_count'), value.get('load_average')
    affinity = value.get('cpu_affinity')
    require(type(cores) is int and cores > 16 and isinstance(load, list) and
            len(load) == 3 and all(math.isfinite(x) and x >= 0 for x in load) and
            load[0] < cores - 16 and isinstance(affinity, list) and affinity and
            len(set(affinity)) == len(affinity) and
            all(type(cpu) is int and 0 <= cpu < cores for cpu in affinity) and
            value.get('numerical_threads') == value.get('interop_threads') == 1,
            'historical CPU headroom/thread contract failed')
    free, used, utilization = (value.get(k) for k in
        ('memory_free_MiB', 'memory_used_MiB', 'utilization_percent'))
    require(all(type(v) is int for v in (free, used, utilization)) and
            free >= 6144 and used >= 0 and 0 <= utilization <= 100 and
            not (used > 18 * 1024 and utilization > 90),
            'historical GPU memory contract failed')
    return stamp


def source_check(design):
    source = Path(design['source']['root'])
    metadata = design['source']
    expected = read(source / 'source-manifest.json', metadata['source_manifest_sha256'])
    actual = {str(p.relative_to(source / 'source')): digest(p)
              for p in (source / 'source').rglob('*') if p.is_file()}
    require(actual == expected, 'frozen source inventory changed')
    receipt = read(source / 'remote-tests.json', metadata['remote_test_receipt_sha256'])
    require(receipt['status'] == 'PASS' and receipt['exitcode'] == 0 and
            receipt['archive_sha256'] == metadata['archive_sha256'] and
            digest(source / 'remote-tests.log') == receipt['log_sha256'],
            'source has no matching successful remote test receipt')
    return source, actual


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
    group_seconds = {}
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
        pairing, pilot, observation = timing._timing_pairing(regenerated, manifest)
        common_key, pilot_key = (snr, block), (snr, block, pilot)
        require(common_key not in pairings or pairings[common_key] == pairing,
                'exogenous arrays differ between arms')
        require(pilot_key not in observed_by_pilot or observed_by_pilot[pilot_key] == observation,
                'observed arrays differ for a common pilot')
        pairings[common_key], observed_by_pilot[pilot_key] = pairing, observation
        input_key = (snr, block, symbol)
        require(input_key not in frame_identities or frame_identities[input_key] == regenerated,
                'warmup/measured input identity differs')
        frame_identities[input_key] = regenerated
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
            raw_bytes=raw_ref['bytes'], power=regenerated['metadata']['power']))
        required_files.update((Path(ref['path']), started_path, raw_path))
        del frame, raw, checked
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
    paths += [Path(str(out) + s) for s in ('.log', '.pid', '.exit', '-admission.json',
              '-authorization.json', '-preflight.json')]
    paths += reservations + [Path(options.design)]
    for path in (root / 'cost02-full-arm-quote-launch-v1.json',
                 root / 'cost02-full-arm-quote-v1.sh'):
        if path.exists():
            paths.append(path)
    require(len(paths) == len(set(paths)), 'duplicate harvest path')
    index = [file_record(path) for path in paths]
    summary = dict(schema='COST02-completed-collection-raw-audit-v1', status='PASS',
        production_scope='all-method resource quote; one independent exogenous block; no variance or formal verdict',
        design_sha256=options.design_sha256, manifest_sha256=options.manifest_sha256,
        source_archive_sha256=design['source']['archive_sha256'], source_files=len(source_inventory),
        producer_calls=complete['calls'], audit_calls=dict(F=0, E=0, T=0, MC=0),
        records=len(refs), raw_arrays=arrays_audited, generated_input_identities=len(refs),
        unique_measured_exogenous_blocks=len({v['block'] for v in compact_records if v['phase'] == 'measured'}),
        measured_n_by_snr=complete['measured_n_by_snr'], order_groups=len(expected_orders),
        telemetry_records=len(telemetries), telemetry_scope=contract['telemetry_scope'],
        reserved_timing_F=reserved_f, excluded_next_pilot_range=[0, manifest['block_start'] + max(manifest['n_by_snr'].values())],
        producer_wall_seconds=complete['wall_seconds'], producer_setup_seconds=contract['setup_seconds'],
        raw_bytes=sum(v['raw_bytes'] for v in compact_records), quotes=quotes, records_compact=compact_records,
        aliases=manifest['catalogue']['aliases'], deployment_cost_pass=False, formal_n_selected=False,
        runtime_versions=contract['runtime_versions'], audit_seconds=time.perf_counter() - started,
        review_agent_mode='main-session-fallback', review_independence='weak')
    put(options.audit_out / 'summary.json', summary)
    put(options.audit_out / 'raw-file-index.json', dict(files=index, remote_originals_unchanged=True))
    bundle = root / (options.audit_out.name + '-harvest.zip')
    with zipfile.ZipFile(bundle, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in paths + [options.audit_out / 'summary.json', options.audit_out / 'raw-file-index.json']:
            require(path.resolve().is_relative_to(root), 'harvest path outside output root')
            require(path.stat().st_size <= 10 * 1024**2, 'individual artifact exceeds return-size policy')
            archive.write(path, str(path.relative_to(root)))
    print(json.dumps(dict(status='PASS', audit_seconds=summary['audit_seconds'],
        records=len(refs), raw_arrays=arrays_audited, audit_calls=summary['audit_calls'], bundle=file_record(bundle))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', type=Path, required=True)
    parser.add_argument('--design-sha256', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--audit-out', type=Path, required=True)
    options = parser.parse_args()
    require(options.audit_out.resolve().is_relative_to('/data/guoyikun/'), 'audit output outside permitted root')
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'audit must not enable CUDA')
    audit(options)


if __name__ == '__main__':
    main()
