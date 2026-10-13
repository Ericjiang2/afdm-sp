"""Synthetic contracts for the registered prospective harness only."""
from pathlib import Path
import json
import sys

import numpy as np
import pytest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import generate_population as generator  # noqa: E402
import run_prospective as receiver  # noqa: E402
from audit_io import sha256, write_json  # noqa: E402


def population_rows():
    return [dict(observation_id=f's{snr}_f{frame:04d}',
                 snr_centi_db=snr,frame=frame)
            for snr in generator.CELLS for frame in range(generator.FRAMES)]


def test_new_256_bit_streams_are_domain_separated_and_deterministic():
    entropy='ab'*32
    a=generator.seed_words(entropy,600,0,1)
    assert len(a)==12 and a[8]==generator.DOMAIN
    assert a!=generator.seed_words(entropy,600,0,2)
    assert a!=generator.seed_words(entropy,650,0,1)
    assert a!=generator.seed_words(entropy,600,1,1)
    assert generator.stream_ids(entropy,600,0)==generator.stream_ids(entropy,600,0)
    ids=generator.stream_ids(entropy,600,0)
    assert len(set(ids.values()))==3
    for value in ids.values():
        assert len(value)==64
    with pytest.raises(ValueError,match='invalid prospective'):
        generator.seed_words('short',600,0,1)


def test_fixed_paired_arm_order_covers_all_3072_inputs():
    rows=population_rows()
    schedule=receiver.arm_schedule(rows)
    assert len(schedule)==6144
    assert [arm for _,arm in schedule[:6]]==[
        'TF','TF_CSTATE','TF_CSTATE','TF','TF','TF_CSTATE']
    assert len({(r['observation_id'],arm) for r,arm in schedule})==6144
    with pytest.raises(ValueError,match='allocation'):
        receiver.arm_schedule(rows[:-1])


def test_paired_native_identity_checks_continuous_and_hard_outputs():
    a=dict(baseline_arrays=dict(r0_decoded=np.array([0,1],np.uint8),
        r1_decoded=np.array([1,0],np.uint8),
        r1_mu=np.array([.2+.1j,.3-.2j]),
        r1_inference_trace=[dict(iteration=0,variance=.5,
                                 guard=False)]))
    b=dict(baseline_arrays={key:value.copy() if isinstance(value,np.ndarray)
        else [dict(record) for record in value]
        for key,value in a['baseline_arrays'].items()})
    assert receiver._native_identity(a,b)==0.
    b['baseline_arrays']['r1_mu'][0]+=1e-9
    with pytest.raises(ValueError,match='continuous'):
        receiver._native_identity(a,b)
    b['baseline_arrays']['r1_mu']=a['baseline_arrays']['r1_mu'].copy()
    b['baseline_arrays']['r0_decoded'][0]=1
    with pytest.raises(ValueError,match='decoded bits'):
        receiver._native_identity(a,b)


def test_seals_reject_tampering_and_incomplete_allocations(tmp_path):
    observed=tmp_path/'population_observed'
    observed.mkdir()
    (observed/'artifact').write_bytes(b'frame')
    digest=sha256(observed/'artifact')
    rows=[dict(observation_id=f's{snr}_f{frame:04d}',
        snr_centi_db=snr,frame=frame,
        observation_path='artifact',observation_sha256=digest)
        for snr in generator.CELLS for frame in range(generator.FRAMES)]
    (observed/'ledger.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write_json(observed/'generation_receipt.json',dict(status='pass',
        schema=generator.SCHEMA,observations=3072,
        cells=[{'snr_centi_db':x,'frames':generator.FRAMES} for x in generator.CELLS],
        observed_ledger_sha256=sha256(observed/'ledger.jsonl')))
    write_json(observed/'observed_seal.json',dict(status='pass',schema=generator.SCHEMA,
        observations=3072,files={p.name:sha256(p) for p in observed.iterdir()
            if p.name!='observed_seal.json'}))
    generator.verify_population_seal(observed)
    write_json(observed/'generation_receipt.json',dict(status='pass',
        schema=generator.SCHEMA,observations=1))
    write_json(observed/'observed_seal.json',dict(status='pass',schema=generator.SCHEMA,
        observations=3072,files={p.name:sha256(p) for p in observed.iterdir()
            if p.name!='observed_seal.json'}))
    with pytest.raises(ValueError,match='generation receipt'):
        generator.verify_population_seal(observed)
    (observed/'artifact').write_bytes(b'tampered')
    with pytest.raises(ValueError,match='seal'):
        generator.verify_population_seal(observed)


def test_receiver_seal_checks_two_or_three_checkpoints(tmp_path):
    root=tmp_path/'receiver'
    root.mkdir()
    (root/'artifact').write_bytes(b'decision')
    digest=sha256(root/'artifact')
    rows=[]
    for item,arm in receiver.arm_schedule(population_rows()):
        triggered=arm=='TF_CSTATE' and item['frame']==0
        rows.append(dict(status='ok',observation_id=item['observation_id'],
            arm=arm,triggered=triggered,
            raw_path='artifact',raw_sha256=digest,
            decision_record_path='artifact',decision_record_sha256=digest,
            checkpoints=[dict(path='artifact',artifact_sha256=digest)
                for _ in range(3 if triggered else 2)]))
    (root/'ledger.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write_json(root/'observed_seal.json',dict(status='pass',schema=receiver.SCHEMA,
        files={p.name:sha256(p) for p in root.iterdir()
            if p.name!='observed_seal.json'}))
    receiver.verify_observed_seal(root)
    rows[0],rows[1]=rows[1],rows[0]
    (root/'ledger.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write_json(root/'observed_seal.json',dict(status='pass',schema=receiver.SCHEMA,
        files={p.name:sha256(p) for p in root.iterdir()
            if p.name!='observed_seal.json'}))
    with pytest.raises(ValueError,match='allocation'):
        receiver.verify_observed_seal(root)
    rows[0],rows[1]=rows[1],rows[0]
    rows[0]['checkpoints']=[]
    (root/'ledger.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write_json(root/'observed_seal.json',dict(status='pass',schema=receiver.SCHEMA,
        files={p.name:sha256(p) for p in root.iterdir()
            if p.name!='observed_seal.json'}))
    with pytest.raises(ValueError,match='checkpoint'):
        receiver.verify_observed_seal(root)
