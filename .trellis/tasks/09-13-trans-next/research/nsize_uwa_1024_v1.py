"""Bounded N1024 UWA producer and independent saved-array audit.

Nothing runs at import. A stage needs a separately frozen, source-bound contract
and an explicit ``run`` command. The old N256 receiver is never invoked.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np
import torch

import physical_transfer_model_v1 as physical
import physical_transfer_receiver_v1 as old_adapter
from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles

HERE = Path(__file__).resolve().parent
REGISTERED = HERE / 'nsize-uwa-1024-contract-v1.json'
PILOTS = ('p0', 'pZ')
SNRS = (10, 20)
N = 1024
PREFIX = 256
SEED = (20260915, 1024)


def sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def config():
    old = physical.config('uwa')
    cfg = vars(old).copy()
    cfg.update(N=N, N_total=N, k_max_cap=5, c1=11/(2*N),
        c2=(np.sqrt(2)-1)/(2*N*N), dictionary_size=275,
        nomination=40, nomination_plus4=44, _zc_seq=physical._p0(N))
    return SimpleNamespace(**cfg)


def _rng(block: int, stream: int):
    if type(block) is not int or block not in range(16) or stream not in (1, 2):
        raise ValueError('registered block and stream required')
    return np.random.default_rng([*SEED, block, stream])


def paired_streams(old: dict, block: int):
    """Share DAFT data symbols and physical time-noise samples exactly."""
    old_cfg, new_cfg = physical.config('uwa'), config()
    if (old.get('block') != block or old.get('domain') != 'uwa'
            or np.asarray(old['data']).shape != (PREFIX,)
            or np.asarray(old['bits']).shape != (2*PREFIX,)
            or np.asarray(old['noise']).shape != (PREFIX,)):
        raise ValueError('old physical raw identity or stream shape differs')
    extra_bits = _rng(block, 1).integers(0, 2, 2*(N-PREFIX), dtype=np.uint8)
    bits = np.concatenate((old['bits'][:PREFIX], extra_bits[:N-PREFIX],
                           old['bits'][PREFIX:], extra_bits[N-PREFIX:]))
    signs = 1.-2.*bits.astype(float)
    data = .5*(signs[:N]+1j*signs[N:])
    old_time = physical.transform(old['noise'], old_cfg.c1, old_cfg.c2, inverse=True)
    rng = _rng(block, 2)
    tail = (rng.standard_normal(N-PREFIX)+1j*rng.standard_normal(N-PREFIX))/np.sqrt(2)
    noise_time = np.concatenate((old_time, tail))
    noise = physical.transform(noise_time, new_cfg.c1, new_cfg.c2)
    if (not np.array_equal(data[:PREFIX], old['data'])
            or not np.array_equal(noise_time[:PREFIX], old_time)
            or not np.array_equal(bits[:PREFIX], old['bits'][:PREFIX])
            or not np.array_equal(bits[N:N+PREFIX], old['bits'][PREFIX:])):
        raise ValueError('paired stream prefix changed')
    return bits, data, old_time, noise_time, noise


def generate(old: dict, block: int):
    cfg = config()
    bits, data, old_time, noise_time, noise = paired_streams(old, block)
    for key in ('delays', 'doppler_hz', 'gains'):
        if not np.isfinite(old[key]).all():
            raise ValueError('nonfinite old physical path: '+key)
    delays = np.asarray(old['delays']).copy()
    hz = np.asarray(old['doppler_hz']).copy()
    gains = np.asarray(old['gains']).copy()
    dopplers = hz*cfg.N/cfg.Fs
    h = physical.cpp_channel_matrix(cfg.N, cfg.c1, cfg.c2,
        delays, dopplers, gains, cfg.prefix_length)
    pilots = dict(p0=np.sqrt(cfg.rho)*cfg._zc_seq,
                  pZ=np.sqrt(cfg.N*cfg.rho)*np.eye(1,cfg.N,0,dtype=complex)[0])
    noiseless, closure, waveform = {}, {}, {}
    for name, pilot in pilots.items():
        x = pilot+data
        direct = physical.transform(physical.propagate_cpp(
            physical.transform(x,cfg.c1,cfg.c2,inverse=True),
            cfg.c1,delays,dopplers,gains,prefix_length=cfg.prefix_length),
            cfg.c1,cfg.c2)
        err = np.linalg.norm(direct-h@x)/max(1.,np.linalg.norm(direct))
        if not np.isfinite(err) or err > 1e-10:
            raise ValueError('N1024 direct CPP/matrix closure failed')
        noiseless[name], closure[name] = direct, float(err)
        waveform[name] = physical._waveform_metrics(cfg,pilot,data)
        if not (np.isclose(waveform[name]['pilot_energy'],N*.5,atol=2e-12,rtol=0)
                and np.isclose(waveform[name]['data_energy'],N*.5,atol=2e-12,rtol=0)):
            raise ValueError('fixed pilot/data component energy changed')
    return dict(domain='uwa',block=block,N=N,H=h,bits=bits,data=data,
        old_noise_time=old_time,noise_time=noise_time,noise=noise,
        pilots=pilots,noiseless=noiseless,
        delays=delays,doppler_hz=hz,dopplers=dopplers,gains=gains,
        metadata=dict(Fs=cfg.Fs,fc_hz=cfg.fc_hz,c_m_s=cfg.c_m_s,
            tau_max_s=cfg.tau_max_s,fd_max_hz=cfg.fd_max_hz,
            c1=cfg.c1,c2=cfg.c2,l_max=cfg.l_max_cap,k_max=cfg.k_max_cap,
            dictionary_size=cfg.dictionary_size,nomination=cfg.nomination,
            cluster_extension=cfg.cluster_extension,prefix_length=cfg.prefix_length,
            rho=cfg.rho,seed_prefix=list(SEED),cpp_closure=closure,waveform=waveform,
            gain_normalization='none',model_scope='fixed paths over 256 ms; no wideband time scaling'))


def validate_input(raw: dict, old: dict, block: int):
    cfg = config()
    if (raw.get('domain') != 'uwa' or raw.get('block') != block or raw.get('N') != N
            or np.asarray(raw.get('H')).shape != (N,N)
            or set(raw.get('pilots',{})) != set(PILOTS)):
        raise ValueError('N1024 raw identity, shape or pilots differ')
    bits,data,old_time,noise_time,noise = paired_streams(old,block)
    if not np.array_equal(raw['noise_time'][:PREFIX],raw['old_noise_time']):
        raise ValueError('saved new time noise does not exactly share old prefix')
    if not np.allclose(raw['old_noise_time'],old_time,atol=1e-12,rtol=0):
        raise ValueError('old DAFT noise inverse no longer matches saved source')
    for name,expected in [('bits',bits),('data',data),
                          ('delays',old['delays']),
                          ('doppler_hz',old['doppler_hz']),('gains',old['gains'])]:
        if not np.array_equal(raw[name],expected):
            raise ValueError('saved N1024 raw stream/path changed: '+name)
    for name,expected in [('noise_time',noise_time),('noise',noise)]:
        if not np.allclose(raw[name],expected,atol=1e-12,rtol=0):
            raise ValueError('saved N1024 noise stream changed: '+name)
    if not np.array_equal(raw['dopplers'],old['doppler_hz']*N/cfg.Fs):
        raise ValueError('normalized Doppler differs from fixed physical Hz')
    expected_pilots = dict(p0=np.sqrt(.5)*cfg._zc_seq,
        pZ=np.sqrt(N*.5)*np.eye(1,N,0,dtype=complex)[0])
    for name in PILOTS:
        if not np.array_equal(raw['pilots'][name],expected_pilots[name]):
            raise ValueError('saved pilot differs: '+name)
        x = raw['pilots'][name]+raw['data']
        direct = physical.transform(physical.propagate_cpp(
            physical.transform(x,cfg.c1,cfg.c2,inverse=True),cfg.c1,
            raw['delays'],raw['dopplers'],raw['gains'],
            prefix_length=cfg.prefix_length),cfg.c1,cfg.c2)
        if not np.allclose(direct,raw['noiseless'][name],atol=1e-12,rtol=1e-12):
            raise ValueError('saved direct propagation differs: '+name)
        err = np.linalg.norm(direct-raw['H']@x)/max(1.,np.linalg.norm(direct))
        if not np.isfinite(err) or err>1e-10:
            raise ValueError('saved H fails CPP direct propagation: '+name)
    expected = dict(Fs=4000,fc_hz=12000,c_m_s=1500,tau_max_s=.006,
        fd_max_hz=16.,c1=cfg.c1,c2=cfg.c2,l_max=24,k_max=5,
        dictionary_size=275,nomination=40,cluster_extension=2,
        prefix_length=32,rho=.5,seed_prefix=list(SEED),gain_normalization='none')
    if any(raw['metadata'].get(k)!=v for k,v in expected.items()):
        raise ValueError('saved N1024 public metadata changed')
    if not all(np.isfinite(a).all() for a in (raw['H'],data,noise,noise_time)):
        raise ValueError('nonfinite N1024 physical raw')
    return dict(block=block,CPP_closure='PASS',paired_prefix='PASS',
        physical_H_sha256=physical.array_sha256(raw['H']))


def observed(raw: dict,pilot: str,snr: int):
    if pilot not in PILOTS or snr not in SNRS:
        raise ValueError('registered pilot/SNR required')
    sigma2=10.**(-snr/10)
    return dict(y=raw['noiseless'][pilot]+np.sqrt(sigma2)*raw['noise'],
        pilot=raw['pilots'][pilot].copy(),sigma2=np.asarray(sigma2),
        constellation=physical.QPSK.copy())


def _copy_state(state):
    return {key:(value.detach().cpu().numpy().copy() if isinstance(value,torch.Tensor)
                 else value) for key,value in state.items()}


def receive(model,obs:dict):
    """Real observed-only OMP_BASE path with all nine consumed CE states."""
    from afdm_sp_joint_unrolled import classical_joint_unrolled as joint
    from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
    cfg=model.cfg
    old_adapter.base.validate_observed(obs,cfg.N)
    if (cfg.N!=N or cfg.l_max!=24 or cfg.k_max!=5 or cfg.k_leak!=2
            or cfg.n_outer_iter!=10 or cfg.pic_iter!=20):
        raise ValueError('receiver geometry/recipe differs from frozen N1024')
    cfg.n_paths=40
    model.use_soft_decisions=True
    head=model.cand_active_rel
    head.set_refine_config(2,96,True,2)
    head._gateA_scorer=None
    head._gateA_tau=-1e9
    counts=dict(lstsq=0,coding_calls=0,repair_calls=0,
        learned_score_calls=0,initial_omp_calls=0)
    original_omp=joint.omp_sparse_torch
    def omp(*args,**kwargs):
        counts['initial_omp_calls']+=1
        return original_omp(*args,**kwargs)
    joint.omp_sparse_torch=omp
    support,ce=[],[]
    def support_observer(raw,final,delays,dopplers):
        support.append(dict(initial=list(raw),final_nomination=list(final),
            expanded_delays=delays.detach().cpu().numpy().copy(),
            expanded_dopplers=dopplers.detach().cpu().numpy().copy()))
    try:
        with torch.no_grad(),old_adapter.base.cpu_lstsq(counts),old_adapter.base.forbid_coding(counts):
            result=model(torch.tensor(obs['y'],dtype=cfg.dtype),
                torch.tensor(obs['pilot'],dtype=cfg.dtype),
                torch.tensor(obs['sigma2'],dtype=cfg.rdtype),
                torch.tensor(obs['constellation'],dtype=cfg.dtype),
                enable_support_repair=False,code_feedback=None,
                diagnostic_support_observer=support_observer,
                diagnostic_dals_observer=lambda state:ce.append(_copy_state(state)),
                bp_schedule=UniformBPSchedule(outer_bp_iterations=20))
    finally:
        joint.omp_sparse_torch=original_omp
        head._gateA_scorer=None
    array=lambda key:result[key].detach().cpu().numpy().copy()
    value=dict(x_soft=array('x_soft'),H=array('H_est'),
        sigma2_final=array('sigma2_final'),gains=array('gains'),
        delays=array('support_delays'),dopplers=array('support_dopplers'),
        support_trace=support[0] if len(support)==1 else support,
        counts=counts,bp_schedule=result['bp_schedule'],
        nomination=40,cluster_extension=2,soft_decisions=True,CE=ce,
        x_soft_history=[x.detach().cpu().numpy().copy() for x in result['x_soft_history']],
        resnorm_history=[x.detach().cpu().numpy().copy() for x in result['resnorm_history']])
    value['bits']=old_adapter.base.bits_of(value['x_soft'])
    check_receiver(value)
    return value


def check_receiver(value:dict):
    old_adapter.check(value,'OMP_BASE',SimpleNamespace(N=N,l_max=24,k_max=5,k_leak=2),40)
    ce=value['CE']
    if len(ce)!=9 or [s['outer_iter'] for s in ce]!=list(range(1,10)):
        raise ValueError('exact nine actual CE observer states required')
    required={'A','y','g_previous','g_solution','H','mu','finite_variance',
        'sigma2','regularization','base_regularization','constellation',
        'support_delays','support_dopplers','outer_iter','mode'}
    for state in ce:
        if not required.issubset(state) or state['A'].shape[0]!=N or state['mu'].shape!=(N,):
            raise ValueError('CE observer state missing input, previous or solve')
        if state['A'].shape[1]!=len(state['g_previous']):
            raise ValueError('CE active design and previous gain differ')
        if any(not np.isfinite(a).all() for a in (state['A'],state['mu'],state['g_solution'])):
            raise ValueError('nonfinite CE observer state')
    if len(value['x_soft_history'])!=10 or len(value['resnorm_history'])!=10:
        raise ValueError('actual outer trajectory is incomplete')
    if not all(np.isfinite(a).all() for a in value['x_soft_history']):
        raise ValueError('nonfinite detector trajectory')


def score(value,raw,pilot):
    return physical.offline_score(value,raw,pilot)


def terminal_accounting(value,raw,pilot,snr):
    """Observed residual and its external truth-side additive components."""
    obs=observed(raw,pilot,snr)
    x=value['x_soft'];p=obs['pilot'];estimated=value['H'];truth=raw['H']
    residual=obs['y']-estimated@(p+x)
    components=dict(operator=(truth-estimated)@(p+x),
        symbol=truth@(raw['data']-x),noise=np.sqrt(float(obs['sigma2']))*raw['noise'])
    if not np.allclose(residual,sum(components.values()),atol=2e-11,rtol=2e-11):
        raise ValueError('terminal residual decomposition does not close')
    norm=lambda a:float(np.vdot(a,a).real)
    return dict(residual_sq=norm(residual),components_sq={k:norm(v) for k,v in components.items()},
        cross={a+'__'+b:float(2*np.vdot(components[a],components[b]).real)
               for a,b in (('operator','symbol'),('operator','noise'),('symbol','noise'))},
        denominator=norm(obs['y']),scope='offline scoring; truth never passed to receiver')


def gram_accounting(state):
    singular=np.linalg.svd(state['A'],compute_uv=False)
    if singular.size==0:
        raise ValueError('CE active design has no singular values')
    precision=np.float32 if state['A'].dtype==np.complex64 else np.float64
    rank=int(np.count_nonzero(singular>singular[0]*max(state['A'].shape)*np.finfo(precision).eps))
    condition=float((singular[0]/singular[-1])**2) if singular[-1]>0 else None
    return dict(active_columns=state['A'].shape[1],rank=rank,
        Gram_condition=condition,
        singular_min=float(singular[-1]),singular_max=float(singular[0]))


def _bound_contract(path:Path,expected_sha:str):
    if sha(path)!=expected_sha:
        raise ValueError('stage contract SHA differs')
    c=json.loads(path.read_text())
    reg=json.loads(REGISTERED.read_text())
    if c.get('schema')!='nsize-uwa-1024-stage-v1' or c.get('registration_sha256')!=sha(REGISTERED):
        raise ValueError('stage contract is not bound to frozen registration')
    stage=c.get('stage')
    blocks=reg['engineering_blocks'] if stage=='engineering' else list(range(2,16))
    if (stage not in ('engineering','development') or c.get('blocks')!=blocks
            or c.get('bounds')!={'A':len(blocks),'F':4*len(blocks),'seconds':7200}
            or c.get('output_bytes')!=20*1024**3 or c.get('threads')!=1
            or c.get('device')!='cpu'):
        raise ValueError('stage scope/budget differs from registration')
    if (not isinstance(c.get('tag'),str) or not c['tag']
            or Path(c['tag']).name!=c['tag'] or c['tag'] in ('.','..')):
        raise ValueError('single-component run tag required')
    if not Path(c['new_root']).resolve().is_relative_to(Path('/data/guoyikun').resolve()):
        raise ValueError('new experiment writes must stay under /data/guoyikun')
    helper_names={'physical_transfer_model_v1.py','physical_transfer_receiver_v1.py',
                  'uncoded-g1-v1.py'}
    if c.get('run_order_seed')!=reg['run_order_seed'] or set(c.get('helper_hashes',{}))!=helper_names:
        raise ValueError('run order/helper inventory differs')
    files={path:expected_sha,REGISTERED:sha(REGISTERED),Path(__file__):c['runner_sha256'],
        Path(c['source_manifest']):c['source_sha256'],Path(c['checkpoint_path']):c['checkpoint_sha256']}
    manifest=json.loads(Path(c['source_manifest']).read_text())
    if not isinstance(manifest,dict) or not manifest:
        raise ValueError('source manifest must bind isolated package files')
    package=Path(c['source_directory'])/'afdm_sp_joint_unrolled'
    if set(manifest)!={str(p.relative_to(package)) for p in package.rglob('*.py')}:
        raise ValueError('isolated receiver package inventory differs from manifest')
    for name,digest in manifest.items():
        if Path(name).is_absolute() or '..' in Path(name).parts or not name.endswith('.py'):
            raise ValueError('invalid source snapshot manifest entry')
        files[package/name]=digest
    for name,digest in c['helper_hashes'].items():
        files[Path(c['helper_directory'])/name]=digest
    for module,name in ((physical,'physical_transfer_model_v1.py'),
                        (old_adapter,'physical_transfer_receiver_v1.py'),
                        (old_adapter.base,'uncoded-g1-v1.py')):
        if Path(module.__file__).resolve()!=(Path(c['helper_directory'])/name).resolve():
            raise ValueError('loaded physical helper differs from bound helper source: '+name)
    import afdm_sp_joint_unrolled as package_module
    if Path(package_module.__file__).resolve().parent!=package.resolve():
        raise ValueError('loaded receiver package differs from bound source snapshot')
    for old_stage,binding in c['old_stages'].items():
        if old_stage not in ('engineering','development'):
            raise ValueError('unregistered old source stage')
        files[Path(binding['summary'])]=binding['sha256']
    if set(c['old_stages'])!={'engineering','development'}:
        raise ValueError('both immutable old source stages required')
    if stage=='development':
        files[Path(c['engineering_audit'])]=c['engineering_audit_sha256']
    guard=BoundFiles(files)
    guard.verify()
    return c,guard


def _old_inputs(c):
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    inputs={}
    for old_stage,binding in c['old_stages'].items():
        summary=json.loads(Path(binding['summary']).read_text())
        if summary.get('status')!='COMPLETE':
            raise ValueError('old physical-transfer summary is incomplete')
        old_root=Path(binding['root'])
        for entry in summary['records']:
            if entry['kind']!='A':
                continue
            block=entry['block']
            if block in inputs or block not in range(16):
                raise ValueError('old A channel duplicated/outside registered 16')
            record,raw=verified_record(entry,old_root)
            if record.get('domain')!='uwa' or record.get('physical_block')!=block:
                raise ValueError('old A provenance differs')
            physical.validate(raw,'uwa',block)
            inputs[block]=(entry,raw)
    if set(inputs)!=set(range(16)):
        raise ValueError('all 16 old physical A channels required')
    return inputs


def _entries(summary):
    entries={(e['kind'],e['block'],e['snr'],e['arm']):e for e in summary['records']}
    if len(entries)!=len(summary['records']):
        raise ValueError('duplicated saved new record identity')
    return entries


def engineering_gate(c):
    report=json.loads(Path(c['engineering_audit']).read_text())
    expected=dict(status='PASS',registration_sha256=sha(REGISTERED),
        runner_sha256=c['runner_sha256'],source_sha256=c['source_sha256'],
        checkpoint_sha256=c['checkpoint_sha256'],new_F=8,
        same_channel_operator_constructions=2)
    for name,value in expected.items():
        if report.get(name)!=value:
            raise ValueError('engineering raw gate differs: '+name)
    return report


def audit_saved(c,summary,root,old_inputs):
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    if summary.get('status')!='COMPLETE' or summary.get('calls')!={'A':len(c['blocks']),'F':4*len(c['blocks'])}:
        raise ValueError('producer incomplete or F/A budget differs')
    if summary.get('runner_sha256')!=c['runner_sha256'] or summary.get('contract_sha256')!=sha(Path(c['contract_path'])):
        raise ValueError('producer source/contract binding differs')
    entries=_entries(summary)
    if len(entries)!=5*len(c['blocks']):
        raise ValueError('saved record count differs')
    checks,rows,arrays=[],[],0
    total_cpu=summary.get('CPU_seconds_total')
    if total_cpu is None or not np.isfinite(total_cpu) or total_cpu<=0:
        raise ValueError('full stage CPU accounting missing')
    for block in c['blocks']:
        old_entry,old=old_inputs[block]
        ae=entries['A',block,10,'UWA_N1024_INPUT']
        arecord,raw=verified_record(ae,root)
        if arecord['old_A_sha256']!=old_entry['sha256']:
            raise ValueError('new A provenance differs from old source')
        checks.append(validate_input(raw,old,block))
        arrays+=finite_arrays(raw)
        for pilot in PILOTS:
            for snr in SNRS:
                key=('F',block,snr,pilot+'__OMP_BASE')
                e=entries[key]
                record,value=verified_record(e,root)
                obs=observed(raw,pilot,snr)
                if record['observed_hashes']!=hashes(obs) or record['input_record_sha256']!=ae['sha256']:
                    raise ValueError('observed input or A record binding differs')
                check_receiver(value)
                scores=score(value,raw,pilot)
                if scores!=record['scores'] or scores!=e['scores']:
                    raise ValueError('saved scores differ from raw recomputation')
                rows.append(dict(block=block,pilot=pilot,snr=snr,
                    seconds=e['seconds'],CPU_seconds=e['CPU_seconds'],scores=scores,
                    CE_states=len(value['CE']),active_atoms=len(value['delays']),
                    BP_iterations=sum(x['executed_iterations'] for x in value['bp_schedule']['calls']),
                    receiver_cpu_ms_bit=1000*e['CPU_seconds']/(2*N),
                    terminal_residual=terminal_accounting(value,raw,pilot,snr),
                    initial_feedback_Gram=gram_accounting(value['CE'][0]),
                    final_feedback_Gram=gram_accounting(value['CE'][-1])))
                arrays+=finite_arrays(value)
    return dict(rows=rows,input_checks=checks,arrays_audited=arrays,
        saved_records=len(entries),new_F=len(rows),coding_calls=0,
        same_channel_operator_constructions=len(c['blocks']),
        full_stage_CPU_seconds=total_cpu,
        full_stage_CPU_ms_bit=1000*total_cpu/(len(rows)*2*N))


def main(args):
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun
    from afdm_sp_joint_unrolled.supplement_adjacent_run import flatten
    cpu_started=time.process_time()
    stage_started=time.monotonic()
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
        if os.environ.get(name)!='1':
            raise ValueError('single-thread CPU environment required: '+name)
    contract=Path(args.contract).resolve()
    c,guard=_bound_contract(contract,args.contract_sha256)
    c['contract_path']=str(contract)
    if args.runner_sha256!=sha(Path(__file__)) or c['runner_sha256']!=args.runner_sha256:
        raise ValueError('runner source SHA differs')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    root=Path(c['new_root']).resolve()
    old_inputs=_old_inputs(c)
    if args.mode=='audit':
        exit_info=json.loads((root/'evidence'/(c['tag']+'-'+c['stage']+'-exit.json')).read_text())
        if exit_info.get('exit_code')!=0 or exit_info.get('timed_out'):
            raise ValueError('producer exit was not successful')
        summary_path=root/'runs'/c['tag']/c['stage']/'summary.json'
        summary=json.loads(summary_path.read_text())
        details=audit_saved(c,summary,root,old_inputs)
        if flatten(details,{})!=flatten(summary['raw_checks'],{}):
            raise ValueError('separate audit differs from producer checks')
        guard.verify()
        report=dict(status='PASS',**details,summary_sha256=sha(summary_path),
            contract_sha256=sha(contract),runner_sha256=sha(Path(__file__)),
            source_sha256=c['source_sha256'],checkpoint_sha256=c['checkpoint_sha256'],
            registration_sha256=sha(REGISTERED),
            scope='N1024 UWA uncoded development; old N256 terminal only; no CONF/COST',
            independence='saved-array readback; scientific review weak')
        target=root/'evidence'/(c['tag']+'-'+c['stage']+'-raw-audit.json')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream:json.dump(report,stream,indent=2)
        print(json.dumps({k:v for k,v in report.items() if k not in ('rows','input_checks')}),flush=True)
        return
    if c['stage']=='development':
        engineering_gate(c)
    remaining=7200-(time.monotonic()-stage_started)
    if remaining<=0:
        raise TimeoutError('stage setup exhausted registered two-hour budget')
    run_bounds=dict(c['bounds'],seconds=remaining)
    run=LightRun(root/'runs'/c['tag'],c['stage'],run_bounds,c['output_bytes'],guard)
    try:
        started=time.perf_counter()
        model,setup=old_adapter.build(c['checkpoint_path'],config())
        setup['seconds']=time.perf_counter()-started
        run.write('environment.json',dict(device='cpu',threads=1,lstsq_driver='gels',
            numpy=np.__version__,torch=torch.__version__,setup=setup,
            source_sha256=c['source_sha256'],checkpoint_sha256=c['checkpoint_sha256'],
            helper_hashes=c['helper_hashes'],runner_sha256=c['runner_sha256']))
        tasks=[(block,pilot,snr) for block in c['blocks'] for pilot in PILOTS for snr in SNRS]
        if c['stage']=='development':
            np.random.default_rng(c['run_order_seed']).shuffle(tasks)
        raw_by_block={}
        for block,pilot,snr in tasks:
            if block not in raw_by_block:
                old_entry,old=old_inputs[block]
                raw,_=run.call('A',dict(block=block,snr=10,arm='UWA_N1024_INPUT',split=1),
                    lambda:generate(old,block),lambda _: {},dict(old_A_sha256=old_entry['sha256']))
                validate_input(raw,old,block)
                raw_by_block[block]=(raw,run.records[-1])
            raw,ae=raw_by_block[block]
            obs=observed(raw,pilot,snr)
            before=hashes(obs)
            value,record=run.call('F',dict(block=block,snr=snr,arm=pilot+'__OMP_BASE',split=1),
                lambda:receive(model,obs),lambda v:score(v,raw,pilot),
                dict(observed_hashes=before,input_record_sha256=ae['sha256']))
            if hashes(obs)!=before:
                raise ValueError('receiver mutated observed input')
            print(json.dumps(dict(block=block,pilot=pilot,snr=snr,
                calls=run.counts,seconds=record['seconds'],scores=record['scores'])),flush=True)
        summary=dict(status='COMPLETE',calls=run.counts,records=run.records,
            runner_sha256=c['runner_sha256'],contract_sha256=sha(contract),
            source_sha256=c['source_sha256'],checkpoint_sha256=c['checkpoint_sha256'],
            helper_hashes=c['helper_hashes'],registration_sha256=sha(REGISTERED),
            stage=c['stage'],CPU_seconds_total=time.process_time()-cpu_started,
            CPU_scope='contract/source checks, old raw readback, model setup, N1024 operator, full receiver and archival I/O; producer audit excluded')
        summary['raw_checks']=audit_saved(c,summary,root,old_inputs)
        summary['wall_seconds']=time.monotonic()-stage_started
        if summary['wall_seconds']>=7200:
            raise TimeoutError('stage including producer raw checks exceeded two-hour budget')
        guard.verify()
        run.write('summary.json',summary)
        print(json.dumps(dict(status='COMPLETE',calls=run.counts,
            wall_seconds=summary['wall_seconds'])),flush=True)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=('run','audit'),required=True)
    p.add_argument('--contract',required=True)
    p.add_argument('--contract-sha256',required=True)
    p.add_argument('--runner-sha256',required=True)
    main(p.parse_args())
