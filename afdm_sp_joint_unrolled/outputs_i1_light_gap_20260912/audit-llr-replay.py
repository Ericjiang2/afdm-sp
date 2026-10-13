"""Read every saved replay array and independently recount bit/frame errors."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--stage', choices=('engineering', 'development'), required=True)
parser.add_argument('--admit', action='store_true')
args = parser.parse_args()
root = args.root.resolve()
sys.path.insert(0, str(root / 'source-llr-v1'))
from afdm_sp_joint_unrolled.bottleneck_pilot import load_state, sha, hashes

started = time.time()
contract_path = root / 'contracts/llr-replay-v1.json'
contract = json.loads(contract_path.read_text())
summary_path = root / 'runs/llr-v1' / args.stage / 'summary.json'
summary = json.loads(summary_path.read_text())
blocks = contract[args.stage + '_blocks']
if summary['status'] != 'COMPLETE' or summary['calls'] != {'D': blocks*60, 'F': 0, 'T': 0}:
    raise ValueError('replay incomplete or call inventory differs')
if summary['contract_sha256'] != sha(contract_path):
    raise ValueError('contract identity differs')
old_root = Path(contract['old_root'])
old_summary = json.loads((old_root / 'runs' / args.stage / 'summary.json').read_text())
old_index = {(r['block'], r['snr'], r['arm']): r for r in old_summary['records']}
exo = {r['block']: r for r in summary['exogenous']}
cache = next((summary_path.parent / 'code-cache').glob('e1_ldpc_code_*.npz'))
with np.load(cache, allow_pickle=False) as z:
    parity, free = z['H'], z['free_cols']
check_ids, bit_ids = np.nonzero(parity)
expected = {(b,s,a,beta) for b in range(blocks) for s in contract['snrs']
            for a in contract['arms'] for beta in contract['betas']}
seen, rows, inputs = set(), [], {}
truths = {b: load_state(v['state']) for b,v in exo.items()}
arrays = 0
for item in summary['records']:
    key = item['block'], item['snr'], item['arm'], item['beta']
    if key in seen or key not in expected:
        raise ValueError('duplicate or unexpected replay')
    seen.add(key)
    path = Path(item['record'])
    if sha(path) != item['sha256']:
        raise ValueError('replay record changed')
    record = json.loads(path.read_text())
    reserve = json.loads((path.parent / (record['token']+'-reserve.json')).read_text())
    for field in ('block','snr','arm','beta','kind','token'):
        if reserve[field] != record[field]:
            raise ValueError('reservation and result differ')
    value = load_state(record['state'])
    arrays += len(record['state']['file']['fields'])
    source_key = key[:3]
    if source_key not in inputs:
        source = old_index[source_key]
        if sha(source['record']) != source['sha256']:
            raise ValueError('old source record changed')
        inputs[source_key] = load_state(json.loads(Path(source['record']).read_text())['state'])
    old = inputs[source_key]
    target_llr = np.minimum(20., np.maximum(-20., key[3]*old['llr']))
    if not np.array_equal(value['llr'], target_llr):
        raise ValueError('saved LLR differs from declared transformation')
    if key[3] == 1:
        if any(not np.array_equal(value[k], old[k]) for k in ('decoded','info_hat','decode_ok')):
            raise ValueError('beta-one identity failed during raw audit')
    if not np.array_equal(value['info_hat'], value['decoded'][free]):
        raise ValueError('decoded information extraction differs')
    syndrome = np.bincount(check_ids, weights=value['decoded'][bit_ids], minlength=parity.shape[0]) % 2
    if bool(value['decode_ok']) != (not syndrome.any()):
        raise ValueError('recorded validity differs from actual parity checks')
    truth = truths[key[0]]
    if record['exogenous_hashes'] != exo[key[0]]['hashes']:
        raise ValueError('paired source identity differs')
    errors = int((value['info_hat'] != truth['info']).sum())
    coded_errors = int((value['decoded'] != truth['coded']).sum())
    raw_errors = int(((value['llr'] < 0) != truth['coded']).sum())
    score = record['scores']
    if (score['FER'] != int(errors>0) or score['info_bit_errors'] != errors
            or score['decoded_codeword_bit_errors'] != coded_errors or score['raw_bit_errors'] != raw_errors
            or item['scores'] != score):
        raise ValueError('stored errors differ from raw bit recount')
    rows.append(dict(block=key[0],snr=key[1],arm=key[2],beta=key[3],FER=int(errors>0),
                     info_bit_errors=errors,raw_bit_errors=raw_errors,decode_ok=bool(value['decode_ok']),
                     NLL=score['bit_NLL'],Brier=score['bit_Brier']))
if seen != expected:
    raise ValueError('missing replay observations')
files = list(summary_path.parent.glob('D-*-result.json'))
reservations = list(summary_path.parent.glob('D-*-reserve.json'))
if len(files) != len(expected) or len(reservations) != len(expected):
    raise ValueError('unmatched call records or reservations')
tables=[]
for snr in contract['snrs']:
    for arm in contract['arms']:
        baseline={r['block']:r for r in rows if (r['snr'],r['arm'],r['beta'])==(snr,arm,1.)}
        for beta in contract['betas']:
            group=[r for r in rows if (r['snr'],r['arm'],r['beta'])==(snr,arm,beta)]
            tables.append(dict(snr=snr,arm=arm,beta=beta,blocks=len(group),
                errors=sum(r['FER'] for r in group),info_errors=sum(r['info_bit_errors'] for r in group),
                rescued=sum(baseline[r['block']]['FER'] and not r['FER'] for r in group),
                broken=sum(not baseline[r['block']]['FER'] and r['FER'] for r in group),
                mean_NLL=float(np.mean([r['NLL'] for r in group]))))
result=dict(status='PASS',stage=args.stage,independent_blocks=blocks,arrays_audited=arrays,
    records_audited=len(rows),summary_sha256=sha(summary_path),contract_sha256=sha(contract_path),
    new_calls=dict(D=0,F=0,T=0),tables=tables,rows=rows,wall_seconds=time.time()-started,
    auditor_sha256=sha(__file__),scope='recount and parity validation; development data, no confirmation claim')
out=root/'evidence'/('llr-'+args.stage+'-audit.json')
with out.open('x') as f:json.dump(result,f,indent=2)
if args.admit:
    if args.stage != 'engineering':raise ValueError('only engineering may admit development')
    quote=3*summary['wall_seconds']*contract['development_blocks']/blocks+30
    if quote > contract['bounds']['development']['seconds']:
        raise RuntimeError('conservative wall-time quote exceeds light development bound')
    admission=dict(status='PASS',contract_sha256=sha(contract_path),source_sha256=summary['source_manifest_sha256'],
        engineering_summary_sha256=sha(summary_path),engineering_audit_sha256=sha(out),
        beta_one_replays=summary['beta_one_exact_replays'],conservative_development_seconds=quote,
        quote_rule='3 * full engineering stage wall time * block ratio + 30s',device='cpu')
    with (root/'evidence/llr-admission-v1.json').open('x') as f:json.dump(admission,f,indent=2)
print(json.dumps(dict(status='PASS',stage=args.stage,records=len(rows),arrays=arrays,wall_seconds=result['wall_seconds'])))
print(json.dumps(tables))
