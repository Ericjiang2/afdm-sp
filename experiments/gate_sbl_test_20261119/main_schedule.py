"""Frame keys and CPU budget selection for the two registered SBL schedules."""

from math import isfinite

from audit_fresh import S_BASE, S_EXTENSION, X

S_SNRS = (600, 700, 800, 900, 1000, 1100)
S_SCENARIOS = ("U", "G")
S_RHO = 300
CORE_HOUR_CAP = 25.0
MULTIPLIER = 1.3


def s_keys(segments):
    """Enumerate the paired receiver keys, grouped by physical frame."""
    blocks = tuple(tuple(block) for block in segments)
    if blocks not in ((S_BASE,), (S_BASE, S_EXTENSION)):
        raise ValueError(f"Unregistered SBL frame segments: {blocks}")
    return [(scenario, S_RHO, snr, frame)
            for first, last in blocks for frame in range(first, last + 1)
            for scenario in S_SCENARIOS for snr in S_SNRS]


def choose(s_cpu_seconds_per_key, x_cpu_seconds_per_frame, *, extension_passed):
    """Apply the shared 25-core-hour cap after the registered margin."""
    if any(not isfinite(t) or t <= 0 for t in (s_cpu_seconds_per_key, x_cpu_seconds_per_frame)):
        raise ValueError("Cost projection requires positive finite CPU timings")
    n_x = X[1] - X[0] + 1
    x_hours = MULTIPLIER * x_cpu_seconds_per_frame * n_x / 3600
    base = (S_BASE,)
    expanded = (S_BASE, S_EXTENSION)
    s_hours = {len(keys): MULTIPLIER * s_cpu_seconds_per_key * len(keys) / 3600
               for keys in (s_keys(base), s_keys(expanded))}
    totals = {count: hours + x_hours for count, hours in s_hours.items()}
    if extension_passed and totals[4800] <= CORE_HOUR_CAP:
        segments, reason = expanded, "audited_extension_within_cap"
    elif totals[2400] <= CORE_HOUR_CAP:
        segments = base
        reason = "extension_over_cap" if extension_passed else "extension_audit_failed"
    else:
        raise ValueError("Both registered schedules exceed the 25-core-hour cap")
    keys = s_keys(segments)
    schedule = dict(s_segments=segments, s_keys=len(keys), s_frames=len({key[3] for key in keys}),
                    s_scenarios=S_SCENARIOS, s_rho_permille=S_RHO, s_snr_centi_db=S_SNRS,
                    cluster_unit="physical frame", x_segment=X, x_frames=n_x,
                    x_snr_db=7, x_rho=.5, reason=reason)
    cost = dict(multiplier=MULTIPLIER, cap_core_hours=CORE_HOUR_CAP,
                s_cpu_seconds_per_key=s_cpu_seconds_per_key, x_cpu_seconds_per_frame=x_cpu_seconds_per_frame,
                s_core_hours=s_hours, x_core_hours=x_hours, total_core_hours=totals,
                selected_total_core_hours=totals[len(keys)])
    return schedule, cost
