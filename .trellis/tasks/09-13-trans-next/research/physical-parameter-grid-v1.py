"""Deterministic proposed acoustic/RF parameter grids; no channel/BER simulation."""

from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


FC_HZ = 12_000
C_M_S = 1_500
MAIN_FS_HZ = 4_000
TAU_MAX_MS = (6, 10, 20)
VMAX_M_S = (Fraction(2), Fraction(7, 2))
BLOCK_LENGTHS = (128, 256, 512, 1024)
RF_FC_HZ = 3_500_000_000
RF_C_M_S = 300_000_000
RF_FB_HZ = 10_000_000
RF_DELAY_SPREAD_NS = (100, 300)
RF_VELOCITY_KMH = (30, 120, 300)
TDL_C_LAST_TAP_DS = Fraction(86_523, 10_000)


def ratio(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def calculate_core(
    tau_s: Fraction,
    velocity_m_s: Fraction,
    n: int,
    fs_hz: int,
    fc_hz: int,
    c_m_s: int,
    prefix_s: Fraction,
) -> dict:
    fd_hz = velocity_m_s * fc_hz / c_m_s
    duration_s = Fraction(n, fs_hz)
    spacing_hz = Fraction(fs_hz, n)
    l_max = math.ceil(tau_s * fs_hz)
    k_ceil = math.ceil(fd_hz * duration_s)
    integer_d = (l_max + 1) * (2 * k_ceil + 1)
    guard_d = (l_max + 1) * (2 * (k_ceil + 2) + 1)
    prefix_l = math.ceil(prefix_s * fs_hz)
    prefix_fraction = Fraction(prefix_l, n + prefix_l)
    quadratic_relative = Fraction(n * n, 1024 * 1024)
    cubic_relative = Fraction(n * n * n, 1024 * 1024 * 1024)

    return {
        "N": n,
        "Fs_hz": fs_hz,
        "fd_hz": float(fd_hz),
        "delta_f_hz": float(spacing_hz),
        "l_max": l_max,
        "k_ceil": k_ceil,
        "integer_D": integer_d,
        "guard_D": guard_d,
        "prefix_L": prefix_l,
        "prefix_fraction": float(prefix_fraction),
        "prefix_fraction_exact": ratio(prefix_fraction),
        "E_p": float(Fraction(n, 2)),
        "cost_N2_relative_1024": float(quadratic_relative),
        "cost_N2_relative_1024_exact": ratio(quadratic_relative),
        "cost_N3_relative_1024": float(cubic_relative),
        "cost_N3_relative_1024_exact": ratio(cubic_relative),
    }


def calculate_water(tau_ms: int, vmax_m_s: Fraction, n: int) -> dict:
    row = calculate_core(
        Fraction(tau_ms, 1000),
        vmax_m_s,
        n,
        MAIN_FS_HZ,
        FC_HZ,
        C_M_S,
        Fraction(tau_ms + 2, 1000),
    )
    return {
        "tau_max_ms": tau_ms,
        "vmax_m_s": float(vmax_m_s),
        "N": row.pop("N"),
        "Fs_hz": row.pop("Fs_hz"),
        "fd_hz": row.pop("fd_hz"),
        "T_ms": float(Fraction(n, MAIN_FS_HZ) * 1000),
        **row,
    }


def calculate_rf(delay_spread_ns: int, velocity_kmh: int, n: int) -> dict:
    delay_spread_s = Fraction(delay_spread_ns, 1_000_000_000)
    tau_s = TDL_C_LAST_TAP_DS * delay_spread_s
    velocity_m_s = Fraction(velocity_kmh * 5, 18)
    prefix_s = Fraction(16 if delay_spread_ns == 100 else 32, RF_FB_HZ)
    row = calculate_core(
        tau_s,
        velocity_m_s,
        n,
        RF_FB_HZ,
        RF_FC_HZ,
        RF_C_M_S,
        prefix_s,
    )
    return {
        "delay_spread_ns": delay_spread_ns,
        "tau_max_us": float(tau_s * 1_000_000),
        "velocity_kmh": velocity_kmh,
        "velocity_m_s": float(velocity_m_s),
        "N": row.pop("N"),
        "Fb_hz": row.pop("Fs_hz"),
        "fd_hz": row.pop("fd_hz"),
        "T_us": float(Fraction(n, RF_FB_HZ) * 1_000_000),
        "fd_times_T": float(velocity_m_s * RF_FC_HZ * n / (RF_C_M_S * RF_FB_HZ)),
        "prefix_us": float(prefix_s * 1_000_000),
        **row,
    }


def main() -> None:
    source_path = Path(__file__)
    water_rows = [
        calculate_water(tau_ms, vmax_m_s, n)
        for tau_ms in TAU_MAX_MS
        for vmax_m_s in VMAX_M_S
        for n in BLOCK_LENGTHS
    ]
    legacy = calculate_core(
        Fraction(6, 1000), Fraction(2), 1024, 16_000, FC_HZ, C_M_S, Fraction(8, 1000)
    )
    legacy = {
        "tau_max_ms": 6,
        "vmax_m_s": 2.0,
        "N": legacy.pop("N"),
        "Fs_hz": legacy.pop("Fs_hz"),
        "fd_hz": legacy.pop("fd_hz"),
        "T_ms": 64.0,
        **legacy,
    }
    rf_rows = [
        calculate_rf(delay_spread_ns, velocity_kmh, n)
        for delay_spread_ns in RF_DELAY_SPREAD_NS
        for velocity_kmh in RF_VELOCITY_KMH
        for n in BLOCK_LENGTHS
    ]

    known = calculate_water(6, Fraction(2), 256)
    assert known["l_max"] == 24
    assert known["k_ceil"] == 2
    assert known["integer_D"] == 125
    assert known["guard_D"] == 225
    assert known["T_ms"] == 64.0
    assert known["prefix_L"] == 32
    assert len(water_rows) == 24
    rf_known = calculate_rf(100, 120, 128)
    assert rf_known["tau_max_us"] == 0.86523
    assert rf_known["l_max"] == 9
    assert rf_known["k_ceil"] == 1
    assert rf_known["integer_D"] == 30
    assert rf_known["prefix_L"] == 16
    rf_stress = calculate_rf(300, 120, 128)
    assert rf_stress["l_max"] == 26
    assert rf_stress["prefix_L"] == 32
    assert len(rf_rows) == 24

    result = {
        "status": "COMPLETE",
        "scope": (
            "Deterministic proposed physical water-acoustic and ordinary RF parameter design only; "
            "no channel, BER, speed, or runtime evidence, and not a frozen execution contract."
        ),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "inputs": {
            "fc_hz": FC_HZ,
            "c_m_s": C_M_S,
            "complex_critical_baseband_Fs_hz": MAIN_FS_HZ,
            "tau_max_ms": list(TAU_MAX_MS),
            "vmax_m_s": [float(value) for value in VMAX_M_S],
            "N": list(BLOCK_LENGTHS),
            "prefix_margin_ms": 2,
        },
        "rf_inputs": {
            "fc_hz": RF_FC_HZ,
            "c_m_s": RF_C_M_S,
            "complex_baseband_Fb_hz": RF_FB_HZ,
            "channel_model": "3GPP TDL-C",
            "delay_spread_ns": list(RF_DELAY_SPREAD_NS),
            "tau_max_delay_spread_multiplier": float(TDL_C_LAST_TAP_DS),
            "tau_max_delay_spread_multiplier_exact": ratio(TDL_C_LAST_TAP_DS),
            "velocity_kmh": list(RF_VELOCITY_KMH),
            "N": list(BLOCK_LENGTHS),
            "prefix_us_by_delay_spread_ns": {"100": 1.6, "300": 3.2},
        },
        "definitions": {
            "fd": "vmax*fc/c",
            "T": "N/Fs",
            "delta_f": "Fs/N",
            "l_max": "ceil(tau_max*Fs)",
            "k_ceil": "ceil(fd*T), a conservative integer bound",
            "integer_D": "(l_max+1)*(2*k_ceil+1)",
            "guard_D": (
                "(l_max+1)*(2*(k_ceil+2)+1), a finite leakage proxy only; "
                "not a full fractional-orthogonality theorem"
            ),
            "water_prefix_L": "ceil((tau_max+2 ms)*Fs), using a fixed proposed 2 ms margin",
            "rf_prefix_L": "ceil(explicit prefix time*Fb): 1.6 us main and 3.2 us stress",
            "prefix_fraction": "prefix_L/(N+prefix_L)",
            "E_p": "0.5*N",
            "cost_proxies": "N^2 and N^3 relative to N=1024; not wall-clock costs",
        },
        "rows": water_rows,
        "legacy_scale_comparison": legacy,
        "rf_rows": rf_rows,
        "rf_dimension_check": {
            "scenario": "DS=100 ns, velocity=120 km/h, N=128",
            "integer_D": rf_known["integer_D"],
            "initial_nomination": 40,
            "legal": False,
            "reason": "initial nomination 40 exceeds the 30-column integer dictionary dimension",
        },
    }
    output_path = source_path.with_name("physical-parameter-grid-v1-results.json")
    output_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "water_rows": len(water_rows),
                "rf_rows": len(rf_rows),
                "output": str(output_path),
            }
        )
    )


if __name__ == "__main__":
    main()
