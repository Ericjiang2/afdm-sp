import json
from types import SimpleNamespace
import numpy as np
import pytest
import wrapper as base
import wrapper_global as global_wrapper


def test_v2_rejects_v1_runtime_and_registration():
    with pytest.raises(ValueError,match='global_v2'):
        global_wrapper.receive({},'cascade',SimpleNamespace())
    with pytest.raises(ValueError,match='global_v2'):
        global_wrapper.verify_registration(SimpleNamespace(),dict(mechanism_version='v1'))


def test_distinct_producer_receiver_identities_without_manifest_rewrite(tmp_path):
    source=tmp_path/'original.py';source.write_text('original source')
    rt=SimpleNamespace(project=tmp_path,system=SimpleNamespace(N_total=4,rho=.5,c1=.1,c2=.01,l_max_cap=2),code=dict(H=np.eye(2,dtype=np.uint8),G=np.eye(2,dtype=np.uint8)),environment=dict(host='receiver'),header={})
    old_binding=base.runtime_binding(rt);old_binding['environment']=dict(host='producer')
    producer_reg=dict(candidate_options=base.OPTIONS,source_files={'original.py':base.sha256(source)},allocation_sha256='allocation',runtime_binding=old_binding)
    pop=tmp_path/'population';pop.mkdir();(pop/'frame.npz').write_bytes(b'unit-test fixture, not real observation')
    base.write_json(pop/'manifest.json',dict(registration=producer_reg,registration_sha256='producer-reg-sha',runtime_binding=old_binding))
    base.append_json(pop/'ledger.jsonl',dict(observation_id='unit_frame',observation_path='frame.npz',observation_sha256=base.sha256(pop/'frame.npz')))
    base.write_json(pop/'observed_seal.json',dict(status='pass',registration_sha256='producer-reg-sha',allocation_sha256='allocation',observations=1,files={p.name:base.sha256(p) for p in pop.iterdir()}))
    before=(pop/'manifest.json').read_bytes()
    receiver_reg=dict(mechanism_version='global_v2',producer_binding=global_wrapper.producer_binding(pop),allocation_sha256='allocation',runtime_binding=base.runtime_binding(rt))
    rows=global_wrapper.validate_producer(rt,pop,receiver_reg)
    assert len(rows)==1 and (pop/'manifest.json').read_bytes()==before
    receiver_reg['producer_binding']['manifest_sha256']='wrong'
    with pytest.raises(ValueError,match='producer binding'):
        global_wrapper.validate_producer(rt,pop,receiver_reg)
