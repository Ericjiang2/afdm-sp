from types import SimpleNamespace
import numpy as np
import pytest
from wrapper import receive,final_channel,OPTIONS


def runtime(prefix_bad=True,scalar_bad=True,coherent_bad=True,restart_bad=True):
    h=np.zeros((1,2048),np.uint8);h[0,0]=1
    calls=[]
    def dec(bad):
        w=np.zeros(2048,np.uint8);w[0]=int(bad)
        return dict(decoded=w,raw_app=np.ones(2048))
    def native(*a,**kw):calls.append('prefix');return dec(prefix_bad),{},{}
    def branch(*a,**kw):calls.append('scalar');return dict(decoder=dec(scalar_bad))
    def coherent(*a,**kw):calls.append('coherent');return dict(decoder=dec(coherent_bad))
    def restart(*a,**kw):
        calls.append('restart')
        return dict(final_decoder=dec(restart_bad),branch=dict(geometry_result=dict(paths=[dict(delay=7,doppler=.42)],gains=np.array([2+3j]))))
    def channel(n,c1,c2,delays,dopplers,gains):
        return SimpleNamespace(delays=np.asarray(delays),dopplers=np.asarray(dopplers),gains=gains)
    def acquire(*args,**kwargs):
        calls.append('acquire_'+kwargs['mode'])
        assert args[2].delays[0]==7 and args[2].gains[0]==2+3j
        return dict(decoded=np.zeros(2048,np.uint8))
    return SimpleNamespace(code=dict(H=h),system=SimpleNamespace(N=1024,c1=.1,c2=.01,rho=.5),native=SimpleNamespace(receive=native),kernel=None,_branch=branch,receive_f1=None,variant=None,reused_coherent=coherent,f1_call=restart,branch_payload=lambda x:x,finite=lambda x:None,Channel=channel,acquire=acquire,calls=calls)

OBS=dict(y=np.zeros(1024,complex),pilot=np.ones(1024,complex),sigma2=1.)


def test_success_protected_and_all_failure_routes():
    rt=runtime(prefix_bad=False)
    out=receive(OBS,'cascade_geometry',rt)
    assert rt.calls==['prefix'] and out['acquisition'] is None
    rt=runtime()
    out=receive(OBS,'cascade_geometry',rt)
    assert rt.calls==['prefix','scalar','coherent','restart','acquire_geometry']
    assert out['final_syndrome']==0 and out['pre_acquisition_decoder']['decoded'][0]==1
    assert out['final_decoder']['decision_source']=='legal_candidate_gain_profile'
    assert 'raw_app' not in out['final_decoder']


def test_each_guard_and_independent_baselines():
    for kwargs,expected in [(dict(scalar_bad=False),['prefix','scalar']), (dict(coherent_bad=False),['prefix','scalar','coherent']), (dict(restart_bad=False),['prefix','scalar','coherent','restart'])]:
        rt=runtime(**kwargs);receive(OBS,'cascade_osd',rt);assert rt.calls==expected
    for policy,expected in [('scalar',['prefix','scalar']),('coherent',['prefix','scalar','coherent']),('f1',['restart']),('cascade',['prefix','scalar','coherent','restart'])]:
        rt=runtime();receive(OBS,policy,rt);assert rt.calls==expected


def test_observed_only_and_frozen_options():
    with pytest.raises(ValueError):receive(dict(OBS,truth=np.zeros(2048)),'cascade',runtime())
    with pytest.raises(ValueError):receive(OBS,'cascade',runtime(),dict(OPTIONS,list_size=17))
    with pytest.raises(ValueError):final_channel(dict(restart=None),runtime(),1024)


def test_saved_scorer_reports_legal_wrong_as_undetected(tmp_path):
    import importlib.util
    import json
    from pathlib import Path
    from wrapper import PROJECT,sha256,write_json,append_json
    from score import score
    spec=importlib.util.spec_from_file_location('fixture_evidence',PROJECT/'experiments/sp_afdm_frozen_20260920/src/evidence.py')
    evidence=importlib.util.module_from_spec(spec);spec.loader.exec_module(evidence)
    run=tmp_path/'run';truthroot=tmp_path/'truth';run.mkdir();truthroot.mkdir()
    h=np.array([[1,1,0,0],[0,0,1,1]],np.uint8)
    streams=dict(channel='a',message='b',noise='c')
    ident=dict(observation_id='fixture',policy='cascade_osd',input_sha256='mock_input',observation_hash='mock_observation',stream_ids=streams)
    truth=dict(coded=np.zeros(4,np.uint8),observation_hash='mock_observation',stream_ids=streams)
    tp=truthroot/'truth.npz';td=evidence.save_artifact(tp,truth,{})
    append_json(truthroot/'ledger.jsonl',dict(observation_id='fixture',truth_path='truth.npz',truth_sha256=td,observation_hash='mock_observation',stream_ids=streams))
    write_json(truthroot/'truth_seal.json',dict(allocation_sha256='mock_allocation',files={'truth.npz':td,'ledger.jsonl':sha256(truthroot/'ledger.jsonl')}))
    decoded=np.ones(4,np.uint8)
    payload=dict(final_decoder=dict(decoded=decoded),acquisition=dict(candidates=np.array([decoded])))
    rp=run/'raw.npz';rd=evidence.save_artifact(rp,payload,ident)
    append_json(run/'ledger.jsonl',dict(ident,raw_path='raw.npz',raw_sha256=rd,final_syndrome=0,receiver_ready_seconds=1.,complete_seconds=1.1))
    write_json(run/'manifest.json',dict(registration=dict(allocation_sha256='mock_allocation',policies=['cascade_osd'])))
    write_json(run/'result.json',dict(status='pass',completed_calls=1,expected_calls=1,ledger_sha256=sha256(run/'ledger.jsonl'),manifest_sha256=sha256(run/'manifest.json')))
    result=score(run,truthroot,evidence,h,output=tmp_path/'scored.json')
    assert result['summary']['cascade_osd']['errors']==1
    assert result['summary']['cascade_osd']['undetected_errors']==1
    assert result['summary']['cascade_osd']['covered']==0


def test_resume_rejects_prior_started_even_without_raw(tmp_path):
    import wrapper
    wrapper.append_json(tmp_path/'attempts.jsonl',dict(observation_id='frame',policy='cascade',event='started'))
    with pytest.raises(ValueError,match='retry authorization'):
        wrapper.validate_retry(tmp_path,{},None)


def test_writer_lock_fails_without_waiting(tmp_path):
    import wrapper
    with wrapper.writer_lock(tmp_path/'output'):
        with pytest.raises(RuntimeError,match='writer'):
            with wrapper.writer_lock(tmp_path/'output'):
                pass


def test_generation_requires_registration_before_output(tmp_path):
    import generate
    import inspect
    assert 'registration' in inspect.signature(generate.generate).parameters


def test_runtime_registration_rejects_changed_code_and_source(tmp_path):
    from wrapper import runtime_binding,verify_runtime_registration,sha256,OPTIONS
    p=tmp_path/'source.py';p.write_text('original')
    rt=SimpleNamespace(project=tmp_path,required_sources={'source.py':sha256(p)},system=SimpleNamespace(N_total=4,rho=.5,c1=.1,c2=.01,l_max_cap=2),code=dict(H=np.eye(2,dtype=np.uint8),G=np.eye(2,dtype=np.uint8)),environment={},header={},up=tmp_path,evidence=SimpleNamespace(verify_runtime_binding=lambda:None))
    reg=dict(candidate_options=OPTIONS,source_files=rt.required_sources.copy(),runtime_binding=runtime_binding(rt))
    verify_runtime_registration(rt,reg)
    rt.code['G'][0,0]=0
    with pytest.raises(ValueError,match='actual code'):
        verify_runtime_registration(rt,reg)
    rt.code['G'][0,0]=1;p.write_text('mutated')
    with pytest.raises(ValueError,match='source binding'):
        verify_runtime_registration(rt,reg)


def test_retry_authorization_preserves_measured_failed_cost(tmp_path):
    from wrapper import validate_retry,append_json,write_json,sha256
    path=tmp_path/'attempts.jsonl'
    append_json(path,dict(observation_id='a',policy='cascade',event='started'))
    append_json(path,dict(observation_id='a',policy='cascade',event='failed',elapsed_seconds=2.5))
    auth=tmp_path/'retry.json'
    write_json(auth,dict(attempts_sha256=sha256(path),reason='explicit engineering retry',authorized_by='unit-test fixture',retries=[dict(observation_id='a',policy='cascade',previous_elapsed_seconds=2.5)]))
    receipt=validate_retry(tmp_path,{},auth)
    assert receipt['authorization']['retries'][0]['previous_elapsed_seconds']==2.5
    assert len(path.read_text().splitlines())==3


def test_generator_rejects_missing_registration_before_creation(tmp_path):
    from generate import generate
    with pytest.raises(FileNotFoundError):
        generate(None,tmp_path/'allocation.json','development',tmp_path/'population',tmp_path/'missing-registration.json')
    assert not (tmp_path/'population').exists()


def test_path_escape_is_rejected(tmp_path):
    from wrapper import safe_child
    with pytest.raises(ValueError,match='escapes'):
        safe_child(tmp_path,'../outside')
