"""Read-only, hash-bound scoring of completed enriched development calls."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from scipy.stats import binomtest
ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation')
TASK = ROOT / 'issues/20261001-afdm-innovation-exploration'
RUN = TASK / 'experiments/development_v1'
BASE = ROOT / 'experiments/sp_afdm_frozen_reviewed_20260921'
sys.path.insert(0, str(BASE / 'src'))
import evidence

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bound(path, digest, identity=None):
    if sha(path) != digest:
        raise ValueError(f'raw hash differs: {path}')
    payload, actual_identity = evidence.load_artifact(path)
    if identity is not None and actual_identity != identity:
        raise ValueError(f'artifact identity differs: {path}')
    return payload

def same(left, right):
    if isinstance(left, dict):
        return left.keys() == right.keys() and all((same(left[k], right[k]) for k in left))
    if isinstance(left, (tuple, list)):
        return len(left) == len(right) and all((same(a, b) for a, b in zip(left, right)))
    if isinstance(left, np.ndarray):
        return left.dtype == right.dtype and np.array_equal(left, right)
    return left == right

def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]

def main():
    result = json.loads((RUN / 'result.json').read_text())
    manifest = json.loads((RUN / 'manifest.json').read_text())
    if not (result['status'] == 'pass' and result['completed_calls'] == 384):
        raise ValueError("audit failed: result['status'] == 'pass' and result['completed_calls'] == 384")
    for filename, key in [('manifest.json', 'manifest_sha256'), ('ledger.jsonl', 'ledger_sha256'), ('allcalls.jsonl', 'allcalls_sha256')]:
        if not sha(RUN / filename) == result[key]:
            raise ValueError('audit failed: sha(RUN / filename) == result[key]')
    rows = lines(RUN / 'ledger.jsonl')
    attempts = lines(RUN / 'allcalls.jsonl')
    if not (len(rows) == 384 and len(attempts) == 768):
        raise ValueError('audit failed: len(rows) == 384 and len(attempts) == 768')
    if not [[r['observation_id'], r['arm']] for r in rows] == manifest['planned_calls']:
        raise ValueError("audit failed: [[r['observation_id'], r['arm']] for r in rows] == manifest['planned_calls']")
    if not all((r['status'] == 'ok' for r in rows)):
        raise ValueError("audit failed: all((r['status'] == 'ok' for r in rows))")
    keys = [(r['call_index'], r['observation_id'], r['arm']) for r in rows]
    if not len(set(keys)) == len(keys):
        raise ValueError('audit failed: len(set(keys)) == len(keys)')
    for index, row in enumerate(rows):
        start, finish = attempts[2 * index:2 * index + 2]
        if not (start['event'] == 'attempt_started' and finish['event'] == 'attempt_finished'):
            raise ValueError("audit failed: start['event'] == 'attempt_started' and finish['event'] == 'attempt_finished'")
        for key in ('call_index', 'observation_id', 'arm', 'observation_sha256'):
            if not start[key] == finish[key] == row[key]:
                raise ValueError('audit failed: start[key] == finish[key] == row[key]')
        if not {k: v for k, v in finish.items() if k != 'event'} == row:
            raise ValueError("audit failed: {k: v for k, v in finish.items() if k != 'event'} == row")
    population = ROOT / 'results/tf_cstate_prospective_20260923/population_observed'
    if not sha(population / 'ledger.jsonl') == manifest['locked_hashes']['population_ledger_sha256']:
        raise ValueError("audit failed: sha(population / 'ledger.jsonl') == manifest['locked_hashes']['population_ledger_sha256']")
    inputs = {r['observation_id']: r for r in lines(population / 'ledger.jsonl')}
    truthroot = ROOT / 'results/tf_cstate_prospective_20260923/population_truth'
    seal = json.loads((truthroot / 'truth_seal.json').read_text())
    if not (seal['status'] == 'pass' and seal['files']['ledger.jsonl'] == sha(truthroot / 'ledger.jsonl')):
        raise ValueError("audit failed: seal['status'] == 'pass' and seal['files']['ledger.jsonl'] == sha(truthroot / 'ledger.jsonl')")
    truthrows = {r['observation_id']: r for r in lines(truthroot / 'ledger.jsonl')}
    historical = ROOT / 'results/cstate_necessity_stageA_20260928/observed'
    historical_seal = json.loads((historical / 'observed_seal.json').read_text())
    if not historical_seal['files']['ledger.jsonl'] == sha(historical / 'ledger.jsonl'):
        raise ValueError("audit failed: historical_seal['files']['ledger.jsonl'] == sha(historical / 'ledger.jsonl')")
    old = {(r['observation_id'], r['arm']): r for r in lines(historical / 'ledger.jsonl')}
    cache = BASE / 'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    if not sha(cache) == manifest['locked_hashes']['ldpc_cache_sha256']:
        raise ValueError("audit failed: sha(cache) == manifest['locked_hashes']['ldpc_cache_sha256']")
    with np.load(cache) as z:
        H, free = (z['H'], z['free_cols'])
    byframe = {}
    for row in rows:
        stem, arm = (row['observation_id'], row['arm'])
        if not row['observation_sha256'] == inputs[stem]['observation_sha256']:
            raise ValueError("audit failed: row['observation_sha256'] == inputs[stem]['observation_sha256']")
        identity = dict(schema=row['schema'], observation_id=stem, arm=arm, observation_sha256=row['observation_sha256'])
        raw = bound(RUN / row['raw_path'], row['raw_sha256'], identity)
        for cp in row['checkpoints']:
            bound(RUN / cp['path'], cp['artifact_sha256'], dict(identity, round=cp['round']))
        prefix = raw['prefix_arrays']['r1_decoded']
        final = raw['final_decoder']['decoded']
        if not prefix.shape == final.shape == (2048,):
            raise ValueError('audit failed: prefix.shape == final.shape == (2048,)')
        if not np.isin(final, (0, 1)).all():
            raise ValueError('audit failed: np.isin(final, (0, 1)).all()')
        item = byframe.setdefault(stem, {'observation_id': stem, 'input_sha256': row['observation_sha256'], 'arms': {}})
        if '_prefix' in item:
            if not same(item['_prefix'], raw['prefix_arrays']):
                raise ValueError("audit failed: same(item['_prefix'], raw['prefix_arrays'])")
        else:
            item['_prefix'] = raw['prefix_arrays']
        trow = truthrows[stem]
        if not trow['stream_ids'] == inputs[stem]['stream_ids']:
            raise ValueError("audit failed: trow['stream_ids'] == inputs[stem]['stream_ids']")
        if not trow['observation_hash'] == inputs[stem]['observation_hash']:
            raise ValueError("audit failed: trow['observation_hash'] == inputs[stem]['observation_hash']")
        if not seal['files'][trow['truth_path']] == trow['truth_sha256']:
            raise ValueError("audit failed: seal['files'][trow['truth_path']] == trow['truth_sha256']")
        truth = bound(truthroot / trow['truth_path'], trow['truth_sha256'])
        _, truth_identity = evidence.load_artifact(truthroot / trow['truth_path'])
        if not (truth_identity['kind'] == 'truth' and truth_identity['observation_id'] == stem):
            raise ValueError("audit failed: truth_identity['kind'] == 'truth' and truth_identity['observation_id'] == stem")
        if not truth['stream_ids'] == inputs[stem]['stream_ids']:
            raise ValueError("audit failed: truth['stream_ids'] == inputs[stem]['stream_ids']")
        if not truth['observation_hash'] == inputs[stem]['observation_hash']:
            raise ValueError("audit failed: truth['observation_hash'] == inputs[stem]['observation_hash']")
        coded, info = (np.asarray(truth['coded']), np.asarray(truth['info']))
        if not (coded.shape == (2048,) and coded.dtype == np.uint8):
            raise ValueError('audit failed: coded.shape == (2048,) and coded.dtype == np.uint8')
        if not np.array_equal(coded[free], info):
            raise ValueError('audit failed: np.array_equal(coded[free], info)')
        syndrome = int(np.count_nonzero(H @ final % 2))
        if not syndrome == row['final_syndrome_weight']:
            raise ValueError("audit failed: syndrome == row['final_syndrome_weight']")
        if arm == 'scalar':
            digest = hashlib.sha256(final.tobytes()).hexdigest()
            if not digest == old[stem, 'B']['final_decoded_sha256']:
                raise ValueError("audit failed: digest == old[stem, 'B']['final_decoded_sha256']")
            if not row['observation_sha256'] == old[stem, 'B']['input_sha256']:
                raise ValueError("audit failed: row['observation_sha256'] == old[stem, 'B']['input_sha256']")
        branch = raw['branch']
        diagnostics = {}
        if branch is not None:
            common = {k: branch[k] for k in ('app_input', 'check_prior', 'ce_mu', 'ce_variance', 'initial_paths')}
            common['geometry_paths'] = branch['geometry_result']['paths']
            common['geometry_gains'] = branch['geometry_result']['gains']
            if '_branch_common' in item:
                if not same(item['_branch_common'], common):
                    raise ValueError("audit failed: same(item['_branch_common'], common)")
            else:
                item['_branch_common'] = common
            mu, v = (branch['ce_mu'], branch['ce_variance'])
            pseudo = mu.imag ** 2 - mu.real ** 2
            diagnostics = dict(ce_pseudovariance_ratio=float(np.linalg.norm(pseudo) / max(np.linalg.norm(v), 1e-30)), min_working_variance=float(np.min(v)), mean_working_variance=float(np.mean(v)), reaction_gamma_calls=branch['detector']['reaction_gamma_calls'], estimated_duplicate_delays=len(branch['geometry_result']['paths']) - len({p['delay'] for p in branch['geometry_result']['paths']}))
        item['truth_sha256'] = trow['truth_sha256']
        item['arms'][arm] = dict(info_errors=int(np.count_nonzero(final[free] != info)), coded_errors=int(np.count_nonzero(final != coded)), syndrome=syndrome, prefix_coded_errors=int(np.count_nonzero(prefix != coded)), triggered=row['triggered'], raw_sha256=row['raw_sha256'], complete_seconds=row['complete_artifact_seconds'], receiver_seconds=row['receiver_seconds'], **diagnostics)
    ordered = [byframe[s] for s in sorted(byframe)]
    for item in ordered:
        del item['_prefix']
        item.pop('_branch_common', None)
        if not set(item['arms']) == {'scalar', 'coherent', 'full'}:
            raise ValueError("audit failed: set(item['arms']) == {'scalar', 'coherent', 'full'}")
    summary = {}
    for arm in ('scalar', 'coherent', 'full'):
        vals = [f['arms'][arm] for f in ordered]
        summary[arm] = dict(errors=sum((r['info_errors'] > 0 for r in vals)), coded_errors=sum((r['coded_errors'] > 0 for r in vals)), triggers=sum((r['triggered'] for r in vals)), complete_mean_seconds=float(np.mean([r['complete_seconds'] for r in vals])), receiver_mean_seconds=float(np.mean([r['receiver_seconds'] for r in vals])), failure_ids=[f['observation_id'] for f in ordered if f['arms'][arm]['info_errors'] > 0])
    pairs = []
    for left, right in [('scalar', 'coherent'), ('scalar', 'full'), ('coherent', 'full')]:
        rescue = [f['observation_id'] for f in ordered if f['arms'][left]['info_errors'] > 0 and f['arms'][right]['info_errors'] == 0]
        harm = [f['observation_id'] for f in ordered if f['arms'][left]['info_errors'] == 0 and f['arms'][right]['info_errors'] > 0]
        n = len(rescue) + len(harm)
        pairs.append(dict(left=left, right=right, rescue_ids=rescue, harm_ids=harm, paired_exact_p=float(binomtest(len(rescue), n, 0.5).pvalue) if n else 1.0))
    print(json.dumps(dict(status='pass', evaluation_type='simulation_only', receiver_calls_added=0, scope='128 exposed enriched development frames; not population FER or fresh confirmation', checks=dict(raw_count=384, attempt_events=768, attempt_semantics=True, raw_identity_envelopes=True, full_prefix_arrays_equal=True, branch_common_inputs_equal=True, scalar_bits_equal_archived_B=True), summary=summary, pairs=pairs, frames=ordered, manifest_sha256=result['manifest_sha256'], ledger_sha256=result['ledger_sha256'], truth_seal_sha256=sha(truthroot / 'truth_seal.json')), indent=2, allow_nan=False))
if __name__ == '__main__':
    main()
