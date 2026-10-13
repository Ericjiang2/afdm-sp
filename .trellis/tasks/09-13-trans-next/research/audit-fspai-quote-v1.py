"""Read-only replay of four saved factor outputs; no new factor construction."""
import json
from pathlib import Path
import time

import numpy as np
from scipy import sparse
from afdm_sp_joint_unrolled.bottleneck_pilot import sha, load_state


def audit(root):
    started = time.time()
    path = root/'runs/fspai-quote-v2/quote/summary.json'
    assert sha(path) == '33e16f5a7f8ca65f5e6af88f88cb78ee1fe6d6a118477ad2b561b78f659b0b2f'
    summary = json.loads(path.read_text())
    source_path = root/'runs/siso-chain-v2/engineering/summary.json'
    assert sha(source_path) == '6ce76c156425f395f694243e309e1d3463860894bc717ab1aae8b9031006f295'
    source = json.loads(source_path.read_text())
    index = {(r['block'], r['snr'], r['arm']): r for r in source['records']}
    rows = []
    for entry in [summary['recovered'], *summary['records']]:
        record_path = Path(entry['record'])
        assert record_path.resolve().is_relative_to(root.resolve())
        assert sha(record_path) == entry['sha256']
        record = json.loads(record_path.read_text())
        source_entry = index[record['block'], record['snr'], 'SISO_REF47']
        assert record['source_record_sha256'] == source_entry['sha256']
        assert record['input_summary_sha256'] == sha(source_path)
        assert sha(Path(source_entry['record'])) == source_entry['sha256']
        if 'split' not in record:
            assert entry is summary['recovered']
            assert entry['split_from_bound_source'] == source_entry['split'] == 1
        else:
            assert record['split'] == source_entry['split'] == 1
        cached = load_state(json.loads(Path(source_entry['record']).read_text())['state'])
        state = cached['siso_states'][record['outer_iter']]
        saved = load_state(record['state'])
        L = sparse.csc_matrix((saved['L_data'], saved['L_indices'], saved['L_indptr']),
                              shape=saved['factor_shape']).toarray()
        H = state['H'].astype(np.complex128)
        assert np.isfinite(L).all() and not np.any(np.triu(L, 1))
        assert np.count_nonzero(L) == saved['factor_nnz']
        transformed = L.conj().T @ H
        xi = np.sum(np.abs(transformed)**2, axis=0)
        denominator = 1-state['prior_variance']*xi
        assert np.all(denominator > 0) and saved['candidate_valid']
        residual = state['y']-H@state['prior_mean']
        solution = L@(L.conj().T@residual)
        C = (H*state['prior_variance'][None, :])@H.conj().T + state['sigma2']*np.eye(H.shape[0])
        eta = (H.conj().T@solution+xi*state['prior_mean'])/denominator
        channel = 2*np.concatenate((eta.real, eta.imag))
        for actual, expected in ((xi, saved['approximate_xi']), (denominator, saved['denominator']),
                                 (channel, saved['channel_llr'])):
            np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)
        values = {
            'channel_relative_error': float(np.linalg.norm(channel-state['channel_llr'])/np.linalg.norm(state['channel_llr'])),
            'xi_relative_error': float(np.linalg.norm(xi-state['leverage'])/np.linalg.norm(state['leverage'])),
            'residual_relative_error': float(np.linalg.norm(C@solution-residual)/np.linalg.norm(residual)),
        }
        metric = next(m for m in summary['metrics'] if (m['snr'], m['outer_iter']) ==
                      (record['snr'], record['outer_iter']))
        for key, value in values.items():
            np.testing.assert_allclose(value, saved[key], rtol=1e-10, atol=1e-10)
            np.testing.assert_allclose(value, metric[key], rtol=1e-10, atol=1e-10)
        rows.append(dict(block=record['block'], snr=record['snr'], outer_iter=record['outer_iter'],
                         record_sha256=entry['sha256'], **values))
    assert {(r['snr'], r['outer_iter']) for r in rows} == {(s, o) for s in (7, 8) for o in (0, 2)}
    return dict(status='PASS', records=4, rows=rows, summary_sha256=sha(path),
                source_summary_sha256=sha(source_path), wall_seconds=time.time()-started,
                scope='saved CSC factor, dense likelihood reconstruction and metric replay; no new F/T/A/LDPC, no FER claim')


if __name__ == '__main__':
    import sys
    print(json.dumps(audit(Path(sys.argv[1])), indent=2, allow_nan=False))
