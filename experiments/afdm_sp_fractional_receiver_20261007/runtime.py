"""Frozen function loading, strict public receiver boundary and operation counts.

preload imports only. build_system is generator setup and must run in the
admitted callback. No checkpoint, model or LDPC code is constructed.
"""
from contextlib import contextmanager
import importlib
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np
import scipy.linalg

from . import continuous, data_step
from .continuous import count, raise_with_evidence

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT/'experiments/sp_afdm_frozen_20260920'
UP = FROZEN/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled'
F1 = ROOT/'experiments/cstate_necessity_stageA_20260928'
ARMS = ('f1_scalar', 'vb_point', 'vb_continuous')
COLLAPSED_ARMS = ('f1_scalar', 'vb_point', 'vb_local_point', 'vb_collapsed_point')


def diagnostic_tree(value):
    """Keep nonfinite failure metadata explicit; arrays retain their raw bytes."""
    if isinstance(value, continuous.DopplerFactor):
        return diagnostic_tree(value.record())
    if isinstance(value, dict):
        return {key: diagnostic_tree(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [diagnostic_tree(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return dict(nonfinite_scalar=repr(value))
    return value


def save_new(rt, path, payload, identity):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb'):
        pass
    return rt.evidence.save_artifact(path, diagnostic_tree(payload), identity)


@contextmanager
def observe_component_evidence(rt):
    """Capture unit-fixture counters and returned/failed numerical traces.

    Wrappers never alter numeric inputs/outputs or swallow errors. In particular
    failed quadrature levels and rejected MM proposals survive unittest handling.
    """
    evidence = dict(counters={}, counter_events=[], calls=[])
    originals = []
    original_count = continuous.count

    def counted(target, name, amount=1):
        original_count(evidence['counters'], name, amount)
        evidence['counter_events'].append(dict(name=name, amount=amount))
        return original_count(target, name, amount)

    def capture(owner, name):
        original = getattr(owner, name)

        def invoke(*args, **kwargs):
            entry = dict(operation=name, status='started')
            evidence['calls'].append(entry)
            try:
                result = original(*args, **kwargs)
            except Exception as error:
                entry.update(status='failed', error_type=type(error).__name__, error=str(error),
                             evidence=getattr(error, 'evidence', {}))
                raise
            entry.update(status='complete', result=result)
            return result

        originals.append((owner, name, original))
        setattr(owner, name, invoke)

    try:
        for owner in (continuous, data_step, rt.core):
            if owner.count is not original_count:
                raise RuntimeError('core counter alias drift')
            originals.append((owner, 'count', original_count))
            owner.count = counted
        capture(continuous.ContinuousIntegrator, '_integrate')
        capture(continuous.PointOptimizer, 'update')
        capture(data_step.DataStepper, 'step')
        capture(data_step.DataStepper, 'evaluate_objective')
        yield evidence
    finally:
        for owner, name, original in reversed(originals):
            setattr(owner, name, original)


def _load(name, path):
    path = Path(path).resolve()
    if name in sys.modules:
        if Path(sys.modules[name].__file__).resolve() != path:
            raise RuntimeError('module path collision: '+name)
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_imports(rt):
    for name, module in tuple(sys.modules.items()):
        if name == 'afdm_sp_joint_unrolled' or name.startswith('afdm_sp_joint_unrolled.'):
            paths = list(getattr(module, '__path__', []))
            if getattr(module, '__file__', None):
                paths.append(module.__file__)
            if not paths or any(not Path(path).resolve().is_relative_to(UP) for path in paths):
                raise RuntimeError('non-frozen upstream module: '+name)
        filename = getattr(module, '__file__', None)
        if filename and Path(filename).is_absolute():
            for canonical in (rt.physical, rt.messages):
                if Path(filename).resolve() == Path(canonical.__file__).resolve() and module is not canonical:
                    raise RuntimeError('duplicate physical/message module identity: '+name)
    if sys.modules['physical'] is not rt.physical or sys.modules['messages'] is not rt.messages:
        raise RuntimeError('frozen alias identity changed')


def preload():
    start = time.perf_counter()
    physical = importlib.import_module('experiments.sp_afdm_frozen_20260920.src.physical')
    messages = importlib.import_module('experiments.sp_afdm_frozen_20260920.src.messages')
    for name, module in (('physical', physical), ('messages', messages)):
        if name in sys.modules and sys.modules[name] is not module:
            raise RuntimeError('duplicate frozen alias: '+name)
        sys.modules[name] = module
    name = 'afdm_sp_joint_unrolled'
    if name not in sys.modules:
        spec = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
        module = importlib.util.module_from_spec(spec)
        module.__path__ = [str(UP)]
        sys.modules[name] = module
    rt = SimpleNamespace(physical=physical, messages=messages)
    verify_imports(rt)
    rt.f1 = _load('f1', F1/'f1.py')
    rt.keep = _load('keep_slots', F1/'keep_slots.py')
    rt.twofft = _load('twofft', ROOT/'experiments/sp_afdm_native_joint_20260921/src/twofft.py')
    rt.frames = importlib.import_module(name+'.budgeted_support_eval')
    rt.generator = importlib.import_module(name+'.loop9_cache_features')
    rt.g1 = importlib.import_module(name+'.supplement_g1')
    rt.ldpc = importlib.import_module(name+'.e1_ldpc')
    rt.torch = importlib.import_module('torch')
    rt.core = importlib.import_module('experiments.afdm_sp_fractional_receiver_20261007.receiver')
    rt.evidence = importlib.import_module('experiments.sp_afdm_frozen_20260920.src.evidence')
    # Force lazy function resolution, without evaluating a numeric fixture.
    _ = np.linalg.eigvalsh, np.fft.fft, np.savez_compressed, scipy.linalg.solve_triangular
    verify_imports(rt)
    rt.preload_seconds = time.perf_counter()-start
    return rt


def build_system(rt):
    system = rt.generator._make_config_a(1024, 2., 8, 10., 4.)
    if (system.N_total != 1024 or system.rho != .5 or system.l_max_cap != 102 or
            system.k_max_cap != 2 or not system.use_frac_doppler):
        raise ValueError('frozen generator configuration drift')
    expected = np.exp(-1j*np.pi*7*np.arange(1024)**2/1024)
    if not np.array_equal(system._zc_seq, expected):
        raise ValueError('root7 ZC differs')
    public = dict(n=1024, c1=float(system.c1), c2=float(system.c2), rho=.5, lmax=102)
    validate_public(public)
    return system, public


def validate_public(public):
    if set(public) != {'n', 'c1', 'c2', 'rho', 'lmax'}:
        raise ValueError('public receiver configuration whitelist violation')
    if (type(public['n']) is not int or public['n'] != 1024 or
            type(public['lmax']) is not int or public['lmax'] != 102 or public['rho'] != .5):
        raise ValueError('public N/rho/lmax differ from frozen protocol')
    for name in ('c1', 'c2', 'rho'):
        if not isinstance(public[name], (int, float)) or not np.isfinite(public[name]):
            raise ValueError('public configuration must contain only finite scalars')


def receive_arm(rt, observation, public, arm, *, quadrature='fixed'):
    validate_public(public)
    if quadrature not in ('fixed', 'adaptive'):
        raise ValueError('unregistered continuous quadrature variant')
    if arm not in ARMS+COLLAPSED_ARMS or set(observation) != {'y', 'pilot', 'sigma2'}:
        raise ValueError('receiver input whitelist or arm violation')
    if any(np.shape(observation[key]) != (1024,) for key in ('y', 'pilot')):
        raise ValueError('receiver observation dimensions')
    if (np.shape(observation['sigma2']) != () or float(observation['sigma2']) <= 0 or
            not all(np.isfinite(value).all() for value in observation.values())):
        raise ValueError('receiver input must be finite, with positive scalar noise')
    acquisition = None
    phase = 'F1'
    try:
        begin = time.perf_counter()
        initial = rt.f1.PhysicalF1(1024, public['c1'], public['c2'], 102).acquire(
            observation['y'], observation['pilot'], float(observation['sigma2']))
        acquisition_seconds = time.perf_counter()-begin
        acquisition = {key: value for key, value in initial.items() if key != 'channel'}
        slots = {key: np.asarray(initial[key]).copy() for key in ('delays', 'dopplers', 'gains')}
        phase = arm
        if arm == 'f1_scalar':
            channel, ce = rt.keep.time_refine_keep_slots(
                observation['y'], observation['pilot'], np.zeros(1024, complex), np.full(1024, .5),
                slots['delays'], slots['dopplers'], slots['gains'], public['c1'], public['c2'],
                float(observation['sigma2']), mode='soft', max_paths=8, rounds=2)
            detector = rt.twofft.scalar_joint(
                observation['y'], observation['pilot'], channel, float(observation['sigma2']),
                pd=.5, prior=np.zeros(2048), iterations=20, damping=.3, gain_mode='joint',
                record_states=True, observation_domain='time')
            llr = detector['app']
            backend = dict(ce=ce, detector=detector, delays=channel.delays,
                           dopplers=channel.dopplers, ce_gains=channel.gains)
        else:
            backend = rt.core.receive(observation, c1=public['c1'], c2=public['c2'],
                                      initial_slots=slots, mode=arm,
                                      quadrature=quadrature if arm == 'vb_continuous' else 'fixed')
            llr = backend['bit_llr']
        if np.shape(llr) != (2048,) or not np.isfinite(llr).all():
            raise FloatingPointError('invalid uncoded bit-marginal LLR')
        return dict(arm=arm, acquisition=acquisition, acquisition_seconds=acquisition_seconds,
                    backend=backend, bit_llr=np.asarray(llr),
                    hard_bits=(np.asarray(llr) < 0).astype(np.uint8), decoder_calls=0,
                    bit_order='all-I then all-Q; LLR<0 -> 1; zero tie -> 0')
    except Exception as error:
        raise_with_evidence(error, 'uncoded arm failed: ', dict(phase=phase, acquisition=acquisition))


@contextmanager
def observe_operations(rt, checkpoint=lambda: None):
    """Count actual primitive calls, including failed ones; restore every alias."""
    counts, originals = {}, []

    def patch(owner, name, wrapper):
        original = getattr(owner, name)
        originals.append((owner, name, original))
        setattr(owner, name, wrapper(original))

    def counted(name, shape=None):
        def decorate(original):
            def invoke(*args, **kwargs):
                checkpoint()
                count(counts, name+'_calls')
                if shape is not None:
                    shape(args, kwargs)
                result = original(*args, **kwargs)
                checkpoint()
                return result
            return invoke
        return decorate

    def fft_shape(args, kwargs):
        array = np.asarray(args[0])
        axis = kwargs.get('axis', args[2] if len(args) > 2 else -1)
        length = kwargs.get('n', args[1] if len(args) > 1 else None)
        length = array.shape[axis] if length is None else int(length)
        vectors = array.size//array.shape[axis]
        count(counts, f'fft_vectors_length_{length}', vectors)

    def solve_shape(args, kwargs):
        shape = np.shape(args[0])
        count(counts, f'solve_order_{shape[-1]}')

    try:
        for name in ('fft', 'ifft'):
            patch(np.fft, name, counted(name, fft_shape))
        for name in ('solve', 'cholesky', 'eigvalsh', 'cond'):
            patch(np.linalg, name, counted(name, solve_shape))
        original_triangular = scipy.linalg.solve_triangular
        wrapped_triangular = counted('solve_triangular', solve_shape)(original_triangular)
        for owner in (scipy.linalg, rt.core):
            if getattr(owner, 'solve_triangular') is not original_triangular:
                raise RuntimeError('triangular solve alias drift')
            originals.append((owner, 'solve_triangular', original_triangular))
            owner.solve_triangular = wrapped_triangular
        for name in ('apply', 'adjoint', 'regressors'):
            patch(rt.physical.Channel, name, counted('channel_'+name))
        for name in ('responses_time', 'adjoint_time'):
            patch(rt.twofft.TimePathOps, name, counted(name))
        for name in ('response', 'score', 'score_derivatives', 'refit'):
            patch(rt.f1, name, counted('f1_'+name))
        # Any accidental code construction/encoding/decoding is a fatal contract
        # error. Replace imported aliases as well as their defining module.
        forbidden = {getattr(rt.ldpc, name): name for name in
                     ('build_code', 'encode', 'decode_llr', 'decode_soft_messages')}
        for module in tuple(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if not filename or not Path(filename).is_absolute() or not Path(filename).resolve().is_relative_to(ROOT):
                continue
            for name, value in tuple(vars(module).items()):
                if callable(value) and any(value is function for function in forbidden):
                    operation = forbidden[value]

                    def reject(*args, _operation=operation, **kwargs):
                        count(counts, 'forbidden_'+_operation+'_calls')
                        raise RuntimeError('uncoded stage attempted LDPC operation: '+_operation)

                    originals.append((module, name, value))
                    setattr(module, name, reject)
        yield counts
    finally:
        for owner, name, original in reversed(originals):
            setattr(owner, name, original)
