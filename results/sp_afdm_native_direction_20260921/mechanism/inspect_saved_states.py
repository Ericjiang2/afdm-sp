"""Read-only inventory of the six audited TF/POINT frame-zero batches."""
import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--baseline', type=Path, required=True)
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
a = parser.parse_args()
sys.path[:0] = [str(a.source / 'src'), str(a.baseline / 'src')]
import evidence
manifest = json.loads((a.run / 'manifest.json').read_text())
run_hash = evidence.canonical_hash(manifest)
rows = [json.loads(line) for line in (a.run / 'ledger.jsonl').read_text().splitlines()]
found = []
for snr in (600,650,700):
    input_path = a.run / 'frames' / f's{snr}_f000_input.npz'
    input_id = {'schema':'spafdm-native-direction-compact/1','run_identity_sha256':run_hash,
                'kind':'frame_input','snr_centi_db':snr,'frame':0}
    observed, _ = evidence.load_artifact(input_path,input_id)
    if set(observed) != {'y','pilot','sigma2'}:
        raise ValueError('saved observed input fields differ')
    for arm in ('TF_J20_R2','TF_POINT20_R2'):
        row = next(r for r in rows if r['snr_centi_db']==snr and r['frame']==0 and r['arm']==arm)
        if len(row['checkpoints']) != 2:
            raise ValueError(f'missing round: {snr} {arm}')
        for cp in row['checkpoints']:
            path = a.run / cp['path']
            ident = {'schema':'spafdm-native-direction-compact/1','run_identity_sha256':run_hash,
                     'kind':'checkpoint','snr_centi_db':snr,'frame':0,'arm':arm,'round':cp['round']}
            payload,_ = evidence.load_artifact(path,ident)
            states = payload.get('inference_states')
            trace = payload['snapshot'].get('inference_trace')
            if len(states or []) != 20 or len(trace or []) != 20:
                raise ValueError(f'missing full states/trace: {snr} {arm} round{cp["round"]}')
            required = {'h','mu','v','s','vr','vq','vh','sv','bar','vp'}
            if any(set(item) != required for item in states):
                raise ValueError(f'state fields differ: {snr} {arm} round{cp["round"]}')
            found.append({'snr_centi_db':snr,'arm':arm,'round':cp['round'],
                'checkpoint_path':str(path),'checkpoint_sha256':cp['artifact_sha256'],
                'input_sha256':row['input_sha256'],'states':len(states),'trace':len(trace),
                'state_fields':sorted(required)})
if len(found)!=12:
    raise ValueError('expected twelve audited round checkpoints')
receipt={'status':'pass','run_identity_sha256':run_hash,'audited_batches':len(found),
         'audited_iterations':sum(x['states'] for x in found),'entries':found}
if a.out.exists():
    raise ValueError('inventory exists')
a.out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':'pass','audited_batches':len(found),'audited_iterations':receipt['audited_iterations']}))
