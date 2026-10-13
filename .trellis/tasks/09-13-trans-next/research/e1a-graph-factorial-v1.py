"""Controlled original-domain reweighting versus added detector edges; no CE."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np

ARMS=['G_REWEIGHT','G_ADD']


def factor_graph(H0,H1,mask):
    H0=np.asarray(H0,dtype=np.complex128);H1=np.asarray(H1,dtype=np.complex128);mask=np.asarray(mask)
    if (H0.ndim!=2 or H0.shape[0]!=H0.shape[1] or not H0.size or H1.shape!=H0.shape
            or mask.shape!=H0.shape or mask.dtype!=np.bool_
            or not np.isfinite(H0).all() or not np.isfinite(H1).all()):
        raise ValueError('finite matching square matrices and boolean mask required')
    return dict(G_REWEIGHT=np.where(mask,H1,H0),G_ADD=np.where(mask,H0,H1),mask=mask.copy())


def main(args):
    root = args.root; source = root/'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    import torch
    from afdm_sp_joint_unrolled import direction_receiver as receiver
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
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
    assert c['schema'] == 'e1a-graph-factorial-v1' and c['tag'] == args.tag
    assert c['stage'] in ('engineering', 'development')
    engineering = c['stage'] == 'engineering'
    assert c['blocks'] == ([0, 20] if engineering else [b for b in range(32) if b not in (0, 20)])
    assert c['snrs'] == [7, 8] and c['arms'] == ARMS
    assert c['device'] == 'cpu' and c['threads'] == 1
    na = len(c['blocks'])*2; nt = na*len(ARMS)
    assert c['bounds'] == dict(A=na, T=nt, D=nt, seconds=900 if engineering else 1800)
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for sp, ap in c['audited_inputs'].items():
        a = json.loads((root/ap).read_text())
        assert a['status'] == 'PASS' and a['summary_sha256'] == sha(root/sp)
    if not engineering:
        admission = json.loads((root/c['engineering_audit']).read_text())
        assert admission['script_sha256'] == args.script_sha256 and admission['saved_records'] == 20
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    upstream = json.loads((root/'runs/g1-strong-development-recovery-v1/development/summary.json').read_text())
    index = {(r['kind'], r['block'], r['snr'], r['arm']):r for r in upstream['records']}
    assert len(index) == len(upstream['records']) == 288
    env = json.loads((root/'runs/refs-v1/development/environment.json').read_text())
    out = root/'runs'/args.tag/c['stage']
    endpoints={}
    source_estimates={}
    for sp in c['endpoint_summaries']:
        for entry in json.loads((root/sp).read_text())['records']:
            if entry['kind']=='A':
                key=entry['block'],entry['snr'];assert key not in source_estimates;source_estimates[key]=entry
            if entry['kind']=='T' and entry['arm'] in ('W_D_P','W_D_ALL'):
                key=entry['block'],entry['snr'],entry['arm'];assert key not in endpoints;endpoints[key]=entry
    assert len(endpoints)==128 and len(source_estimates)==64

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
        checkpoints = [v for v in state['code_feedback_records'] if v['stage'] == 'decoder']
        assert [v['iteration'] for v in checkpoints] == [1, 4, 7]
        prior = checkpoints[-1]['prior_after']
        np.testing.assert_array_equal(prior, np.clip(checkpoints[-1]['raw_check_extrinsic'], -20., 20.))
        endpoint_values={};endpoint_meta={}
        source_estimate=source_estimates[block,snr]
        for arm in ('W_D_P','W_D_ALL'):
            entry=endpoints[block,snr,arm];metadata,value=verified_record(entry,root)
            assert metadata['physical_record_sha256']==pe['sha256']
            assert metadata['reference_record_sha256']==ref['sha256']
            assert metadata['estimate_record_sha256']==source_estimate['sha256']
            assert metadata['truth_access']=='external scoring only' and entry['split']==ref['split']
            assert metadata['terminal_input_hashes']==hashes({k:value[k] for k in ('H','z','cancellation','sigma2_terminal','last_check_prior')})
            endpoint_values[arm]=value;endpoint_meta[arm]=entry['sha256']
        pvalue=endpoint_values['W_D_P'];avalue=endpoint_values['W_D_ALL']
        fixed_keys=('z','cancellation','sigma2_terminal','last_check_prior')
        for key in fixed_keys:np.testing.assert_array_equal(pvalue[key],avalue[key])
        np.testing.assert_array_equal(pvalue['H'],state['H'])
        np.testing.assert_array_equal(pvalue['z'],observed['y']-pvalue['cancellation'])
        np.testing.assert_array_equal(pvalue['last_check_prior'],prior)
        assert float(pvalue['sigma2_terminal'])==float(observed['sigma2'])
        legal=dict(H0=pvalue['H'],H1=avalue['H'],**{k:pvalue[k] for k in fixed_keys})
        provenance=dict(reference_record_sha256=ref['sha256'],physical_record_sha256=pe['sha256'],
            observed_hashes=hashes(observed),legal_input_hashes=hashes(legal),truth_access='external scoring only',
            endpoint_P_record_sha256=endpoint_meta['W_D_P'],endpoint_ALL_record_sha256=endpoint_meta['W_D_ALL'],
            source_estimate_record_sha256=source_estimate['sha256'])
        return raw,observed,state,legal,prior,provenance,ref['split']

    def build_factor(legal):
        started=time.perf_counter()
        mask=(torch.as_tensor(legal['H0'],dtype=torch.complex128).abs()>=1e-4).numpy()
        fit=factor_graph(legal['H0'],legal['H1'],mask)
        fit['terminal_fixed']={k:np.array(legal[k],copy=True) if k!='sigma2_terminal' else float(legal[k])
                               for k in ('z','cancellation','sigma2_terminal','last_check_prior')}
        fit['seconds']=time.perf_counter()-started
        return fit

    def check_factor(fit,legal):
        mask=(torch.as_tensor(legal['H0'],dtype=torch.complex128).abs()>=1e-4).numpy()
        expected_factor=factor_graph(legal['H0'],legal['H1'],mask)
        for key in (*ARMS,'mask'):np.testing.assert_array_equal(fit[key],expected_factor[key])
        assert np.isfinite(fit['seconds']) and fit['seconds']>=0
        assert hashes(fit['terminal_fixed'])==hashes({k:legal[k] for k in ('z','cancellation','sigma2_terminal','last_check_prior')})
        active={arm:(torch.as_tensor(fit[arm],dtype=torch.complex128).abs()>=1e-4).numpy() for arm in ARMS}
        assert not np.any(active['G_REWEIGHT']&~mask)
        assert np.all(active['G_ADD'][mask])
        return dict(original_edges=int(mask.sum()),reweight_edges=int(active['G_REWEIGHT'].sum()),
                    add_edges=int(active['G_ADD'].sum()),removed_original_edges=int((mask&~active['G_REWEIGHT']).sum()),
                    added_edges=int((active['G_ADD']&~mask).sum()),CE_solves=0)

    def expected(arm,observed,state,fit,prior):
        assert arm in ARMS
        return dict(H=fit[arm],**fit['terminal_fixed'])

    def check_terminal(value, exp):
        check_value(value, exp, 'RETAIN')
        assert not value['baseline_eligible'] and value['scope'] == c['scope']
        assert len(value['graphs']) == 1
        graph = value['graphs'][0]
        assert graph['H_hash'] == array_hash(np.asarray(exp['H'], dtype=np.complex128))
        assert graph['stage'] == 'final_bp' and graph['threshold'] == 1e-4
        assert graph['dtype'] == 'torch.complex128'
        assert graph['edges'] == value['actual_edges'] == int((torch.as_tensor(exp['H'],dtype=torch.complex128).abs()>=1e-4).sum())

    def audit(summary):
        assert summary['status'] == 'COMPLETE' and summary['calls'] == dict(A=na, T=nt, D=nt)
        records = {(r['kind'],r['block'],r['snr'],r['arm']):r for r in summary['records']}
        wanted = {(k,b,s,a) for k in ('T','D') for b in c['blocks'] for s in c['snrs'] for a in ARMS}
        wanted |= {('A',b,s,'GRAPH_FACTOR') for b in c['blocks'] for s in c['snrs']}
        assert set(records) == wanted and len(records) == len(summary['records'])
        arrays = 0; rows = []; fits = []
        for b in c['blocks']:
            for snr in c['snrs']:
                raw, observed, state, legal, prior, provenance, split = inputs(b, snr)
                ae = records['A',b,snr,'GRAPH_FACTOR']; ar, fit = verified_record(ae, root)
                assert all(ar[k] == v for k,v in provenance.items()) and ae['split'] == split
                fits.append(dict(block=b,snr=snr,checks=check_factor(fit,legal),construction_seconds=fit['seconds']))
                arrays += finite_arrays(fit)
                for arm in ARMS:
                    exp = expected(arm, observed, state, fit, prior)
                    te = records['T',b,snr,arm]; tr, value = verified_record(te,root)
                    assert all(tr[k] == v for k,v in provenance.items())
                    assert tr['construction_record_sha256'] == ae['sha256'] and tr['terminal_input_hashes'] == hashes(exp)
                    check_terminal(value,exp)
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
        return dict(saved_records=len(records),arrays=arrays,CE_solves=0,rows=rows,fits=fits)

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
        cache = run.out/'code-cache'; cache.mkdir(); code = build_code(cache_dir=cache); run.meter.adopt_tree(cache)
        assert hashes({k:code[k] for k in CODE_KEYS}) == env['code_identity']
        run.write('environment.json',dict(code_identity=env['code_identity'],source_sha256=sha(manifest),
            numpy=np.__version__,torch=torch.__version__,device='cpu',threads=1,scope=c['scope']))
        for b in c['blocks']:
            for snr in c['snrs']:
                raw,observed,state,legal,prior,provenance,split = inputs(b,snr)
                fit,_ = run.call('A',dict(block=b,snr=snr,split=split,arm='GRAPH_FACTOR'),
                    lambda:build_factor(legal),lambda v:dict(CE_solves=0),provenance)
                ae = run.records[-1]; check_factor(fit,legal)
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
                    metadata = dict(provenance,construction_record_sha256=ae['sha256'],terminal_input_hashes=hashes(exp))
                    value,_ = run.call('T',identity,terminal,lambda v:decoder_scores(v,raw),metadata)
                    te = run.records[-1]; check_terminal(value,exp)
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
