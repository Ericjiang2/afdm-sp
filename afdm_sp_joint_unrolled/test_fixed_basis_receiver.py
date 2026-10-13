"""Real small receiver wiring; N256 qualification is a separate experiment."""
import numpy as np
import pytest
import torch

from afdm_sp_joint_unrolled import classical_joint_unrolled as joint
from afdm_sp_joint_unrolled.fixed_basis_receiver import FixedBasisRepresentation
from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule


@pytest.fixture(autouse=True)
def deterministic_cpu_gels(monkeypatch):
    original=torch.linalg.lstsq
    def solve(*args,**kwargs):
        kwargs['driver']='gels';return original(*args,**kwargs)
    monkeypatch.setattr(torch.linalg,'lstsq',solve)


def setup():
    n=16;c1=3/32;c2=.0003
    model=joint.build_classical_joint_unrolled(n,2,1,c1,c2,n_paths=2,n_outer_iter=3,
        pic_iter=2,rho=.5,mp_mode='bp',k_leak=0,dtype=torch.complex64,rdtype=torch.float32,use_soft_decisions=True).eval()
    rng=np.random.default_rng(300)
    y=torch.tensor(rng.normal(size=n)+1j*rng.normal(size=n),dtype=torch.complex64)
    pilot=torch.zeros(n,dtype=torch.complex64);pilot[0]=np.sqrt(8)
    constellation=torch.tensor([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j],dtype=torch.complex64)
    return model,(y,pilot,torch.tensor(.1),constellation)


def representation():
    return FixedBasisRepresentation(family='fourier',q=3,n=16,c1=3/32,c2=.0003,
        delay_cap=2,prefix_length=3,sample_rate=4000.,max_doppler=16.,coefficient_cap=6)


def test_real_common_loop_consumes_basis_design_and_channel(monkeypatch):
    model,args=setup();rep=representation();counts=dict(ce=0,bp=0);variances=[]
    original_ce=joint.soft_gain_update;original_bp=joint.mp_detect_bp_torch
    def ce(*a,**kw):counts['ce']+=1;return original_ce(*a,**kw)
    def bp(*a,**kw):
        result=original_bp(*a,**kw);counts['bp']+=1
        variances.append(result[2].detach().numpy());return result
    monkeypatch.setattr(joint,'soft_gain_update',ce);monkeypatch.setattr(joint,'mp_detect_bp_torch',bp)
    with torch.no_grad():out=model(*args,enable_support_repair=False,channel_representation=rep,bp_schedule=UniformBPSchedule(outer_bp_iterations=2))
    assert counts==dict(ce=2,bp=3)
    assert 'support_dopplers' not in out and len(out['support_basis_indices'])==6
    assert out['bp_schedule']['completed_ce_solves']==2
    assert rep.counts['dals_designs']==2 and rep.counts['channel_reconstructions']==3
    assert all(np.isfinite(v).all() and np.min(v)>=0 and np.max(v)<=.50001 for v in variances)
    np.testing.assert_allclose(rep.last_design@rep.last_coefficients,
        rep.last_channel@rep.last_symbols,atol=2e-6,rtol=2e-6)
    with torch.no_grad(),pytest.raises(ValueError,match='fresh fixed basis'):
        model(*args,enable_support_repair=False,channel_representation=rep)


def test_default_none_path_is_exact():
    model,args=setup()
    with torch.no_grad():
        a=model(*args,enable_support_repair=False)
        b=model(*args,enable_support_repair=False,channel_representation=None)
    for key in ('H_est','x_soft','gains','support_delays','support_dopplers','sigma2_final'):
        assert torch.equal(a[key],b[key]),key


@pytest.mark.parametrize('options',[
    dict(enable_support_repair=True),dict(code_feedback=object()),
    dict(diagnostic_channel_override=lambda h,*args:h),dict(dals_mode='jsoft'),
    dict(outer_bp_graph='integer'),dict(Phi=torch.zeros(16,9,dtype=torch.complex64)),
])
def test_unqualified_interventions_rejected(options):
    model,args=setup();kw=dict(enable_support_repair=False,channel_representation=representation());kw.update(options)
    with torch.no_grad(),pytest.raises(ValueError):model(*args,**kw)
