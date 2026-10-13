from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from osd1 import acquire_osd1,GRID,ROOT
sys.path.insert(0,str(ROOT/'acquisition'))
from candidates import reliable_basis,PhysicalScore
from test_candidates import small_code,make_channel
import runner


def fixture():
    h=small_code();llr=np.array([-.2,4,3,2,1,.4,.8,5]);ch=make_channel(4)
    return h,llr,ch,np.ones(4,dtype=complex),np.arange(4)*(.1+.2j)


def test_full_order1_exact_legal_set_and_common_scorer():
    h,llr,ch,y,p=fixture();b=reliable_basis(h,llr)
    out=acquire_osd1(h,llr,ch,y,p,.3,scale=.7,full=True)
    expected=[b['anchor'],*[b['anchor']^b['generator'][:,j] for j in range(len(b['free']))]]
    assert {tuple(w) for w in out['candidates']}=={tuple(w) for w in expected}
    assert not np.any(h@out['candidates'].T%2)
    assert out['counts']['physical_scores']==len(b['free'])+1
    scorer=PhysicalScore(ch,y,p,.3,.7)
    np.testing.assert_allclose(out['scores'],[scorer(w)[0] for w in out['candidates']])
    assert out['full_order1'] and out['counts']['geometry_prescreens']==0


def test_budget_is_prefix_and_deterministic():
    h,llr,ch,y,p=fixture()
    full=acquire_osd1(h,llr,ch,y,p,.3,scale=.7,full=True)
    limited=acquire_osd1(h,llr,ch,y,p,.3,scale=.7,k=3)
    again=acquire_osd1(h,llr,ch,y,p,.3,scale=.7,k=3)
    np.testing.assert_array_equal(limited['candidates'],full['candidates'][:4])
    np.testing.assert_array_equal(limited['candidates'],again['candidates'])
    assert not limited['full_order1'] and limited['k']==3
    assert limited['counts']['physical_scores']==4
    with pytest.raises(ValueError):acquire_osd1(h,llr,ch,y,p,.3,scale=.7,k=1024)
    with pytest.raises(ValueError):acquire_osd1(h,llr,ch,y,p,.3,scale=.7,k=3,full=True)


def test_osd_adapter_is_private_and_labels_correctly(monkeypatch):
    original=lambda *a,**kw:None
    rt=SimpleNamespace(control_version='strong_osd1_v1',acquire=original)
    seen=[]
    def fake_osd(*args,**kwargs):
        seen.append(kwargs)
        return dict(method='osd1_full' if kwargs['full'] else 'osd1_budget')
    def fake_receive(obs,policy,private):
        assert policy=='cascade_geometry'
        return dict(acquisition=private.acquire(None,None,None,None,None,1.,scale=.7,mode='geometry',**runner.base.OPTIONS))
    monkeypatch.setattr(runner,'verify_effective',lambda rt:None)
    monkeypatch.setattr(runner,'acquire_osd1',fake_osd)
    monkeypatch.setattr(runner.base,'receive',fake_receive)
    for policy in ('osd1_budget','osd1_full'):
        out=runner.receive({},policy,rt,16)
        assert out['comparison_policy']==policy and out['acquisition']['method']==policy
    assert seen[0]['k']==16 and seen[1]['k'] is None and seen[1]['full']
    assert rt.acquire is original


def test_calibration_and_registration_reject_missing_contract(tmp_path):
    import calibrate
    with pytest.raises(ValueError,match='calibration protocol'):
        calibrate.calibrate(None,tmp_path,tmp_path,tmp_path/'calibration',{})
    assert not (tmp_path/'calibration').exists()
    with pytest.raises(ValueError):runner.verify_registration(None,{})
    assert GRID==(16,32,64,128,256,512,1024)


def test_thread_contract_rejects_unobservable_backend(monkeypatch):
    import thread_binding as tb
    monkeypatch.setattr(tb.threadpoolctl,'threadpool_info',lambda:[])
    monkeypatch.setattr(tb.np.__config__,'CONFIG',{'Build Dependencies':{'blas':{'name':'unknown'}}})
    with pytest.raises(RuntimeError,match='cannot be verified'):tb.blas_binding()


def test_accelerate_queries_effective_mode(monkeypatch):
    import thread_binding as tb
    calls=[]
    class Function:
        def __init__(self,fn):self.fn=fn
        def __call__(self,*args):return self.fn(*args)
    lib=SimpleNamespace(BLASSetThreading=Function(lambda n:(calls.append(n) or 0)),BLASGetThreading=Function(lambda:1))
    monkeypatch.setattr(tb.threadpoolctl,'threadpool_info',lambda:[])
    monkeypatch.setattr(tb.np.__config__,'CONFIG',{'Build Dependencies':{'blas':{'name':'accelerate'}}})
    monkeypatch.setattr(tb.ctypes,'CDLL',lambda _:lib)
    result=tb.blas_binding()
    assert calls==[1] and result['accelerate_current_thread_mode']==1


def calibration_fixture(tmp_path,medians=None):
    """144 tiny evidence files, explicitly synthetic; no numerical receiver."""
    import json
    base=runner.base
    medians={k:.5 for k in GRID} if medians is None else medians
    shared=dict(source_files={'fixture.py':'fixture-hash'},runtime_binding={'environment':{'host':'fixture'}},producer_binding={'seal':'fixture'},allocation_sha256='fixture-allocation',candidate_options=base.OPTIONS)
    reg=dict(shared,osd1_budget_k=16,budget_choice_reason='fixture timing choice')
    calreg=dict(shared,mechanism_version='strong_osd1_calibration_v1',k_grid=list(GRID),repeats=3,expected_observable_triggers=6)
    states=[dict(observation_id=f'fixture_{i}',raw_sha256=f'original_{i}') for i in range(6)]
    manifest=dict(registration=calreg,environment=shared['runtime_binding']['environment'],source_states=states)
    base.write_json(tmp_path/'manifest.json',manifest)
    for state in states:
        for k in (None,*GRID):
            for repeat in range(3):
                stem=state['observation_id'];policy='residual_global_reference' if k is None else f'osd1_k{k}'
                ident=dict(observation_id=stem,policy=policy,k=k,repeat=repeat,reference_raw_sha256=state['raw_sha256'])
                raw=tmp_path/f'{stem}_{policy}_{repeat}.fixture';raw.write_bytes(b'explicit synthetic non-receiver evidence')
                seconds=1. if k is None else medians[k]
                row=dict(ident,module_seconds=seconds,complete_artifact_seconds=seconds+.1,physical_scores=16 if k is None else k+1,raw_path=raw.name,raw_sha256=base.sha256(raw))
                base.append_json(tmp_path/'attempts.jsonl',dict(ident,event='started',epoch=1.))
                base.append_json(tmp_path/'ledger.jsonl',row)
                base.append_json(tmp_path/'attempts.jsonl',dict(row,event='finished'))
    feasible=[k for k in GRID if medians[k]<=1.]
    receipt=dict(status='pass',expected_calls=144,completed_calls=144,target_seconds=1.,median_module_seconds={str(k):v for k,v in medians.items()},suggested_k=max(feasible) if feasible else None,manifest_sha256=base.sha256(tmp_path/'manifest.json'),ledger_sha256=base.sha256(tmp_path/'ledger.jsonl'),attempts_sha256=base.sha256(tmp_path/'attempts.jsonl'))
    base.write_json(tmp_path/'result.json',receipt)
    return reg,receipt


def test_calibration_actual_complete_fixture_accepted(tmp_path):
    reg,receipt=calibration_fixture(tmp_path)
    runner.validate_calibration(tmp_path/'result.json',receipt,reg)


@pytest.mark.parametrize('field',['source_files','runtime_binding','producer_binding','allocation_sha256','candidate_options'])
def test_calibration_cross_protocol_mismatch_rejected(tmp_path,field):
    reg,receipt=calibration_fixture(tmp_path)
    reg[field]='different-receiver-contract'
    with pytest.raises(ValueError,match='calibration '+field):
        runner.validate_calibration(tmp_path/'result.json',receipt,reg)


def test_smaller_k_can_be_over_budget_nonmonotonically(tmp_path):
    medians={k:.5 for k in GRID};medians[16]=2.
    reg,receipt=calibration_fixture(tmp_path,medians)
    assert reg['osd1_budget_k']<receipt['suggested_k']
    with pytest.raises(ValueError,match='selected K itself'):
        runner.validate_calibration(tmp_path/'result.json',receipt,reg)


def test_self_reported_complete_but_empty_calibration_ledger_rejected(tmp_path):
    reg,receipt=calibration_fixture(tmp_path)
    (tmp_path/'ledger.jsonl').write_text('')
    receipt['ledger_sha256']=runner.base.sha256(tmp_path/'ledger.jsonl')
    with pytest.raises(ValueError,match='ledger does not cover'):
        runner.validate_calibration(tmp_path/'result.json',receipt,reg)


@pytest.mark.parametrize('value',[0.,-1.,float('nan'),float('inf'),True])
def test_calibration_target_must_be_finite_positive(tmp_path,value):
    reg,receipt=calibration_fixture(tmp_path);receipt['target_seconds']=value
    with pytest.raises(ValueError,match='finite positive target'):
        runner.validate_calibration(tmp_path/'result.json',receipt,reg)


def test_calibration_raw_and_attempts_not_just_ledger_hash(tmp_path):
    reg,receipt=calibration_fixture(tmp_path)
    raw=next(tmp_path.glob('*.fixture'));raw.write_bytes(b'tampered')
    with pytest.raises(ValueError,match='raw hash'):
        runner.validate_calibration(tmp_path/'result.json',receipt,reg)
    raw.write_bytes(b'explicit synthetic non-receiver evidence')
    attempts=tmp_path/'attempts.jsonl';attempts.write_text('\n'.join(attempts.read_text().splitlines()[:-1])+'\n')
    receipt['attempts_sha256']=runner.base.sha256(attempts)
    with pytest.raises(ValueError,match='attempts do not cover'):
        runner.validate_calibration(tmp_path/'result.json',receipt,reg)
