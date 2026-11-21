"""Controlled P1 frames and disjoint calibration and outcome paths."""
from types import SimpleNamespace

import numpy as np


ENTROPY = "a07ed5cd6343eb6c7443735dfdcbca71455412cb37a6631126cc374d98612659"
DOMAIN = 0x52535750
CAL = range(52000, 52200)
MAIN = range(53000, 54000)
RATIOS = (2, 4, 8, 16, 32, 64, 128, 256)
RHOS = (.3, .5)
SNRS = (4.5, 5.5, 6.5, 7.5, 8.5, 10.)
CAP = 8
MARGIN = 1e-6
BANK = dict(doppler_min=-3., doppler_max=3., grid_step=.25)
DUPLICATE = 1e-6


def draw_frame(study, frame):
    """Reuse P1's draw and stream helpers, adding distinct-delay rejection."""
    q, ctx = study[:2]
    p1 = q.sm.p1ctx.p1_driver
    gen, flags, s = p1.gen_fixed, p1.SCENARIOS["G"], ctx.system
    seed_fn = p1.make_seed_fn(ENTROPY, DOMAIN)
    rng = gen.make_rng_factory(seed_fn, frame)
    channel_seed = gen.expected_channel_seed(seed_fn, frame)
    rs = np.random.RandomState(channel_seed)
    for _ in range(gen.MAX_REDRAWS_FIXED):
        draw = gen.one_attempt(s, rs, flags)
        delays = gen.delay_bins(s, draw["delay_idx_bar"], flags, clip=False)
        if delays.max() <= flags.trunc_bin and len(np.unique(delays)) == CAP:
            break
    else:
        raise RuntimeError(f"No distinct supported P1 geometry at frame {frame}")
    dopplers = gen.doppler_k_real(s, draw["doppler_a"], flags, gen.geo_rng_for(channel_seed))
    gains = draw["gain_tap"]
    powers = abs(gains) ** 2
    strong, weak = int(powers.argmax()), int(powers.argmin())
    info = rng(0, frame, p1.COMPONENTS["message"], split=2).integers(0, 2, size=ctx.code["k"]).astype(np.uint8)
    coded = ctx.encode(ctx.code, info)
    noise_rng = rng(0, frame, p1.COMPONENTS["noise"], split=2)
    n = s.N_total
    noise = (noise_rng.standard_normal(n) + 1j * noise_rng.standard_normal(n)) / np.sqrt(2)
    return dict(l_i=delays, k_real=dopplers, info=info, coded=coded, noise=noise,
                channel_seed=channel_seed, powers=powers, phase=gains / abs(gains),
                strong=strong, weak=weak, qpsk=ctx.qpsk_map(coded, scale=1))


def controlled_base(ctx, draw, rho, ratio, *, background_clip=None):
    """Assemble the corrected P1 untruncated CPP observation without the unused G0 reference."""
    s = ctx.system
    strong, weak = draw["strong"], draw["weak"]
    old = draw["powers"]
    if background_clip is None:
        background_clip = (1 + MARGIN) / ratio, 1 - MARGIN
    powers = np.clip(old / old[strong], *background_clip)
    powers[strong], powers[weak] = 1., 1. / ratio
    gains = np.sqrt(powers / powers.sum()) * draw["phase"]
    truth = {field: draw[field] for field in ("l_i", "k_real", "info", "coded")}
    truth["g_i"] = gains
    pilot = np.sqrt(rho) * s._zc_seq
    data = np.sqrt(1 - rho) * draw["qpsk"]
    waveform = ctx.transform(pilot + data, s.c1, s.c2, inverse=True)
    received = ctx.propagate_cpp(waveform, s.c1, truth["l_i"], truth["k_real"], gains,
                                 prefix_length=int(s.l_max_cap))
    noiseless = ctx.transform(received, s.c1, s.c2)
    return dict(pilot=pilot, data=data, noise=draw["noise"], noiseless=noiseless), truth


def observation(ctx, base, rho, snr):
    sigma2 = 10 ** (-snr / 10)
    raw = dict(base, sigma2=sigma2, y=base["noiseless"] + np.sqrt(sigma2) * base["noise"])
    return ctx.hd.observe(raw, rho, snr)


def weak_missed(arrays, truth, weak):
    return bool(truth["l_i"][weak] not in arrays["r1_delays"])


def calibration_inputs(full, system, obs, arrays, truth, strong, rho):
    """Read pre-exchange inputs and static bank geometry without running a selector."""
    from messages import moments
    from physical import daft, dkernel

    mu, v, _ = moments(np.clip(arrays["r1_app"], -20, 20), 1 - system.rho)
    mean = obs["pilot"] + mu
    E = float(np.vdot(mean, mean).real)
    values = dict(E=E, u=float(v.sum()), x=float(2 * (1 - rho) * v.mean()),
                  spacing=None, kappa=None, D=None, **{"lambda": float(obs["sigma2"])})
    delay = truth["l_i"][strong]
    paths = [full.Path(int(l), float(nu))
             for l, nu in zip(arrays["r1_delays"], arrays["r1_dopplers"], strict=True)]
    anchors = [i for i, p in enumerate(paths) if p.delay == delay]
    if not anchors or len(paths) < 2 or E <= 0:
        return values
    i = min(anchors, key=lambda k: (abs(paths[k].doppler - truth["k_real"][strong]), k))
    anchor = paths[i]
    _, _, nus = full._bank(system.l_max_cap, **BANK)
    bank = [full.Path(int(delay), float(nu)) for nu in nus]
    legal = full._valid(paths, bank, DUPLICATE)[np.arange(len(paths)) != i].any(axis=0)
    if not legal.any():
        return values
    candidate = min((p for p, valid in zip(bank, legal, strict=True) if valid),
                    key=lambda p: (abs(p.doppler - anchor.doppler), p.doppler))
    delta = candidate.doppler - anchor.doppler
    xt = daft(mean, system.c1, system.c2, inverse=True)
    a, c = full._responses(xt, [anchor, candidate], system.c1, system.c2).T
    values.update(spacing=abs(delta), kappa=np.vdot(a, c) / E, D=dkernel(delta, len(mean)))
    return values


def first_class(trace, truth, weak):
    edit = trace["accepted"]
    if edit is None:
        return "no_edit"
    entered = trace["entering_paths"]
    incoming = edit["new"]["delay"]
    if any(p["delay"] == incoming for i, p in enumerate(entered) if i != edit["slot"]):
        return "phantom"
    missing = set(truth["l_i"]) - {p["delay"] for p in entered}
    if incoming in missing:
        return "weak_recovery" if incoming == truth["l_i"][weak] else "other_missing_recovery"
    return "other"


def continuation(study, obs, arrays, truth, weak, *, eligible, triggered):
    """Use the E-1 branch input path. Eligible-only keys skip detector and decoder."""
    from messages import moments
    from physical import daft

    q, ctx, _, full, closed, _ = study
    result = {}
    for name, kernel, spec in (("A2", full, "A2"), ("CODELAY", closed, "A1")):
        if triggered:
            row = {}

            def record(Y, x, v, paths, **opts):
                branch = kernel.reopen_geometry(Y, x, v, paths, **opts)
                if eligible:
                    row["first_edit_class"] = first_class(branch.global_trace[0], truth, weak)
                return branch

            observer = SimpleNamespace(Path=kernel.Path, reopen_geometry=record)
            branch = q.sm.e1d.run_branch(ctx, observer, obs, arrays, spec)
            row["frame_error"] = bool(q.sm.gd.score(ctx, branch["decoder"]["decoded"], truth))
            result[name] = row
        elif eligible:
            s = ctx.system
            mu, v, _ = moments(np.clip(arrays["r1_app"], -20, 20), 1 - s.rho)
            Y = daft(obs["y"], s.c1, s.c2, True)
            paths = [kernel.Path(int(l), float(nu))
                     for l, nu in zip(arrays["r1_delays"], arrays["r1_dopplers"], strict=True)]
            branch = kernel.reopen_geometry(
                Y, obs["pilot"] + mu, v, paths, c1=s.c1, c2=s.c2, ridge=float(obs["sigma2"]),
                max_delay=s.l_max_cap, **BANK, max_edits=1, chunk_size=64, local_passes=0,
                duplicate_tolerance=DUPLICATE, top_k=20, strategy="compact",
                gamma_mode=q.sm.e1d.ARM_SPECS[spec]["gamma_mode"])
            result[name] = {"first_edit_class": first_class(branch.global_trace[0], truth, weak)}
    return result


def main_row(study, draw, base, truth, rho, snr):
    """Receiver row for a later main driver, with F0 pass-through on nontriggers."""
    q, ctx, variant = study[:3]
    obs = observation(ctx, base, rho, snr)
    dec, arrays, syndrome, _ = q.sm.f0_state(ctx, variant, obs, CAP)
    error = bool(q.sm.gd.score(ctx, dec["decoded"], truth))
    eligible = weak_missed(arrays, truth, draw["weak"])
    arms = continuation(study, obs, arrays, truth, draw["weak"], eligible=eligible,
                        triggered=bool(syndrome))
    for name in ("A2", "CODELAY"):
        arms.setdefault(name, {}).setdefault("frame_error", error)
    return dict(weak_path_missed=eligible, f0_frame_error=error, triggered=bool(syndrome), arms=arms)
