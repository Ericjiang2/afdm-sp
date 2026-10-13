"""Frozen bounded two-domain transfer experiment and saved-array audit."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np
import torch

DOMAINS = ('uwa',)
PILOTS = ('p0', 'pZ')
SNRS = (10, 20)


def main(args):
    root = args.root
    contract_path = root/'contracts'/(args.tag+'.json')
    c = json.loads(contract_path.read_text())
    source = root/'source-terminal-controls-unit-v1'
    helpers = root/c['helper_directory']
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert digest(contract_path) == args.contract_sha256 and digest(Path(__file__)) == args.script_sha256
    for name, expected in c['helper_hashes'].items():
        assert digest(helpers/name) == expected, name
    sys.path[:0] = [str(helpers), str(source)]
    import physical_transfer_model_v1 as physical
    import physical_transfer_receiver_v1 as receiver
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun, setup_guard, verified_record
    from afdm_sp_joint_unrolled.supplement_adjacent_run import flatten
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    assert sha(contract_path) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert c['schema'] == 'physical-transfer-v1' and c['domains'] == list(DOMAINS)
    assert c['pilots'] == list(PILOTS) and c['snrs'] == list(SNRS) and c['arms'] == list(receiver.ARMS)
    assert c['device'] == 'cpu' and c['threads'] == 1
    def source_guard():
        assert sha(c['checkpoint_path']) == c['checkpoint_sha256']
        for name, digest in c['helper_hashes'].items():
            assert sha(helpers/name) == digest, name
    source_guard()
    assert c['stage'] in ('engineering','development')
    engineering = c['stage'] == 'engineering'
    assert c['blocks'] == ([0, 1] if engineering else list(range(2, 16)))
    na = len(c['blocks'])*len(DOMAINS)
    assert c['bounds']['A'] == na and c['bounds']['F'] == na*20+(5*len(DOMAINS) if engineering else 0)
    recipe = {k:c[k] for k in ('schema','domains','pilots','snrs','arms','source_sha256','checkpoint_sha256','helper_hashes')}
    if not engineering:
        ea = json.loads((root/c['engineering_audit']).read_text())
        assert ea['status'] == 'PASS' and ea['script_sha256'] == sha(Path(__file__))
        assert ea['helper_hashes'] == c['helper_hashes'] and ea['recipe'] == recipe
        assert ea['source_sha256'] == c['source_sha256'] and ea['checkpoint_sha256'] == c['checkpoint_sha256']
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    manifest = source/'source-manifest.json'
    assert sha(manifest) == c['source_sha256']
    guard = setup_guard(SimpleNamespace(contract=contract_path, contract_sha256=sha(contract_path),
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    configs = {domain: physical.config(domain) for domain in DOMAINS}
    def score(value, raw, pilot):
        return receiver.base.offline_score(value, dict(bits=raw['bits'], H=raw['H'], pilot=raw['pilots'][pilot]))
    def equal(a, b):
        return flatten(a, {}) == flatten(b, {})
    def audit(summary):
        assert summary['calls'] == {k:v for k,v in c['bounds'].items() if k != 'seconds'}
        assert summary['helper_hashes'] == c['helper_hashes']
        assert summary['script_sha256'] == sha(Path(__file__)) and summary['contract_sha256'] == sha(contract_path)
        entries = {(e['kind'], e['block'], e['snr'], e['arm']):e for e in summary['records']}
        assert len(entries) == len(summary['records']) == na+c['bounds']['F']
        env_path = root/'runs'/args.tag/c['stage']/'environment.json'
        env = json.loads(env_path.read_text())
        assert env['domains'] == list(DOMAINS) and set(env['setup']) == set(DOMAINS)
        assert env['device'] == 'cpu' and env['threads'] == 1 and env['lstsq_driver'] == 'gels'
        assert env['source_sha256'] == c['source_sha256'] and env['checkpoint_sha256'] == c['checkpoint_sha256']
        assert env['helper_hashes'] == c['helper_hashes'] and summary['recipe'] == recipe
        for item in env['setup'].values():
            assert item['guarded_setup_coding_calls'] == 0 and item['new_training'] is False
            assert item['checkpoint_load'] == 'strict existing build_receiver'
            assert np.isfinite(item['seconds']) and item['seconds'] >= 0
        rows, inputs, arrays = [], [], 0
        for did, domain in enumerate(DOMAINS):
            system = configs[domain]
            cfg = SimpleNamespace(N=system.N_total, l_max=system.l_max_cap, k_max=system.k_max_cap, k_leak=2)
            nominal = min(40, ((cfg.l_max+1)*(2*cfg.k_max+1))//2)
            for block in c['blocks']:
                uid = did*1000+block
                ae = entries['A',uid,10,domain+'_INPUT']
                _, raw = verified_record(ae, root)
                checks = physical.validate(raw, domain, block)
                inputs.append(dict(domain=domain,block=block,checks=checks))
                arrays += finite_arrays(raw)
                for snr in SNRS:
                    for pilot in PILOTS:
                        obs = physical.observed(raw, pilot, snr)
                        for arm in receiver.ARMS:
                            name = pilot+'__'+arm
                            e = entries['F',uid,snr,name]
                            record, value = verified_record(e, root)
                            assert record['observed_hashes'] == hashes(obs)
                            assert record['input_record_sha256'] == ae['sha256']
                            receiver.check(value, arm, cfg, nominal)
                            scores = score(value, raw, pilot)
                            assert scores == e['scores'] == record['scores']
                            rows.append(dict(domain=domain,block=block,N=cfg.N,snr=snr,pilot=pilot,arm=arm,
                                seconds=e['seconds'],CPU_seconds=e['CPU_seconds'],scores=scores,counts=value['counts'],
                                nomination=value['nomination'], total_bp_iterations=sum(x['executed_iterations'] for x in value['bp_schedule']['calls']),
                                mean_bp_edges=float(np.mean([x['edges'] for x in value['bp_schedule']['calls']]))))
                            arrays += finite_arrays(value)
                            if engineering and block == 0 and pilot == 'p0' and snr == 20:
                                re = entries['F',uid,snr,name+'_REPEAT']
                                rr, rv = verified_record(re, root)
                                assert rr['observed_hashes'] == hashes(obs) and equal(rv, value)
                                assert rr['scores'] == re['scores'] == scores
                                arrays += finite_arrays(rv)
        return dict(rows=rows, inputs=inputs, arrays=arrays, saved_records=len(entries),
                    coding_calls=0, exact_repeat_receivers=5*len(DOMAINS) if engineering else 0,
                    environment_sha256=sha(env_path), setup=env['setup'])
    out = root/'runs'/args.tag/c['stage']
    if args.mode == 'audit':
        started = time.time()
        end = json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        summary = json.loads((out/'summary.json').read_text())
        assert summary['status'] == 'COMPLETE'
        details = audit(summary)
        assert details == summary['raw_checks']
        source_guard(); guard.verify()
        report = dict(status='PASS', **details, script_sha256=sha(Path(__file__)),
            contract_sha256=sha(contract_path), source_sha256=sha(manifest),helper_hashes=c['helper_hashes'],
            checkpoint_sha256=c['checkpoint_sha256'],recipe=recipe,
            summary_sha256=sha(out/'summary.json'), wall_seconds=time.time()-started,
            scope=c['scope'], independence='bounded independent code/math review; not independent confirmation')
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f:json.dump(report,f,indent=2)
        print(json.dumps({k:v for k,v in report.items() if k not in ('rows','inputs')}))
        return
    run = LightRun(root/'runs'/args.tag,c['stage'],c['bounds'],c['output_bytes'],guard)
    try:
        models, setup = {}, {}
        for domain in DOMAINS:
            start = time.perf_counter()
            models[domain], setup[domain] = receiver.build(c['checkpoint_path'], configs[domain])
            setup[domain]['seconds'] = time.perf_counter()-start
        run.write('environment.json', dict(numpy=np.__version__,torch=torch.__version__,
            device='cpu',threads=1,lstsq_driver='gels',domains=list(DOMAINS),setup=setup,helper_hashes=c['helper_hashes'],
            source_sha256=sha(manifest), checkpoint_sha256=c['checkpoint_sha256']))
        for did, domain in enumerate(DOMAINS):
            model = models[domain]
            nominal = min(40, ((model.cfg.l_max+1)*(2*model.cfg.k_max+1))//2)
            for block in c['blocks']:
                uid = did*1000+block
                raw, _ = run.call('A',dict(block=uid,snr=10,arm=domain+'_INPUT',split=1),
                    lambda:physical.generate(domain,block),lambda v:{},dict(domain=domain,physical_block=block))
                ae = run.records[-1]
                physical.validate(raw,domain,block)
                for snr in SNRS:
                    for pid, pilot in enumerate(PILOTS):
                        obs = physical.observed(raw,pilot,snr)
                        before = hashes(obs)
                        order = list(receiver.ARMS)
                        np.random.default_rng([20260914,741031,did,block,7,snr,pid]).shuffle(order)
                        for arm in order:
                            name = pilot+'__'+arm
                            value, record = run.call('F',dict(block=uid,snr=snr,arm=name,split=1),
                                lambda:receiver.receive(model,obs,arm,nominal),lambda v:score(v,raw,pilot),
                                dict(domain=domain,physical_block=block,pilot=pilot,receiver_arm=arm,
                                     observed_hashes=before,input_record_sha256=ae['sha256'],order=order))
                            assert hashes(obs) == before
                            print(json.dumps(dict(domain=domain,block=block,pilot=pilot,snr=snr,arm=arm,
                                calls=run.counts,scores=record['scores'],seconds=record['seconds'])),flush=True)
                            if engineering and block == 0 and pilot == 'p0' and snr == 20:
                                repeat, _ = run.call('F',dict(block=uid,snr=snr,arm=name+'_REPEAT',split=1),
                                    lambda:receiver.receive(model,obs,arm,nominal),lambda v:score(v,raw,pilot),
                                    dict(observed_hashes=before,input_record_sha256=ae['sha256']))
                                assert hashes(obs) == before and equal(value,repeat)
        summary = dict(status='COMPLETE',calls=run.counts,records=run.records,
            source_sha256=sha(manifest),script_sha256=sha(Path(__file__)),contract_sha256=sha(contract_path),
            helper_hashes=c['helper_hashes'],recipe=recipe,scope=c['scope'])
        summary['raw_checks'] = audit(summary)
        source_guard(); guard.verify()
        summary['wall_seconds'] = time.time()-run.started
        run.write('summary.json',summary)
        print(json.dumps(dict(status='COMPLETE',calls=run.counts,wall_seconds=summary['wall_seconds'])),flush=True)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--script-sha256',required=True)
    parser.add_argument('--mode',choices=['run','audit'],default='run')
    main(parser.parse_args())
