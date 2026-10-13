"""Read immutable terminal evidence; separately qualify three saved CPU/CUDA cases.

Raw mode runs no BP, LDPC, receiver, transform or new physical generator.
GPU mode reuses saved H/z/prior and makes only the six registered terminal calls.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
from types import SimpleNamespace

import numpy as np


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def margins(llr, bits):
    llr, bits = np.asarray(llr), np.asarray(bits)
    require(llr.ndim == 1 and llr.size > 0 and llr.shape == bits.shape
            and np.isfinite(llr).all() and np.isin(bits, (0, 1)).all(), 'invalid LLR/truth')
    margin = (1 - 2*bits.astype(float))*llr
    wrong = margin < 0
    return dict(bit_NLL=float(np.logaddexp(0, -margin).mean()),
                wrong_sign_bits=int(wrong.sum()), zero_margin_bits=int((margin == 0).sum()),
                mean_wrong_abs_llr=float(abs(llr[wrong]).mean()) if wrong.any() else None,
                max_wrong_abs_llr=float(abs(llr[wrong]).max()) if wrong.any() else None,
                wrong_positions=np.flatnonzero(wrong).tolist())


def bind(base, contract_path):
    c = read(contract_path)
    campaign = base/'outputs_tail_terminal_v5_20260916'
    source = base/'outputs_ce_state_20260915/source-v4'
    analysis = campaign/'analysis-source-v1'
    require(sha(source/'source-manifest.json') == c['source_manifest_sha256'], 'source manifest')
    require(sha(analysis/'tail-terminal-contract-v5.json') == c['old_contract_sha256'], 'old contract')
    old = read(analysis/'tail-terminal-contract-v5.json')
    for name, digest in old['implementation_sha256'].items():
        require(sha(analysis/name) == digest, 'analysis source: '+name)
    sys.path[:0] = [str(source), str(analysis)]
    import torch
    import tail_completion_v2 as tail
    from tail_terminal_run_v4 import InputBank
    tail.assert_threads()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    args = SimpleNamespace(source_dir=source, source_manifest=source/'source-manifest.json',
        old_root=base/'outputs_trans_next_20260913',
        ridge_root=base/'outputs_dirichlet_shrinkage_20260914')
    tail.source_guard(args, old)
    tail.input_guard(args, old)
    summaries = {}
    entries = {}
    for stage in ('engineering', 'development'):
        p = campaign/f'runs/{stage}/producer/summary.json'
        producer, audit = read(p), read(campaign/f'runs/{stage}/audit/summary.json')
        require(producer['status'] == audit['status'] == 'COMPLETE', 'incomplete stage')
        require(audit['producer_summary_sha256'] == sha(p), 'summary binding')
        require(producer['rows'] == audit['rows'] and producer['original_rows'] == audit['original_rows'], 'row parity')
        require(producer['contract_sha256'] == audit['contract_sha256'] == c['old_contract_sha256'], 'record contract')
        summaries[stage] = producer, audit
        for e in producer['records']:
            key = e['block'], e['snr'], e['arm']
            require(key not in entries, 'duplicate terminal')
            entries[key] = e
    require(len(entries) == 132, 'terminal inventory')
    return c, campaign, InputBank(args, old), summaries, entries


def historical_accounting(base):
    versions = []
    for version in range(1, 6):
        root = base/('outputs_tail_terminal_20260916' if version == 1 else f'outputs_tail_terminal_v{version}_20260916')
        require(root.is_dir(), 'missing historical run')
        reserves = sorted(root.glob('runs/**/*-reserve.json'))
        results = sorted(root.glob('runs/**/*-result.json'))
        stages = []
        for stage in sorted({p.parent for p in reserves+results}):
            rr, done = list(stage.glob('*-reserve.json')), list(stage.glob('*-result.json'))
            completed_tokens = {read(p)['token'] for p in done}
            stages.append(dict(path=str(stage), reserved=len(rr), completed=len(done),
                kind=read(rr[0])['kind'] if rr else read(done[0])['kind'],
                unfinished=[read(p) for p in rr if read(p)['token'] not in completed_tokens]))
        exits = [dict(path=str(p), sha256=sha(p), **read(p)) for p in sorted(root.glob('evidence/*-exit.json'))]
        failures = [dict(path=str(p), sha256=sha(p), **read(p)) for p in sorted(root.glob('runs/**/failure.json'))]
        versions.append(dict(version=version, stages=stages, exits=exits, failures=failures))
    completed = {k:sum(s['completed'] for v in versions for s in v['stages'] if s['kind']==k) for k in ('T','D')}
    reserved = {k:sum(s['reserved'] for v in versions for s in v['stages'] if s['kind']==k) for k in ('T','D')}
    return dict(versions=versions, completed=completed, reserved=reserved,
                supervisor_seconds=sum(e['wall_seconds'] for v in versions for e in v['exits']),
                completed_LDPC=sum(completed.values()),
                note='Unfinished reservations are attempts, not proof that numerical work or LDPC completed.')


def raw_audit(base, out, contract):
    c, campaign, bank, summaries, entries = bind(base, contract)
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record, check_decode_identity, decoder_scores
    from afdm_sp_joint_unrolled.supplement_profile import score_errors
    from tail_terminal_run_v4 import channel_scores
    from tail_terminal_v1 import check_terminal, TERMINAL_FIELDS
    inventory, rows = [], []
    arrays = 0
    for stage, (producer, audit) in summaries.items():
        pairs = {(e['block'], e['snr'], e['arm']):e for e in audit['records']}
        originals = {(r['block'], r['snr']):r for r in producer['original_rows']}
        seen_original = set()
        for entry in producer['records']:
            key = entry['block'], entry['snr'], entry['arm']
            record, value = verified_record(entry, campaign/'runs')
            ae = pairs[key]
            audit_record, replay = verified_record(ae, campaign/'runs')
            require(audit_record['terminal_record_sha256'] == entry['sha256'], 'audit terminal binding')
            check_decode_identity(replay, value)
            np.testing.assert_array_equal(replay['llr'], value['llr'])
            point = bank.load(key[0], key[1])
            for k, v in point['provenance'].items():
                require(record[k] == v, 'physical/prior binding: '+k)
            check_terminal(value, value, float(point['observed']['sigma2']), point['prior'])
            scores = dict(score_errors(value, point['raw']), **channel_scores(value['H'], point['raw']))
            require(scores == record['scores'] == entry['scores'], 'raw producer scoring')
            require(decoder_scores(replay, point['raw']) == audit_record['scores'] == ae['scores'], 'raw audit scoring')
            for e, r in ((entry, record), (ae, audit_record)):
                reserve_path = Path(e['record']).with_name(r['token']+'-reserve.json')
                reserve = read(reserve_path)
                require(all(reserve[k] == r[k] for k in ('token','kind','block','snr','split','arm')), 'reservation binding')
                arrays += len(r['state']['file']['fields'])
                file = r['state']['file']
                require(Path(file['path']).stat().st_size == file['bytes'], 'raw size')
                require(hashlib.md5(Path(file['path']).read_bytes()).hexdigest() == file['md5'], 'raw md5')
                inventory.append(dict(record=e['record'], sha256=e['sha256'], reserve_sha256=sha(reserve_path), file=file))
            if key[2] == 'ORIGINAL':
                for k in TERMINAL_FIELDS:
                    np.testing.assert_array_equal(value[k], point['old'][k])
            rows.append(dict(block=key[0], snr=key[1], arm=key[2], scores=scores,
                clipped=margins(value['llr'], point['raw']['coded']),
                raw=margins(value['raw_llr'], point['raw']['coded'])))
            if key[:2] not in seen_original:
                require(originals[key[:2]]['scores'] == point['original_scores'], 'original raw score')
                if key[2] != 'ORIGINAL':
                    rows.append(dict(block=key[0], snr=key[1], arm='ORIGINAL', scores=point['original_scores'],
                        clipped=margins(point['old']['llr'], point['raw']['coded']),
                        raw=margins(point['old']['raw_llr'], point['raw']['coded'])))
                seen_original.add(key[:2])
        print(json.dumps(dict(stage=stage, records=len(inventory), arrays=arrays)), flush=True)
    require(len(inventory) == 264 and len(rows) == 192, 'raw/point inventory')
    write(out/'raw-audit.json', dict(status='PASS', records=264, arrays=arrays, inventory=inventory,
        old_contract_sha256=c['old_contract_sha256'], source_manifest_sha256=c['source_manifest_sha256'],
        summaries={str(campaign/f'runs/{s}/{mode}/summary.json'):sha(campaign/f'runs/{s}/{mode}/summary.json')
                   for s in summaries for mode in ('producer','audit')},
        scope='stored arrays, source, scores, provenance and stored producer/audit identity; no new decoding',
        new_calls=dict(F=0,T=0,D=0,A=0)))
    write(out/'historical-accounting.json', historical_accounting(base))
    write(out/'mechanism.json', dict(status='COMPLETE_DESCRIPTIVE_ONLY', rows=rows,
        scope='192 exposed saved endpoints on 32 shared channels; no causal attribution or independent confirmation',
        new_calls=dict(F=0,T=0,D=0,A=0)))


def gpu_qual(base, out, contract):
    c, campaign, bank, summaries, entries = bind(base, contract)
    import torch
    from afdm_sp_joint_unrolled.direction_receiver import terminal_decode
    from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS, verified_record
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.supplement_adjacent_run import save_state
    from afdm_sp_joint_unrolled.supplement_timing_integrity import OutputMeter
    from tail_terminal_v1 import TERMINAL_FIELDS
    require(torch.cuda.is_available(), 'CUDA unavailable')
    require(c['gpu_cases'] == [[0,7,'ORIGINAL'],[14,7,'TAIL'],[14,7,'RIDGE_T']]
        and c['max_T_cpu'] == c['max_T_cuda'] == 3 and c['max_LDPC'] == 6
        and c['atol'] == 1e-9 and c['rtol'] == 1e-7, 'qualification scope changed')
    torch.cuda.set_per_process_memory_fraction(.25, 0)
    (out/'code-cache').mkdir()
    code = build_code(cache_dir=out/'code-cache')
    expected = read(campaign/'runs/engineering/producer/environment.json')['code_identity']
    require(hashes({k:code[k] for k in CODE_KEYS}) == expected, 'LDPC identity')
    meter = OutputMeter(out, c['max_output_bytes'])
    meter.adopt_tree(out)
    write(out/'environment.json', dict(torch=torch.__version__, numpy=np.__version__,
        cuda=torch.version.cuda, GPU=torch.cuda.get_device_name(0), threads=torch.get_num_threads(),
        source_manifest_sha256=c['source_manifest_sha256'], code_identity=expected))
    rows = []
    def timeout(signum, frame):
        raise TimeoutError('terminal call exceeded 120 seconds')
    signal.signal(signal.SIGALRM, timeout)
    for index, case in enumerate(c['gpu_cases']):
        key = tuple(case)
        e = entries[key]
        record, saved = verified_record(e, campaign/'runs')
        point = bank.load(case[0], case[1])
        prior = saved['last_check_prior']
        np.testing.assert_array_equal(prior, point['prior'])
        values, receipts = {}, {}
        for device in ('cpu','cuda:0'):
            label = f'case{index}-{device.replace(":", "")}'
            write(out/(label+'-reserve.json'), dict(case=case, device=device, T=1, LDPC=1, reserved_at=time.time(),
                source_record=e, contract_sha256=sha(contract), observed_hashes=hashes({
                    'H':saved['H'],'z':saved['z'],'prior':prior})))
            signal.alarm(c['timeout_per_call'])
            started = time.perf_counter()
            try:
                value = terminal_decode(saved['z'], saved['H'], saved['sigma2_terminal'],
                    point['observed']['constellation'], code, device=device, audit=True,
                    code_prior=prior, bp_temperature=1., bp_iterations=20)
                if device.startswith('cuda'):
                    torch.cuda.synchronize()
            finally:
                signal.alarm(0)
            artifact = save_state(out/(label+'.npz'), value, meter, readback=True)
            receipt = dict(case=case, device=device, T=1, LDPC=1, seconds=time.perf_counter()-started,
                           state=artifact, source_record=e, completed=True)
            write(out/(label+'-result.json'), receipt)
            values[device], receipts[device] = value, receipt
        cpu, cuda = values['cpu'], values['cuda:0']
        cpu_checks = {k:bool(np.array_equal(cpu[k],saved[k])) for k in TERMINAL_FIELDS}
        hard = {k:bool(np.array_equal(cpu[k],cuda[k])) for k in ('decoded','info_hat','x_hard','decode_ok')}
        numeric = {k:dict(allclose=bool(np.allclose(cuda[k],cpu[k],atol=c['atol'],rtol=c['rtol'])),
            max_abs=float(np.max(abs(cuda[k]-cpu[k]))),exact=bool(np.array_equal(cuda[k],cpu[k])))
            for k in ('mu','var','raw_llr','llr')}
        graphs_equal = cpu['graphs'][0]['H_hash'] == cuda['graphs'][0]['H_hash']
        passed = (all(cpu_checks.values()) and all(hard.values())
                  and all(v['allclose'] for v in numeric.values()) and graphs_equal)
        rows.append(dict(case=case, CPU_saved_exact=cpu_checks, CUDA_hard_exact=hard, CUDA_numeric=numeric, passed=passed,
            graphs_equal=graphs_equal,
            seconds={d:r['seconds'] for d,r in receipts.items()}))
        print(json.dumps(rows[-1]), flush=True)
    write(out/'summary.json', dict(status='PASS' if all(r['passed'] for r in rows) else 'FAIL_QUALIFICATION',
        cases=rows, calls=dict(T_cpu=3,T_cuda=3,LDPC=6,F=0,A=0),
        scope='three exposed terminal samples only; CE/full receiver equivalence and formal cost untested',
        contract_sha256=sha(contract), source_manifest_sha256=c['source_manifest_sha256']))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--mode', choices=('raw','gpu'), required=True)
    a = p.parse_args()
    require(a.output.resolve().is_relative_to('/data/guoyikun/'), 'output outside data root')
    a.output.mkdir(exist_ok=False)
    try:
        (raw_audit if a.mode == 'raw' else gpu_qual)(a.base, a.output, a.contract)
    except BaseException as exc:
        import traceback
        write(a.output/'failure.json', dict(error=repr(exc), traceback=traceback.format_exc()))
        raise
