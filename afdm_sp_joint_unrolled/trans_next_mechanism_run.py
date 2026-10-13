"""Paired finite differences of CE-mediated delivered-prior self influence.

All scientific inputs are previously generated development observations. Truth
is used only for offline scores, never bit selection or receiver intervention.
"""
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
from .light_gap_receiver_run import NUMERIC_FIELDS
from .trans_next_sensitivity import ce_direction, mean_design_direction, eligible_bits


def decoder_record(value):
    rows=[r for r in value['code_feedback_records'] if r['stage']=='decoder']
    if len(rows)!=1:raise ValueError('mechanism needs exactly one original decoder checkpoint')
    return rows[0]


def channel_at_two(value):
    rows=[r for r in value['code_feedback_records'] if r['stage']=='detector_consume']
    if len(rows)!=3:raise ValueError('three instrumented outer BP messages required')
    return rows[2]['channel_llr']


def assert_frozen_prefix(value, base, *, frozen_ce):
    """Check actual consumer arrays and the unmodified decoder invocation."""
    for field in ('A','g_previous','H','mu','sigma2','regularization','g_solution'):
        np.testing.assert_array_equal(value['dals'][0][field],base['dals'][0][field])
    a,b=decoder_record(value),decoder_record(base)
    for field in ('channel_llr','decoder_input','raw_app','raw_check_extrinsic','prior_after'):
        np.testing.assert_array_equal(a[field],b[field])
    a,b=value['dals'][1],base['dals'][1]
    for field in ('H','g_previous','sigma2','regularization','support_delays','support_dopplers'):
        np.testing.assert_array_equal(a[field],b[field])
    if frozen_ce:
        for field in ('A','mu','finite_variance','g_solution'):
            np.testing.assert_array_equal(a[field],b[field])
        np.testing.assert_array_equal(value['H'],base['H'])


def execute(args):
    if sha(args.contract)!=args.contract_sha256 or sha(args.source_manifest)!=args.source_sha256:
        raise ValueError('mechanism source/contract identity changed')
    c=json.loads(args.contract.read_text())
    if (c['schema']!='trans-ce-mediation-v1' or c['device']!='cpu' or c['threads']!=1
            or c['steps']!=[.1,.05] or args.root.name!=c['tag']
            or sha(c['input_summary'])!=c['input_summary_sha256']
            or sha(c['checkpoint_path'])!=c['checkpoint_sha256']):
        raise ValueError('mechanism frozen input/algorithm differs')
    guard=setup_guard(args,c)
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(args.root,'diagnostic',dict(F=c['F_limit'],seconds=c['seconds']),c['output_bytes'],guard)
    try:
        cache=run.out/'code-cache';cache.mkdir();code=build_code(cache_dir=cache);run.meter.adopt_tree(cache)
        source=json.loads(Path(c['input_summary']).read_text())
        if source['status']!='COMPLETE':raise ValueError('incomplete input campaign')
        source_env=json.loads(Path(c['input_summary']).with_name('environment.json').read_text())
        if hashes({k:code[k] for k in CODE_KEYS})!=source_env['code_identity']:
            raise ValueError('mechanism code differs from reference')
        exo={e['block']:e for e in source['exogenous']}
        refs={(r['block'],r['snr']):r for r in source['records'] if r['arm']=='MEAN'}
        system=_make_config_a(1024,2.,8,10.,4.)
        model=build_receiver(c['checkpoint_path'],system,1024,'cpu',receiver_shell='direct40',active_cap=40)
        receiver=BaselineReceiver(model,code,'B0-p2-s0.5',system=system,initial_lstsq_driver='gels')
        run.write('environment.json',dict(device='cpu',torch=torch.__version__,numpy=np.__version__,
            threads=1,initial_lstsq_driver='gels',source_sha256=args.source_sha256,
            contract_sha256=args.contract_sha256,code_identity=source_env['code_identity']))
        comparisons=[];selection=[];checks=0
        for block in c['blocks']:
            raw=load_state(exo[block]['state'])
            if hashes({k:raw[k] for k in exo[block]['hashes']})!=exo[block]['hashes']:
                raise ValueError('input raw identity differs')
            for snr in c['snrs']:
                observed=observed_at_snr(raw,snr);before=hashes(observed)
                def evaluate(name, stimulus=None, outer=3):
                    def fn():
                        fb=CodeFeedback(code,checkpoint=1,retain_messages=True,
                            retain_detector_messages=True,diagnostic_perturbation=stimulus)
                        value=receiver.run(observed,audit=True,code_feedback=fb,
                            bp_schedule=UniformBPSchedule(outer_bp_iterations=12),outer_iteration_limit=outer)
                        if len(value['dals'])!=outer-1 or len(value['bp_schedule']['calls'])!=outer:
                            raise ValueError('incomplete mechanism receiver')
                        value['resource_counts']=dict(outer_BP_calls=outer,
                            outer_BP_iterations=sum(r['executed_iterations'] for r in value['bp_schedule']['calls']),
                            terminal_BP_calls=1,terminal_BP_iterations=20 if value['graphs'][-1]['edges'] else 0,
                            LDPC_calls=2,CE_solves=outer-1)
                        return value
                    value,_=run.call('F',dict(block=block,snr=snr,split=exo[block]['split'],arm=name),fn,
                        lambda v:offline_scores(v,raw,v['H']),dict(observed_hashes=before,
                            input_summary_sha256=c['input_summary_sha256'],stimulus=stimulus,
                            outer_iterations=outer,truth_access='offline scores only; no truth in intervention'))
                    if hashes(observed)!=before:raise ValueError('mechanism changed paired input')
                    return value
                _,reference=verified_record(refs[block,snr],Path(c['reference_root']))
                if c['default_ten_step_replay']:
                    replay=evaluate('DEFAULT10',outer=10)
                    for field in NUMERIC_FIELDS:np.testing.assert_array_equal(replay[field],reference[field])
                    checks+=1
                base=evaluate('BASE3')
                for index in (0,1):
                    for field in ('A','g_previous','H','mu','sigma2','regularization','g_solution'):
                        np.testing.assert_array_equal(base['dals'][index][field],reference['dals'][index][field])
                message=decoder_record(base);bits=eligible_bits(message['channel_llr'],message['prior_after'])
                selection.append(dict(block=block,snr=snr,bits=bits,missing_components=2-len(bits),
                    rule='first unsaturated I and Q, abs(channel+prior)<8 and abs(prior)<19.9'))
                state=base['dals'][1];app=message['channel_llr']+message['prior_after']
                for bit in bits:
                    if c['zero_controls']:
                        for affect in (False,True):
                            zero=evaluate(f'ZERO-{bit}-{int(affect)}',dict(bit=bit,delta=0.,affect_ce=affect))
                            for field in NUMERIC_FIELDS:np.testing.assert_array_equal(zero[field],base[field])
                            assert_frozen_prefix(zero,base,frozen_ce=True);checks+=1
                    dA=mean_design_direction(app,bit,state['support_delays'],state['support_dopplers'],
                        raw['params']['c1'],raw['params']['c2'])
                    gain,dgain=ce_direction(state['A'],state['y'],state['g_previous'],
                        float(state['regularization']),dA)
                    for step in c['steps']:
                        values={}
                        for affect in (False,True):
                            for sign in (-1,1):
                                stimulus=dict(bit=bit,delta=sign*step,affect_ce=affect)
                                value=evaluate(f'BIT{bit}-H{step:g}-CE{int(affect)}-S{sign}',stimulus)
                                assert_frozen_prefix(value,base,frozen_ce=not affect)
                                event=next(r for r in value['code_feedback_records'] if r['stage']=='prior_perturbation')
                                changed=np.flatnonzero(event['prior_after']!=event['prior_before'])
                                np.testing.assert_array_equal(changed,[bit])
                                if value['baseline_eligible'] or value.get('deployment_eligible') is not False:
                                    raise ValueError('diagnostic incorrectly eligible for baseline claim')
                                values[affect,sign]=(channel_at_two(value),value['dals'][1]['g_solution'])
                                checks+=1
                        det=(values[False,1][0]-values[False,-1][0])/(2*step)
                        total=(values[True,1][0]-values[True,-1][0])/(2*step)
                        numerical=(values[True,1][1]-values[True,-1][1])/(2*step)
                        error=float(np.linalg.norm(numerical-dgain));norm=float(np.linalg.norm(dgain))
                        comparisons.append(dict(block=block,snr=snr,bit=bit,step=step,
                            detector_self=float(det[bit]),total_self=float(total[bit]),
                            mediated_self=float(total[bit]-det[bit]),
                            mediated_vector_norm=float(np.linalg.norm(total-det)),
                            analytic_gain_derivative_norm=norm,gain_derivative_error=error,
                            gain_derivative_relative_error=error/max(norm,1e-12),
                            float64_gain_relative_error=float(np.linalg.norm(gain-state['g_solution'])/max(1e-12,np.linalg.norm(gain)))))
                print(json.dumps(dict(block=block,snr=snr,calls=run.counts,bits=bits)),flush=True)
        guard.verify();run.meter.verify()
        if sha(c['input_summary'])!=c['input_summary_sha256']:raise ValueError('input summary changed')
        run.write('summary.json',dict(status='COMPLETE',tag=c['tag'],calls=run.counts,
            records=run.records,comparisons=comparisons,selection=selection,exact_checks=checks,
            contract_sha256=args.contract_sha256,source_sha256=args.source_sha256,
            input_summary_sha256=c['input_summary_sha256'],wall_seconds=time.time()-run.started,
            scope='fixed 3-outer-step local diagnostic; no independent FER confirmation'))
        print(json.dumps(dict(status='COMPLETE',calls=run.counts,exact_checks=checks)),flush=True)
    except BaseException as exc:
        run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','contract','source-manifest'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('contract-sha256','source-sha256'):p.add_argument('--'+name,required=True)
    execute(p.parse_args())
