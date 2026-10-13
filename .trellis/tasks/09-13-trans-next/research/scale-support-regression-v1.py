"""Four fixed-input regressions for noncanonical public support metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main(args):
    root=args.root;source=root/'source-receiver-domain-v2';sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha,hashes,load_state,observed_at_snr,offline_scores
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun,setup_guard,verified_record,CODE_KEYS,replay_decode
    from afdm_sp_joint_unrolled.light_gap_receiver_run import run_arm,receiver_resources,NUMERIC_FIELDS
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
    from afdm_sp_joint_unrolled.direction_data import ReceiverDomain
    manifest=source/'source-manifest.json';contract=root/'contracts/scale-support-regression-v1.json';c=json.loads(contract.read_text())
    assert sha(manifest)=='2fd0beb6efd405e7c7921a79c8e209f87203322bed67bc41c7f6cde4a6bb9dd9'
    assert sha(contract)==args.contract_sha256 and sha(Path(__file__))==args.script_sha256
    assert c['bounds']==dict(F=4,D=4,seconds=180) and c['blocks']==[0,2,3,4]
    assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
    guard=setup_guard(SimpleNamespace(contract=contract,contract_sha256=args.contract_sha256,source_manifest=manifest,source_sha256=sha(manifest)),c);guard.verify()
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(root/'runs'/c['tag'],'regression',c['bounds'],c['output_bytes'],guard)
    try:
        previous=json.loads((root/'runs/integer-scale-engineering-v2/engineering/summary.json').read_text())
        assert previous['status']=='COMPLETE';codes={};checks=[]
        for block in c['blocks']:
            domain=c['cells'][block];N=domain['N'];k=domain['k_max']
            old_entry=next(r for r in previous['records'] if r['kind']=='F' and r['block']==block and r['arm']=='INTEGER' and r['phase']=='qualification')
            old_record,expected=verified_record(old_entry,root)
            raw=load_state(previous['exogenous'][block]['state']);observed=observed_at_snr(raw,7);before=hashes(observed)
            assert before==old_record['observed_hashes']
            cache=run.out/f'code-cache-{block}';cache.mkdir();code=build_code(n=2*N,cache_dir=cache);run.meter.adopt_tree(cache)
            assert hashes({key:code[key] for key in CODE_KEYS})==domain['code_identity']
            system=_make_config_a(N,domain['v_mean'],8,10.,4.)
            model=build_receiver(c['checkpoint_path'],system,N,'cpu',receiver_shell='direct40',active_cap=40)
            declared=ReceiverDomain(N,domain['l_max'],k,hashlib.sha256(code['G'].tobytes()).hexdigest())
            receiver=BaselineReceiver(model,code,'B0-p2-s0.5',system=system,initial_lstsq_driver='gels',receiver_domain=declared)
            identity=dict(block=block,snr=7,split=1,arm='INTEGER',N=N,k_max=k)
            value,record=run.call('F',identity,lambda:run_arm(receiver,code,observed,c['arms'][1],audit=True),
                lambda v:offline_scores(v,raw,v['H']),dict(observed_hashes=before,reference_record_sha256=old_entry['sha256']))
            assert hashes(observed)==before
            for field in NUMERIC_FIELDS:
                if field!='support':same_state(value[field],expected[field])
            same_state(value['bp_schedule'],expected['bp_schedule'])
            assert receiver_resources(value)==receiver_resources(expected)
            state=expected['dals'][-1];correct=(state['support_delays']*(2*k+1)+state['support_dopplers']+k).tolist()
            assert value['support']==correct
            assert value['support_trace'][-1]['expanded_atom_ids']==correct
            assert all(r['complete_matrix_verified'] for r in value['integer_graph_calls'])
            checks.append(dict(identity,correct_support=correct,old_support=expected['support'],other_numeric_exact=True,
                resource_counts=receiver_resources(value),reference_record_sha256=old_entry['sha256']))
            codes[block]=code
        for entry in list(run.records):
            _,saved=verified_record(entry,root);code=codes[entry['block']]
            identity={k:entry[k] for k in ('block','snr','split','arm','N','k_max')}
            run.call('D',identity,lambda:replay_decode(code,saved,1.,20.,50),lambda v:dict(identity_exact=True),dict(source_record_sha256=entry['sha256']))
        guard.verify();assert sha(Path(__file__))==args.script_sha256 and run.counts==dict(F=4,D=4)
        assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
        run.write('summary.json',dict(status='COMPLETE',calls=run.counts,checks=checks,records=run.records,
            source_sha256=sha(manifest),contract_sha256=args.contract_sha256,script_sha256=args.script_sha256,scope=c['scope']))
        print(json.dumps(dict(status='COMPLETE',calls=run.counts,checks=checks)))
    except BaseException as exc:run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--contract-sha256',required=True);p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
