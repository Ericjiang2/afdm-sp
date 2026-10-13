"""Bounded paired complete integer-graph engineering across five code domains."""
import argparse
import json
from pathlib import Path
import resource
import sys
import time
from types import SimpleNamespace


def main(args):
    root=args.root;source=root/'source-cpu-cost-factorial-v1';sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha,hashes,load_state,observed_at_snr,offline_scores
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun,setup_guard,verified_record,CODE_KEYS,replay_decode
    from afdm_sp_joint_unrolled.light_gap_receiver_run import run_arm,receiver_resources,NUMERIC_FIELDS
    from afdm_sp_joint_unrolled.light_gap_fresh import save_fresh_input
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state
    from afdm_sp_joint_unrolled.trans_next_cpu_cost_quote import arms
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
    manifest=source/'source-manifest.json';contract=root/'contracts/integer-scale-engineering-v1.json';c=json.loads(contract.read_text())
    assert sha(manifest)=='087b4c81c6817785562e8b05d20c48873611a6b0f0f0433c536a23b363aea766'
    assert sha(contract)==args.contract_sha256 and sha(Path(__file__))==args.script_sha256
    assert c['schema']=='trans-integer-scale-engineering-v1' and c['bounds']==dict(F=30,D=30,seconds=600)
    assert c['arms']==arms() and c['blocks']==list(range(5)) and c['snrs']==[7]
    assert c['namespace']==[20260913,154000,612309] and c['output_bytes']==8*1024**3
    domain=json.loads((root/'evidence/scale-domain-precheck-v1.json').read_text())
    assert domain['status']=='COMPLETE' and domain['calls']==dict(A=5,F=0,D=0) and c['cells']==domain['rows']
    assert [(r['N'],r['v_mean']) for r in c['cells']]==[(512,2.),(1024,2.),(2048,2.),(1024,0.),(1024,4.)]
    assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256']
    guard=setup_guard(SimpleNamespace(contract=contract,contract_sha256=args.contract_sha256,source_manifest=manifest,source_sha256=sha(manifest)),c);guard.verify()
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(root/'runs'/c['tag'],'engineering',c['bounds'],c['output_bytes'],guard)
    try:
        earlier=json.loads((root/'runs/refs-v1/development/summary.json').read_text())['exogenous']
        codes={};exogenous=[];checks=[];cells=[]
        for block,domain in enumerate(c['cells']):
            setup_start=time.perf_counter();N=domain['N'];v=domain['v_mean']
            system=_make_config_a(N,v,8,10.,4.)
            cache=run.out/f'code-cache-{block}';cache.mkdir();code=build_code(n=2*N,cache_dir=cache);run.meter.adopt_tree(cache)
            code_identity=hashes({k:code[k] for k in CODE_KEYS});assert code_identity==domain['code_identity']
            actual_domain=dict(N=N,v_mean=v,fs=system.fs,l_max=system.l_max_cap,k_max=system.k_max_cap,
                K=2*system.k_max_cap+1,dictionary_columns=(system.l_max_cap+1)*(2*system.k_max_cap+1),
                delta_max=system.delta_max,nonoverlap_domain=bool(system.delta_max<N),c1=system.c1,c2=system.c2,
                code_n=code['n'],code_k=int(code['G'].shape[1]),actual_code_rate=code['G'].shape[1]/code['n'])
            assert all(actual_domain[k]==domain[k] for k in actual_domain)
            model=build_receiver(c['checkpoint_path'],system,N,'cpu',receiver_shell='direct40',active_cap=40)
            receiver=BaselineReceiver(model,code,'B0-p2-s0.5',system=system,initial_lstsq_driver='gels')
            setup_seconds=time.perf_counter()-setup_start
            raw,exo=save_fresh_input(run,system,code,block,1,tuple(c['namespace']),earlier+exogenous)
            exogenous.append(exo);observed=observed_at_snr(raw,7);before=hashes(observed)
            plan=[('qualification',0,a) for a in c['arms']]
            plan += [('measurement',repeat,a) for repeat in range(2) for a in (c['arms'][::-1] if repeat==0 else c['arms'])]
            reference=None;reference_counts=None;reference_sha=None;reference_schedule=None
            for phase,repeat,arm in plan:
                audit=phase=='qualification';identity=dict(block=block,snr=7,split=1,arm=arm['name'],phase=phase,repeat=repeat,N=N,v_mean=v)
                value,record=run.call('F',identity,lambda:run_arm(receiver,code,observed,arm,audit=audit),
                    lambda result:offline_scores(result,raw,result['H']),
                    dict(configuration=arm,observed_hashes=before,audit=audit,code_identity=code_identity))
                assert hashes(observed)==before
                counts=receiver_resources(value)
                if reference is None:
                    reference={k:value[k] for k in NUMERIC_FIELDS};reference_counts=counts;reference_sha=run.records[-1]['sha256'];reference_schedule=value['bp_schedule']
                for field in NUMERIC_FIELDS:same_state(value[field],reference[field])
                assert counts==reference_counts
                same_state(value['bp_schedule'],reference_schedule)
                graph_bounds=[]
                if arm['name']=='INTEGER':
                    layouts=value['integer_graph_calls'];calls=value['bp_schedule']['calls']
                    assert len(layouts)==len(calls)==value['completed_outer_detections']
                    assert [r['outer_iter'] for r in layouts]==list(range(len(layouts)))
                    for layout,call in zip(layouts,calls):
                        assert layout['complete_matrix_verified']==audit
                        assert layout['candidate_entries'] % N == 0
                        assert call['edges'] <= layout['candidate_entries']
                        graph_bounds.append(dict(D=layout['candidate_entries']//N,E=call['edges'],N_times_D=layout['candidate_entries'],complete_matrix_verified=layout['complete_matrix_verified']))
                if not audit:assert not value['graphs'] and not value['dals']
                checks.append(dict(identity,numeric_exact=True,resource_counts=counts,reference_record_sha256=reference_sha,
                    graph_edges=[g['edges'] for g in value['graphs']],integer_graph_bounds=graph_bounds,
                    process_peak_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                print(json.dumps(dict(identity,calls=run.counts)),flush=True)
            codes[block]=code
            cells.append(dict(block=block,domain=actual_domain,code_identity=code_identity,setup_seconds=setup_seconds))
            del receiver,model,system,raw,observed,value,reference
        collection_finished=time.time();receiver_records=list(run.records)
        for entry in receiver_records:
            _,saved=verified_record(entry,root);code=codes[entry['block']]
            identity={k:entry[k] for k in ('block','snr','split','arm','phase','repeat','N','v_mean')}
            run.call('D',identity,lambda:replay_decode(code,saved,1.,20.,50),lambda value:dict(identity_exact=True),dict(source_record_sha256=entry['sha256']))
        guard.verify();assert sha(Path(__file__))==args.script_sha256
        assert sha(Path(c['checkpoint_path']))==c['checkpoint_sha256'] and run.counts==dict(F=30,D=30)
        run.write('summary.json',dict(status='COMPLETE',calls=run.counts,cells=cells,exogenous=exogenous,checks=checks,records=run.records,
            source_sha256=sha(manifest),contract_sha256=args.contract_sha256,script_sha256=args.script_sha256,
            collection_finished_at=collection_finished,scope=c['scope']))
        print(json.dumps(dict(status='COMPLETE',calls=run.counts)))
    except BaseException as exc:run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--contract-sha256',required=True);p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
