"""Fixed failing input: two full calls and four own-LLR decoder replays."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main(args):
    root=args.root;source=root/'source-cpu-cost-factorial-v1'
    sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes, load_state, observed_at_snr, offline_scores
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun, setup_guard, verified_record, CODE_KEYS, replay_decode
    from afdm_sp_joint_unrolled.light_gap_receiver_run import run_arm, receiver_resources, NUMERIC_FIELDS
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state
    from afdm_sp_joint_unrolled.trans_next_cpu_cost_quote import arms
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
    manifest=source/'source-manifest.json';contract=root/'contracts/projection-sensitive-replay-v1.json'
    c=json.loads(contract.read_text())
    assert sha(manifest)=='087b4c81c6817785562e8b05d20c48873611a6b0f0f0433c536a23b363aea766'
    assert sha(contract)==args.contract_sha256 and sha(Path(__file__))==args.script_sha256
    assert c['schema']=='trans-projection-sensitive-replay-v1' and c['bounds']==dict(F=2,D=4,seconds=120)
    assert c['blocks']==[4] and c['snrs']==[7] and c['arms']==arms(True)[2:]
    assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
    guard=setup_guard(SimpleNamespace(contract=contract,contract_sha256=args.contract_sha256,source_manifest=manifest,source_sha256=sha(manifest)),c);guard.verify()
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(root/'runs'/c['tag'],'diagnostic',c['bounds'],c['output_bytes'],guard)
    try:
        cache=run.out/'code-cache';cache.mkdir();code=build_code(cache_dir=cache);run.meter.adopt_tree(cache)
        old_env=json.loads((root/'runs/cpu-cost-factorial-v1/quote/environment.json').read_text())
        assert hashes({k:code[k] for k in CODE_KEYS})==old_env['code_identity']
        inputs=json.loads((root/'runs/refs-v1/development/summary.json').read_text())
        exo=next(e for e in inputs['exogenous'] if e['block']==4);raw=load_state(exo['state'])
        assert hashes({k:raw[k] for k in exo['hashes']})==exo['hashes']
        observed=observed_at_snr(raw,7);before=hashes(observed)
        ref_summary=json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
        ref_entry=next(r for r in ref_summary['records'] if r['block']==4 and r['snr']==7 and r['arm']=='BP_RETAIN_STOP')
        ref_record,reference=verified_record(ref_entry,root)
        path=root/'runs/cpu-cost-factorial-v1/quote/F-00075-result.json';failed_record=json.loads(path.read_text())
        failed_entry=dict(failed_record,record=str(path),sha256=sha(path));_,failed=verified_record(failed_entry,root)
        assert before==ref_record['observed_hashes']==failed_record['observed_hashes']
        system=_make_config_a(1024,2.,8,10.,4.)
        model=build_receiver(c['checkpoint_path'],system,1024,'cpu',receiver_shell='direct40',active_cap=40)
        receiver=BaselineReceiver(model,code,'B0-p2-s0.5',system=system,initial_lstsq_driver='gels')
        saved=[('REFERENCE_SAVED',reference,ref_entry['sha256']),('QPSK_FAILED_SAVED',failed,failed_entry['sha256'])]
        checks=[]
        for arm in c['arms']:
            identity=dict(block=4,snr=7,split=2,arm=arm['name'])
            value,record=run.call('F',identity,lambda:run_arm(receiver,code,observed,arm,audit=True),
                lambda v:offline_scores(v,raw,v['H']),dict(configuration=arm,observed_hashes=before))
            assert hashes(observed)==before
            for field in NUMERIC_FIELDS:same_state(value[field],failed[field])
            resources=receiver_resources(value);assert resources==reference['resource_counts']
            saved.append((arm['name'],value,run.records[-1]['sha256']))
            checks.append(dict(identity,numeric_exact_to_failed_QPSK=True,resource_counts=resources,
                instrumented_graphs=len(value['graphs']),saved_CE_states=len(value['dals'])))
        for name,state,digest in saved:
            run.call('D',dict(block=4,snr=7,split=2,arm=name),lambda:replay_decode(code,state,1.,20.,50),
                lambda v:dict(identity_exact=True),dict(source_record_sha256=digest))
        guard.verify();assert sha(Path(__file__))==args.script_sha256
        assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
        assert run.counts==dict(F=2,D=4)
        run.write('summary.json',dict(status='COMPLETE',calls=run.counts,checks=checks,records=run.records,
            source_sha256=sha(manifest),contract_sha256=args.contract_sha256,script_sha256=args.script_sha256,
            code_identity=old_env['code_identity'],scope=c['scope']))
        print(json.dumps(dict(status='COMPLETE',calls=run.counts,checks=checks)))
    except BaseException as exc:run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--contract-sha256',required=True);p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
