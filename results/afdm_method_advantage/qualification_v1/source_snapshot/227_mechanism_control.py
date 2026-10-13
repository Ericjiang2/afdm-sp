"""Frozen reference pools and numeric priors for one complete F2P transaction."""
import torch

from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.classical_joint_unrolled import SupportProposalRejected
from afdm_sp_joint_unrolled.common_score import MODES, prepare_geometry_scores, prepare_common_scores
from afdm_sp_joint_unrolled.support_transaction import finalize_support_transaction


def tensor_hash(value):
    return array_hash(value.detach().cpu().numpy())


def aligned_logits(table, mode, device):
    return torch.tensor([row[mode] if row['eligible'] else float('-inf')
                         for row in table['candidates']], dtype=torch.float64, device=device)


@torch.no_grad()
def prepare_mechanism_reference(phi, y, support, noise, covariance, *, head,
                                lookup, l_max, k_max, nomination_cap, prior_reference):
    """Capture one declared old-statistics reference before any shuffled arms.

    The shared reference proposal is preparation, not an extra coded receiver
    observation. Both pools and actual pi/sh2 arrays survive arm state changes.
    """
    rounds, events = [], []
    head.set_refine_config(2, 96, True, min(2, nomination_cap))
    def capture(P, z, S, columns, sigma):
        table = prepare_geometry_scores(z, P, covariance, S, columns.tolist(),
            lookup=lookup, k_max=k_max, K_per_l=2*k_max+1, prior_reference=prior_reference)
        if not table['valid_current']:
            raise SupportProposalRejected(table['reason'])
        rounds.append(dict(support=list(S), candidate_ids=columns.tolist(),
            pi=[row['pi'] for row in table['candidates']],
            sh2=[row['sh2'] for row in table['candidates']], prior_hash=table['prior_hash']))
        return aligned_logits(table, 'legacy_stats_prior', columns.device)
    preparation_rejection = None
    try:
        head.apply_f2p_refinement(phi, y, list(support), noise, l_max, k_max, nomination_cap,
            score_override=capture, tau_override=float('-inf'), stable_selection=True,
            proposal_covariance=covariance, proposal_observer=events.append)
    except SupportProposalRejected as error:
        preparation_rejection = str(error)
    while len(rounds) < 2:
        rounds.append(dict(support=[], candidate_ids=[], pi=[], sh2=[], prior_hash=None))
    return dict(rounds=rounds, preparation_events=events, preparation_rejection=preparation_rejection, support=list(support),
        covariance=covariance.detach().clone(), hashes=dict(phi=tensor_hash(phi), y=tensor_hash(y),
        covariance=tensor_hash(covariance)), noise=float(noise), l_max=l_max, k_max=k_max,
        nomination_cap=nomination_cap, prior_reference=prior_reference,
        reference_policy='old-statistics prior, shared GLS rank mask, stable float64, two F2P rounds')


def make_mechanism_transaction(reference, *, head, mode, gate_enabled, protect_added=None,
                               diagnostic_keep=False):
    if mode not in MODES or type(gate_enabled) is not bool:
        raise ValueError('invalid mechanism mode')
    cap = reference['nomination_cap']
    protect = min(2, cap) if protect_added is None else protect_added
    if type(protect) is not int or protect < 0 or protect > cap:
        raise ValueError('invalid protected addition count')

    @torch.no_grad()
    def transaction(phi, y, raw, noise, k_max, extension, active_cap, capacity_observer):
        covariance = reference['covariance']
        if (raw != reference['support'] or float(noise) != reference['noise'] or
                k_max != reference['k_max'] or
                tensor_hash(phi) != reference['hashes']['phi'] or
                tensor_hash(y) != reference['hashes']['y'] or
                tensor_hash(covariance) != reference['hashes']['covariance']):
            raise ValueError('transaction differs from frozen common observation/model')
        tables, events = [], []
        if diagnostic_keep:
            result = finalize_support_transaction(y, phi, covariance, raw, None,
                k_max=k_max, extension=extension, active_cap=active_cap, gate_enabled=True)
            if result['valid_current']:
                result['reason'] = 'diagnostic_forced_keep'
            result.update(score_tables=[], proposal_events=[], frozen_candidate_ids=[],
                          mode='common_gls_keep', protect_added=0,
                          reference_hashes=dict(reference['hashes']))
            return result
        head.set_refine_config(2, 96, True, protect)
        pools = [list(r['candidate_ids']) for r in reference['rounds']]
        def score(P, z, S, columns, sigma):
            ref = reference['rounds'][len(tables)]
            positions = {i: j for j, i in enumerate(ref['candidate_ids'])}
            ids = columns.tolist()
            pi = [ref['pi'][positions[i]] for i in ids]
            sh2 = [ref['sh2'][positions[i]] for i in ids]
            table = prepare_common_scores(z, P, covariance, S, ids, pi=pi, sh2=sh2,
                                          prior_reference=reference['prior_reference'])
            if not table['valid_current']:
                raise SupportProposalRejected(table['reason'])
            table['reference_support'] = ref['support']
            table['state_relation'] = 'same' if list(S) == ref['support'] else 'diverged_support_frozen_prior'
            tables.append(table)
            return aligned_logits(table, mode, columns.device)
        rejection = None
        try:
            proposal, _ = head.apply_f2p_refinement(phi, y, list(raw), noise,
                reference['l_max'], k_max, cap, score_override=score,
                tau_override=float('-inf'), frozen_candidates=pools, stable_selection=True,
                proposal_covariance=covariance, proposal_observer=events.append,
                capacity_observer=capacity_observer)
        except SupportProposalRejected as error:
            rejection = str(error)
            proposal = None
        result = finalize_support_transaction(y, phi, covariance, raw, proposal,
            k_max=k_max, extension=extension, active_cap=active_cap, gate_enabled=gate_enabled)
        if rejection is not None and result['valid_current']:
            result.update(reason='reject_proposal_rank', proposal_failure=rejection,
                          complete_proposals_used=1, stop_reason='proposal_budget_exhausted')
        result.update(score_tables=tables, proposal_events=events,
                      frozen_candidate_ids=pools, mode=mode, protect_added=protect,
                      reference_hashes=dict(reference['hashes']))
        return result
    return transaction
