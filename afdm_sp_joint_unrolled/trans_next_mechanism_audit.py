"""Read back mediation states and separate design/solve finite precision."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from .bottleneck_pilot import hashes, load_state, observed_at_snr, offline_scores, sha
from .light_gap_replay import verified_record
from .light_gap_receiver_run import NUMERIC_FIELDS
from .light_gap_receiver_audit import check_ce, check_feedback
from .trans_next_mechanism_run import decoder_record, channel_at_two, assert_frozen_prefix
from .trans_next_sensitivity import ce_direction, mean_design_direction, eligible_bits


def independent_refit(state):
    A=state['A'].astype(np.complex128);k=A.shape[1];lam=float(state['regularization'])
    augmented=np.vstack((A,np.sqrt(lam)*np.eye(k)))
    rhs=np.concatenate((state['y'],np.sqrt(lam)*state['g_previous']))
    return np.linalg.lstsq(augmented,rhs,rcond=None)[0]


def audit(root, contract_path, source_manifest):
    started=time.time();c=json.loads(contract_path.read_text());tag=c['tag']
    p=root/'runs'/tag/'diagnostic/summary.json';s=json.loads(p.read_text())
    exit_path=root/'evidence'/f'{tag}-exit.json';exit_record=json.loads(exit_path.read_text())
    if (s['status']!='COMPLETE' or exit_record['exit_code']!=0 or exit_record['timed_out']
            or s['contract_sha256']!=sha(contract_path) or s['source_sha256']!=sha(source_manifest)
            or sha(c['input_summary'])!=c['input_summary_sha256']):
        raise ValueError('incomplete or mismatched mechanism evidence')
    inputs=json.loads(Path(c['input_summary']).read_text())
    exo={e['block']:e for e in inputs['exogenous']}
    references={(r['block'],r['snr']):r for r in inputs['records'] if r['arm']=='MEAN'}
    index={};seen=set();arrays=0;ce_count=0;bytes_total=0;zero_checks=0
    for item in s['records']:
        key=(item['block'],item['snr'],item['arm'])
        if key in seen:raise ValueError('duplicate diagnostic record')
        seen.add(key);r,v=verified_record(item,root)
        if (r['block'] not in c['blocks'] or r['snr'] not in c['snrs']
                or r['split']!=exo[r['block']]['split']):raise ValueError('unregistered diagnostic input')
        reservation=json.loads(Path(item['record']).with_name(r['token']+'-reserve.json').read_text())
        if any(reservation[k]!=r[k] for k in ('token','block','snr','arm','split','kind')):
            raise ValueError('diagnostic reservation differs')
        truth=load_state(exo[r['block']]['state']);observed=observed_at_snr(truth,r['snr'])
        if r['observed_hashes']!=hashes(observed) or offline_scores(v,truth,v['H'])!=r['scores']:
            raise ValueError('paired observations or raw diagnostic scores differ')
        if r['scores']!=item['scores']:raise ValueError('summary score differs')
        consumers={x['iteration']:x for x in v['code_feedback_records'] if x['stage']=='CE_consume'}
        for state in v['dals']:
            check_ce(state,observed,truth['params'],consumers[state['outer_iter']],{})
            ce_count+=1
        count=r['outer_iterations']
        expected=dict(outer_BP_calls=count,
            outer_BP_iterations=sum(x['executed_iterations'] for x in v['bp_schedule']['calls']),
            terminal_BP_calls=1,terminal_BP_iterations=20 if v['graphs'][-1]['edges'] else 0,
            LDPC_calls=2,CE_solves=count-1)
        if v['resource_counts']!=expected:raise ValueError('nested diagnostic call accounting differs')
        index[key]=(r,v);arrays+=len(r['state']['file']['fields'])
        bytes_total+=Path(r['state']['file']['path']).stat().st_size
    comparisons=[];selection=[];expected_keys=set()
    for block in c['blocks']:
        truth=load_state(exo[block]['state'])
        for snr in c['snrs']:
            expected_keys.add((block,snr,'BASE3'));base=index[block,snr,'BASE3'][1]
            check_feedback(base,{'feedback':{'retain_messages':True}})
            _,reference=verified_record(references[block,snr],Path(c['reference_root']))
            for i in (0,1):
                for field in ('A','H','g_solution','mu','g_previous','sigma2','regularization'):
                    np.testing.assert_array_equal(base['dals'][i][field],reference['dals'][i][field])
            if c['default_ten_step_replay']:
                expected_keys.add((block,snr,'DEFAULT10'));value=index[block,snr,'DEFAULT10'][1]
                for field in NUMERIC_FIELDS:np.testing.assert_array_equal(value[field],reference[field])
            message=decoder_record(base);bits=eligible_bits(message['channel_llr'],message['prior_after'])
            selection.append(dict(block=block,snr=snr,bits=bits))
            state=base['dals'][1];app=message['channel_llr']+message['prior_after']
            for bit in bits:
                if c['zero_controls']:
                    for affect in (False,True):
                        name=f'ZERO-{bit}-{int(affect)}';expected_keys.add((block,snr,name))
                        value=index[block,snr,name][1]
                        for field in NUMERIC_FIELDS:np.testing.assert_array_equal(value[field],base[field])
                        assert_frozen_prefix(value,base,frozen_ce=True);zero_checks+=1
                tangent=mean_design_direction(app,bit,state['support_delays'],state['support_dopplers'],
                    truth['params']['c1'],truth['params']['c2'])
                _,analytic=ce_direction(state['A'],state['y'],state['g_previous'],float(state['regularization']),tangent)
                for step in c['steps']:
                    values={}
                    for affect in (False,True):
                        for sign in (-1,1):
                            name=f'BIT{bit}-H{step:g}-CE{int(affect)}-S{sign}';expected_keys.add((block,snr,name))
                            record,value=index[block,snr,name];stimulus=dict(bit=bit,delta=sign*step,affect_ce=affect)
                            if record['stimulus']!=stimulus:raise ValueError('stimulus configuration differs')
                            assert_frozen_prefix(value,base,frozen_ce=not affect)
                            event=next(x for x in value['code_feedback_records'] if x['stage']=='prior_perturbation')
                            expected=message['prior_after'].copy();expected[bit]+=sign*step
                            np.testing.assert_array_equal(event['prior_after'],expected)
                            capture=[x for x in value['code_feedback_records'] if x['stage']=='detector_consume'][2]
                            np.testing.assert_array_equal(capture['consumed_prior'],expected)
                            if value['baseline_eligible'] or value['deployment_eligible']:
                                raise ValueError('diagnostic mislabeled deployable')
                            values[affect,sign]=value
                    det=(channel_at_two(values[False,1])-channel_at_two(values[False,-1]))/(2*step)
                    total=(channel_at_two(values[True,1])-channel_at_two(values[True,-1]))/(2*step)
                    plus,minus=[values[True,sign]['dals'][1] for sign in (1,-1)]
                    actual=(plus['g_solution']-minus['g_solution'])/(2*step)
                    high_precision=(independent_refit(plus)-independent_refit(minus))/(2*step)
                    comparisons.append(dict(block=block,snr=snr,bit=bit,step=step,
                        detector_self=float(det[bit]),total_self=float(total[bit]),
                        mediated_self=float(total[bit]-det[bit]),
                        analytic_gain_derivative_norm=float(np.linalg.norm(analytic)),
                        total_gain_derivative_error=float(np.linalg.norm(actual-analytic)),
                        float32_solve_contribution=float(np.linalg.norm(actual-high_precision)),
                        rounded_design_and_nonlinearity=float(np.linalg.norm(high_precision-analytic))))
    if seen!=expected_keys or s['calls']!={'F':len(expected_keys)}:
        raise ValueError('missing or unregistered diagnostic call')
    if len(list(p.parent.glob('F-*-result.json')))!=len(seen) or len(list(p.parent.glob('F-*-reserve.json')))!=len(seen):
        raise ValueError('unmatched diagnostic reservations')
    for row in comparisons:
        match=[x for x in s['comparisons'] if all(x[k]==row[k] for k in ('block','snr','bit','step'))]
        if len(match)!=1:raise ValueError('missing/duplicate derivative summary')
        for k in ('detector_self','total_self','mediated_self'):
            if row[k]!=match[0][k]:raise ValueError('raw derivative differs from summary')
    result=dict(status='PASS',scope='raw engineering and local derivative audit, not scientific performance qualification',
        records=len(seen),arrays_audited=arrays,CE_states=ce_count,zero_checks=zero_checks,
        state_bytes=bytes_total,selection=selection,comparisons=comparisons,
        summary_sha256=sha(p),contract_sha256=sha(contract_path),source_sha256=sha(source_manifest),
        auditor_sha256=sha(__file__),wall_seconds=time.time()-started)
    out=root/'evidence'/f'{tag}-raw-audit.json'
    with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({k:result[k] for k in ('status','records','arrays_audited','CE_states','comparisons','wall_seconds')}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','contract','source-manifest'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();audit(args.root,args.contract,args.source_manifest)
