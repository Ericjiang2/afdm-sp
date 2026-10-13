"""Classical full-covariance working GCV on legal frozen G1 inputs."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np

ARMS=['W_S_P','W_S_ALL','W_D_P','W_D_ALL']


def fit_legal(y,pilot,mu,variance,sigma2,Hc,support,c1,c2,*,l_max=102,k_max=2):
    import torch
    from gcv_ridge_selector import select_ridge
    from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch,soft_gain_update,reconstruct_H_torch,residual_data_covariance
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support
    n=len(y);width=2*k_max+1
    if (any(not np.isfinite(a).all() for a in (y,pilot,mu,variance,Hc,support))
            or any(np.shape(a)!=(n,) for a in (y,pilot,mu,variance)) or np.shape(Hc)!=(n,n)
            or np.iscomplexobj(variance) or np.any(np.asarray(variance)<0) or not np.isfinite(sigma2) or sigma2<=0
            or not np.isfinite([c1,c2]).all() or np.asarray(support).dtype.kind not in 'iu'
            or np.asarray(support).ndim!=1 or not len(support)
            or len(set(support.tolist()))!=len(support)
            or np.any(support<0) or np.any(support>=(l_max+1)*width)
            or (l_max+1)*width>=n or 2*n*c1!=width):
        raise ValueError('invalid legal inputs or tall collision-free domain')
    yt=torch.as_tensor(y,dtype=torch.complex128)
    total=torch.as_tensor(pilot,dtype=torch.complex128)+torch.as_tensor(mu,dtype=torch.complex128)
    hc=torch.as_tensor(Hc,dtype=torch.complex128)
    covariance_started=time.perf_counter()
    noise_power=torch.tensor(sigma2,dtype=torch.float64)
    C=residual_data_covariance(hc,torch.as_tensor(variance,dtype=torch.float64),noise_power)
    L=torch.linalg.cholesky(C)
    yw=torch.sqrt(noise_power)*torch.linalg.solve_triangular(L,yt[:,None],upper=False)[:,0]
    fitted=dict(covariance=dict(C=C.numpy(),L=L.numpy(),yw=yw.numpy(),sigma2=float(sigma2),
        seconds=time.perf_counter()-covariance_started,C_constructions=1,Cholesky_calls=1,whitening_triangular_solves=1))
    for name,ids in [('S',support),('D',np.arange((l_max+1)*width))]:
        started=time.perf_counter();delays=torch.tensor(ids//width,dtype=torch.long);dopplers=torch.tensor(ids%width-k_max,dtype=torch.long)
        projection,previous=project_channel_on_support(hc,delays,dopplers,c1,c2,k_max)
        error=float(torch.linalg.norm(projection-hc)/torch.linalg.norm(hc))
        if not np.isfinite(error) or error>1e-6:raise ValueError('Hc outside prior support')
        A=build_A_for_DALS_torch(n,delays,dopplers,total,c1,c2,k_max)
        Aw=torch.sqrt(noise_power)*torch.linalg.solve_triangular(L,A,upper=False)
        Aw_array=np.asfortranarray(Aw.numpy())
        selection=select_ridge(Aw_array,yw.numpy(),previous.numpy())
        if selection['no_update']:
            gain=previous;H=np.array(Hc,copy=True);solves=0
        else:
            reg=torch.tensor(selection['selected_regularization'],dtype=torch.float64)
            gain=soft_gain_update(A,yt,previous,reg,C=C,sigma2=noise_power)
            solves=1;H=reconstruct_H_torch(n,delays,dopplers,gain,c1,c2,k_max).numpy()
            np.testing.assert_allclose(gain.numpy(),previous.numpy()+selection['delta'],rtol=2e-10,atol=2e-10)
        fitted[name]=dict(ids=np.asarray(ids),A=A.numpy(),Aw=Aw_array,previous=previous.numpy(),gains=gain.numpy(),H=H,
            selection=selection,projection_error=error,seconds=time.perf_counter()-started,CE_solves=solves,Cholesky_calls=solves,cholesky_solve_calls=solves,whitening_triangular_solves=1)
        validate_fit(fitted[name],yw.numpy())
    return fitted


def validate_fit(value,y):
    A=np.asfortranarray(value['Aw']);g0=value['previous'];selection=value['selection'];n,p=A.shape
    if any(not np.isfinite(v).all() for v in (A,g0,value['gains'],value['H'])):
        raise ValueError('nonfinite GCV fit')
    matrix=A.conj().T@A;residual=y-A@g0;rhs=A.conj().T@residual
    spectrum=np.linalg.eigvalsh(matrix)[::-1]
    np.testing.assert_allclose(selection['singular_values']**2,spectrum,rtol=1e-10,atol=2e-10)
    scale=float(np.vdot(A,A).real/p)
    np.testing.assert_allclose(selection['scale'],scale,rtol=1e-14,atol=0)
    rows=selection['candidates'];deltas=selection['candidate_deltas'];normal=[]
    assert len(rows)==8 and deltas.shape==(8,p)
    for j,exponent in enumerate(range(-3,4)):
        row=rows[j];delta=deltas[j];reg=scale*10.**exponent
        assert row['exponent']==exponent and row['regularization']==reg and not row['no_update']
        left=matrix+reg*np.eye(p)
        den=np.linalg.norm(left)*np.linalg.norm(delta)+np.linalg.norm(rhs)
        err=float(np.linalg.norm(left@delta-rhs)/den) if den else 0.
        if err>1e-10:raise ValueError('spectral candidate normal equation mismatch')
        normal.append(err)
        df=float(np.sum(selection['singular_values']**2/(selection['singular_values']**2+reg)))
        remaining=residual-A@delta;score=float(np.vdot(remaining,remaining).real/n/(1-df/n)**2)
        assert row['degrees_of_freedom']==df and row['score']==score
    assert rows[-1]==dict(exponent=None,regularization=None,degrees_of_freedom=0.,score=float(np.vdot(residual,residual).real/n),no_update=True)
    np.testing.assert_array_equal(deltas[-1],np.zeros(p,dtype=np.complex128))
    selected=min(range(8),key=lambda i:(rows[i]['score'],-i))
    assert selection['selected_index']==selected and selection['no_update']==rows[selected]['no_update']
    assert selection['selected_regularization']==rows[selected]['regularization']
    assert selection['SVD_calls']==1 and selection['spectral_ridge_candidates']==7
    np.testing.assert_array_equal(selection['delta'],deltas[selected])
    assert value['CE_solves']==value['Cholesky_calls']==value['cholesky_solve_calls']==int(not selection['no_update'])
    assert value['whitening_triangular_solves']==1
    np.testing.assert_allclose(value['gains'],g0+selection['delta'],rtol=2e-10,atol=2e-10)
    return dict(max_candidate_normal_residual=max(normal),selected_index=selected,
        selected_exponent=rows[selected]['exponent'],selected_regularization=rows[selected]['regularization'],
        no_update=selection['no_update'],GCV_score=rows[selected]['score'],baseline_GCV_score=rows[-1]['score'],
        CE_solves=value['CE_solves'],Cholesky_calls=value['Cholesky_calls'],cholesky_solve_calls=value['cholesky_solve_calls'],whitening_triangular_solves=1,SVD_calls=1,spectral_ridge_candidates=7)


def terminal_inputs(arm,y,pilot,Hc,fitted,sigma2,prior):
    if arm not in ARMS:raise ValueError('unknown GCV arm')
    fit=fitted[arm.split('_')[1]]
    cancellation=fit['H']@pilot
    H=fit['H'] if arm.endswith('_ALL') else Hc
    return dict(H=H,z=y-cancellation,cancellation=cancellation,sigma2_terminal=float(sigma2),last_check_prior=prior)


def check_no_update(value,state,fit,arm):
    if not fit[arm.split('_')[1]]['selection']['no_update']:return
    from afdm_sp_joint_unrolled.trans_next_terminal_prior import FIELDS
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    for key in (*FIELDS,'raw_llr'):np.testing.assert_array_equal(value[key],state[key])
    assert hashes(value['finite_message'])==hashes(state['finite_message'])


def main(args):
    root = args.root; source = root/'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    import torch
    from afdm_sp_joint_unrolled import direction_receiver as receiver
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch, reconstruct_H_torch
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.light_gap_replay import (
        CODE_KEYS, LightRun, setup_guard, verified_record, decoder_scores,
        replay_decode, check_decode_identity)
    from afdm_sp_joint_unrolled.supplement_profile import OperatorProfile
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    from afdm_sp_joint_unrolled.trans_next_terminal_prior import check_value
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.trans_next_stop_run import check_calls
    contract = root/'contracts'/(args.tag+'.json'); c = json.loads(contract.read_text())
    manifest = source/'source-manifest.json'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert sha(manifest) == c['source_sha256'] == '5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0'
    assert c['schema'] == 'e1a-whitened-gcv-v2' and c['tag'] == args.tag
    assert c['stage'] in ('engineering', 'development')
    engineering = c['stage'] == 'engineering'
    assert c['blocks'] == ([0, 20] if engineering else [b for b in range(32) if b not in (0, 20)])
    assert c['snrs'] == [7, 8] and c['arms'] == ARMS
    assert c['device'] == 'cpu' and c['threads'] == 1
    na = len(c['blocks'])*2; nt = na*len(ARMS)
    assert c['Aw_replay_order']=='F'
    assert c['bounds'] == (dict(A=0,T=0,D=0,seconds=300) if engineering else dict(A=na,T=nt,D=nt,seconds=3600))
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    assert sha(root/c['selector_path']) == c['selector_sha256']
    sys.path.insert(0,str((root/c['selector_path']).parent))
    for sp, ap in c['audited_inputs'].items():
        a = json.loads((root/ap).read_text())
        assert a['status'] == 'PASS' and a['summary_sha256'] == sha(root/sp)
    if not engineering:
        admission = json.loads((root/c['engineering_audit']).read_text())
        assert admission['script_sha256'] == args.script_sha256 and admission['saved_records'] == 36
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    upstream = json.loads((root/'runs/g1-strong-development-recovery-v1/development/summary.json').read_text())
    index = {(r['kind'], r['block'], r['snr'], r['arm']):r for r in upstream['records']}
    assert len(index) == len(upstream['records']) == 288
    env = json.loads((root/'runs/refs-v1/development/environment.json').read_text())
    out = root/'runs'/args.tag/c['stage']

    def inputs(block, snr):
        pe = index['A', block, 7, 'G1_PROPAGATION']; _, physical = verified_record(pe, root)
        raw, _ = reuse_at_snr(physical['raw'], physical['diagnostics'], snr)
        observed = {k:np.array(raw[k], copy=True) for k in ('y', 'pilot', 'sigma2')}
        observed['constellation'] = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
        ref = index['F', block, snr, 'G1_FULL']; record, state = verified_record(ref, root)
        assert record['observed_hashes'] == hashes(observed)
        assert record['physical_record_sha256'] == pe['sha256'] and ref['split'] == pe['split']
        assert check_calls(state)['operators']['terminal_BP'] == 1
        assert state['terminal_controls_consumed'] and state['terminal_check_prior_consumed']
        assert state['terminal_bp_temperature'] == 1. and state['terminal_variance_source'] == 'physical'
        assert state['sigma2_terminal'] == float(observed['sigma2']) and not state['terminal_scale_applied']
        d = state['dals'][-1]
        assert d['outer_iter'] == 9 and d['mode'] == 'mean' and not d['oracle_mean']
        assert d['moment_source'] == 'code_feedback.ce'
        ids = d['support_delays']*5+d['support_dopplers']+2
        assert len(ids) == 24 and set(ids.tolist()) == set(state['support'])
        legal = dict(y=observed['y'], pilot=observed['pilot'], mu=d['mu'], variance=d['finite_variance'],sigma2=float(observed['sigma2']),
            Hc=state['H'], support=ids, c1=raw['params']['c1'], c2=raw['params']['c2'])
        assert len(legal['y']) == 1024 and 2*1024*legal['c1'] == 5
        checkpoints = [v for v in state['code_feedback_records'] if v['stage'] == 'decoder']
        assert [v['iteration'] for v in checkpoints] == [1, 4, 7]
        prior = checkpoints[-1]['prior_after']
        np.testing.assert_array_equal(prior, np.clip(checkpoints[-1]['raw_check_extrinsic'], -20., 20.))
        provenance = dict(reference_record_sha256=ref['sha256'], physical_record_sha256=pe['sha256'],
            observed_hashes=hashes(observed), legal_input_hashes=hashes(legal), truth_access='external scoring only')
        return raw, observed, state, legal, prior, provenance, ref['split']

    def check_fit(fit, legal):
        cov=fit['covariance'];C=cov['C'];L=cov['L'];sigma2=legal['sigma2']
        Hc=np.asarray(legal['Hc'],dtype=np.complex128);variance=np.asarray(legal['variance'],dtype=np.float64)
        expected_C=(Hc*variance[None,:])@Hc.conj().T+sigma2*np.eye(len(Hc))
        np.testing.assert_allclose(C,expected_C,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(L@L.conj().T,C,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(L@cov['yw'],np.sqrt(sigma2)*legal['y'],rtol=1e-12,atol=1e-12)
        assert cov['sigma2']==sigma2 and cov['C_constructions']==cov['Cholesky_calls']==cov['whitening_triangular_solves']==1
        checks = {}
        for name in ('S', 'D'):
            v = fit[name]; ids = v['ids']
            np.testing.assert_array_equal(ids, legal['support'] if name == 'S' else np.arange(515))
            dt = torch.tensor(ids//5); kt = torch.tensor(ids%5-2)
            A = build_A_for_DALS_torch(1024, dt, kt,
                torch.tensor(legal['pilot'], dtype=torch.complex128)+torch.tensor(legal['mu'], dtype=torch.complex128),
                legal['c1'], legal['c2'], 2).numpy()
            np.testing.assert_array_equal(A, v['A'])
            np.testing.assert_allclose(L@v['Aw'],np.sqrt(sigma2)*A,rtol=1e-12,atol=1e-12)
            if v['selection']['no_update']:
                np.testing.assert_array_equal(v['H'],legal['Hc'])
                assert v['H'].dtype==legal['Hc'].dtype
            else:
                H = reconstruct_H_torch(1024,dt,kt,torch.tensor(v['gains']),legal['c1'],legal['c2'],2).numpy()
                np.testing.assert_array_equal(H,v['H'])
            previous_H = reconstruct_H_torch(1024,dt,kt,torch.tensor(v['previous']),legal['c1'],legal['c2'],2).numpy()
            assert np.linalg.norm(previous_H-legal['Hc'])/np.linalg.norm(legal['Hc']) <= 1e-6
            checks[name] = validate_fit(v,cov['yw'])
        return checks

    def expected(arm, observed, state, fit, prior):
        return terminal_inputs(arm, observed['y'], observed['pilot'], state['H'], fit,
                               observed['sigma2'], prior)

    def check_terminal(value, exp):
        check_value(value, exp, 'RETAIN')
        assert not value['baseline_eligible'] and value['scope'] == c['scope']
        assert len(value['graphs']) == 1
        graph = value['graphs'][0]
        assert graph['H_hash'] == array_hash(np.asarray(exp['H'], dtype=np.complex128))
        assert graph['stage'] == 'final_bp' and graph['threshold'] == 1e-4
        assert graph['dtype'] == 'torch.complex128'
        assert graph['edges'] == value['actual_edges'] == int(np.count_nonzero(abs(np.asarray(exp['H'],dtype=np.complex128)) >= 1e-4))

    def audit(summary):
        assert summary['status'] == 'COMPLETE'
        if engineering:
            assert summary['calls']==dict(A=0,T=0,D=0) and summary['recovered_calls']==dict(A=na,T=nt,D=nt)
        else:
            assert summary['calls']==dict(A=na,T=nt,D=nt)
        records = {(r['kind'],r['block'],r['snr'],r['arm']):r for r in summary['records']}
        wanted = {(k,b,s,a) for k in ('T','D') for b in c['blocks'] for s in c['snrs'] for a in ARMS}
        wanted |= {('A',b,s,'LEGAL_FIT') for b in c['blocks'] for s in c['snrs']}
        assert set(records) == wanted and len(records) == len(summary['records'])
        arrays = 0; rows = []; fits = []
        for b in c['blocks']:
            for snr in c['snrs']:
                raw, observed, state, legal, prior, provenance, split = inputs(b, snr)
                ae = records['A',b,snr,'LEGAL_FIT']; ar, fit = verified_record(ae, root)
                assert all(ar[k] == v for k,v in provenance.items()) and ae['split'] == split
                fits.append(dict(block=b,snr=snr,checks=check_fit(fit,legal),
                    S_seconds=fit['S']['seconds'],D_seconds=fit['D']['seconds'],covariance_seconds=fit['covariance']['seconds']))
                arrays += finite_arrays(fit)
                for arm in ARMS:
                    exp = expected(arm, observed, state, fit, prior)
                    te = records['T',b,snr,arm]; tr, value = verified_record(te,root)
                    assert all(tr[k] == v for k,v in provenance.items())
                    assert tr['estimate_record_sha256'] == ae['sha256'] and tr['terminal_input_hashes'] == hashes(exp)
                    check_terminal(value,exp)
                    check_no_update(value,state,fit,arm)
                    de = records['D',b,snr,arm]; dr, decoded = verified_record(de,root)
                    assert dr['terminal_record_sha256'] == te['sha256']
                    check_decode_identity(decoded,value); np.testing.assert_array_equal(decoded['llr'],value['llr'])
                    scores = decoder_scores(value,raw)
                    assert scores == tr['scores'] == te['scores'] == decoder_scores(decoded,raw) == dr['scores'] == de['scores']
                    for e,r in ((ae,ar),(te,tr),(de,dr)):
                        reservation = json.loads(Path(e['record']).with_name(r['token']+'-reserve.json').read_text())
                        assert all(reservation[k] == r[k] == e[k] for k in ('kind','block','snr','arm','split'))
                        assert e['split'] == split and reservation['token'] == r['token']
                    arrays += finite_arrays(value)+finite_arrays(decoded)
                    rows.append(dict(block=b,snr=snr,arm=arm,scores=scores,actual_edges=value['actual_edges']))
        return dict(saved_records=len(records),arrays=arrays,CE_solves=sum(v['checks'][n]['CE_solves'] for v in fits for n in ('S','D')),SVD_calls=2*na,spectral_ridge_candidates=14*na,C_constructions=na,Cholesky_calls=na+sum(v['checks'][n]['Cholesky_calls'] for v in fits for n in ('S','D')),whitening_triangular_solves=3*na,cholesky_solve_calls=sum(v['checks'][n]['cholesky_solve_calls'] for v in fits for n in ('S','D')),rows=rows,fits=fits)

    if args.mode == 'audit':
        started = time.time(); end = json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        summary = json.loads((out/'summary.json').read_text())
        assert summary['script_sha256'] == args.script_sha256 and summary['contract_sha256'] == args.contract_sha256
        result = audit(summary); assert result == summary['raw_checks']; guard.verify()
        result.update(status='PASS',source_sha256=sha(manifest),script_sha256=args.script_sha256,
            contract_sha256=args.contract_sha256,summary_sha256=sha(out/'summary.json'),
            wall_seconds=time.time()-started,new_F_T_D_A_calls=0,new_CE_solves=0,
            independence='main-session self-review; weak',scope=c['scope'])
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
        print(json.dumps({k:v for k,v in result.items() if k not in ('rows','fits')})); return
    run = LightRun(root/'runs'/args.tag,c['stage'],c['bounds'],c['output_bytes'],guard)
    try:
        if engineering:
            inventory=json.loads((root/c['recovery_inventory']).read_text())
            failure=json.loads((root/c['failed_engineering_failure']).read_text())
            assert failure['calls']==dict(A=4,T=16,D=16) and failure['active'] is None
            assert inventory['producer_script_sha256']=='27f6669618bbbc234673e5ba5277fd3e20b77c592d1c9f32e1152d9012d6c6f5'
            assert inventory['failure_sha256']==sha(root/c['failed_engineering_failure']) and len(inventory['records'])==36
            for entry in inventory['records']:
                verified_record(entry,root);run.records.append(entry)
            summary=dict(status='COMPLETE',calls=run.counts,recovered_calls=dict(A=4,T=16,D=16),records=run.records,
                source_sha256=sha(manifest),script_sha256=args.script_sha256,contract_sha256=args.contract_sha256,scope=c['scope'])
            summary['raw_checks']=audit(summary);guard.verify();run.meter.verify()
            summary['wall_seconds']=time.time()-run.started;run.write('summary.json',summary)
            print(json.dumps(dict(status='RECOVERED',new_calls=run.counts,recovered_calls=summary['recovered_calls'])))
            return
        cache = run.out/'code-cache'; cache.mkdir(); code = build_code(cache_dir=cache); run.meter.adopt_tree(cache)
        assert hashes({k:code[k] for k in CODE_KEYS}) == env['code_identity']
        run.write('environment.json',dict(code_identity=env['code_identity'],source_sha256=sha(manifest),
            numpy=np.__version__,torch=torch.__version__,device='cpu',threads=1,scope=c['scope']))
        for b in c['blocks']:
            for snr in c['snrs']:
                raw,observed,state,legal,prior,provenance,split = inputs(b,snr)
                fit,_ = run.call('A',dict(block=b,snr=snr,split=split,arm='LEGAL_FIT'),
                    lambda:fit_legal(**legal),lambda v:dict(CE_solves=v['S']['CE_solves']+v['D']['CE_solves']),provenance)
                ae = run.records[-1]; check_fit(fit,legal)
                assert hashes(legal) == provenance['legal_input_hashes']
                for arm in ARMS:
                    exp = expected(arm,observed,state,fit,prior)
                    def terminal():
                        edges = []
                        with OperatorProfile(torch.device('cpu')) as profile:
                            value = receiver.terminal_decode(exp['z'],exp['H'],exp['sigma2_terminal'],
                                observed['constellation'],code,audit=True,code_prior=prior,
                                bp_temperature=1.,bp_iterations=20,edge_count_observer=edges.append)
                        assert len(edges) == 1 and edges[0] > 0
                        value.update(exp,operator_profile=profile.rows,actual_edges=edges[0],
                            resource_counts=dict(T=1,BP=1,BP_iterations=20,LDPC=1,CE=0),
                            baseline_eligible=False,scope=c['scope'])
                        return value
                    identity = dict(block=b,snr=snr,split=split,arm=arm)
                    metadata = dict(provenance,estimate_record_sha256=ae['sha256'],terminal_input_hashes=hashes(exp))
                    value,_ = run.call('T',identity,terminal,lambda v:decoder_scores(v,raw),metadata)
                    te = run.records[-1]; check_terminal(value,exp); check_no_update(value,state,fit,arm)
                    assert hashes(exp) == metadata['terminal_input_hashes']
                    run.call('D',identity,lambda:replay_decode(code,value,1.,20.,50),
                        lambda v:decoder_scores(v,raw),dict(terminal_record_sha256=te['sha256']))
                    print(json.dumps(dict(block=b,snr=snr,arm=arm,scores=te['scores'],calls=run.counts)),flush=True)
        summary = dict(status='COMPLETE',calls=run.counts,records=run.records,
            source_sha256=sha(manifest),script_sha256=args.script_sha256,contract_sha256=args.contract_sha256,scope=c['scope'])
        summary['raw_checks'] = audit(summary); guard.verify(); run.meter.verify()
        summary['wall_seconds'] = time.time()-run.started; run.write('summary.json',summary)
    except BaseException as exc:
        run.fail(exc); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True); p.add_argument('--tag',required=True)
    p.add_argument('--mode',choices=['run','audit'],default='run')
    p.add_argument('--contract-sha256',required=True); p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
