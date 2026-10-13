"""Observed-only adapter over the existing receiver and terminal BP/LDPC chain."""
from __future__ import annotations

import math
import time
from pathlib import Path
import hashlib

import numpy as np
import torch

from afdm_sp_joint_unrolled.direction_data import (validate_code, validate_observed, source_manifest,
                                                  FROZEN_RECEIVER_DOMAIN)
from afdm_sp_joint_unrolled.e1_ldpc import demap_llr, decode_llr, decode_soft_messages, extract_info
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch
from afdm_sp_joint_unrolled.v3_initial import InitialEstimator
from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback

CHECKPOINT_HASH = '052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91'
REGISTERED_DATA_RHO = (0.25, 0.5, 0.75)


def data_constellation(rho):
    """QPSK at public operating rho; default campaign remains 0.5."""
    value = float(rho)
    if value not in REGISTERED_DATA_RHO or isinstance(rho, bool):
        raise ValueError('data rho outside registered operating points')
    return np.sqrt((1.0 - value) / 2.0) * np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j])


def _copy_state(value):
    """Detach snapshots at the observer boundary; no mutable model views escape."""
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().numpy().copy()
    if isinstance(value, np.ndarray):
        return value.copy()
    if isinstance(value, dict):
        return {k:_copy_state(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):
        return [_copy_state(v) for v in value]
    return value


def terminal_decode(y_data, H, sigma2, constellation, code, *, device='cpu', audit=False,
                    bp_temperature=None, bp_iterations=20, convergence_observer=None,
                    bp_noncircular=None, bp_pseudovariance_scale=1., cavity_observer=None,
                    detector=None, code_prior=None, bp_edge_projection=None,
                    edge_count_observer=None, bp_complete_nonzero=False,
                    decoder_observer=None):
    """Run the selected observed-data detector, channel LLRs, then common LDPC.

    This primitive accepts already-cancelled observed data; no true channel,
    symbols, codeword or error metrics are accepted. Sigma is a VARIANCE.
    Explicit BP code_prior selects finite posterior moments and channel-only
    LLRs. Its default terminal edge temperature stays 2, as on the legacy path.
    """
    y, h, c = np.asarray(y_data), np.asarray(H), np.asarray(constellation)
    if type(bp_complete_nonzero) is not bool:
        raise ValueError('bp_complete_nonzero must be boolean')
    if decoder_observer is not None and not callable(decoder_observer):
        raise ValueError('decoder_observer must be callable')
    if type(bp_iterations) is not int or bp_iterations < 1:
        raise ValueError('terminal BP iterations must be a positive integer')
    if (y.ndim != 1 or h.shape != (len(y),len(y)) or c.shape != (4,)
            or code['n'] != 2*len(y) or any(not np.isfinite(a).all() for a in (y,h,c))
            or not math.isfinite(float(sigma2)) or sigma2 <= 0):
        raise ValueError('invalid terminal chain inputs')
    amp = float(abs(c[0].real))
    expected = amp*np.array([1+1j,1-1j,-1+1j,-1-1j])
    if amp <= 0 or not np.allclose(c, expected, rtol=1e-12, atol=1e-12):
        raise ValueError('terminal chain requires the frozen QPSK order/amplitude')
    if detector not in (None, 'siso_mmse'):
        raise ValueError('unknown terminal detector')
    explicit_bp_prior = detector is None and code_prior is not None
    if explicit_bp_prior:
        prior = np.asarray(code_prior)
        if (prior.shape != (2*len(y),) or prior.dtype.kind not in 'fiu'
                or not np.isfinite(prior).all() or amp != .5
                or bp_noncircular is not None or bp_pseudovariance_scale != 1.
                or cavity_observer is not None or convergence_observer is not None):
            raise ValueError('explicit BP prior requires finite real QPSK prior and circular controls')
    finite_bp = bp_noncircular is not None or explicit_bp_prior
    graphs = []
    siso = None
    raw_llr = None
    messages=[];extra={}
    if detector == 'siso_mmse':
        if (torch.device(device).type != 'cpu' or bp_temperature is not None
                or bp_noncircular is not None or bp_pseudovariance_scale != 1.
                or convergence_observer is not None or cavity_observer is not None
                or bp_iterations != 20 or bp_edge_projection is not None
                or edge_count_observer is not None or bp_complete_nonzero):
            raise ValueError('SISO terminal cannot consume BP controls or run on CUDA')
        from .supplement_siso_mmse import siso_mmse
        prior = np.zeros(2*len(y)) if code_prior is None else np.asarray(code_prior)
        siso = siso_mmse(y, h, sigma2, prior, amplitude=amp)
        hard, mu, var = (siso[k] for k in ('hard', 'posterior_mean', 'posterior_variance'))
        raw_llr = siso['channel_llr']
        llr = np.clip(raw_llr, -20., 20.)
    else:
        if explicit_bp_prior:
            extra.update(code_prior=prior, message_observer=messages.append)
        if bp_noncircular is not None:
            if type(bp_noncircular) is not bool:raise ValueError('explicit finite BP control must be boolean')
            extra.update(code_prior=np.zeros(2*len(y)),message_observer=messages.append,
                noncircular=bp_noncircular,pseudovariance_scale=bp_pseudovariance_scale)
        if cavity_observer is not None:extra['cavity_observer']=cavity_observer
        if bp_edge_projection is not None:extra['edge_projection']=bp_edge_projection
        if edge_count_observer is not None:extra['edge_count_observer']=edge_count_observer
        hard, mu, var = mp_detect_bp_torch(y, h, sigma2, c, n_iter=bp_iterations,
            threshold=1e-4, complete_nonzero=bp_complete_nonzero, damp=.5, device=torch.device(device), return_numpy=True,
            message_temperature=(2. if finite_bp and bp_temperature is None else bp_temperature),
            convergence_observer=convergence_observer,
            return_soft=True, graph_observer=(lambda event:graphs.append(
                dict(stage='final_bp',outer_iter=None,**event))) if audit else None,**extra)
        if (not np.isfinite(mu).all() or not np.isfinite(var).all()
                or np.any(var < 0 if finite_bp else var <= 0)):
            raise FloatingPointError('invalid terminal BP statistics')
        if not finite_bp:
            llr = demap_llr(mu, var, amp, clip=20.)
        else:
            if len(messages)!=1:raise ValueError('terminal finite message was not captured')
            raw_llr=messages[0]['channel_llr'].cpu().numpy().copy()
            llr=np.clip(raw_llr,-20.,20.)
    if not np.isfinite(llr).all():
        raise FloatingPointError('nonfinite terminal LLR')
    decoder_started = time.perf_counter()
    if decoder_observer is None:
        decoded, ok = decode_llr(code, llr, maxiter=50)
        decoder_record = None
    else:
        decoder_record = decode_soft_messages(code, llr, maxiter=50)
        decoded, ok = decoder_record['decoded'], decoder_record['decode_ok']
    decoder_seconds = time.perf_counter()-decoder_started
    observer_seconds = None
    if decoder_record is not None:
        observer_started = time.perf_counter()
        decoder_observer(_copy_state(decoder_record))
        observer_seconds = time.perf_counter()-observer_started
    result={'mu':mu, 'var':var, 'llr':llr, 'decoded':decoded,
            'info_hat':extract_info(code,decoded), 'decode_ok':bool(ok),
            'x_hard':hard, 'graphs':graphs}
    if decoder_record is not None:
        result.update(decoder_seconds=decoder_seconds,
                      decoder_observer_seconds=observer_seconds)
    if siso is not None:
        result.update(raw_llr=raw_llr, terminal_siso={k: siso[k] for k in
            ('linear_solves', 'linear_rhs', 'factorization_dimension', 'linear_relative_residual')},
            llr_statistic='SISO channel extrinsic; terminal decoder excludes consumed check prior')
        if audit:
            result['terminal_siso_state'] = _copy_state(dict(siso, H=h, y=y, sigma2=float(sigma2), consumed_prior=prior))
    elif raw_llr is not None:
        result.update(raw_llr=raw_llr,finite_message=_copy_state(messages[0]),
            llr_statistic=('finite BP channel extrinsic; terminal decoder excludes consumed check prior'
                if explicit_bp_prior else 'finite constellation marginal; explicit zero code prior'))
    return result


class ObservedReceiver:
    def __init__(self, model, code, *, domain=None):
        validate_code(code, domain=domain)
        expected = FROZEN_RECEIVER_DOMAIN if domain is None else domain
        cfg = model.cfg
        if ((cfg.N,cfg.l_max,cfg.k_max,cfg.n_paths,cfg.n_outer_iter,cfg.pic_iter)
                != (expected.N,expected.l_max,expected.k_max,40,10,20) or cfg.early_stop
                or cfg.dtype != torch.complex64 or cfg.rdtype != torch.float32
                or cfg.mp_mode != 'bp' or not cfg.update_sigma2
                or not model.use_soft_decisions):
            raise ValueError('receiver differs from frozen direct40 campaign')
        data_constellation(cfg.rho)
        self.model, self.code = model, code
        self.device = torch.device(cfg.device)
        if self.device.type == 'cuda' and not torch.cuda.is_available():
            raise ValueError('requested CUDA unavailable; no CPU substitution')
        self.sources = source_manifest()

    @classmethod
    def build(cls, checkpoint, system, code, *, device='cuda'):
        if hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest() != CHECKPOINT_HASH:
            raise ValueError('checkpoint differs from frozen campaign')
        from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
        model = build_receiver(checkpoint, system, 1024, device,
                               receiver_shell='direct40', active_cap=40)
        return cls(model, code)

    def run(self, observed, *, family='b0', parameter=None, terminal_scale=1., audit=False, terminal_transform=None, channel_refit=None, code_feedback=None, bp_schedule=None,
            dals_mode='mean', dals_strength=1., outer_iteration_limit=None, ce_update_iterations=None, dals_start_iteration=1,ce_support_exchange=None,detector=None,bp_edge_projection=None,terminal_check_prior=None,outer_bp_graph=None,
                 terminal_bp_temperature=None,terminal_variance_source=None,dals_prior=None,one_shot_true_data_ce=None):
        return self._execute(observed,family=family,parameter=parameter,terminal_scale=terminal_scale,
            audit=audit,terminal_transform=terminal_transform,channel_refit=channel_refit,code_feedback=code_feedback,bp_schedule=bp_schedule,
            dals_mode=dals_mode,dals_strength=dals_strength,
            outer_iteration_limit=outer_iteration_limit,ce_update_iterations=ce_update_iterations,
                             dals_start_iteration=dals_start_iteration,ce_support_exchange=ce_support_exchange,detector=detector,bp_edge_projection=bp_edge_projection,terminal_check_prior=terminal_check_prior,outer_bp_graph=outer_bp_graph,
                             terminal_bp_temperature=terminal_bp_temperature,terminal_variance_source=terminal_variance_source,dals_prior=dals_prior,
                             one_shot_true_data_ce=one_shot_true_data_ce)

    def run_diagnostic(self, observed, *, diagnostic_code_symbols, family='b0', parameter=None,
                       terminal_scale=1., audit=False, channel_refit=None, bp_schedule=None):
        from .supplement_feedback_diagnostic import DiagnosticCodeSymbols
        if type(diagnostic_code_symbols) is not DiagnosticCodeSymbols or diagnostic_code_symbols.code is not self.code:
            raise ValueError('explicit diagnostic controller with the receiver code required')
        return self._execute(observed,family=family,parameter=parameter,terminal_scale=terminal_scale,
            audit=audit,channel_refit=channel_refit,diagnostic_code_symbols=diagnostic_code_symbols,bp_schedule=bp_schedule)

    def _execute(self, observed, *, family='b0', parameter=None, terminal_scale=1., audit=False,
                 terminal_transform=None, channel_refit=None, code_feedback=None, diagnostic_code_symbols=None, bp_schedule=None,
                 dals_mode='mean', dals_strength=1., outer_iteration_limit=None, ce_update_iterations=None, dals_start_iteration=1,ce_support_exchange=None,detector=None,bp_edge_projection=None,terminal_check_prior=None,outer_bp_graph=None,
                 terminal_bp_temperature=None,terminal_variance_source=None,dals_prior=None,one_shot_true_data_ce=None):
        cfg = self.model.cfg
        dictionary_width = 2*cfg.k_max+1
        if bp_edge_projection not in (None, 'qpsk_tanh') or (bp_edge_projection is not None and
                (detector is not None or cfg.rho != .5 or cfg.mp_mode != 'bp')):
            raise ValueError('QPSK projection requires the amplitude-.5 BP receiver')
        if detector not in (None, 'siso_mmse'):
            raise ValueError('unknown detector')
        if detector == 'siso_mmse' and (self.device.type != 'cpu' or bp_schedule is not None
                or code_feedback is None or not code_feedback.enabled or diagnostic_code_symbols is not None):
            raise ValueError('SISO chain requires CPU and active feedback without BP schedule')
        if code_feedback is not None:
            if (type(code_feedback) is not CodeFeedback or code_feedback.code is not self.code or
                    type(code_feedback.enabled) is not bool or
                    code_feedback.control not in ('legal','zero','fixed_sham')):
                raise ValueError('feedback requires legal CodeFeedback with the receiver code')
            if code_feedback.stop_on_valid_codeword and any(x is not None for x in
                    (terminal_transform, channel_refit, diagnostic_code_symbols, ce_support_exchange,
                     one_shot_true_data_ce)):
                raise ValueError('checkpoint stop cannot combine with terminal refit, transforms or diagnostics')
        if one_shot_true_data_ce is not None:
            from .one_shot_true_data_ce import OneShotTrueDataCE
            if (type(one_shot_true_data_ce) is not OneShotTrueDataCE or
                    code_feedback is None or not code_feedback.enabled or
                    diagnostic_code_symbols is not None or
                    terminal_transform is not None or channel_refit is not None):
                raise ValueError('one-shot true data CE requires isolated active feedback')
        if terminal_check_prior not in (None, 'retain'):
            raise ValueError('unknown terminal check-prior policy')
        if terminal_check_prior == 'retain' and (
                detector is not None or cfg.rho != .5 or cfg.mp_mode != 'bp'
                or code_feedback is None or not code_feedback.enabled
                or code_feedback.control != 'legal' or code_feedback.consumer != 'both'
                or code_feedback.diagnostic_perturbation is not None
                or any(x is not None for x in (terminal_transform, channel_refit,
                       diagnostic_code_symbols, ce_support_exchange))):
            raise ValueError('terminal retained prior requires legal both-consumer BP feedback')
        if terminal_bp_temperature is not None and (
                type(terminal_bp_temperature) not in (int, float) or terminal_bp_temperature not in (1., 2.)):
            raise ValueError('terminal BP temperature must be None, 1 or 2')
        if terminal_variance_source not in (None, 'physical'):
            raise ValueError('terminal variance source must be None or physical')
        explicit_terminal_controls = terminal_bp_temperature is not None or terminal_variance_source is not None
        if explicit_terminal_controls and terminal_check_prior != 'retain':
            raise ValueError('explicit terminal controls require qualified retained-prior BP')
        y, pilot, sigma2, const = validate_observed(observed, cfg.N)
        if terminal_scale not in (.5,1.) or isinstance(terminal_scale,bool):
            raise ValueError('terminal scale outside frozen design recipes')
        if type(audit) is not bool:
            raise ValueError('audit must be boolean')
        expected = data_constellation(cfg.rho)
        if not np.allclose(const,expected,rtol=1e-12,atol=1e-12):
            raise ValueError('constellation differs from frozen data power/order')
        if (family, parameter) not in (('b0',None),('size',1.),('ridge',.01),('sbl',.001)):
            raise ValueError('initial estimator parameter outside the eight frozen recipes')
        if terminal_transform is not None and not callable(terminal_transform):
            raise ValueError('terminal_transform must be callable')
        if channel_refit is not None and not callable(channel_refit):
            raise ValueError('channel_refit must be callable')
        if channel_refit is not None and terminal_transform is not None:
            raise ValueError('M refit and cancellation transform are separate frozen routes')
        estimator = InitialEstimator(family,parameter)
        # Tensors are copied so neither the generator's arrays nor other arms mutate.
        setup_started = time.perf_counter()
        yt = torch.tensor(y,dtype=cfg.dtype,device=self.device)
        pt = torch.tensor(pilot,dtype=cfg.dtype,device=self.device)
        nt = torch.tensor(sigma2,dtype=cfg.rdtype,device=self.device)
        ct = torch.tensor(const,dtype=cfg.dtype,device=self.device)
        if self.device.type == 'cuda':
            torch.cuda.synchronize(self.device)
        transfer_seconds = time.perf_counter()-setup_started
        graphs, supports, dals = [], [], []
        kwargs = {'enable_support_repair':False,'receiver_extension':0,
                  'active_support_cap':40,'initial_estimator':estimator}
        if dals_prior is not None:kwargs['dals_prior']=dals_prior
        if isinstance(dals_strength,bool) or dals_mode != 'mean' or dals_strength != 1.:
            kwargs.update(dals_mode=dals_mode,dals_strength=dals_strength)
        if outer_iteration_limit is not None:kwargs['outer_iteration_limit']=outer_iteration_limit
        if ce_update_iterations is not None:kwargs['ce_update_iterations']=ce_update_iterations
        if type(dals_start_iteration) is not int or dals_start_iteration != 1:
            kwargs['dals_start_iteration']=dals_start_iteration
        if ce_support_exchange is not None:kwargs['ce_support_exchange']=ce_support_exchange
        if detector is not None:
            kwargs.update(detector=detector,retain_siso_states=audit)
        if bp_edge_projection is not None:kwargs['bp_edge_projection']=bp_edge_projection
        if outer_bp_graph is not None:kwargs['outer_bp_graph']=outer_bp_graph
        if bp_schedule is not None:
            kwargs['bp_schedule'] = bp_schedule
        if diagnostic_code_symbols is not None:
            kwargs['diagnostic_code_symbols'] = diagnostic_code_symbols
        if one_shot_true_data_ce is not None:
            kwargs['one_shot_true_data_ce'] = one_shot_true_data_ce
        if code_feedback is not None:
            kwargs['code_feedback'] = code_feedback
        if audit:
            def support_observer(raw, selected, dl, dk):
                supports.append({'raw':list(raw),'selected':list(selected),
                                 'expanded_atom_ids':(dl*dictionary_width+dk+cfg.k_max).detach().cpu().tolist()})
            kwargs.update(diagnostic_support_observer=support_observer,
                          diagnostic_graph_observer=lambda state:graphs.append(_copy_state(state)),
                          diagnostic_dals_observer=lambda state:dals.append(_copy_state(state)))
        started = time.perf_counter()
        with torch.no_grad():
            output = self.model(yt,pt,nt,ct,**kwargs)
        H = output['H_est'].detach().cpu().numpy().copy()
        x_soft = output['x_soft'].detach().cpu().numpy().copy()
        sigma_final = float(output['sigma2_final'].detach().cpu())
        if not np.isfinite(H).all() or not np.isfinite(x_soft).all() or not math.isfinite(sigma_final) or sigma_final<=0:
            raise FloatingPointError('invalid receiver terminal state')
        # Physical noise is the original observation variance, without recipe scaling.
        sigma_terminal = sigma2 if terminal_variance_source == 'physical' else sigma_final*terminal_scale
        support = (output['support_delays']*dictionary_width+output['support_dopplers']+cfg.k_max).detach().cpu().tolist()
        if len(support)>40 or len(set(support)) != len(support):
            raise AssertionError('committed receiver capacity violation')
        gains = output['gains'].detach().cpu().numpy().copy()
        refitted = None
        if channel_refit is not None:
            before_H, before_gains = H.copy(), gains.copy()
            update = channel_refit(y=y.copy(), pilot=pilot.copy(), H=H.copy(),
                x_soft=x_soft.copy(), support=list(support), gains=gains.copy(),
                sigma_base=sigma_terminal)
            if not isinstance(update,dict) or set(update)!={'H','gains','diagnostics'}:
                raise ValueError('invalid channel refit return schema')
            next_H, next_gains = np.asarray(update['H']), np.asarray(update['gains'])
            if (next_H.shape!=H.shape or next_gains.shape!=(len(support),)
                    or not np.isfinite(next_H).all() or not np.isfinite(next_gains).all()
                    or not isinstance(update['diagnostics'],dict)):
                raise ValueError('invalid channel refit shapes/finite values/diagnostics')
            H, gains = next_H.copy(), next_gains.copy()
            refitted = dict(diagnostics=update['diagnostics'], H_before=before_H,
                            gains_before=before_gains)
        transformed = None
        sigma_base = sigma_terminal
        checkpoint_stop = output.get('checkpoint_stop')
        z_terminal, H_terminal = (y-H@pilot if checkpoint_stop is None else None), H
        if terminal_transform is not None:
            transformed = terminal_transform(y=y.copy(), pilot=pilot.copy(), H=H.copy(),
                x_soft=x_soft.copy(), support=list(support), sigma_base=sigma_base)
            if not isinstance(transformed,dict) or set(transformed)!={'z','H','sigma_out','diagnostics','B'}:
                raise ValueError('invalid terminal transform return schema')
            z_terminal, H_terminal = transformed['z'], transformed['H']
            sigma_terminal = transformed['sigma_out']
        terminal_options = {} if detector is None or checkpoint_stop is not None else dict(
            detector=detector, code_prior=code_feedback.prior.detach().cpu().numpy())
        terminal_edge_counts = []
        if bp_schedule is not None and checkpoint_stop is None:
            terminal_options['edge_count_observer'] = terminal_edge_counts.append
        if terminal_check_prior == 'retain' and checkpoint_stop is None:
            terminal_options['code_prior'] = code_feedback.prior.detach().cpu().numpy()
        if bp_edge_projection is not None:terminal_options['bp_edge_projection']=bp_edge_projection
        if terminal_bp_temperature is not None:
            terminal_options['bp_temperature'] = terminal_bp_temperature
        if checkpoint_stop is None:
            terminal = terminal_decode(z_terminal,H_terminal,sigma_terminal,const,self.code,
                                       device=self.device,audit=audit,**terminal_options)
        else:
            stop = _copy_state(checkpoint_stop)
            llr, decoded = stop['decoder_input'], stop['decoded']
            if (not stop['decode_ok'] or stop['unsatisfied_checks'] != 0 or
                    llr.shape != (self.code['n'],) or decoded.shape != llr.shape or
                    not np.isfinite(llr).all()):
                raise ValueError('invalid completed checkpoint decoder')
            n = len(y)
            hard_indices = 2*(llr[:n] < 0).astype(int)+(llr[n:] < 0).astype(int)
            terminal = dict(mu=stop['posterior_mean'], var=stop['posterior_variance'],
                llr=llr, decoded=decoded, info_hat=extract_info(self.code, decoded),
                decode_ok=True, x_hard=const[hard_indices], graphs=[],
                decode_source='checkpoint', terminal_executed=False,
                llr_statistic=stop['llr_statistic'], checkpoint_stop=stop)
            sigma_terminal = None  # No terminal detector consumed a noise variance.
        if self.device.type == 'cuda':
            torch.cuda.synchronize(self.device)
        elapsed = time.perf_counter()-started
        terminal_graphs = terminal.pop('graphs')
        result = dict(terminal, H=H, sigma2=sigma_final, sigma2_terminal=sigma_terminal,
                    terminal_scale=terminal_scale, x_soft=x_soft, support=support,
                    gains=gains,
                    graphs=graphs+terminal_graphs, dals=dals, support_trace=supports,
                    capacity_trace=_copy_state(output['capacity_trace']),
                    initial_estimator=_copy_state(estimator.record), seconds=elapsed,
                    transfer_seconds=transfer_seconds, inclusive_seconds=elapsed+transfer_seconds,
                    timing_scope='device-ready y through terminal BP, LLR and LDPC; audit copies included when enabled',
                    source_sha256=dict(self.sources))

        if explicit_terminal_controls:
            result.update(terminal_bp_temperature=terminal_bp_temperature,
                          terminal_variance_source=terminal_variance_source,
                          terminal_controls_consumed=checkpoint_stop is None,
                          terminal_scale_applied=checkpoint_stop is None and terminal_variance_source is None)
        if terminal_check_prior is not None:
            result.update(terminal_check_prior=terminal_check_prior,
                          terminal_check_prior_consumed=checkpoint_stop is None)
        if bp_edge_projection is not None:result['bp_edge_projection']=bp_edge_projection
        if outer_bp_graph is not None:
            result.update(outer_bp_graph=outer_bp_graph, integer_graph_calls=_copy_state(output['integer_graph_calls']))
        if code_feedback is not None and code_feedback.stop_on_valid_codeword:
            result.update(terminal_executed=checkpoint_stop is None,
                decode_source='terminal' if checkpoint_stop is None else 'checkpoint',
                completed_outer_detections=output['completed_outer_detections'],
                x_soft_stage=output['x_soft_stage'])
        if detector == 'siso_mmse':
            result['detector'] = detector
            result['siso_calls'] = _copy_state(output['siso_calls'])
            if audit:
                result['siso_states'] = _copy_state(output['siso_states'])
            result['timing_scope'] = 'device-ready y through exact SISO, channel LLR and LDPC; residual checks and audit included'
        if checkpoint_stop is not None:
            result['timing_scope'] = 'device-ready y through successful checkpoint LDPC; no terminal detector or decoder'
        if bp_schedule is not None:
            if len(terminal_edge_counts) != int(checkpoint_stop is None):
                raise RuntimeError('terminal BP edge counter missing or duplicated')
            terminal_edges = terminal_edge_counts[0] if terminal_edge_counts else 0
            result['bp_schedule'] = dict(_copy_state(output['bp_schedule']),
                final_bp_iterations=20 if checkpoint_stop is None else 0,
                final_bp_edges=terminal_edges,
                final_executed_bp_iterations=20 if terminal_edges else 0,
                final_ldpc_maxiter=50 if checkpoint_stop is None else 0)
        if 'support_exchange' in output:result['support_exchange']=_copy_state(output['support_exchange'])
        if 'iteration_schedule' in output:result['iteration_schedule']=_copy_state(output['iteration_schedule'])
        if dals_mode != 'mean' or dals_strength != 1.:
            result['dals_objective'] = dict(mode=dals_mode,normalized_strength=dals_strength,start_iteration=dals_start_iteration,
                scale='squared Frobenius energy of current A divided by number of columns')
        if code_feedback is not None:
            result['code_feedback_records'] = _copy_state(code_feedback.records) if code_feedback.enabled else []
            if code_feedback.diagnostic_perturbation is not None:
                result.update(deployment_eligible=False,
                    diagnostic_prior_perturbation=dict(code_feedback.diagnostic_perturbation),
                    truth_access_level='observed_only_prior_perturbation')
        if diagnostic_code_symbols is not None:
            result.update(truth_access_level='true_symbols_oracle',diagnostic_arm=diagnostic_code_symbols.tag,
                diagnostic_consumption_records=_copy_state(diagnostic_code_symbols.records),
                code_feedback_records=_copy_state(diagnostic_code_symbols.feedback.records)
                    if diagnostic_code_symbols.feedback is not None else [])
        if one_shot_true_data_ce is not None:
            result.update(truth_access_level='true_data_ce_only',
                          deployment_eligible=False,
                          one_shot_true_data_ce_records=_copy_state(one_shot_true_data_ce.records))
        if refitted is not None:
            result['channel_refit'] = refitted
        if transformed is not None:
            result['cancellation_transform'] = transformed
            result['sigma2_terminal_base'] = sigma_base
        return result
