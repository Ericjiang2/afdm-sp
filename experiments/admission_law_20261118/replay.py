"""Summarize the frozen first structural exchange and apply the archived rule."""

from types import SimpleNamespace

import numpy as np


def modeled_gain(E, u, T, kappa, operator_coherence, h, gamma_mode):
    q = E * kappa
    if gamma_mode == 'full':
        q = q + u * operator_coherence
    return abs(T * kappa - q) ** 2 * abs(h) ** 2 / (T - abs(q) ** 2 / T)


def measured_gains(entering_objective, entering_h, inverse, scores):
    deletion_cost = abs(entering_h) ** 2 / inverse.diagonal().real
    return entering_objective + deletion_cost[:, None] - scores


def model_outputs(maxima, K):
    P, N, O = (maxima[name]['net_gain'] if maxima[name] is not None else -np.inf
               for name in ('P', 'N', 'O'))
    tau = 1e-8 * K
    competition = max(N, O, tau)
    predicted = 'P' if P > competition else 'N' if N > max(P, O, tau) else 'O'
    # Null represents -infinity for an empty maximum and its A2 margin.
    return dict(P_a=None if P == -np.inf else P, N_a=None if N == -np.inf else N,
                O_a=None if O == -np.inf else O, tau=tau, predicted_class=predicted,
                margin=float((P - competition) / K) if K > 0 and P != -np.inf else None)


def subset_checks(E, u, ridge, K_A2, K_A1c, phantom, novel):
    return dict(E_positive=bool(E > 0), u_positive=bool(u > 0),
                lambda_positive=bool(ridge > 0), K_A2_positive=bool(K_A2 > 0),
                K_A1c_positive=bool(K_A1c > 0), legal_P=phantom is not None,
                legal_N=novel is not None,
                one_surviving_anchor=phantom is not None and phantom['anchor_count'] == 1,
                D_ge_090=phantom is not None and phantom['abs_D'] >= .90,
                kappa_minus_D_le_005=phantom is not None and phantom['abs_kappa_minus_D'] <= .05,
                P_other_coherence_le_015=phantom is not None and phantom['other_coherence'] <= .15,
                N_entering_coherence_le_015=novel is not None and novel['entering_coherence'] <= .15)


def summarize(kernel, trace, Y, x, v, *, c1, c2, ridge, gamma_mode, **_):
    from physical import daft, dkernel

    E, u = float(np.vdot(x, x).real), float(v.sum())
    T = E + u + ridge
    entering = trace['entering_paths']
    F = [kernel.Path(**path) for path in entering]
    h = trace['entering_gains']
    h_power = abs(h) ** 2
    K = float(T * h_power.max())
    xt = daft(x, c1, c2, inverse=True)
    B, Q, b, _, _, _ = kernel._system(Y, xt, v, F, c1, c2, ridge, gamma_mode)
    inverse = kernel.state_from_normal(Q, b, float(np.vdot(Y, Y).real)).inverse
    gain = measured_gains(trace['entering_objective'], h, inverse, trace['scores'])

    delays = trace['candidate_delays']
    dopplers = trace['candidate_dopplers']
    valid = trace['valid']
    entering_delays = np.array([p.delay for p in F])
    occupied = np.isin(delays, entering_delays)
    # Only occupied-delay responses are needed for P and the winning N is
    # evaluated once below. The full measured score grid stays in memory.
    bank_on_support = np.flatnonzero(occupied)
    occupied_paths = [kernel.Path(int(delays[i]), float(dopplers[i])) for i in bank_on_support]
    B_occupied = kernel._responses(xt, occupied_paths, c1, c2)
    coherence = B.conj().T @ B_occupied / E if E > 0 else np.zeros((len(F), len(occupied_paths)), complex)
    maxima = dict.fromkeys(('P', 'N', 'O'))
    slots = []
    p_geometry = n_index = None
    for slot in range(len(F)):
        survivors = np.arange(len(F)) != slot
        phantom = np.isin(delays, entering_delays[survivors])
        deletion_proxy = T * h_power[slot]
        net_gain = gain[slot] - deletion_proxy
        row = dict(slot=slot, N=None, O=None, P=[])
        for name, mask in (('N', ~occupied), ('O', occupied & ~phantom)):
            indices = np.flatnonzero(valid[slot] & mask)
            if not len(indices):
                continue
            index = indices[np.argmax(net_gain[indices])]
            winner = dict(slot=slot, delay=int(delays[index]), doppler=float(dopplers[index]),
                          net_gain=float(net_gain[index]))
            row[name] = winner
            if maxima[name] is None or winner['net_gain'] > maxima[name]['net_gain']:
                maxima[name] = winner
                if name == 'N':
                    n_index = index

        for delay in np.unique(entering_delays[survivors]):
            anchors = np.flatnonzero(survivors & (entering_delays == delay))
            anchor = anchors[np.argmax(h_power[anchors])]
            indices = np.flatnonzero((delays[bank_on_support] == delay) & valid[slot, bank_on_support])
            if not len(indices):
                continue
            candidates = bank_on_support[indices]
            kappa = coherence[anchor, indices]
            D = dkernel(dopplers[candidates] - F[anchor].doppler, len(Y))
            predicted = modeled_gain(E, u, T, kappa, D, h[anchor], gamma_mode)
            for i, index in enumerate(candidates):
                row['P'].append(dict(delay=int(delay), doppler=float(dopplers[index]), anchor=int(anchor),
                                     kappa=[float(kappa[i].real), float(kappa[i].imag)],
                                     D=[float(D[i].real), float(D[i].imag)],
                                     modeled_gain=float(predicted[i]), measured_gain=float(gain[slot, index])))
            net_predicted = predicted - deletion_proxy
            best = int(np.argmax(net_predicted))
            index = candidates[best]
            winner = dict(slot=slot, delay=int(delay), doppler=float(dopplers[index]),
                          net_gain=float(net_predicted[best]))
            if maxima['P'] is None or winner['net_gain'] > maxima['P']['net_gain']:
                maxima['P'] = winner
                others = survivors.copy()
                others[anchor] = False
                p_geometry = dict(anchor_count=len(anchors), abs_D=float(abs(D[best])),
                                  abs_kappa_minus_D=float(abs(kappa[best] - D[best])),
                                  other_coherence=float(np.max(abs(coherence[others, indices[best]]), initial=0)))
        slots.append(row)

    n_geometry = None
    if n_index is not None:
        candidate = kernel.Path(int(delays[n_index]), float(dopplers[n_index]))
        response = kernel._responses(xt, [candidate], c1, c2)[:, 0]
        value = float(np.max(abs(B.conj().T @ response)) / E) if E > 0 else None
        # Coherence is undefined at E=0 and cannot pass the subset check.
        n_geometry = dict(entering_coherence=value) if value is not None else None
    result = model_outputs(maxima, K)
    margin = result.pop('margin')
    if gamma_mode == 'diag':
        result['m_A2'] = margin
    return dict(E=E, u=u, **{'lambda': ridge}, T=T, F=entering,
                h_tilde=[[float(z.real), float(z.imag)] for z in h], K_a=K,
                maxima=maxima, slots=slots, P_geometry=p_geometry, N_geometry=n_geometry, **result)


def scoring_truth(arms, traces, truth, n):
    from physical import dkernel

    true_delays = np.asarray(truth['l_i'])
    true_nus = np.asarray(truth['k_real'])
    true_power = abs(np.asarray(truth['g_i'])) ** 2
    trace = traces['A2']
    F = trace['entering_paths']
    occupied_delays = {p['delay'] for p in F}
    missing = set(true_delays) - occupied_delays

    for name, arm in arms.items():
        edit = traces[name]['accepted']
        observed = 'none'
        if edit is not None:
            incoming = edit['new']['delay']
            support = traces[name]['entering_paths']
            survivors = {p['delay'] for slot, p in enumerate(support) if slot != edit['slot']}
            observed = 'P' if incoming in survivors else 'N' if incoming in missing else 'O'
        arm['actual_first_edit'] = edit
        arm['actual_class'] = observed
        arm['predicted_N_is_true'] = (arm['maxima']['N']['delay'] in missing
                                      if arm['predicted_class'] == 'N' else None)

    def strongest(want_missing):
        indices = [i for i, delay in enumerate(true_delays) if (delay in missing) == want_missing]
        if not indices:
            return None
        i = max(indices, key=lambda k: true_power[k])
        return dict(delay=int(true_delays[i]), doppler=float(true_nus[i]), power=float(true_power[i]))

    weak, strong = strongest(True), strongest(False)
    window = dict(strongest_missing=weak, strongest_occupied=strong, r=None, R=None,
                  z=None, bounds=None, inside_W=None, comparison_pair=None)
    if weak is None or strong is None or strong['power'] == 0:
        return window
    r = weak['power'] / strong['power']
    window.update(r=r, R=strong['power'] / weak['power'] if weak['power'] else None)
    anchor = min((i for i, p in enumerate(F) if p['delay'] == strong['delay']),
                 key=lambda i: (abs(F[i]['doppler'] - strong['doppler']), i))
    anchor_nu = F[anchor]['doppler']
    delays, dopplers = trace['candidate_delays'], trace['candidate_dopplers']
    slots = np.arange(len(F)) != anchor
    legal = np.flatnonzero((delays == strong['delay']) & trace['valid'][slots].any(axis=0))
    if not len(legal):
        return window
    comparison = min(legal, key=lambda i: (abs(dopplers[i] - anchor_nu), dopplers[i]))
    z = float(abs(dkernel(dopplers[comparison] - anchor_nu, n)))
    E, u, ridge, T = (arms['A2'][key] for key in ('E', 'u', 'lambda', 'T'))
    lower = z ** 2 * ridge ** 2 / (T ** 2 - z ** 2 * (E + u) ** 2)
    upper = z ** 2 * (u + ridge) ** 2 / (T ** 2 - z ** 2 * E ** 2)
    sample_slot = int(np.flatnonzero(slots & trace['valid'][:, comparison])[0])
    window.update(z=z, bounds=[lower, upper], inside_W=lower < r < upper,
                  comparison_pair=dict(anchor=anchor, slot=sample_slot, delay=strong['delay'],
                                       doppler=float(dopplers[comparison])))
    return window


def summarize_unit(arms, traces, truth, n):
    a2, a1c = arms['A2'], arms['A1c']
    checks = subset_checks(a2['E'], a2['u'], a2['lambda'], a2['K_a'], a1c['K_a'],
                           a2['P_geometry'], a2['N_geometry'])
    for arm in arms.values():
        arm['abstains'] = not all(checks.values())
    return dict(arms=arms, subset_checks=checks, subset_pass=all(checks.values()),
                truth=scoring_truth(arms, traces, truth, n))


def first_exchange(kernel, Y, x, v, paths, **opts):
    opts = dict(opts, max_edits=1, local_passes=0)
    result = kernel.reopen_geometry(Y, x, v, paths, **opts)
    trace = result.global_trace[0]
    return summarize(kernel, trace, Y, x, v, **opts), trace


def first_exchange_from_f0(study, obs, arrays, truth):
    # Match the input preparation and exchange options in E-1 run_branch.
    from messages import moments
    from physical import daft

    q, ctx, _, full, closed, _ = study
    system = ctx.system
    mu, v, _ = moments(np.clip(arrays['r1_app'], -20, 20), 1 - system.rho)
    x = obs['pilot'] + mu
    Y = daft(obs['y'], system.c1, system.c2, True)
    arms, traces = {}, {}
    for name, kernel, spec_name in (('A1c', closed, 'A1'), ('A2', full, 'A2')):
        paths = [kernel.Path(int(delay), float(nu))
                 for delay, nu in zip(arrays['r1_delays'], arrays['r1_dopplers'], strict=True)]
        arms[name], traces[name] = first_exchange(
            kernel, Y, x, v, paths, c1=system.c1, c2=system.c2, ridge=float(obs['sigma2']),
            max_delay=system.l_max_cap, doppler_min=-3., doppler_max=3., grid_step=.25,
            chunk_size=64, duplicate_tolerance=1e-6, top_k=20, strategy='compact',
            gamma_mode=q.sm.e1d.ARM_SPECS[spec_name]['gamma_mode'])
    return summarize_unit(arms, traces, truth, len(Y))


def observed_kernel(kernel, observation):
    """Run the original continuation in G1 while logging its returned first step."""
    def reopen(Y, x, v, paths, **opts):
        result = kernel.reopen_geometry(Y, x, v, paths, **opts)
        trace = result.global_trace[0]
        log = summarize(kernel, trace, Y, x, v, **opts)
        first_log, first_trace = first_exchange(kernel, Y, x, v, paths, **opts)
        observation.update(log=log, trace=trace, first_only_parity=(
            first_log == log and first_trace['accepted'] == trace['accepted']))
        return result

    return SimpleNamespace(Path=kernel.Path, reopen_geometry=reopen)
