"""Budgeted full CPU receiver comparisons on shared observed-only inputs."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from .bottleneck_pilot import hashes, load_state, observed_at_snr, sha, offline_scores
from .budgeted_support_eval import build_receiver
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver
from .supplement_feedback import CodeFeedback
from .supplement_feedback_schedule import UniformBPSchedule
from .e1_ldpc import build_code
from .light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record
from .light_gap_fresh import fresh_namespace, stage_arms, earlier_exogenous, save_fresh_input

NUMERIC_FIELDS=('H','sigma2','sigma2_terminal','x_soft','gains','mu','var','llr',
                'support','x_hard','decoded','info_hat','decode_ok')


def run_arm(receiver, code, observed, arm, *, audit=True):
    """Only public configuration and observation cross the receiver boundary."""
    if (type(audit) is not bool or set(arm)-{'name','receiver','feedback','support_exchange'} or not {'name','receiver'}<=set(arm)
            or set(arm['receiver'])-{'dals_mode','dals_strength','outer_iteration_limit','ce_update_iterations','dals_start_iteration','detector','bp_edge_projection','terminal_check_prior','outer_bp_graph','terminal_bp_temperature','terminal_variance_source'}
            or set(arm.get('feedback',{}))-{'refresh_checkpoints','retain_messages','stop_on_valid_codeword'}):
        raise ValueError('unregistered full receiver control')
    extra={}
    if 'support_exchange' in arm:
        from .light_gap_support_exchange import CodeSupportExchange
        extra['ce_support_exchange']=CodeSupportExchange(**arm['support_exchange'])
    if arm['receiver'].get('detector') not in (None, 'siso_mmse'):
        raise ValueError('unknown full-chain detector')
    if arm['receiver'].get('detector') is None:
        extra['bp_schedule'] = UniformBPSchedule(outer_bp_iterations=12)
    return receiver.run(observed,audit=audit,code_feedback=CodeFeedback(code,checkpoint=1,**arm.get('feedback',{})),
        **arm['receiver'],**extra)


def receiver_resources(value):
    """Count observed completed operations, distinguishing SISO solves from BP."""
    terminal = value.get('terminal_executed', True)
    if type(terminal) is not bool:
        raise ValueError('terminal execution flag must be boolean')
    counts = dict(LDPC_calls=int(terminal)+sum(r['stage']=='decoder' for r in value['code_feedback_records']),
                  CE_solves=len(value['dals']))
    if value.get('detector') == 'siso_mmse':
        if 'bp_schedule' in value or value['graphs']:
            raise ValueError('SISO result unexpectedly contains BP activity')
        calls = value['siso_calls']+([value['terminal_siso']] if terminal else [])
        counts.update(outer_BP_calls=0,outer_BP_iterations=0,terminal_BP_calls=0,terminal_BP_iterations=0,
            outer_SISO_calls=len(value['siso_calls']),terminal_SISO_calls=int(terminal),
            SISO_factorizations=sum(r['linear_solves'] for r in calls),
            SISO_rhs=sum(r['linear_rhs'] for r in calls))
    else:
        schedule = value['bp_schedule']
        if 'completed_ce_solves' in schedule:
            counts['CE_solves'] = schedule['completed_ce_solves']
            terminal_iterations = schedule['final_executed_bp_iterations']
        else:
            # Historical audited records predate the cheap actual counters.
            # A graphless old record has no evidence for CE/terminal work.
            if not value['graphs']:
                raise ValueError('legacy BP resource accounting requires saved audit graphs')
            terminal_iterations = 20 if terminal and value['graphs'][-1]['edges'] else 0
        counts.update(outer_BP_calls=len(schedule['calls']),
            outer_BP_iterations=sum(r['executed_iterations'] for r in schedule['calls']),
            terminal_BP_calls=int(terminal),terminal_BP_iterations=terminal_iterations)
    if 'support_exchange' in value:
        counts['support_small_solves']=sum(value['support_exchange']['solve_counts'].values())
    return counts


def execute(args):
    if sha(args.contract)!=args.contract_sha256 or sha(args.source_manifest)!=args.source_sha256:
        raise ValueError('source/contract identity changed')
    c=json.loads(args.contract.read_text())
    if (c['schema']!='i1-light-full-v1' or c['device']!='cpu' or c['threads']!=1
            or c['initial_lstsq_driver']!='gels' or c['snrs']!=[7,8]
            or c['engineering_blocks']!=2 or len({a['name'] for a in c['arms']})!=len(c['arms'])):
        raise ValueError('full CPU campaign contract differs')
    if args.root.name!=c['tag'] or sha(c['checkpoint_path'])!=c['checkpoint_sha256']:
        raise ValueError('run namespace/checkpoint differs')
    guard=setup_guard(args,c)
    namespace=fresh_namespace(c);configured_arms=stage_arms(c,args.stage)
    if args.stage=='engineering':
        blocks=c['engineering_blocks'];seconds=c['engineering_seconds']
    else:
        if args.admission is None or sha(args.admission)!=args.admission_sha256:
            raise ValueError('development requires hashed engineering admission')
        admission=json.loads(args.admission.read_text());blocks=admission['blocks']
        if (admission['status']!='PASS' or admission['contract_sha256']!=args.contract_sha256
                or admission['source_sha256']!=args.source_sha256
                or admission['engineering_summary_sha256']!=sha(args.root/'engineering/summary.json')
                or blocks not in c['development_block_options']):
            raise ValueError('development admission differs')
        seconds=c['development_seconds']
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    bounds=dict(F=blocks*2*len(configured_arms),seconds=seconds)
    run=LightRun(args.root,args.stage,bounds,c['output_bytes'],guard)
    try:
        cache=run.out/'code-cache';cache.mkdir();code=build_code(cache_dir=cache);run.meter.adopt_tree(cache)
        old=Path(c['old_root']);old_summary=json.loads((old/'runs'/args.stage/'summary.json').read_text())
        old_env=json.loads((old/'runs'/args.stage/'environment.json').read_text())
        if hashes({k:code[k] for k in CODE_KEYS})!=old_env['code_identity']:
            raise ValueError('LDPC code identity differs')
        previous=[]
        if namespace is None:
            exo={e['block']:e for e in old_summary['exogenous'] if e['block']<blocks}
            if set(exo)!=set(range(blocks)):raise ValueError('missing old exogenous blocks')
        else:
            previous=earlier_exogenous(c,args.root,args.stage);exo={}
        system=_make_config_a(1024,2.,8,10.,4.)
        model=build_receiver(c['checkpoint_path'],system,1024,'cpu',receiver_shell='direct40',active_cap=40)
        receiver=BaselineReceiver(model,code,'B0-p2-s0.5',system=system,initial_lstsq_driver='gels')
        prior=None
        if args.stage=='engineering' and namespace is None:
            cp=Path(c['cpu_reference_summary'])
            if sha(cp)!=c['cpu_reference_sha256']:raise ValueError('CPU reference differs')
            prior={(r['block'],r['snr']):r for r in json.loads(cp.read_text())['records'] if r['arm']=='I1_CPU'}
        run.write('environment.json',dict(device='cpu',threads=1,numpy=np.__version__,torch=torch.__version__,
            code_identity=old_env['code_identity'],initial_lstsq_driver='gels',
            source_manifest_sha256=args.source_sha256,contract_sha256=args.contract_sha256,
            fresh_namespace=None if namespace is None else list(namespace)))
        comparisons=[]
        for b in range(blocks):
            if namespace is None:
                raw=load_state(exo[b]['state'])
            else:
                split=1 if args.stage=='engineering' else 2
                raw,exo[b]=save_fresh_input(run,system,code,b,split,namespace,previous+list(exo.values()))
            for snr in c['snrs']:
                observed=observed_at_snr(raw,snr);before=hashes(observed)
                shift=(b*2+snr)%len(configured_arms);arms=configured_arms[shift:]+configured_arms[:shift]
                repeats={}
                for arm in arms:
                    limit=arm['receiver'].get('outer_iteration_limit',10)
                    updates=arm['receiver'].get('ce_update_iterations',list(range(1,limit)))
                    decoder_calls=1+len(arm.get('feedback',{}).get('refresh_checkpoints',[]))
                    def full():
                        value=run_arm(receiver,code,observed,arm)
                        decoder_count=sum(r['stage']=='decoder' for r in value['code_feedback_records'])
                        if not value['baseline_eligible'] or decoder_count!=decoder_calls or len(value['dals'])!=len(updates):
                            raise ValueError('incomplete registered CPU full arm')
                        value['resource_counts']=receiver_resources(value)
                        return value
                    value,_=run.call('F',dict(block=b,snr=snr,split=exo[b]['split'],arm=arm['name']),full,
                        lambda v:offline_scores(v,raw,v['H']),dict(observed_hashes=before,
                            exogenous_hashes=exo[b]['hashes'],configuration=arm,
                            truth_access='offline scoring only',nested_calls=(dict(outer_SISO=limit,
                                terminal_SISO=1,LDPC=decoder_calls+1) if arm['receiver'].get('detector')=='siso_mmse'
                                else dict(outer_BP=limit,outer_BP_iterations=limit*12,
                                          terminal_BP=1,terminal_BP_iterations=20,LDPC=decoder_calls+1))))
                    if hashes(observed)!=before:raise ValueError('receiver mutated paired observation')
                    if namespace is not None and args.stage=='engineering' and arm['name'] in ('MEAN','MEAN_REPEAT'):
                        repeats[arm['name']]={field:value[field] for field in NUMERIC_FIELDS}
                    if prior is not None and arm['name']=='MEAN':
                        _,reference=verified_record(prior[b,snr],Path(c['cpu_reference_root']))
                        for field in NUMERIC_FIELDS:np.testing.assert_array_equal(value[field],reference[field])
                        comparisons.append(dict(block=b,snr=snr,CPU_mean_exact=True))
                if namespace is not None and args.stage=='engineering':
                    for field in NUMERIC_FIELDS:
                        np.testing.assert_array_equal(repeats['MEAN'][field],repeats['MEAN_REPEAT'][field])
                    comparisons.append(dict(block=b,snr=snr,CPU_mean_repeat_exact=True))
                print(json.dumps(dict(block=b,snr=snr,calls=run.counts)),flush=True)
        guard.verify();run.meter.verify()
        if sha(c['checkpoint_path'])!=c['checkpoint_sha256']:raise ValueError('checkpoint changed')
        report=dict(status='COMPLETE',stage=args.stage,tag=c['tag'],blocks=blocks,calls=dict(run.counts,T=0,D=0),
            nested_LDPC=blocks*2*sum(2+len(a.get('feedback',{}).get('refresh_checkpoints',[])) for a in configured_arms),
            records=run.records,exogenous=list(exo.values()),
            engineering_comparisons=comparisons,contract_sha256=args.contract_sha256,
            source_manifest_sha256=args.source_sha256,wall_seconds=time.time()-run.started,
            scope='full observed-only CPU-gels development; audit and storage overhead included in process time')
        if namespace is not None:
            report.update(fresh_namespace=list(namespace),generated_exogenous_blocks=blocks,
                input_generation_seconds=sum(e['generation_seconds'] for e in exo.values()))
        if any('support_exchange' in a for a in configured_arms):
            report['nested_support_small_solves']=blocks*2*sum(3+24*a['support_exchange']['candidate_count'] for a in configured_arms if 'support_exchange' in a)
        run.write('summary.json',report);run.meter.verify()
        print(json.dumps(dict(status='COMPLETE',calls=report['calls'],wall_seconds=report['wall_seconds'])),flush=True)
    except BaseException as exc:
        run.fail(exc);raise


def parser():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--stage',choices=('engineering','development'),required=True)
    p.add_argument('--contract',type=Path,required=True);p.add_argument('--contract-sha256',required=True)
    p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--source-sha256',required=True)
    p.add_argument('--admission',type=Path);p.add_argument('--admission-sha256')
    return p


if __name__=='__main__':execute(parser().parse_args())
