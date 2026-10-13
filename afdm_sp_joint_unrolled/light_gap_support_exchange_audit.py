"""Independent NumPy replay of complete integer actions and their BP consumer."""
import numpy as np


def dictionary(n, x, c1, c2, q=515, k_max=2):
    ids=np.arange(q);dl=ids//(2*k_max+1);dk=ids%(2*k_max+1)-k_max
    cols=np.arange(n)[:,None];rows=(cols+(2*k_max+1)*dl[None,:]+dk[None,:])%n
    phase=np.exp(2j*np.pi*(-c1*dl[None,:]**2+c2*(rows**2-cols**2)-cols*dl[None,:]/n))
    result=np.empty((n,q),complex);result[rows,np.arange(q)[None,:]]=phase*x[:,None]
    return result,rows,phase


def check_exchange(value, observed, params, arm):
    config=arm.get('support_exchange')
    if config is None:
        if 'support_exchange' in value:raise ValueError('unregistered support transaction')
        return None
    r=value['support_exchange'];iteration=config['iteration']
    states={s['outer_iter']:s for s in value['dals']};ce=states[iteration]
    if r['iteration']!=iteration or r['nomination']!=config['nomination'] or r['truth_access']!='none':
        raise ValueError('exchange configuration/provenance differs')
    ids=list(r['support_before']);k=len(ids);n=len(observed['y']);q=515
    selected=list(r['selected_ids']);previous=r['previous'].astype(complex);lam=float(r['regularization'])
    np.testing.assert_array_equal(r['mean'],ce['mu']);np.testing.assert_array_equal(r['variance'],ce['finite_variance'])
    if selected!=value['support'] or selected!=(ce['support_delays']*5+ce['support_dopplers']+2).tolist():
        raise ValueError('selected IDs differ from CE/final support')
    if iteration-1 in states:
        preceding=states[iteration-1]
        if ids!=(preceding['support_delays']*5+preceding['support_dopplers']+2).tolist():raise ValueError('pre-exchange support changed')
        np.testing.assert_array_equal(r['previous'],preceding['g_solution'])
    a,rows,phase=dictionary(n,observed['pilot'].astype(np.complex64)+r['mean'],params['c1'],params['c2'])
    pilot,_,_=dictionary(n,observed['pilot'].astype(np.complex64),params['c1'],params['c2'])
    y=observed['y'].astype(np.complex64).astype(complex);gamma=float(r['variance'].sum())
    gram=a.conj().T@a;rhs=a.conj().T@y
    def fit(support,mapped):
        return np.linalg.solve(gram[np.ix_(support,support)]+(gamma+lam)*np.eye(k),rhs[support]+lam*mapped)
    def objective(support,g,mapped,dropped=0.):
        return float(np.linalg.norm(y-a[:,support]@g)**2+gamma*np.linalg.norm(g)**2+lam*(np.linalg.norm(g-mapped)**2+dropped))
    baseline=fit(ids,previous);baseline_j=objective(ids,baseline,previous)
    np.testing.assert_allclose(r['baseline_gains'],baseline,rtol=2e-5,atol=1e-6)
    np.testing.assert_allclose(r['baseline_objective'],baseline_j,rtol=8e-6,atol=1e-5)
    nomination=a if config['nomination']=='code' else pilot;ngamma=gamma if config['nomination']=='code' else 0.
    active=nomination[:,ids];matrix=active.conj().T@active+(lam+ngamma)*np.eye(k)
    fit_nom=np.linalg.solve(matrix,active.conj().T@y+lam*previous);cross=active.conj().T@nomination
    denom=np.sum(abs(nomination)**2,axis=0)+lam+ngamma-np.sum(cross.conj()*np.linalg.solve(matrix,cross),axis=0).real
    inactive=[i for i in range(q) if i not in set(ids)]
    scores=abs(nomination.conj().T@(y-active@fit_nom))**2/denom
    if r['inactive_ids']!=inactive:raise ValueError('nomination domain mismatch')
    np.testing.assert_allclose(r['nomination_scores'],scores[inactive],rtol=3e-5,atol=1e-5)
    np.testing.assert_allclose(r['nomination_denominator'],denom[inactive],rtol=3e-5,atol=1e-5)
    order=sorted(range(len(inactive)),key=lambda i:(-float(r['nomination_scores'][i]),inactive[i]))
    candidates=[inactive[i] for i in order[:config['candidate_count']]]
    if candidates!=r['candidate_ids']:raise ValueError('candidate ranking mismatch')
    actions=[(add,drop,pos) for add in candidates for pos,drop in enumerate(ids)]
    if [tuple(x) for x in r['actions']]!=actions:raise ValueError('complete add/drop inventory differs')
    max_error=0.;all_objectives=[]
    for i,(add,drop,pos) in enumerate(actions):
        support=list(ids);support[pos]=add;mapped=previous.copy();mapped[pos]=0
        g=fit(support,mapped);obj=objective(support,g,mapped,abs(previous[pos])**2)
        np.testing.assert_allclose(r['action_gains'][i],g,rtol=3e-5,atol=1e-6)
        np.testing.assert_allclose(r['action_objectives'][i],obj,rtol=8e-6,atol=1e-5)
        max_error=max(max_error,abs(float(r['action_objectives'][i])-obj));all_objectives.append(obj)
    best=int(np.argmin(r['action_objectives']));tolerance=64*np.finfo(ce['A'].real.dtype).eps*max(1.,abs(float(r['baseline_objective'])))
    accepted=bool(r['action_objectives'][best]<r['baseline_objective']-tolerance)
    if best!=r['best_index'] or accepted!=r['accepted'] or tolerance!=r['tolerance']:raise ValueError('full action decision differs')
    expected=list(ids);mapped=previous.copy()
    if accepted:expected[actions[best][2]]=actions[best][0];mapped[actions[best][2]]=0
    if selected!=expected or len(set(selected))!=k:raise ValueError('committed action/capacity differs')
    np.testing.assert_array_equal(ce['g_previous'],mapped.astype(ce['g_previous'].dtype))
    np.testing.assert_array_equal(r['mapped_previous'],ce['g_previous'])
    np.testing.assert_array_equal(r['consumed_gains'],ce['g_solution'])
    np.testing.assert_allclose(r['selected_gains'],ce['g_solution'],rtol=3e-5,atol=1e-6)
    cols=np.arange(n);mask=np.zeros((n,n),bool)
    for atom in selected:mask[(cols+atom-2)%n,cols]=True
    expected_memory=np.where(mask,ce['H'],0) if accepted else ce['H']
    np.testing.assert_array_equal(r['pruned_memory'],expected_memory)
    h_new=np.zeros((n,n),complex)
    for j,atom in enumerate(selected):h_new[rows[:,atom],cols]+=phase[:,atom]*ce['g_solution'][j]
    d=r['damping'];memory=(1-d['gamma_h'])*expected_memory+d['gamma_h']*h_new
    tau=max(d['tau_h_factor']*np.max(abs(memory)),d['tau_h_sigma_factor']*np.sqrt(d['sigma2']))
    beta=.02*max(tau,1e-12);z=np.clip((abs(memory)-tau)/beta,-709,709)
    predicted=memory/(1+np.exp(-z))
    np.testing.assert_allclose(r['consumed_H'],predicted,rtol=3e-5,atol=1e-6)
    consumer=states[iteration+1]['H'] if iteration+1 in states else value['H']
    np.testing.assert_array_equal(r['consumed_H'],consumer)
    dropped=sorted(set(ids)-set(selected))
    for atom in dropped:np.testing.assert_array_equal(r['consumed_H'][(cols+atom-2)%n,cols],0)
    counts=dict(nomination_fit=1,nomination_schur=1,current_refit=1,exchange_refits=len(actions))
    if r['solve_counts']!=counts:raise ValueError('support solve inventory differs')
    return dict(iteration=iteration,accepted=accepted,nomination=config['nomination'],
        dropped=dropped,added=sorted(set(selected)-set(ids)),actions=len(actions),
        baseline_objective=baseline_j,selected_objective=all_objectives[best] if accepted else baseline_j,
        max_action_objective_error=max_error,additional_small_solves=sum(counts.values()),
        scope='all observed actions, full-coordinate proximal cost, exact removed-memory and actual BP H consumption')
