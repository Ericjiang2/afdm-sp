"""Finite factor/likelihood qualification on cached observed SISO states."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from scipy import sparse
from .supplement_fspai import factorized_sparse_precision
from .bottleneck_pilot import sha, load_state
from .light_gap_replay import LightRun, setup_guard, verified_record


def quote_state(state, controls):
    H = state['H'].astype(np.complex128)
    started = time.perf_counter()
    factor = factorized_sparse_precision(H, state['prior_variance'], state['sigma2'], **controls)
    factor_seconds = time.perf_counter()-started
    C, L = factor.pop('covariance'), factor.pop('factor')
    transformed = L.conj().T@sparse.csc_matrix(H)
    xi = np.asarray(transformed.conj().multiply(transformed).sum(axis=0)).ravel().real
    residual = state['y']-H@state['prior_mean']
    solution = L@(L.conj().T@residual)
    denominator = 1-state['prior_variance']*xi
    valid = bool(np.isfinite(denominator).all() and np.all(denominator > 0))
    channel, relative_error = None, None
    if valid:
        eta = (H.conj().T@solution+xi*state['prior_mean'])/denominator
        channel = 2*np.concatenate((eta.real, eta.imag))
        if not np.isfinite(channel).all():
            raise FloatingPointError('FSPAI finite denominator produced nonfinite likelihood')
        relative_error = float(np.linalg.norm(channel-state['channel_llr'])/
                               max(np.linalg.norm(state['channel_llr']), np.finfo(float).tiny))
    exact_xi = state['leverage']
    return dict(factor, L_data=L.data.copy(), L_indices=L.indices.copy(), L_indptr=L.indptr.copy(),
        factor_shape=list(L.shape), factor_seconds=factor_seconds, total_quote_seconds=time.perf_counter()-started,
        approximate_xi=xi, denominator=denominator, channel_llr=channel,
        candidate_valid=valid, invalid_denominators=int(np.count_nonzero(denominator <= 0)),
        min_denominator=float(np.min(denominator)), channel_relative_error=relative_error,
        xi_relative_error=float(np.linalg.norm(xi-exact_xi)/max(np.linalg.norm(exact_xi), np.finfo(float).tiny)),
        residual_relative_error=float(np.linalg.norm(C@solution-residual)/max(np.linalg.norm(residual), np.finfo(float).tiny)),
        zero_prior_shared_xi_relative_range=(float(np.ptp(exact_xi)/max(np.mean(exact_xi), np.finfo(float).tiny))
            if np.all(state['consumed_prior'] == 0) else None),
        baseline_eligible=False, scope='cached factor diagnostic only; never silently replace invalid denominators')


def quote_metrics(identity, value, seconds):
    return dict(identity, seconds=seconds, **{k: value[k] for k in ('small_solves', 'factor_nnz', 'covariance_nnz', 'graph_edges_before_prune',
         'graph_edges_after_prune', 'candidate_valid', 'invalid_denominators', 'min_denominator',
         'channel_relative_error', 'xi_relative_error', 'residual_relative_error',
         'zero_prior_shared_xi_relative_range')})


def execute(args):
    c = json.loads(args.contract.read_text())
    if (sha(args.contract) != args.contract_sha256 or sha(args.source_manifest) != args.source_sha256
            or c['schema'] != 'trans-fspai-quote-v1' or c['device'] != 'cpu' or c['threads'] != 1
            or c['blocks'] != [0] or c['snrs'] != [7, 8] or c['outer_iterations'] != [0, 2]
            or c['A_limit'] != (3 if 'recover_record' in c else 4) or c['arm'] != 'SISO_REF47' or args.root.name != c['tag']
            or sha(c['input_summary']) != c['input_summary_sha256']):
        raise ValueError('unregistered covariance quote')
    guard = setup_guard(args, c)
    run = LightRun(args.root, 'quote', dict(A=c['A_limit'], seconds=c['seconds']), c['output_bytes'], guard)
    try:
        source = json.loads(Path(c['input_summary']).read_text())
        if source['status'] != 'COMPLETE':
            raise ValueError('incomplete engineering source')
        index = {(r['block'], r['snr'], r['arm']): r for r in source['records']}
        metrics, recovered = [], None
        if 'recover_record' in c:
            path = Path(c['recover_record'])
            if not path.resolve().is_relative_to(Path(c['reference_root']).resolve()) or sha(path) != c['recover_record_sha256']:
                raise ValueError('recovery record identity differs')
            previous = json.loads(path.read_text())
            entry = index[0, 7, c['arm']]
            if (previous['block'], previous['snr'], previous['outer_iter'], previous['arm']) != (0, 7, 0, 'FSPAI8'):
                raise ValueError('recovery is not the single saved first quote')
            if (previous['source_record_sha256'] != entry['sha256'] or previous['configuration'] != c['fspai']
                    or previous['input_summary_sha256'] != c['input_summary_sha256'] or 'split' in previous):
                raise ValueError('recovery provenance or missing-field failure differs')
            # The old artifact stays unchanged. Its source-record hash supplies
            # the absent split identity; validate every saved array through the
            # normal loader, then disclose recovery separately from new calls.
            saved = load_state(previous['state'])
            row = quote_metrics(dict(block=0, snr=7, outer_iter=0, arm='FSPAI8'), saved, previous['seconds'])
            recovered = dict(record=str(path), sha256=sha(path), split_from_bound_source=entry['split'],
                original_missing_field='split', no_new_factorization=True, metric=row)
            run.write('recovered-first-quote.json', recovered)
            metrics.append(row)
        for snr in c['snrs']:
            entry = index[0, snr, c['arm']]
            _, cached = verified_record(entry, Path(c['reference_root']))
            for outer in c['outer_iterations']:
                if recovered is not None and snr == 7 and outer == 0:
                    continue
                state = cached['siso_states'][outer]
                identity = dict(block=0, snr=snr, split=entry['split'], outer_iter=outer, arm='FSPAI8')
                value, record = run.call('A', identity, lambda: quote_state(state, c['fspai']),
                    lambda v: {}, dict(source_record_sha256=entry['sha256'], configuration=c['fspai'],
                        input_summary_sha256=c['input_summary_sha256'], scope=c['scope']))
                _, saved = verified_record(run.records[-1], args.root)
                for field in ('approximate_xi', 'denominator', 'L_data', 'L_indices', 'L_indptr'):
                    np.testing.assert_array_equal(saved[field], value[field])
                row = quote_metrics(identity, saved, record['seconds'])
                metrics.append(row)
                print(json.dumps(row), flush=True)
        guard.verify()
        if sha(c['input_summary']) != c['input_summary_sha256']:
            raise ValueError('quote input changed')
        run.write('summary.json', dict(status='COMPLETE', records=run.records, metrics=metrics, calls=run.counts, recovered=recovered,
            scope=c['scope'], contract_sha256=args.contract_sha256, source_sha256=args.source_sha256,
            wall_seconds=time.time()-run.started))
        run.meter.verify()
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'contract', 'source-manifest'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('contract-sha256', 'source-sha256'):
        parser.add_argument('--'+name, required=True)
    execute(parser.parse_args())
