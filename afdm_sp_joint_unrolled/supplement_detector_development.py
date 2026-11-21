"""Finite development reservations; execution and scientific selection remain separate."""
import fcntl
import hashlib
import json
from pathlib import Path
from .supplement_data import CAMPAIGN_ID
from .supplement_detectors import catalogue
from .budgeted_frame_store import publish_json


def reserve_development(out,*,start,stop,baseline,selection_sha256,source_sha256):
    """Reserve all eight frozen detectors for disjoint blocks; never reclaim failures."""
    out=Path(out).resolve()
    if type(start) is not int or type(stop) is not int or not 0<=start<stop<=192 or stop-start>16:
        raise ValueError('explicit development batch of1..16 blocks inside0..192 required')
    if not isinstance(baseline,str) or not baseline:
        raise ValueError('frozen reference ID required')
    for value in (selection_sha256,source_sha256):
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('content-bound selection and implementation required')
    ids=[r['id'] for r in catalogue()]
    identities={(b,d) for b in range(start,stop) for d in ids}
    ledger=out.parent/'supplement-detector-development-ledger';ledger.mkdir(exist_ok=True)
    binding=dict(campaign_id=CAMPAIGN_ID,baseline=baseline,selection_sha256=selection_sha256,source_sha256=source_sha256)
    with (ledger/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        used=set()
        for path in ledger.glob('reservation-*.json'):
            previous=json.loads(path.read_text())
            if previous.get('binding')!=binding or previous.get('schema')!='supplement-detector-development-reservation-v1':
                raise ValueError('mixed development reference/source/selection')
            entries=previous['identities']
            if (not isinstance(entries,list) or any(not isinstance(v,list) or len(v)!=2 or
                    type(v[0]) is not int or not 0<=v[0]<192 or v[1] not in ids for v in entries)):
                raise ValueError('invalid existing development identity domain')
            old={tuple(v) for v in entries}
            if len(entries)!=len(old) or len(old)!=previous['T'] or old & used:
                raise ValueError('corrupt or overlapping existing reservations')
            used.update(old)
        if identities & used:raise ValueError('development identity already charged; no automatic retry')
        if len(identities|used)>1536:raise ValueError('development1536T cap exceeded')
        record=dict(schema='supplement-detector-development-reservation-v1',binding=binding,
                    identities=sorted(identities),T=len(identities),out=str(out),
                    policy='no automatic retry or reclaim; unqualified configurations remain labeled')
        key=hashlib.sha256(str(out).encode()).hexdigest()
        path=ledger/f'reservation-{key}.json'
        publish_json(path,record)
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),T=len(identities))


def validate_development(args,caches,ids):
    """Bind an explicit sub-batch to the full frozen development manifest."""
    from .supplement_baseline_select import read_json
    if args.admission is None:raise ValueError('development admission required')
    admission,_=read_json(args.admission)
    if admission.get('stage')!='development' or admission.get('campaign_id')!=CAMPAIGN_ID:
        raise ValueError('wrong development admission')
    selection=admission['selection'];result,_=read_json(selection['path'],selection['sha256'])
    baseline=admission['baseline']
    if (result['selection'].get('status')!='development_references_selected' or
            result['selection']['references'][0]!=baseline):
        raise ValueError('development must use frozen primary reference')
    if ids!=[r['id'] for r in catalogue()] or admission['detectors']!=ids:
        raise ValueError('all eight original detector recipes required')
    all_caches=admission['caches']
    if len(all_caches)!=192 or len({json.dumps(v,sort_keys=True) for v in all_caches})!=192:
        raise ValueError('exact192 unique development caches required')
    try:start=all_caches.index(caches[0])
    except ValueError as exc:raise ValueError('cache not in admitted development set') from exc
    stop=start+len(caches)
    if not 1<=len(caches)<=16 or all_caches[start:stop]!=caches:
        raise ValueError('contiguous admitted batch of at most16 blocks required')
    q=admission['qualification'];qualified,_=read_json(q['path'],q['sha256'])
    if qualified.get('stage')!='qualification' or qualified.get('calls_attempted')!=64 or qualified.get('failures'):
        raise ValueError('complete qualification evidence required, including unqualified results')
    if set(qualified['qualified_by_detector'])!=set(ids):raise ValueError('qualification recipe set differs')
    return dict(start=start,stop=stop,baseline=baseline,selection=selection,qualification=q,batches=result['batches'],
                qualified_by_detector=qualified['qualified_by_detector'])


def offline_score(result,proof):
    """Only called AFTER terminal detection; truth never enters detector arguments."""
    import numpy as np
    from .budgeted_support_diagnostics import array_hash
    from .supplement_profile import score_errors
    path=Path(proof['terminal_path'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=proof['files'][str(path)]:
        raise ValueError('terminal cache changed before offline scoring')
    with np.load(path,allow_pickle=False) as raw:truth={k:raw[k].copy() for k in ('info','coded')}
    if any(array_hash(v)!=proof['truth_hashes'][k] for k,v in truth.items()):
        raise ValueError('offline truth lineage mismatch')
    return score_errors(result,truth)


def validate_loaded_development(proofs,development):
    if [p['block'] for p in proofs]!=list(range(development['start'],development['stop'])):
        raise ValueError('cache blocks differ from frozen manifest ordering')
    batches={b['config_sha256']:b for b in development['batches']}
    for proof in proofs:
        batch=batches.get(proof['config_sha256'])
        root=Path(proof['spec']['local_root']).resolve()
        if batch is None or proof['baseline']!=development['baseline'] or proof['split']!='design':
            raise ValueError('cache is not a selected-reference design batch')
        if (proof['files'].get(str(root/'summary.json'))!=batch['summary_sha256'] or
                proof['files'].get(str(root/'contract.json'))!=batch['contract_file_sha256']):
            raise ValueError('cache evidence differs from audited BASE selection')
