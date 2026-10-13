"""Frozen UWA/RF exogenous generator for the physical-transfer v1 experiment."""

import ast
from hashlib import sha256
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SEED_PREFIX = (20260914, 741031)
DOMAIN_IDS = {"uwa": 0, "rf": 1}
SEED_COMPONENTS = {
    "delay": 1,
    "gain": 2,
    "angle": 3,
    "phase": 4,
    "bits": 5,
    "noise": 6,
    "arm_order": 7,
}
QPSK = np.array([0.5 + 0.5j, 0.5 - 0.5j, -0.5 + 0.5j, -0.5 - 0.5j])
TDL_C_NORMALIZED_DELAYS = np.array([
    0, 0.2099, 0.2219, 0.2329, 0.2176, 0.6366, 0.6448, 0.6560,
    0.6584, 0.7935, 0.8213, 0.9336, 1.2285, 1.3083, 2.1704,
    2.7105, 4.2589, 4.6003, 5.4902, 5.6077, 6.3065, 6.6374,
    7.0427, 8.6523,
], dtype=float)
TDL_C_POWERS_DB = np.array([
    -4.4, -1.2, -3.5, -5.2, -2.5, 0, -2.2, -3.9, -7.4, -7.1,
    -10.7, -11.1, -5.1, -6.8, -8.7, -13.2, -13.9, -13.9, -15.8,
    -17.1, -16, -15.7, -21.6, -22.8,
], dtype=float)
SOURCE_REFERENCE = (
    "ETSI TR 138 901 V18.0.0 (2024-05), Table 7.7.2-3 and clause 7.7.3; "
    "https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/18.00.00_60/"
    "tr_138901v180000p.pdf"
)


def _load_production_numpy_functions():
    """Extract pure production functions without importing Torch-bearing modules."""
    package = importlib.util.find_spec("afdm_sp_joint_unrolled")
    if package is None or not package.submodule_search_locations:
        raise ImportError("afdm_sp_joint_unrolled package source is unavailable")
    source = Path(next(iter(package.submodule_search_locations))) / "supplement_pilots.py"
    source_bytes = source.read_bytes()
    names = {"_vector", "transform", "cpp", "propagate_cpp"}
    tree = ast.parse(source_bytes, filename=str(source))
    nodes = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    if {node.name for node in nodes} != names:
        raise ImportError("production CPP/DAFT pure function set is incomplete")
    namespace = {"np": np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace, sha256(source_bytes).hexdigest()


_PRODUCTION_NUMPY, SUPPLEMENT_PILOTS_SHA256 = _load_production_numpy_functions()
transform = _PRODUCTION_NUMPY["transform"]
cpp = _PRODUCTION_NUMPY["cpp"]
propagate_cpp = _PRODUCTION_NUMPY["propagate_cpp"]


def _rng(domain, block, component):
    if domain not in DOMAIN_IDS or type(block) is not int or block < 0:
        raise ValueError("registered domain and nonnegative integer block required")
    return np.random.default_rng([*SEED_PREFIX, DOMAIN_IDS[domain], block, component])


def _p0(n):
    index = np.arange(n)
    return np.exp(-1j * np.pi * 7 * index * index / n)


def config(domain):
    """Return the frozen physical setup with the attributes build_receiver consumes."""
    if domain == "uwa":
        values = dict(N_total=256, N=256, Fb_hz=4_000, fc_hz=12_000,
            c_m_s=1_500, tau_max_s=0.006, l_max_cap=24, vmax_m_s=2.0,
            fd_max_hz=16.0, k_max_cap=2, prefix_length=32, rho=0.5,
            physical_paths=8, model="UWA eight-path exponential PDP")
    elif domain == "rf":
        values = dict(N_total=128, N=128, Fb_hz=10_000_000,
            fc_hz=3_500_000_000, c_m_s=300_000_000, tau_max_s=0.86523e-6,
            l_max_cap=9, vmax_m_s=120 / 3.6, fd_max_hz=3_500_000_000 / 300_000_000 * (120 / 3.6),
            k_max_cap=1, prefix_length=16, rho=0.5, physical_paths=24 * 16,
            model="TDL-C 24 taps with 16-oscillator Jakes approximation")
    else:
        raise ValueError("domain must be 'uwa' or 'rf'")
    n, k = values["N"], values["k_max_cap"]
    values.update(Fs=values["Fb_hz"], c1=(2 * k + 1) / (2 * n),
        c2=(np.sqrt(2) - 1) / (2 * n * n), cluster_extension=2)
    dictionary_size = (values["l_max_cap"] + 1) * (2 * k + 1)
    values.update(dictionary_size=dictionary_size,
        nomination=min(40, dictionary_size // 2),
        nomination_plus4=min(40, dictionary_size // 2) + 4,
        _zc_seq=_p0(n))
    return SimpleNamespace(**values)


configuration = config


def _daft_matrix(n, c1, c2):
    rows = np.arange(n)[:, None]
    columns = np.arange(n)[None, :]
    return (np.exp(2j * np.pi * c2 * rows * rows)
            * np.exp(-2j * np.pi * rows * columns / n) / np.sqrt(n)
            * np.exp(2j * np.pi * c1 * columns * columns))


def cpp_channel_matrix(n, c1, c2, delays, dopplers, gains, prefix_length):
    """Build an explicit sampled CPP matrix in time, then transform it by DAFT."""
    delays, dopplers, gains = map(np.asarray, (delays, dopplers, gains))
    if (type(n) is not int or n < 2 or type(prefix_length) is not int
            or not 0 <= prefix_length < n or not np.isfinite([c1, c2]).all()
            or delays.ndim != 1 or not len(delays)
            or delays.shape != dopplers.shape or delays.shape != gains.shape
            or np.iscomplexobj(delays) or np.iscomplexobj(dopplers)
            or np.any(delays != np.floor(delays)) or np.any(delays < 0)
            or np.any(delays > prefix_length)
            or any(not np.isfinite(value).all() for value in (delays, dopplers, gains))):
        raise ValueError("finite matched paths within the integer CPP are required")
    rows = np.arange(n)
    time_matrix = np.zeros((n, n), complex)
    for delay, doppler, gain in zip(delays.astype(int), dopplers, gains):
        source_time = rows - delay
        source = source_time % n
        prefix_phase = np.ones(n, complex)
        negative = source_time < 0
        prefix_phase[negative] = np.exp(
            2j * np.pi * c1 * (n * n + 2 * n * source_time[negative]))
        time_matrix[rows, source] += (gain * prefix_phase
            * np.exp(2j * np.pi * doppler * rows / n))
    daft = _daft_matrix(n, c1, c2)
    return daft @ time_matrix @ daft.conj().T


def _uwa_paths(cfg, block):
    delays_s = np.empty(8)
    delays_s[0] = 0.0
    delays_s[1:] = _rng("uwa", block, SEED_COMPONENTS["delay"]).uniform(
        0.0, cfg.tau_max_s, 7)
    delays = np.rint(delays_s * cfg.Fb_hz).astype(int)
    powers = np.exp(-delays_s / 0.002)
    powers /= powers.sum()
    angles = _rng("uwa", block, SEED_COMPONENTS["angle"]).uniform(0, 2 * np.pi, 8)
    doppler_hz = cfg.fd_max_hz * np.cos(angles)
    gain_rng = _rng("uwa", block, SEED_COMPONENTS["gain"])
    gains = np.sqrt(powers / 2) * (gain_rng.standard_normal(8) + 1j * gain_rng.standard_normal(8))
    return delays_s, delays, powers, doppler_hz, gains


def _rf_paths(cfg, block):
    tap_powers = 10 ** (TDL_C_POWERS_DB / 10)
    tap_powers /= tap_powers.sum()
    delays_s = TDL_C_NORMALIZED_DELAYS * 100e-9
    tap_delays = np.rint(delays_s * cfg.Fb_hz).astype(int)
    angles = 2 * np.pi * np.arange(16) / 16
    doppler_one_tap = cfg.fd_max_hz * np.cos(angles)
    phases = _rng("rf", block, SEED_COMPONENTS["phase"]).uniform(
        0, 2 * np.pi, (24, 16))
    gains = np.sqrt(tap_powers[:, None] / 16) * np.exp(1j * phases)
    return (np.repeat(delays_s, 16), np.repeat(tap_delays, 16),
        np.repeat(tap_powers / 16, 16), np.tile(doppler_one_tap, 24), gains.ravel())


def _pilot_geometry(cfg, pilot):
    waveform = transform(pilot, cfg.c1, cfg.c2, inverse=True)
    columns = []
    for delay in range(cfg.l_max_cap + 1):
        source_time = np.arange(cfg.N) - delay
        source = source_time % cfg.N
        prefix_phase = np.ones(cfg.N, complex)
        negative = source_time < 0
        prefix_phase[negative] = np.exp(2j * np.pi * cfg.c1 * (
            cfg.N * cfg.N + 2 * cfg.N * source_time[negative]))
        delayed = waveform[source] * prefix_phase
        for doppler in range(-cfg.k_max_cap, cfg.k_max_cap + 1):
            time_y = delayed * np.exp(2j * np.pi * doppler * np.arange(cfg.N) / cfg.N)
            columns.append(transform(time_y, cfg.c1, cfg.c2))
    sensing = np.column_stack(columns)
    gram = sensing.conj().T @ sensing
    norms = np.sqrt(np.real(np.diag(gram)))
    normalized = np.abs(gram / (norms[:, None] * norms[None, :]))
    np.fill_diagonal(normalized, 0)
    return dict(max_coherence=float(normalized.max()),
        gram_condition=float(np.linalg.cond(gram)),
        gram_trace_inverse=float(np.trace(np.linalg.inv(gram)).real),
        columns=sensing.shape[1])


def _waveform_metrics(cfg, pilot, data):
    signal = transform(pilot + data, cfg.c1, cfg.c2, inverse=True)
    extended = cpp(signal, cfg.c1, cfg.prefix_length)
    payload_power = np.abs(signal) ** 2
    peak = float(np.max(np.abs(extended) ** 2))
    mean = float(payload_power.mean())
    return dict(pilot_energy=float(np.vdot(pilot, pilot).real),
        data_energy=float(np.vdot(data, data).real),
        payload_energy=float(np.vdot(signal, signal).real),
        prefix_energy=float(np.vdot(extended[:cfg.prefix_length], extended[:cfg.prefix_length]).real),
        peak_power=peak, papr_db=float(10 * np.log10(peak / mean)),
        clipping="none", sample_gain_normalization="none")


def array_sha256(value):
    array = np.ascontiguousarray(value)
    return sha256(str(array.dtype).encode() + repr(array.shape).encode() + array.tobytes()).hexdigest()


def generate(domain, block):
    """Generate one truth-side channel, two pilots, data, and reusable unit noise."""
    cfg = config(domain)
    if domain == "uwa":
        delays_s, delays, expected_powers, doppler_hz, gains = _uwa_paths(cfg, block)
    else:
        delays_s, delays, expected_powers, doppler_hz, gains = _rf_paths(cfg, block)
    dopplers = doppler_hz * cfg.N / cfg.Fb_hz
    h = cpp_channel_matrix(cfg.N, cfg.c1, cfg.c2, delays, dopplers, gains, cfg.prefix_length)
    bits = _rng(domain, block, SEED_COMPONENTS["bits"]).integers(0, 2, 2 * cfg.N, dtype=np.uint8)
    signs = 1.0 - 2.0 * bits.astype(float)
    data = 0.5 * (signs[:cfg.N] + 1j * signs[cfg.N:])
    noise_rng = _rng(domain, block, SEED_COMPONENTS["noise"])
    noise = (noise_rng.standard_normal(cfg.N) + 1j * noise_rng.standard_normal(cfg.N)) / np.sqrt(2)
    pilots = dict(p0=np.sqrt(cfg.rho) * cfg._zc_seq,
        pZ=np.sqrt(cfg.N * cfg.rho) * np.eye(1, cfg.N, 0, dtype=complex)[0])
    noiseless, closures, geometry, waveforms = {}, {}, {}, {}
    for name, pilot in pilots.items():
        combined = pilot + data
        waveform = transform(combined, cfg.c1, cfg.c2, inverse=True)
        reference = transform(propagate_cpp(waveform, cfg.c1, delays, dopplers, gains,
            prefix_length=cfg.prefix_length), cfg.c1, cfg.c2)
        matrix_value = h @ combined
        error = np.linalg.norm(reference - matrix_value) / max(1.0, np.linalg.norm(reference))
        if not np.isfinite(error) or error > 1e-10:
            raise ValueError("explicit CPP/DAFT matrix failed production propagation closure")
        noiseless[name] = reference
        closures[name] = float(error)
        geometry[name] = _pilot_geometry(cfg, pilot)
        waveforms[name] = _waveform_metrics(cfg, pilot, data)
    if (not np.isclose(expected_powers.sum(), 1, atol=2e-15, rtol=0)
            or not all(np.isclose(v["pilot_energy"], cfg.N * cfg.rho, atol=2e-12, rtol=0)
                       and np.isclose(v["data_energy"], cfg.N * (1 - cfg.rho), atol=2e-12, rtol=0)
                       for v in waveforms.values())):
        raise ValueError("expected path or transmit energy contract failed")
    metadata = dict(domain=domain, block=block, N=cfg.N, Fb_hz=cfg.Fb_hz,
        fc_hz=cfg.fc_hz, c_m_s=cfg.c_m_s, tau_max_s=cfg.tau_max_s,
        fd_max_hz=cfg.fd_max_hz, l_max=cfg.l_max_cap, k_max=cfg.k_max_cap,
        prefix_length=cfg.prefix_length, rho=cfg.rho, dictionary_size=cfg.dictionary_size,
        nomination=cfg.nomination, nomination_plus4=cfg.nomination_plus4,
        seed_prefix=list(SEED_PREFIX), domain_id=DOMAIN_IDS[domain],
        seed_components=SEED_COMPONENTS.copy(), physical_units=True,
        expected_power_sum=float(expected_powers.sum()), gain_normalization="none",
        delay_quantization="nearest integer baseband sample; coincident taps retained",
        model_scope=("no wideband time scaling or measured UWA fit" if domain == "uwa" else
            "TDL-C table with quantized delays and finite 16-oscillator Jakes approximation"),
        source_reference=SOURCE_REFERENCE if domain == "rf" else
            "frozen task-local exponential-PDP and uniform-angle UWA modeling choice",
        rf_normalized_delay_last=(float(TDL_C_NORMALIZED_DELAYS[-1]) if domain == "rf" else None),
        cpp_closure=closures, pilot_geometry=geometry, waveform=waveforms,
        source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        supplement_pilots_sha256=SUPPLEMENT_PILOTS_SHA256)
    params = dict(l_i=delays.copy(), k_real=dopplers.copy(), g_i=gains.copy(),
        delays_s=delays_s.copy(), doppler_hz=doppler_hz.copy(),
        expected_path_powers=expected_powers.copy(), physical_paths=len(gains),
        representation="integer-delay full-fractional-Doppler explicit CPP/DAFT")
    raw = dict(domain=domain, block=block, H=h, bits=bits, data=data, noise=noise,
        pilots=pilots, noiseless=noiseless, delays_s=delays_s, delays=delays,
        doppler_hz=doppler_hz, dopplers=dopplers, gains=gains,
        expected_path_powers=expected_powers, params=params, metadata=metadata)
    if any(not np.isfinite(np.asarray(value)).all() for key, value in raw.items()
           if key not in ("domain", "pilots", "noiseless", "params", "metadata")):
        raise ValueError("generated physical truth contains nonfinite values")
    return raw


def validate(raw, domain, block):
    """Recompute truth-side closure, energy, waveform, and public pilot geometry."""
    cfg = config(domain)
    if raw.get("domain") != domain or raw.get("block") != block:
        raise ValueError("raw identity does not match requested domain/block")
    required = {"H", "bits", "data", "noise", "pilots", "noiseless", "delays",
        "dopplers", "gains", "expected_path_powers", "params", "metadata"}
    if not required.issubset(raw) or raw["H"].shape != (cfg.N, cfg.N):
        raise ValueError("incomplete or dimensionally invalid physical raw")
    replay = _uwa_paths(cfg, block) if domain == "uwa" else _rf_paths(cfg, block)
    replay_names = ("delays_s", "delays", "expected_path_powers", "doppler_hz", "gains")
    for name, expected in zip(replay_names, replay):
        if not np.array_equal(raw[name], expected):
            raise ValueError(f"seed replay changed physical path field {name}")
    expected_dopplers = replay[3] * cfg.N / cfg.Fb_hz
    if not np.array_equal(raw["dopplers"], expected_dopplers):
        raise ValueError("seed replay changed normalized Doppler")
    bits = _rng(domain, block, SEED_COMPONENTS["bits"]).integers(
        0, 2, 2 * cfg.N, dtype=np.uint8)
    signs = 1.0 - 2.0 * bits.astype(float)
    data = 0.5 * (signs[:cfg.N] + 1j * signs[cfg.N:])
    noise_rng = _rng(domain, block, SEED_COMPONENTS["noise"])
    noise = (noise_rng.standard_normal(cfg.N) + 1j * noise_rng.standard_normal(cfg.N)) / np.sqrt(2)
    for name, expected in (("bits", bits), ("data", data), ("noise", noise)):
        if not np.array_equal(raw[name], expected):
            raise ValueError(f"seed replay changed {name}")
    expected_pilots = dict(p0=np.sqrt(cfg.rho) * cfg._zc_seq,
        pZ=np.sqrt(cfg.N * cfg.rho) * np.eye(1, cfg.N, 0, dtype=complex)[0])
    if set(raw["pilots"]) != set(expected_pilots) or any(
            not np.array_equal(raw["pilots"][name], expected)
            for name, expected in expected_pilots.items()):
        raise ValueError("frozen pilots changed")
    parameter_arrays = dict(l_i=raw["delays"], k_real=raw["dopplers"],
        g_i=raw["gains"], delays_s=raw["delays_s"], doppler_hz=raw["doppler_hz"],
        expected_path_powers=raw["expected_path_powers"])
    if any(not np.array_equal(raw["params"].get(name), expected)
           for name, expected in parameter_arrays.items()):
        raise ValueError("truth parameter copy changed")
    if raw["params"].get("physical_paths") != len(raw["gains"]):
        raise ValueError("truth physical-path count changed")
    fixed_metadata = dict(domain=domain, block=block, N=cfg.N, Fb_hz=cfg.Fb_hz,
        fc_hz=cfg.fc_hz, c_m_s=cfg.c_m_s, tau_max_s=cfg.tau_max_s,
        fd_max_hz=cfg.fd_max_hz, l_max=cfg.l_max_cap, k_max=cfg.k_max_cap,
        prefix_length=cfg.prefix_length, rho=cfg.rho, dictionary_size=cfg.dictionary_size,
        nomination=cfg.nomination, nomination_plus4=cfg.nomination_plus4,
        seed_prefix=list(SEED_PREFIX), domain_id=DOMAIN_IDS[domain],
        seed_components=SEED_COMPONENTS, physical_units=True, gain_normalization="none",
        delay_quantization="nearest integer baseband sample; coincident taps retained")
    if any(raw["metadata"].get(name) != expected for name, expected in fixed_metadata.items()):
        raise ValueError("frozen physical metadata changed")
    if (raw["metadata"].get("source_sha256") != sha256(Path(__file__).read_bytes()).hexdigest()
            or raw["metadata"].get("supplement_pilots_sha256") != SUPPLEMENT_PILOTS_SHA256):
        raise ValueError("generator or production CPP/DAFT source hash changed")
    explicit_h = cpp_channel_matrix(cfg.N, cfg.c1, cfg.c2, raw["delays"],
        raw["dopplers"], raw["gains"], cfg.prefix_length)
    matrix_replay = float(np.linalg.norm(explicit_h - raw["H"])
        / max(1.0, np.linalg.norm(raw["H"])))
    closures, geometry, waveforms = {}, {}, {}
    for name in ("p0", "pZ"):
        pilot = raw["pilots"][name]
        combined = pilot + raw["data"]
        waveform = transform(combined, cfg.c1, cfg.c2, inverse=True)
        direct = transform(propagate_cpp(waveform, cfg.c1, raw["delays"],
            raw["dopplers"], raw["gains"], prefix_length=cfg.prefix_length), cfg.c1, cfg.c2)
        closures[name] = float(np.linalg.norm(direct - raw["H"] @ combined)
            / max(1.0, np.linalg.norm(direct)))
        if not np.allclose(direct, raw["noiseless"][name], atol=1e-12, rtol=1e-12):
            raise ValueError("saved noiseless observation does not replay")
        geometry[name] = _pilot_geometry(cfg, pilot)
        waveforms[name] = _waveform_metrics(cfg, pilot, raw["data"])
    evidence = dict(domain=domain, block=block, N=cfg.N,
        matrix_replay_relative_error=matrix_replay, cpp_closure=closures,
        max_cpp_closure=max(closures.values()), pilot_geometry=geometry,
        waveform=waveforms,
        expected_power_sum=float(np.asarray(raw["expected_path_powers"]).sum()),
        actual_component_gain_energy=float(np.vdot(raw["gains"], raw["gains"]).real),
        data_energy=float(np.vdot(raw["data"], raw["data"]).real),
        pilot_energies={name: float(np.vdot(value, value).real)
                        for name, value in raw["pilots"].items()},
        rf_normalized_delay_last=(float(TDL_C_NORMALIZED_DELAYS[-1]) if domain == "rf" else None),
        no_hidden_N_modification=raw["H"].shape == (cfg.N, cfg.N))
    if (evidence["max_cpp_closure"] > 1e-10 or matrix_replay > 1e-12
            or not np.isclose(evidence["expected_power_sum"], 1, atol=2e-15, rtol=0)
            or not np.isclose(evidence["data_energy"], cfg.N * (1 - cfg.rho), atol=2e-12, rtol=0)
            or not all(np.isclose(value, cfg.N * cfg.rho, atol=2e-12, rtol=0)
                       for value in evidence["pilot_energies"].values())):
        raise ValueError("physical raw failed replay validation")
    return evidence


def observed(raw, pilot, snr):
    """Expose exactly the four registered observed-only uncoded receiver fields."""
    if pilot not in ("p0", "pZ") or not np.isfinite(snr):
        raise ValueError("registered pilot and finite SNR required")
    sigma2 = 10.0 ** (-float(snr) / 10)
    return dict(y=raw["noiseless"][pilot] + np.sqrt(sigma2) * raw["noise"],
        pilot=raw["pilots"][pilot].copy(), sigma2=np.array(sigma2),
        constellation=QPSK.copy())


def _bits_of(symbols):
    symbols = np.asarray(symbols)
    return np.concatenate((symbols.real < 0, symbols.imag < 0)).astype(np.uint8)


def offline_score(value, raw, pilot):
    """Recompute the uncoded runner's truth-side BER/channel/pilot scores."""
    if pilot not in raw["pilots"]:
        raise ValueError("unknown pilot")
    bits = np.asarray(value["bits"] if "bits" in value else _bits_of(value["x_soft"]))
    error = np.asarray(value["H"], dtype=complex) - raw["H"]
    norm = lambda x: float(np.vdot(x, x).real)
    delta = bits != raw["bits"]
    pilot_vector = raw["pilots"][pilot]
    return dict(bit_errors=int(delta.sum()), bit_count=len(delta),
        block_error=bool(delta.any()), channel_nmse=norm(error) / norm(raw["H"]),
        pilot_nmse=norm(error @ pilot_vector) / norm(raw["H"] @ pilot_vector),
        active_atoms=len(value["delays"]))
