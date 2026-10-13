"""One observed-only fixed-capacity exchange at a code-conditioned CE step."""
import torch
from .classical_joint_unrolled import construct_sensing_matrix_torch, soft_gain_update


def _fit(a, y, previous, regularization, gamma):
    q=gamma.to(a.dtype)*torch.eye(a.shape[1],dtype=a.dtype,device=a.device)
    return soft_gain_update(a,y,previous,regularization,Q=q)


def _objective(a, y, gains, previous, regularization, gamma, dropped_energy=0.):
    return ((y-a@gains).abs().square().sum()+gamma*gains.abs().square().sum()
            +regularization*((gains-previous).abs().square().sum()+dropped_energy))


def select_exchange(a, pilot_a, y, support, previous, variance, regularization,
                    *, nomination='code', candidate_count=8):
    """Evaluate every add/drop in the nominated pool using a common objective.

    Gamma is scalar only for the collision-free geometry checked by the caller.
    The old gain vector lives on the original full-domain coordinates throughout.
    """
    n,q=a.shape;k=len(support)
    if (nomination not in ('code','pilot') or type(candidate_count) is not int or candidate_count<1
            or not 0<k<q or len(set(support))!=k or any(type(i) is not int or not 0<=i<q for i in support)
            or pilot_a.shape!=a.shape or y.shape!=(n,) or previous.shape!=(k,) or variance.shape!=(n,)
            or not a.is_complex() or any(x.dtype!=a.dtype or x.device!=a.device for x in (pilot_a,y,previous))
            or variance.device!=a.device or variance.is_complex() or (variance<0).any()
            or regularization.numel()!=1 or regularization<=0
            or any(not torch.isfinite(x).all() for x in (a,pilot_a,y,previous,variance,regularization))):
        raise ValueError('invalid observed exchange objective/domain')
    gamma=variance.sum();nom_a=a if nomination=='code' else pilot_a
    nom_gamma=gamma if nomination=='code' else gamma.new_zeros(())
    current=nom_a[:,support]
    nominal_g=_fit(current,y,previous,regularization,nom_gamma)
    matrix=current.conj().T@current+(nom_gamma+regularization).to(a.dtype)*torch.eye(k,dtype=a.dtype,device=a.device)
    cross=current.conj().T@nom_a
    projected=torch.linalg.solve(matrix,cross)
    denominator=nom_a.abs().square().sum(0)+nom_gamma+regularization-(cross.conj()*projected).sum(0).real
    inactive=[i for i in range(q) if i not in set(support)]
    if not torch.isfinite(denominator[inactive]).all() or (denominator[inactive]<=0).any():
        raise FloatingPointError('nonpositive regularized addition Schur complement')
    correlation=nom_a.conj().T@(y-current@nominal_g)
    scores=correlation[inactive].abs().square()/denominator[inactive]
    if not torch.isfinite(scores).all():raise FloatingPointError('nonfinite nomination statistic')
    order=sorted(range(len(inactive)),key=lambda i:(-float(scores[i]),inactive[i]))
    candidates=[inactive[i] for i in order[:candidate_count]]
    baseline_g=_fit(a[:,support],y,previous,regularization,gamma)
    baseline_j=_objective(a[:,support],y,baseline_g,previous,regularization,gamma)
    actions=[];gains=[];objectives=[]
    for add in candidates:
        for drop_position in range(k):
            ids=list(support);dropped=ids[drop_position];ids[drop_position]=add
            mapped=previous.clone();mapped[drop_position]=0
            solution=_fit(a[:,ids],y,mapped,regularization,gamma)
            objective=_objective(a[:,ids],y,solution,mapped,regularization,gamma,previous[drop_position].abs().square())
            actions.append((add,dropped,drop_position));gains.append(solution);objectives.append(objective)
    objectives=torch.stack(objectives);solutions=torch.stack(gains)
    if not torch.isfinite(objectives).all() or not torch.isfinite(solutions).all():
        raise FloatingPointError('nonfinite complete exchange solution')
    best=int(objectives.argmin());tolerance=64*torch.finfo(a.real.dtype).eps*max(1.,abs(float(baseline_j)))
    accepted=bool(objectives[best]<baseline_j-tolerance)
    selected=list(support);mapped=previous.clone()
    if accepted:
        add,_,position=actions[best];selected[position]=add;mapped[position]=0
    return dict(support_before=list(support),selected_ids=selected,mapped_previous=mapped,
        previous=previous.clone(),baseline_gains=baseline_g,baseline_objective=baseline_j,
        inactive_ids=inactive,nomination_scores=scores,nomination_denominator=denominator[inactive],
        nomination_gains=nominal_g,candidate_ids=candidates,actions=actions,action_gains=solutions,
        action_objectives=objectives,best_index=best,accepted=accepted,tolerance=tolerance,
        selected_objective=objectives[best] if accepted else baseline_j,
        selected_gains=solutions[best] if accepted else baseline_g,
        solve_counts=dict(nomination_fit=1,nomination_schur=1,current_refit=1,exchange_refits=len(actions)))


def prune_support_memory(h, support, k_max):
    """Keep only registered integer displacements, including soft-masked memory."""
    n=h.shape[0]
    if h.shape!=(n,n) or len(set((i-k_max)%n for i in support))!=len(support):
        raise ValueError('exchange memory requires unique integer displacements')
    columns=torch.arange(n,device=h.device);mask=torch.zeros((n,n),dtype=torch.bool,device=h.device)
    for atom in support:mask[(columns+atom-k_max)%n,columns]=True
    return torch.where(mask,h,torch.zeros_like(h))


class CodeSupportExchange:
    def __init__(self, *, iteration=2, nomination='code', candidate_count=8, retain_states=False):
        if (type(iteration) is not int or iteration<1 or nomination not in ('code','pilot')
                or type(candidate_count) is not int or candidate_count<1 or type(retain_states) is not bool):
            raise ValueError('invalid discrete support exchange configuration')
        self.iteration=iteration;self.nomination=nomination;self.candidate_count=candidate_count
        self.retain_states=retain_states;self.record=None

    def begin(self, cfg, ce_iterations, start_iteration):
        if ((cfg.l_max+1)*(2*cfg.k_max+1)>cfg.N or self.iteration not in ce_iterations
                or self.iteration<start_iteration):
            raise ValueError('exchange needs collision-free integer domain and an active JSOFT CE')
        self.record=None

    def apply(self, cfg, y, pilot, mean, variance, delays, dopplers, previous, regularization):
        if self.record is not None:raise RuntimeError('only one support exchange per receiver call')
        k=2*cfg.k_max+1;support=(delays*k+dopplers+cfg.k_max).tolist()
        a=construct_sensing_matrix_torch(cfg.N,pilot+mean,cfg.c1,cfg.c2,cfg.l_max,cfg.k_max,cdtype=y.dtype)
        pilot_a=construct_sensing_matrix_torch(cfg.N,pilot,cfg.c1,cfg.c2,cfg.l_max,cfg.k_max,cdtype=y.dtype)
        selected=select_exchange(a,pilot_a,y,support,previous,variance,regularization,
                                 nomination=self.nomination,candidate_count=self.candidate_count)
        self.record=dict(selected,iteration=self.iteration,nomination=self.nomination,
            mean=mean.detach().clone(),variance=variance.detach().clone(),regularization=regularization.detach().clone(),
            truth_access='none',objective='expected squared residual + zero-centered Gamma + full-coordinate proximal')
        ids=torch.tensor(selected['selected_ids'],dtype=torch.long,device=y.device)
        return ids//k,ids%k-cfg.k_max,selected['mapped_previous']

    def prune_memory(self, h, k_max):
        pruned=prune_support_memory(h,self.record['selected_ids'],k_max) if self.record['accepted'] else h
        if self.retain_states:self.record['pruned_memory']=pruned.detach().clone()
        return pruned

    def consume(self, h, gains, gamma_h, tau_h_factor, tau_h_sigma_factor, sigma2):
        self.record['consumed_gains']=gains.detach().clone()
        self.record['damping']=dict(gamma_h=float(gamma_h.real),tau_h_factor=float(tau_h_factor),
            tau_h_sigma_factor=float(tau_h_sigma_factor),sigma2=float(sigma2))
        if self.retain_states:self.record['consumed_H']=h.detach().clone()
