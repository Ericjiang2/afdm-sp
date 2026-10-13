"""Standard-library audit of sealed sweep states; never runs a receiver."""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def npy(raw):
    require(raw[:6] == b'\x93NUMPY', 'not NPY')
    version = tuple(raw[6:8])
    require(version in ((1, 0), (2, 0), (3, 0)), 'unsupported NPY version')
    offset = 10 if version == (1, 0) else 12
    length = int.from_bytes(raw[8:offset], 'little')
    header = ast.literal_eval(raw[offset:offset+length].decode())
    payload = raw[offset+length:]
    shape, dtype = header['shape'], header['descr']
    size = math.prod(shape)
    formats = {'|u1': ('B', 1), '<i8': ('q', 8), '<f8': ('d', 8), '<c16': ('dd', 16)}
    require(dtype in formats, 'unsupported dtype '+str(dtype))
    fmt, width = formats[dtype]
    require(len(payload) == size*width, 'NPY size mismatch')
    values = [complex(*x) if dtype == '<c16' else x[0]
              for x in struct.iter_unpack('<'+fmt, payload)]
    if header['fortran_order'] and len(shape) > 1:
        require(len(shape) == 2, 'unsupported F-order rank')
        rows, cols = shape
        values = [values[r+rows*c] for r in range(rows) for c in range(cols)]
    return shape, values


class Evidence:
    def __init__(self, path):
        self.archive = zipfile.ZipFile(path)
        names = self.archive.namelist()
        require(len(names) == len(set(names)), 'duplicate NPZ members')
        _, raw = npy(self.archive.read('__evidence_metadata__.npy'))
        self.metadata = json.loads(bytes(raw))

    def array(self, ref, shape):
        actual, values = npy(self.archive.read(ref['__evidence_array__']+'.npy'))
        require(actual == shape, 'array shape mismatch')
        require(all(math.isfinite(abs(x)) for x in values), 'nonfinite array')
        return values

    def close(self):
        self.archive.close()


def gain_kl(mean, covariance):
    p = len(mean)
    matrix = [covariance[i*p:(i+1)*p] for i in range(p)]
    scale = max(1., max(abs(x) for x in covariance))
    require(max(abs(matrix[i][j]-matrix[j][i].conjugate())
                for i in range(p) for j in range(p)) <= 1e-10*scale, 'non-Hermitian C')
    lower = [[0j]*p for _ in range(p)]
    for i in range(p):
        for j in range(i+1):
            value = matrix[i][j]-sum(lower[i][k]*lower[j][k].conjugate() for k in range(j))
            if i == j:
                require(abs(value.imag) <= 1e-10*scale and value.real > 0, 'C not positive definite')
                lower[i][j] = complex(math.sqrt(value.real))
            else:
                lower[i][j] = value/lower[j][j]
    residual = max(abs(matrix[i][j]-sum(lower[i][k]*lower[j][k].conjugate()
                   for k in range(p))) for i in range(p) for j in range(p))/scale
    require(residual <= 1e-10, 'C factor reconstruction failed')
    logdet = 2*sum(math.log(lower[i][i].real) for i in range(p))
    value = p*sum(matrix[i][i].real for i in range(p))+p*sum(abs(x)**2 for x in mean)
    value -= p+p*math.log(p)+logdet
    require(value >= -1e-10 and math.isfinite(value), 'invalid gain KL')
    return value, logdet, residual


def logadd(x, y):
    return max(x, y)+math.log1p(math.exp(-abs(x-y)))


def risks(logq, truth, n):
    llr_i, llr_q, entropy, loss = [], [], 0., 0.
    for i in range(n):
        q = logq[4*i:4*i+4]
        require(abs(logadd(logadd(q[0], q[1]), logadd(q[2], q[3]))) <= 1e-10,
                'log q is not normalized')
        llr_i.append(logadd(q[0], q[1])-logadd(q[2], q[3]))
        llr_q.append(logadd(q[0], q[2])-logadd(q[1], q[3]))
        loss -= q[2*truth[i]+truth[n+i]]
        entropy -= sum(math.exp(x)*x for x in q)
    llr = llr_i+llr_q
    hard = [int(x < 0) for x in llr]
    return dict(bit_errors=sum(a != b for a, b in zip(hard, truth)),
                bit_denominator=2*n, symbol_log_loss=loss/n,
                entropy_per_symbol=entropy/n), hard, llr


def analyze(stage, contract):
    for name, digest in contract['inputs'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'invalid input path')
        require(sha(stage/name) == digest, 'input identity mismatch: '+name)
    seal = json.loads((stage/'receiver_seal.json').read_text())
    scores = json.loads((stage/'scores.json').read_text())
    require(seal['receiver_calls'] == 32 and seal['truth_payloads_opened_for_scoring'] == 0,
            'invalid receiver seal')
    require(sha(stage/'receiver_seal.json') == scores['receiver_seal_sha256'], 'score seal mismatch')
    scoremap = {(x['block'], x['snr_db'], x['arm']): x for x in scores['scores']}
    arms = {'vb_point': 20, 'vb_local_point': 5, 'vb_collapsed_point': 5}
    required = {'receiver_seal.json', 'scores.json'} | {f'truth/block_{b}.npz' for b in range(4)}
    required |= {r['raw'] for r in seal['records'] if r['arm'] in arms}
    require(set(contract['inputs']) == required and len(required) == 30, 'input whitelist mismatch')
    records, seen = [], set()
    for record in seal['records']:
        arm = record['arm']
        if arm not in arms:
            continue
        key = record['block'], record['snr_db'], arm
        require(key not in seen and record['status'] == 'complete', 'duplicate/incomplete call')
        seen.add(key)
        require(sha(stage/record['raw']) == record['raw_sha256'], 'receiver raw mismatch')
        source = Evidence(stage/record['raw'])
        truth_source = Evidence(stage/f'truth/block_{record["block"]}.npz')
        try:
            identity = source.metadata['identity']
            require(all(identity[k] == record[k] for k in ('arm', 'block', 'snr_db')), 'call identity')
            payload = source.metadata['payload']['payload']
            backend = payload['backend']
            n, p = 1024, 8
            truth = truth_source.array(truth_source.metadata['payload']['coded'], (2*n,))
            require(all(x in (0, 1) for x in truth), 'invalid truth bits')
            require(len(backend['trace']) == arms[arm] and backend['sweeps'] == arms[arm], 'sweep count')
            previous, cumulative = None, 0.
            for i, event in enumerate(backend['trace']):
                require(event['sweep'] == i and len(event['data']) == 3, 'sweep schedule')
                q = source.array(event['log_q'], (n, 4))
                risk, hard, llr = risks(q, truth, n)
                gain = (event['doppler'][-1]['winner'] if arm == 'vb_collapsed_point'
                        else event['gain_after_doppler'])
                mean = source.array(gain['mean'], (p,))
                covariance = source.array(gain['covariance'], (p, p))
                kl, logdet, residual = gain_kl(mean, covariance)
                data_objective = event['data'][-1]['new_objective']
                cumulative += event['seconds']
                row = dict(block=key[0], snr_db=key[1], arm=arm, sweep=i+1, **risk,
                           data_objective=data_objective, gain_kl=kl,
                           reduced_conditional_objective=data_objective-kl, gain_logdet=logdet,
                           covariance_factor_residual=residual,
                           cumulative_recorded_sweep_seconds=cumulative)
                if previous is not None:
                    row.update(hard_changes=sum(a != b for a, b in zip(previous, hard)),
                               wrong_to_correct=sum(a != t and b == t for a, b, t in zip(previous, hard, truth)),
                               correct_to_wrong=sum(a == t and b != t for a, b, t in zip(previous, hard, truth)))
                records.append(row)
                previous = hard
            final_llr = source.array(payload['bit_llr'], (2*n,))
            final_hard = source.array(payload['hard_bits'], (2*n,))
            require(q == source.array(backend['log_q'], (n, 4)), 'final log q mismatch')
            require(mean == source.array(backend['gain_mean'], (p,)), 'final gain mean mismatch')
            require(covariance == source.array(backend['gain_covariance'], (p, p)), 'final gain C mismatch')
            require(hard == final_hard, 'final hard mismatch')
            maxdiff = max(abs(a-b) for a, b in zip(llr, final_llr))
            require(maxdiff <= 1e-10, 'final LLR mismatch')
            require(records[-1]['bit_errors'] == scoremap[key]['bit_errors'], 'final score mismatch')
            records[-1]['final_llr_max_abs_difference'] = maxdiff
        finally:
            source.close()
            truth_source.close()
    expected = {(b, s, arm) for b in range(4) for s in (6, 8) for arm in arms}
    require(seen == expected and len(records) == 240, 'incomplete trajectory coverage')
    groups = []
    for arm, sweeps in arms.items():
        for sweep in range(1, sweeps+1):
            for snr in (None, 6, 8):
                subset = [r for r in records if r['arm'] == arm and r['sweep'] == sweep
                          and (snr is None or r['snr_db'] == snr)]
                groups.append(dict(arm=arm, sweep=sweep, snr_db=snr, observations=len(subset),
                                   bit_errors=sum(r['bit_errors'] for r in subset),
                                   symbol_log_loss=sum(r['symbol_log_loss'] for r in subset)/len(subset),
                                   entropy_per_symbol=sum(r['entropy_per_symbol'] for r in subset)/len(subset),
                                   reduced_conditional_objective_sum=sum(r['reduced_conditional_objective']
                                                                         for r in subset)))
    return dict(scope='post-hoc sealed trajectory audit; no new observations, receiver or stopping policy',
                records=records, aggregates=groups, saved_states=240, source_observations=8,
                source_independent_blocks=4, new_observations=0, receiver_calls=0,
                time_scope='recorded sweep sums only; not complete receiver latency')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    require(args.stage.resolve() == Path(contract['local_stage']).resolve(), 'stage identity mismatch')
    require(sha(Path(__file__)) == contract['script_sha256'], 'audit script identity mismatch')
    with args.output.open('x') as output:
        result = analyze(args.stage, contract)
        result['contract_sha256'] = sha(args.contract)
        json.dump(result, output, indent=2, allow_nan=False)
        output.write('\n')
    print('Audited all 240 saved states; no receiver executed.')


if __name__ == '__main__':
    main()
