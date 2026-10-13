"""Classical legal response qualification on frozen G1 terminal inputs."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np

ARMS = ['S_P', 'S_ALL', 'D_P_HALF', 'D_P', 'D_ALL', 'SCALE_P']


def fit_legal(y, pilot, mu, variance, Hc, support, c1, c2, regularization,
              *, l_max=102, k_max=2):
    """Only observed inputs. Two classical frozen posterior-proximal solves."""
    import torch
    from afdm_sp_joint_unrolled.classical_joint_unrolled import (
        build_A_for_DALS_torch, data_uncertainty_gram, soft_gain_update,
        reconstruct_H_torch)
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support
    n = len(y); width = 2*k_max+1
    arrays = (y, pilot, mu, variance, Hc, support)
    if (any(not np.isfinite(a).all() for a in arrays)
            or any(np.shape(a) != (n,) for a in (y, pilot, mu, variance))
            or np.shape(Hc) != (n, n) or np.iscomplexobj(variance)
            or np.any(variance < 0) or not np.isfinite(regularization)
            or regularization < 0 or not np.isfinite([c1, c2]).all()
            or np.asarray(support).dtype.kind not in 'iu'
            or np.asarray(support).ndim != 1 or not len(support)
            or len(set(support.tolist())) != len(support)
            or np.any(support < 0) or np.any(support >= (l_max+1)*width)
            or (l_max+1)*width > n or 2*n*c1 != width):
        raise ValueError('invalid frozen legal inputs or collision-free domain')
    yt = torch.as_tensor(y, dtype=torch.complex128)
    pt = torch.as_tensor(pilot, dtype=torch.complex128)
    mt = torch.as_tensor(mu, dtype=torch.complex128)
    vt = torch.as_tensor(variance, dtype=torch.float64)
    hc = torch.as_tensor(Hc, dtype=torch.complex128)
    reg = torch.tensor(regularization, dtype=torch.float64)
    fitted = {}
    for name, ids in [('S', support), ('D', np.arange((l_max+1)*width))]:
        started = time.perf_counter()
        delays = torch.tensor(ids//width, dtype=torch.long)
        dopplers = torch.tensor(ids%width-k_max, dtype=torch.long)
        projection, previous = project_channel_on_support(hc, delays, dopplers, c1, c2, k_max)
        projection_error = float(torch.linalg.norm(projection-hc)/torch.linalg.norm(hc))
        if not np.isfinite(projection_error) or projection_error > 1e-6:
            raise ValueError('Hc is not in the specified legal support')
        A = build_A_for_DALS_torch(n, delays, dopplers, pt+mt, c1, c2, k_max)
        Q = data_uncertainty_gram(n, delays, dopplers, vt, c1, c2, k_max)
        torch.testing.assert_close(Q, vt.sum()*torch.eye(len(ids), dtype=torch.complex128), rtol=0, atol=0)
        gain = soft_gain_update(A, yt, previous, reg, Q=Q)
        H = reconstruct_H_torch(n, delays, dopplers, gain, c1, c2, k_max)
        fitted[name] = dict(ids=np.asarray(ids), A=A.numpy(), Q=Q.numpy(),
            previous=previous.numpy(), gains=gain.numpy(), H=H.numpy(),
            regularization=float(regularization), projection_error=projection_error,
            seconds=time.perf_counter()-started, CE_solves=1)
        validate_fit(fitted[name], y)
        np.testing.assert_allclose(H.numpy()@(pilot+mu), A.numpy()@gain.numpy(), atol=2e-10, rtol=2e-10)
    a = Hc@pilot; denominator = float(np.vdot(a, a).real)
    if denominator <= 0:
        raise ValueError('zero pilot response for scalar comparator')
    fitted['scalar_beta'] = np.asarray(np.vdot(a, y-Hc@mu)/denominator)
    return fitted


def validate_fit(value, y):
    A, Q, previous, gain = [value[k] for k in ('A', 'Q', 'previous', 'gains')]
    reg = value['regularization']
    if any(not np.isfinite(v).all() for v in (A, Q, previous, gain, value['H'])):
        raise ValueError('nonfinite legal estimate')
    matrix = A.conj().T@A + Q + reg*np.eye(len(gain))
    rhs = A.conj().T@y + reg*previous
    denominator = np.linalg.norm(matrix)*np.linalg.norm(gain)+np.linalg.norm(rhs)
    residual = float(np.linalg.norm(matrix@gain-rhs)/denominator) if denominator else 0.
    if residual > 1e-10:
        raise ValueError('legal fit normal equation does not close')
    def objective(g):
        error = y-A@g
        return float(np.vdot(error, error).real + np.vdot(g, Q@g).real
                     + reg*np.vdot(g-previous, g-previous).real)
    before, after = objective(previous), objective(gain)
    if after > before+1e-9*max(1., before):
        raise ValueError('frozen proximal objective increased')
    return dict(normal_residual=residual, objective_before=before, objective_after=after)


def terminal_inputs(arm, y, pilot, Hc, fitted, sigma2, prior):
    H = fitted[arm[0]]['H'] if arm in ('S_ALL', 'D_ALL') else Hc
    base = Hc@pilot
    if arm in ('S_P', 'S_ALL'):
        cancellation = fitted['S']['H']@pilot
    elif arm in ('D_P', 'D_ALL'):
        cancellation = fitted['D']['H']@pilot
    elif arm == 'D_P_HALF':
        cancellation = base+.5*(fitted['D']['H']@pilot-base)
    elif arm == 'SCALE_P':
        cancellation = fitted['scalar_beta']*base
    else:
        raise ValueError('unknown legal response arm')
    return dict(H=H, z=y-cancellation, cancellation=cancellation,
                sigma2_terminal=float(sigma2), last_check_prior=prior)


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
    assert c['schema'] == 'e1a-legal-response-v1' and c['tag'] == args.tag
    assert c['stage'] in ('engineering', 'development')
    engineering = c['stage'] == 'engineering'
    assert c['blocks'] == ([0, 20] if engineering else [b for b in range(32) if b not in (0, 20)])
    assert c['snrs'] == [7, 8] and c['arms'] == ARMS
    assert c['device'] == 'cpu' and c['threads'] == 1
    na = len(c['blocks'])*2; nt = na*len(ARMS)
    assert c['bounds'] == dict(A=na, T=nt, D=nt, seconds=900 if engineering else 3600)
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for sp, ap in c['audited_inputs'].items():
        a = json.loads((root/ap).read_text())
        assert a['status'] == 'PASS' and a['summary_sha256'] == sha(root/sp)
    if not engineering:
        admission = json.loads((root/c['engineering_audit']).read_text())
        assert admission['script_sha256'] == args.script_sha256 and admission['saved_records'] == 52
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
        legal = dict(y=observed['y'], pilot=observed['pilot'], mu=d['mu'], variance=d['finite_variance'],
            Hc=state['H'], support=ids, c1=raw['params']['c1'], c2=raw['params']['c2'],
            regularization=float(d['regularization']))
        assert len(legal['y']) == 1024 and 2*1024*legal['c1'] == 5
        checkpoints = [v for v in state['code_feedback_records'] if v['stage'] == 'decoder']
        assert [v['iteration'] for v in checkpoints] == [1, 4, 7]
        prior = checkpoints[-1]['prior_after']
        np.testing.assert_array_equal(prior, np.clip(checkpoints[-1]['raw_check_extrinsic'], -20., 20.))
        provenance = dict(reference_record_sha256=ref['sha256'], physical_record_sha256=pe['sha256'],
            observed_hashes=hashes(observed), legal_input_hashes=hashes(legal), truth_access='external scoring only')
        return raw, observed, state, legal, prior, provenance, ref['split']

    def check_fit(fit, legal):
        checks = {}
        for name in ('S', 'D'):
            v = fit[name]; ids = v['ids']
            np.testing.assert_array_equal(ids, legal['support'] if name == 'S' else np.arange(515))
            dt = torch.tensor(ids//5); kt = torch.tensor(ids%5-2)
            A = build_A_for_DALS_torch(1024, dt, kt,
                torch.tensor(legal['pilot'], dtype=torch.complex128)+torch.tensor(legal['mu'], dtype=torch.complex128),
                legal['c1'], legal['c2'], 2).numpy()
            np.testing.assert_array_equal(A, v['A'])
            np.testing.assert_allclose(v['Q'], np.sum(legal['variance'])*np.eye(len(ids)), atol=1e-10, rtol=1e-12)
            H = reconstruct_H_torch(1024, dt, kt, torch.tensor(v['gains']), legal['c1'], legal['c2'], 2).numpy()
            np.testing.assert_array_equal(H, v['H'])
            previous_H = reconstruct_H_torch(1024, dt, kt, torch.tensor(v['previous']), legal['c1'], legal['c2'], 2).numpy()
            assert np.linalg.norm(previous_H-legal['Hc'])/np.linalg.norm(legal['Hc']) <= 1e-6
            assert v['CE_solves'] == 1 and v['regularization'] == legal['regularization']
            checks[name] = validate_fit(v, legal['y'])
        a = legal['Hc']@legal['pilot']
        np.testing.assert_array_equal(fit['scalar_beta'], np.asarray(np.vdot(a, legal['y']-legal['Hc']@legal['mu'])/np.vdot(a,a).real))
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
        assert graph['edges'] == value['actual_edges'] == int(np.count_nonzero(abs(exp['H']) >= 1e-4))

    def audit(summary):
        assert summary['status'] == 'COMPLETE' and summary['calls'] == dict(A=na, T=nt, D=nt)
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
                    S_seconds=fit['S']['seconds'],D_seconds=fit['D']['seconds']))
                arrays += finite_arrays(fit)
                for arm in ARMS:
                    exp = expected(arm, observed, state, fit, prior)
                    te = records['T',b,snr,arm]; tr, value = verified_record(te,root)
                    assert all(tr[k] == v for k,v in provenance.items())
                    assert tr['estimate_record_sha256'] == ae['sha256'] and tr['terminal_input_hashes'] == hashes(exp)
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
        return dict(saved_records=len(records),arrays=arrays,CE_solves=2*na,rows=rows,fits=fits)

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
