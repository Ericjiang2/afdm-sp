"""
afdm_env.py — Pure-physics mixin for AFDM superimposed-pilot system.

Contains:
    - __init__, chirp params, DAFT matrix builders
    - Channel generation (MATLAB-style UWA acoustic model), pilot frame assembly
    - AFDM modulation / demodulation / AWGN
    - Tap-to-2D-grid mapping, ZC matched-filter, LS/MMSE estimation
    - DNN feature extraction

No TF/Keras dependency — safe to import in NumPy-only environments.
"""
import numpy as np
from scipy.linalg import dft
import warnings
warnings.filterwarnings('ignore')


class AFDMEnvMixin:
    def __init__(self, N=8, M=8, rho=0.3):
        """
        rho : float in (0,1)
            Pilot-to-total power ratio (Pilot-Data Ratio) for the SP frame.
            x_frame[m] = sqrt(1-rho)*d[m]  for all m (QPSK data symbols)
            x_frame[m0] += sqrt(rho*N)*p    (additive pilot at centre sub-carrier)
            Total frame energy per sub-carrier = 1.0  (normalised).
            Default: rho=0.3  (30% pilot power, 70% data power)
        """
        # OTFS frame parameters
        # N and M are kept for compatibility; total subcarriers = N * M
        self.N = N  # original Doppler dimension
        self.M = M  # original delay dimension
        self.N_total = N * M  # total number of DAFT-domain subcarriers
        
        # System parameters (MATLAB UWA port)
        self.delta_f = 15.0  # subcarrier spacing (Hz)
        self.T = 1 / self.delta_f  # block duration
        self.fc = 12e3  # acoustic carrier frequency (Hz)
        self.c_sound = 1500.0  # speed of sound in seawater (m/s)
        self.B = 4e3  # acoustic bandwidth (Hz)
        self.fs = 2 * self.B  # sampling rate (Hz)
        self.Ts = 1 / self.fs  # sampling period (s)

        # MATLAB UWA channel parameters
        self.P_paths = 10
        self.tau_spread = 10e-3
        self.att_dB = 20.0
        self.tau_mean = 0.8e-3
        self.v_mean = 2.0
        self.v_std = 0.5
        self.k_guard = 4
        
        # AFDM resolution parameters 物理参数转离散参数
        self.delay_resolution = 1 / (self.N_total * self.delta_f)
        self.Doppler_resolution = 1 / (self.N_total * self.T)
        
        # AFDM chirp parameters (will be set based on channel)
        # c1: controls delay-Doppler coupling, should be sufficiently small irrational
        # c2: controls Doppler separation, typically c2 = (k_max + 1) / (2 * N_total)
        self.c1 = 0  # default, will be updated
        self.c2 = 0  # default, will be updated
        self.k_max_default = 2  # UWA default Doppler cap for N_total=100

        # Set default chirp parameters
        self._set_chirp_parameters(self.k_max_default)
        
        # === Physical caps for MATLAB-style UWA port ===
        # With N_total=100 and delta_f=15 Hz:
        #   delay_resolution = 1/(N*delta_f) = 666.7 us
        # MATLAB tau_spread = 10 ms → ~15 delay bins at this AFDM resolution.
        # Keep l_max_cap=15 so the full modeled delay spread remains representable.
        # Doppler is much smaller than terrestrial RF; k_max_cap=2 is sufficient
        # for the MATLAB v_mean=2 m/s, v_std=0.5 m/s UWA regime.
        self.l_max_cap = 15
        self.k_max_cap = self.k_max_default
        K_factor_check = 2 * self.k_max_cap + 1
        self.delta_max = self.k_max_cap + K_factor_check * self.l_max_cap
        self.max_delay_supported_s = self.l_max_cap * self.delay_resolution
        self.max_delay_idx_bar_supported = int(np.floor(self.max_delay_supported_s / self.Ts)) + 1
        self.uwa_resample_max_tries = 32

        # ── Fractional Doppler parameters (mirrors MATLAB AFDM_LEO_frac_switch.m) ──
        # use_frac_doppler=True  : Dirichlet-kernel decomposition of each physical path into
        #                          (2*k_leak+1) integer-bin virtual taps (MATLAB fractional mode).
        # use_frac_doppler=False : hard-round k_real to nearest integer bin (MATLAB integer mode).
        # UWA default is True: acousticChannelEnhanced produces inherently fractional Doppler
        # (v_mean=2 m/s → k_real≈0.02 for N=100), so integer rounding collapses all paths to k=0.
        self.use_frac_doppler = True
        self.k_leak = 2    # Dirichlet leakage half-width (matches MATLAB K_LEAK=2)
        self.frac_prune_rel_thres = 0.01  # Dirichlet pruning: drop taps with |a|² < thres * max(|a|²)
        self._P_actual = self.P_paths     # virtual-tap count after Dirichlet expansion (updated per channel)
        # Baseline toggles for controlled MATLAB-vs-Python ablations.
        self.sp_pilot_kind = 'zc'               # {'zc', 'random-qpsk'}
        self.gen_h_daft_convention = 'python'   # {'python', 'matlab'}
        self.baseline_phase_convention = 'python'  # {'python', 'matlab'}
        self.baseline_mp_detector = 'pic'       # {'pic', 'bp'}
        self.omp_sparsity_mode = 'p_paths'      # {'p_paths', 'p_actual'}
        # SP mode: no guard overhead — guard feasibility assertion removed.
        # Backward-compat note:
        # Some trainer/test code still samples a dummy max_speed_kmh value and passes
        # it into generate_channel_matrix(...). The UWA generator ignores that input,
        # but we keep this attribute so those callers continue to work unchanged.
        self.max_speed_kmh = (self.v_mean + 3.0 * self.v_std) * 3.6
        # ── SP power split ─────────────────────────────────────
        assert 0 < rho < 1, f"rho must be in (0,1), got {rho}"
        self.rho = rho   # pilot power fraction
        # SP: all N sub-carriers carry data
        self.n_data_sp = self.N_total  # used in E2E pipeline
        
        # Normalized DFT matrix 确保酉矩阵，确保相乘是I单位矩阵
        self.F_N = dft(self.N_total) / np.sqrt(self.N_total)

        # Cache DAFT matrices: c1 and c2 are fixed after __init__
        # (the update call in generate_channel_matrix is commented out).
        # Caching saves 3×N² multiply-adds per training sample → ~4.5× speedup
        # for N=100 with 50k samples.
        self._A, self._A_H = self.build_daft_matrix()

        # DNN model
        self.dnn_model_full = None
        # Global scalar scaling: single scalar per domain (preserves PDP shape)
        self.global_std_X = None   # fitted in generate_training_dataset
        self.global_std_y = None
        self.scaler_X = None        # kept for backward-compat, no longer used
        self.scaler_y = None

        # ── Full-Domain ZC pilot (replaces single-point impulse) ─────────
        self._m0 = self.N_total // 2      # canonical phase anchor (≡ old N//2)
        _r  = 7                            # ZC root, coprime to N_total=100
        _n  = np.arange(self.N_total)
        self._zc_seq  = np.exp(-1j * np.pi * _r * _n**2 / self.N_total)  # (N,)
        self._W_match = self._build_zc_correlation_matrix()               # (N, N)

        # ── Stage-2 (post-SIC) RZF matrix ─────────────────────────────────
        # After SIC, true residual interference ratio γ is determined by
        # Stage-1 actual performance, NOT an optimistic theoretical value.
        #
        # Physical derivation from Stage-1 metrics (logged at runtime):
        #   Stage-1 NMSE ≈ -8dB  → channel error  E|ΔH|²  ≈ 0.16
        #   Stage-1 BER  ≈ 0.095 → symbol error   E|Δx|²  ≈ 0.38·(1-ρ)
        #   Residual energy (data term):  0.38 × 0.7 = 0.266
        #   Residual energy (CE term):    0.16 × 0.7 = 0.112
        #   True γ = (0.266 + 0.112) / 0.70 ≈ 0.54
        #
        # Using γ=0.15 (overoptimistic) gives α_s2≈10.5 → nearly zero-forcing
        # → the matrix violently amplifies the 54% residual noise that still
        # exists, making Stage-2 CE/detection WORSE than Stage-1 (observed:
        # val_channel_est_loss 0.233 > Stage-1 0.161, detection 0.352 > 0.186).
        # Calibrated from multi-SNR diagnostic: observed γ≈0.33 (was 0.55).
        # γ=0.33 gives α_s2≈23.1, matching the actual residual power level.
        _gamma_sic       = 0.33   # calibrated from diagnostic: observed γ≈0.33
        _alpha_s2        = float(self.N_total) * (1.0 - self.rho) * _gamma_sic
        _W_s2_raw        = self._build_zc_correlation_matrix(alpha_override=_alpha_s2)

        # Amplitude-alignment correction:
        # RZF bias β = Nρ/(Nρ+α).  Stage-1 has β_s1=ρ=0.3; Stage-2 has
        # β_s2=ρ/(ρ+(1-ρ)γ).  With γ=0.33: β_s2≈0.565.
        # The CE backbone was pre-trained on Stage-1 features (bias 0.3)
        # and learned a 3.33× internal gain.  Without correction,
        # Stage-2 features yield 0.565×3.33≈1.88× the true channel.
        # Scaling W_s2 by β_s1/β_s2 drives Stage-2 feature bias back to 0.3,
        # so the cloned backbone maps it to the correct amplitude.
        _beta_s1         = self.rho                                          # = 0.3
        _beta_s2         = self.rho / (self.rho + (1.0 - self.rho) * _gamma_sic)  # ≈ 0.565
        self._W_match_s2 = _W_s2_raw * (_beta_s1 / _beta_s2)                # scale ≈0.531

        print(f"AFDM System initialized: N_total={self.N_total} subcarriers (from {N}x{M})")
        print(f"  Chirp parameters: c1={self.c1:.6f}, c2={self.c2:.6f}")
        print(f"  Caps: l_max={self.l_max_cap}, k_max={self.k_max_cap}, "
              f"delta_max={self.delta_max} < N={self.N_total}: "
              f"{'OK' if self.delta_max < self.N_total else 'FAIL'}")
        print(f"  UWA params: fc={self.fc/1e3:.1f} kHz, B={self.B/1e3:.1f} kHz, "
              f"fs={self.fs/1e3:.1f} kHz, Ts={self.Ts*1e6:.1f} us")
        print(f"  UWA channel: P={self.P_paths}, tau_spread={self.tau_spread*1e3:.1f} ms, "
              f"v_mean={self.v_mean:.2f} m/s, v_std={self.v_std:.2f} m/s")
        print(f"  Supported AFDM delay window: {self.max_delay_supported_s*1e3:.1f} ms")
        print(f"  Backward-compat speed cap: {self.max_speed_kmh:.1f} km/h")
        print(f"  Channel matrix size: {self.N_total}x{self.N_total}")

    def _set_chirp_parameters(self, k_max_int: int, xi_nu: int = 0, d_min: int = 1):
        """
        Set AFDM chirp parameters c1 and c2.
        
        c1 = (2k_max + 1) / (2 * N_total)
            Ensures different Doppler paths are separated in DAFT domain.
        
        c2: A sufficiently small irrational-like number to ensure full diversity.
              We use c2 = (sqrt(2) - 1) / (2 * N_total^2) as a practical choice.
        
        Args:
            k_max_int: Maximum expected integer Doppler index
        """
        if k_max_int < 0:
            raise ValueError("k_max_int must be non-negative")
        if xi_nu < 0:
            raise ValueError("xi_nu must be non-negative")
        if d_min < 1:
            raise ValueError("d_min must be >= 1")
        
        N = int(self.N_total)
        self.k_max_default = k_max_int
        k_prime = k_max_int + xi_nu
        self.c1 = (2.0 * k_prime + 1.0) / (2.0 * N * d_min)
        # c1: small irrational-like value for full rank guarantee
        self.c2 = (np.sqrt(2.0) - 1.0) / (2.0 * (N ** 2))
        return self.c1, self.c2

    def build_lambda_matrix(self, c_param):
        """
        Build quadratic phase diagonal matrix Lambda_c.
        
        Lambda_c[n, n] = exp(j * 2 * pi * c_param * n^2), n = 0, 1, ..., N_total-1
        
        Args:
            c_param: Chirp parameter (c1 or c2)
            
        Returns:
            Lambda: N_total x N_total diagonal matrix
        """
        n = np.arange(self.N_total)
        diag_elements = np.exp(1j * 2 * np.pi * c_param * n ** 2)
        return np.diag(diag_elements)
    
    def build_daft_matrix(self):
        """
        Build DAFT (Discrete Affine Fourier Transform) matrix.
        
        A = Lambda_c2 @ F_N @ Lambda_c1
        
        Returns:
            A: DAFT matrix (N_total x N_total)
            A_H: Conjugate transpose (IDAFT matrix)
        """
        Lambda_c1 = self.build_lambda_matrix(self.c1)
        Lambda_c2 = self.build_lambda_matrix(self.c2)
        
        A = Lambda_c2 @ self.F_N @ Lambda_c1
        A_H = A.conj().T  # IDAFT = A^H (since A is unitary)
        
        return A, A_H
    
    def validate_implementation(self):
        """Validate implementation correctness"""
        print("=== Validating AFDM Implementation ===")
        
        # Check DAFT matrix unitarity: A @ A^H = I
        A, A_H = self.build_daft_matrix()
        is_unitary = np.allclose(A @ A_H, np.eye(self.N_total), atol=1e-10)
        print(f"DAFT matrix is unitary (A @ A^H = I): {is_unitary}")
        
        # Check Lambda matrices
        Lambda_c1 = self.build_lambda_matrix(self.c1)
        Lambda_c2 = self.build_lambda_matrix(self.c2)
        lambda1_unitary = np.allclose(Lambda_c1 @ Lambda_c1.conj().T, np.eye(self.N_total), atol=1e-10)
        lambda2_unitary = np.allclose(Lambda_c2 @ Lambda_c2.conj().T, np.eye(self.N_total), atol=1e-10)
        print(f"Lambda_c1 is unitary: {lambda1_unitary}")
        print(f"Lambda_c2 is unitary: {lambda2_unitary}")
        
        # Check modulation-demodulation consistency (no channel)
        x_test = np.random.randn(self.N_total) + 1j * np.random.randn(self.N_total)
        s = self.afdm_modulation(x_test)
        x_recovered = self.afdm_demodulation(s)
        
        modulation_error = np.linalg.norm(x_test - x_recovered)
        print(f"Modulation-Demodulation error (no channel): {modulation_error:.2e}")
        
        # Check DFT matrix normalization
        Fn_norm = np.linalg.norm(self.F_N @ self.F_N.conj().T - np.eye(self.N_total))
        print(f"DFT matrix normalization error: {Fn_norm:.2e}")
        
        # Check chirp parameters
        print(f"Chirp parameters: c1={self.c1:.8f}, c2={self.c2:.8f}")
        print(f"c2 * N_total = {self.c2 * self.N_total:.4f} (should be > k_max/2)")
        
        print("=== Validation Complete ===\n")
        
        return {
            'daft_unitary': is_unitary,
            'lambda1_unitary': lambda1_unitary,
            'lambda2_unitary': lambda2_unitary,
            'modulation_ok': modulation_error < 1e-10,
            'dft_ok': Fn_norm < 1e-10
        }
    
    def generate_uwa_channel(self):
        """
        Generate MATLAB-style UWA acoustic channel parameters.

        Port of `acousticChannelEnhanced` from MATLAB:
          1. Exponential delay increments with mean `tau_mean`
          2. Exponential power-delay profile with attenuation `att_dB`
             over total delay spread `tau_spread`
          3. Rayleigh path amplitudes + random phases, norm-normalized
          4. Non-uniform Doppler scaling factors a_i = v_i / c_sound with
             per-path Gaussian velocity v_i ~ |N(v_mean, v_std^2)|
          5. Doppler-corrected discrete delay indices delay_idx_bar

        Returns
        -------
        delay_bar     : (P,) float   — corrected path delays in seconds
        gain_tap      : (P,) complex — complex path gains, ||gain_tap||_2 = 1
        delay_idx_bar : (P,) int     — corrected 1-based sample delay indices
        path_var      : (P,) float   — exponential PDP variances before fading
        doppler_a     : (P,) float   — Doppler scaling factor a_i = v_i/c_sound
        velocities    : (P,) float   — per-path velocities in m/s
        resample_attempts : int      — accepted draw count (1 = accepted immediately)
        """
        P = int(self.P_paths)
        max_supported = self.max_delay_idx_bar_supported

        for attempt in range(1, self.uwa_resample_max_tries + 1):
            # 1) Delay distribution (MATLAB: makedist('exponential','mu',tau_mean))
            d_tau = np.random.exponential(scale=self.tau_mean, size=P)
            d_tau_index = np.maximum(1, np.ceil(d_tau / self.Ts).astype(int))
            delay_index = np.cumsum(d_tau_index)
            delay_vec = (delay_index - 1) * self.Ts

            # 2) Gain power model (exponential decay over delay spread)
            alpha = np.log(10 ** (self.att_dB / 10.0)) / self.tau_spread
            path_var = np.exp(-alpha * delay_vec)

            # MATLAB: sigma = sqrt(path_var * 2/(4-pi)); amp = raylrnd(sigma)
            sigma = np.sqrt(path_var * 2.0 / (4.0 - np.pi))
            amp = np.random.rayleigh(scale=sigma)
            amp_norm = np.linalg.norm(amp)
            if amp_norm > 0:
                amp = amp / amp_norm

            phases = 2.0 * np.pi * np.random.rand(P)
            gain_tap = amp * np.exp(1j * phases)

            # 3) Non-uniform Doppler scaling
            velocities = np.abs(self.v_mean + self.v_std * np.random.randn(P))
            doppler_a = velocities / self.c_sound

            # 4) Delay correction under Doppler scaling
            delay_idx_bar = np.maximum(
                1,
                np.ceil(delay_index / (1.0 + doppler_a)).astype(int)
            )

            # Deep-learning-friendly calibration:
            # Reject rare draws whose corrected delay spread exceeds the AFDM
            # support window. This preserves the MATLAB stochastic law while
            # avoiding systematic clipping that would distort labels/features.
            if np.max(delay_idx_bar) <= max_supported:
                delay_bar = (delay_idx_bar - 1) * self.Ts
                return (
                    delay_bar, gain_tap, delay_idx_bar, path_var,
                    doppler_a, velocities, attempt
                )

        # Fallback: if all attempts overflow, clip once and continue.
        delay_idx_bar = np.minimum(delay_idx_bar, max_supported)
        delay_bar = (delay_idx_bar - 1) * self.Ts
        return (
            delay_bar, gain_tap, delay_idx_bar, path_var,
            doppler_a, velocities, self.uwa_resample_max_tries
        )

    def generate_3gpp_channel(self, channel_type='EVA'):
        """
        Backward-compatible wrapper.

        The environment now uses the MATLAB UWA acoustic channel instead of
        terrestrial 3GPP EPA/EVA taps. This wrapper preserves the old API by
        returning delay positions and a normalized PDP derived from one UWA draw.
        The `channel_type` argument is ignored.
        """
        delays, gain_tap, _, _, _, _, _ = self.generate_uwa_channel()
        pdp_linear = np.abs(gain_tap) ** 2
        pdp_linear = pdp_linear / np.sum(pdp_linear) if np.sum(pdp_linear) > 0 else pdp_linear
        return delays, pdp_linear
    
    def _build_circulant_shift_matrix(self, shift):
        """
        Build N_total x N_total circulant (right) shift matrix Pi^shift.
        
        Pi^l shifts a vector circularly to the right by l positions.
        (Pi^l)_{m,n} = delta((m - n - l) mod N_total)
        
        Args:
            shift: Number of positions to shift (integer)
            
        Returns:
            Pi: Circulant shift matrix
        """
        N = self.N_total
        rows = np.arange(N)
        cols = (rows - shift) % N
        Pi = np.zeros((N, N), dtype=complex)
        Pi[rows, cols] = 1.0
        return Pi
        
    def _build_doppler_diagonal_matrix(self, kappa):
        """
        Build Doppler phase diagonal matrix.
        
        Delta_kappa = diag(exp(j * 2 * pi * kappa * n / N_total)), n = 0, ..., N_total-1
        
        This represents the Doppler frequency shift of a path.
        
        Args:
            kappa: Doppler shift index (can be fractional)
            
        Returns:
            Delta: Diagonal Doppler matrix
        """
        n = np.arange(self.N_total)
        diag_elements = np.exp(1j * 2 * np.pi * kappa * n / self.N_total)
        return np.diag(diag_elements)
            
    # ─────────────────────────────────────────────────────────────────────────
    # Fractional-Doppler helpers  (Python ports of MATLAB helper functions)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def dirichlet_alpha(m: float, kappa: float, N: int) -> complex:
        """Dirichlet kernel coefficient for fractional Doppler decomposition.

        Computes the complex weighting of the (k_base + m)-th integer grid bin
        when a path has true Doppler k_base + kappa  (|kappa| ≤ 0.5).

        Matches MATLAB:
            dirichlet_alpha.m / function a = dirichlet_alpha(m, kappa, N)

        Args:
            m:     integer offset relative to the nearest integer bin
            kappa: fractional part of the true Doppler index (|kappa| ≤ 0.5)
            N:     DFT size (self.N_total)

        Returns:
            Complex scalar weighting coefficient.
        """
        x = m + kappa
        if abs(x) < 1e-12:
            return 1.0 + 0j
        denom = np.sin(np.pi * x / N)
        if abs(denom) < 1e-12:
            # L'Hôpital / periodicity: e^{jπ(N-1)x/N}
            return complex(np.exp(1j * np.pi * (N - 1) * x / N))
        return complex(
            np.exp(1j * np.pi * (N - 1) * x / N)
            * np.sin(np.pi * x)
            / (N * denom)
        )

    def gen_h_daft(self,
                   chan_coef: np.ndarray,
                   delay_index: np.ndarray,
                   doppler_index: np.ndarray) -> np.ndarray:
        """Build the N×N DAFT-domain channel matrix from integer tap parameters.

        Uses the Python DAFT convention (Bemani Eq. 3.39):

            H[m, n] += h_i * exp(j*2π * [ -c1*l_i² + c2*(m²-n²) - l_i*n/N ])

        where  m = (n + δ_i) mod N,  δ_i = l_i * K_factor + k_i,
        and  K_factor = round(2 * N * c1).

        IMPORTANT: This is the PYTHON convention (signs of c1, c2 terms differ
        from MATLAB GEN_H_DAFT which uses +c1*l² and c2=0).  The Python chirp
        matrix Lambda_c = diag(exp(+j*2π*c*n²)) produces a different analytical
        formula than MATLAB's convention.

        Args:
            chan_coef:     1-D complex array of length P (tap gains)
            delay_index:   1-D int array of length P (delay bin indices l_i ≥ 0)
            doppler_index: 1-D int array of length P (Doppler bin indices k_i)

        Returns:
            H: (N_total × N_total) complex channel matrix in DAFT domain.
        """
        N, c1 = self.N_total, self.c1
        convention = getattr(self, 'gen_h_daft_convention', 'python')
        c2 = 0.0 if convention == 'matlab' else self.c2
        K_factor = max(int(np.round(2 * N * c1)), 1)
        H = np.zeros((N, N), dtype=complex)
        n_arr = np.arange(N, dtype=np.float64)
        for i in range(len(chan_coef)):
            l_i = int(delay_index[i])
            k_i = int(doppler_index[i])
            if convention == 'matlab':
                q_arr = n_arr
                loc_val = k_i + 2.0 * N * c1 * l_i
                p_arr = np.mod(np.round(q_arr - loc_val).astype(int), N)
                phase = (2.0 * np.pi / N) * (
                    N * c1 * (l_i ** 2)
                    - q_arr * l_i
                    + N * c2 * (q_arr ** 2 - p_arr.astype(np.float64) ** 2)
                )
                H[p_arr, np.arange(N)] += chan_coef[i] * np.exp(1j * phase)
            else:
                delta = l_i * K_factor + k_i
                m_arr = ((n_arr.astype(int) + delta) % N)
                m_arr_f = m_arr.astype(np.float64)
                phase = (2.0 * np.pi) * (
                    -c1 * (l_i ** 2)
                    + c2 * (m_arr_f ** 2 - n_arr ** 2)
                    - float(l_i) * n_arr / N
                )
                H[m_arr, np.arange(N)] += chan_coef[i] * np.exp(1j * phase)
        return H

    def generate_channel_matrix(self, max_speed_kmh=300, channel_type='EVA'):
        """
        Generate AFDM channel matrix using the MATLAB UWA acoustic model.

        Backward compatibility:
        - `max_speed_kmh` is accepted but ignored
        - `channel_type` is accepted but ignored

        Physical model ported from MATLAB `AFDM_UWA_IDMA.m`:
          1. Draw UWA path delays / gains / Doppler-scaling factors
          2. Map physical delays to AFDM delay bins via `self.delay_resolution`
          3. Map MATLAB normalized Doppler D_i = a_i * fc / fs to AFDM bins via
             k_i = round(D_i * N_total), then clip to system design cap
          4. Build H_time = Σ_i g_i · Δ(k_i) · Π^{l_i}
          5. Normalize Frobenius norm to sqrt(N_total), matching MATLAB
          6. Compute H_eff = A @ H_time @ A^H

        Returns:
            H_eff: Effective channel matrix in DAFT domain (N_total x N_total)
            H_time: Time-domain channel matrix (N_total x N_total)
            channel_params: Dictionary of channel parameters
        """
        delays, g_i_raw, delay_idx_bar, path_var, doppler_a, velocities, resample_attempts = \
            self.generate_uwa_channel()
        taps = len(g_i_raw)

        # Delay mapping: physical UWA delays → AFDM delay bins
        l_i = np.round(delays / self.delay_resolution).astype(int)
        l_i = np.clip(l_i, 0, self.l_max_cap)
        collision = getattr(self, 'delay_collision', None)
        if collision == 'neighbor':
            if taps < 2:
                raise ValueError('neighbor delay collision requires at least two paths')
            l_i = np.array(l_i, dtype=int, copy=True)
            l_i[1] = int(np.clip(int(l_i[0]) + 1, 0, self.l_max_cap))
            if l_i[1] == l_i[0]:
                l_i[0] = int(np.clip(int(l_i[1]) - 1, 0, self.l_max_cap))
            if l_i[0] == l_i[1]:
                raise ValueError('neighbor delay collision could not be realized')
        elif collision not in (None,):
            raise ValueError('unknown delay_collision')

        # ── Doppler: physical continuous Doppler → AFDM bin indices ──────────
        # D_i = a_i * fc / fs  (MATLAB normalized Doppler, dimensionless)
        # k_real_i = D_i * N_total  (un-rounded, continuous fractional bin index)
        D_vals  = doppler_a * self.fc / self.fs
        k_real  = D_vals * self.N_total
        k_clip  = min(self.k_max_cap,
                      int(np.floor(self.N_total / 2) - self.k_guard - 1))
        k_real  = np.clip(k_real, -float(k_clip), float(k_clip))
        k_max   = float(np.max(np.abs(k_real))) if taps > 0 else 0.0

        # ── Doppler quantization: integer or fractional (Dirichlet) mode ─────
        #
        # INTEGER MODE  (self.use_frac_doppler = False):
        #   Round each physical k_real to the nearest integer bin.
        #
        # FRACTIONAL MODE  (self.use_frac_doppler = True,  default):
        #   Each physical path is decomposed into (2*k_leak + 1) virtual integer-
        #   bin taps via the Dirichlet kernel (mirrors MATLAB AFDM_UWA_acoustic.m
        #   with USE_FRAC_DOPPLER=true, K_LEAK=5).  This creates a sparse integer-
        #   indexed representation that is compatible with GEN_H_DAFT / gen_h_daft
        #   and the downstream OMP / joint-MP channel estimators.
        if not self.use_frac_doppler:
            # ── Integer mode ──────────────────────────────────────────────────
            k_int_all = np.round(k_real).astype(int)
            k_int_all = np.clip(k_int_all, -k_clip, k_clip)
            chan_coef_exp = list(g_i_raw)
            l_exp         = list(l_i.astype(int))
            k_exp         = list(k_int_all)
            k_max_int     = int(np.max(np.abs(k_int_all))) if taps > 0 else 0
            # Per-path k_i stored as integer for channel_params
            k_i_stored = k_int_all.astype(float)
        else:
            # ── Fractional (Dirichlet decomposition) mode ─────────────────────
            # Each physical path i → 2*k_leak+1 virtual integer taps, where
            #   virtual_k = k_base + m,   m ∈ {-k_leak, …, +k_leak}
            #   virtual_gain = g_i * dirichlet_alpha(m, kappa, N),  energy-normalised
            chan_coef_exp = []
            l_exp         = []
            k_exp         = []
            m_range       = np.arange(-self.k_leak, self.k_leak + 1, dtype=int)
            prune_thres   = self.frac_prune_rel_thres
            for i in range(taps):
                k_base = int(np.round(k_real[i]))
                kappa  = k_real[i] - k_base      # fractional residual |kappa| ≤ 0.5
                # Dirichlet weights for this path
                a_vec  = np.array(
                    [self.dirichlet_alpha(int(m), kappa, self.N_total) for m in m_range],
                    dtype=complex
                )
                # Energy-normalise (matches MATLAB: a_vec = a_vec / sqrt(sum(|a_vec|^2)))
                a_norm = np.sqrt(np.sum(np.abs(a_vec) ** 2) + 1e-300)
                a_vec /= a_norm
                # Amplitude pruning: drop weak Dirichlet sidelobes
                # (mirrors MATLAB FRAC_PRUNE_REL_THRES = 0.01)
                a_pow = np.abs(a_vec) ** 2
                a_peak = np.max(a_pow)
                for mm, m in enumerate(m_range):
                    k_eff = k_base + int(m)
                    if abs(k_eff) > k_clip:
                        continue   # discard out-of-range virtual taps
                    if a_pow[mm] < prune_thres * a_peak:
                        continue   # prune weak Dirichlet sidelobe
                    chan_coef_exp.append(g_i_raw[i] * a_vec[mm])
                    l_exp.append(int(l_i[i]))
                    k_exp.append(k_eff)
            k_max_int   = int(max((abs(k) for k in k_exp), default=0))
            k_i_stored  = k_real   # keep physical fractional value for diagnostics

        P_actual = len(chan_coef_exp)
        self._P_actual = P_actual  # store for OMP sparsity

        # ── Build H_eff via gen_h_daft (analytical DAFT formula) ──────────────
        # gen_h_daft requires integer delay + Doppler indices and produces the
        # DAFT-domain (H_eff) matrix directly from the expanded virtual taps.
        chan_coef_arr = np.array(chan_coef_exp, dtype=complex)
        l_arr         = np.array(l_exp,         dtype=int)
        k_arr         = np.array(k_exp,         dtype=int)

        if P_actual > 0:
            H_eff_unnorm = self.gen_h_daft(chan_coef_arr, l_arr, k_arr)
        else:
            H_eff_unnorm = np.zeros((self.N_total, self.N_total), dtype=complex)

        # Frobenius normalisation: ||H_eff||_F = sqrt(N)  (matches MATLAB)
        H_fro = np.linalg.norm(H_eff_unnorm, 'fro')
        if H_fro > 0:
            scale          = np.sqrt(float(self.N_total)) / H_fro
            H_eff          = H_eff_unnorm * scale
            chan_coef_arr *= scale
        else:
            scale = 1.0
            H_eff = H_eff_unnorm

        # Back-compute normalised physical path gains (for diagnostics / RL reward)
        g_i  = g_i_raw * scale
        # H_time (time-domain): invert DAFT transform for backward compatibility
        # H_time = A^H @ H_eff @ A
        H_time = self._A_H @ H_eff @ self._A

        channel_params = {
            'g_i':              g_i,
            'g_i_raw':          g_i_raw,
            'l_i':              l_i,
            'k_i':              k_i_stored,
            'k_real':           k_real,           # continuous physical Doppler bins
            'k_max':            k_max,
            'k_max_int':        k_max_int,
            'delay_spread':     int(np.max(l_i)) if taps > 0 else 0,
            'taps':             taps,
            'P_actual':         P_actual,         # expanded virtual tap count
            'chan_coef_exp':     chan_coef_arr,    # expanded (normalised) gains
            'l_exp':            l_arr,            # expanded delay indices
            'k_exp':            k_arr,            # expanded integer Doppler indices
            'delay_idx_bar':    delay_idx_bar,
            'delay_seconds':    delays,
            'path_var':         path_var,
            'doppler_a':        doppler_a,
            'velocities_ms':    velocities,
            'resample_attempts':resample_attempts,
            'fro_scale':        scale,
            'use_frac_doppler': self.use_frac_doppler,
            'k_leak':           self.k_leak if self.use_frac_doppler else 0,
            'channel_model':    'uwa_acoustic',
            'c1':               self.c1,
            'c2':               self.c2,
        }

        return H_eff, H_time, channel_params
    
    def generate_pilot_frame(self, pilot_density=None, guard_factor=None,
                              rho_override=None):
        """
        Generate AFDM **Superimposed Pilot (SP)** frame.

        SP design (power-boosted additive overlay):
          x_frame[m]  = sqrt(1 - rho) * d[m]   for all m in [0, N)
          x_frame[m0] += sqrt(rho * N) * p       (additive pilot at centre)

        where d[m] ~ QPSK and p = (1+j)/sqrt(2) (unit-energy QPSK symbol).

        Power accounting (per sub-carrier):
          Data energy per sub-carrier      = (1 - rho)   [from sqrt(1-rho) * QPSK]
          Pilot energy spread over N taps  = rho*N / N = rho
          Total energy per sub-carrier     = (1-rho) + rho = 1.0  ✓

        Full-domain ZC design (this implementation):
          pilot[n] = sqrt(rho) * zc[n]  for ALL n in [0, N)
          Power per sub-carrier = rho; total pilot power = rho * N.

        No guard interval is required — data symbols are treated as coloured
        noise by the CNN channel estimator.

        Args:
            pilot_density  : ignored (kept for API compatibility with old EP code)
            guard_factor   : ignored (kept for API compatibility)
            rho_override   : if given, use this rho instead of self.rho

        Returns (all consistent with the old EP API so callers need minimal change):
            x_frame          : (N,) complex — DATA-only frame (pilot NOT yet added).
                               Callers that need the full SP frame should build:
                                   x_full = x_frame + x_pilot_only
                               where x_pilot_only is the second return value.
            pilot_positions  : (N,) int array — all N subcarriers [0..N-1]
            pilot_symbols    : (N,) complex array — sqrt(rho) * zc_seq
            guard_positions  : (0,) empty int array — SP has no guards
            data_positions   : (N,) int array — all N sub-carriers carry data
        """
        N   = self.N_total
        rho = rho_override if rho_override is not None else self.rho
        pilot_positions = np.arange(N, dtype=int)            # all N subcarriers
        pilot_kind = getattr(self, 'sp_pilot_kind', 'zc')
        if pilot_kind == 'random-qpsk':
            qpsk = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
            pilot_symbols = np.sqrt(rho) * qpsk[np.random.randint(0, 4, N)]
        else:
            pilot_symbols = np.sqrt(rho) * self._zc_seq        # (N,) complex
        # Power: |sqrt(rho)*zc[n]|^2 = rho per subcarrier → total = rho*N ✓

        # ── Guard: empty (SP has no guard interval) ────────────────
        guard_positions = np.array([], dtype=int)

        # ── Data: all N sub-carriers ───────────────────────────────
        data_positions = np.arange(N, dtype=int)

        # ── Frame: data-only portion (scaled QPSK) ─────────────────
        # Actual SP frame = x_frame + x_pilot_only (assembled by callers).
        # x_frame here carries zeros; callers fill data_positions with
        # sqrt(1 - rho) * QPSK symbols and then add pilot_only separately.
        x_frame = np.zeros(N, dtype=complex)

        return x_frame, pilot_positions, pilot_symbols, guard_positions, data_positions
    
    
    def afdm_modulation(self, x_daft):
        """
        AFDM modulation: DAFT domain -> time domain
        
        s = A^H @ x = Lambda_c1^H @ F^H @ Lambda_c2^H @ x
        
        Args:
            x_daft: DAFT-domain symbol vector (N_total,)
            
        Returns:
            s: Time-domain signal (N_total,)
        """
        return self._A_H @ x_daft
    
    def afdm_demodulation(self, r):
        """
        AFDM demodulation: time domain -> DAFT domain
        
        y = A @ r = Lambda_c2 @ F @ Lambda_c1 @ r
        
        Args:
            r: Time-domain received signal (N_total,)
            
        Returns:
            y: DAFT-domain received signal (N_total,)
        """
        return self._A @ r
    
    def add_awgn(self, signal, snr_db, reference="adaptive"):
        """Add AWGN noise to signal.

        reference:
          - "adaptive" (default, legacy): sigma^2 = mean(|signal|^2) / SNR.
            Gives per-sample received SNR; absorbs Tx power changes into the
            noise scaling, so rho/pilot-power trade-offs are not physically
            comparable across rho.
          - "fixed": sigma^2 = 1 / SNR. Matches the MATLAB convention
            (unit total Tx power Es/N0); rho trade-offs are physically
            interpretable.
        """
        SNR = 10 ** (snr_db / 10)
        if reference == "fixed":
            sigma_w_2 = 1.0 / SNR
        elif reference == "adaptive":
            Es = np.mean(np.abs(signal) ** 2)
            if Es < 1e-10:
                Es = 1.0
            sigma_w_2 = Es / SNR
        else:
            raise ValueError(f"unknown awgn reference '{reference}', expected 'adaptive' or 'fixed'")

        noise = np.sqrt(sigma_w_2 / 2) * (
            np.random.randn(len(signal)) + 1j * np.random.randn(len(signal)))

        return signal + noise, sigma_w_2
    
    def calculate_nmse(self, H_true, H_est):
        """
        Calculate NMSE: ||H_true - H_est||_F^2 / ||H_true||_F^2
        """
        error = H_true - H_est
        mse = np.mean(np.abs(error) ** 2)
        norm_squared = np.linalg.norm(H_true, 'fro') ** 2
        
        if norm_squared == 0:
            return float('inf') if mse > 0 else 0
        
        nmse = mse * H_true.size / norm_squared
        return nmse
    
    # ================================================================
    # Core reconstruction + de-chirp/re-chirp methods
    # ================================================================
    
    def _reconstruct_H_eff_from_taps(self, h_tap, m0, threshold_db=-30):
        """
        Reconstruct full H_eff from DAFT-domain tap estimates using
        Bemani (2023) Eq. (3.39) + Algorithm 5.2.2.
        
        Vectorized implementation: inner loop over n replaced by NumPy
        array operations, yielding ~100x speedup for N=100.
        
        Three-step process per significant tap:
        A. Parameter Extraction: delta → (l_i, k_i)
        B. Phase Stripping: h_obs / phase_at_m0 → h_i
        C. Analytical Synthesis: vectorized Eq. (3.39) over all columns
        """
        N = self.N_total
        c1 = self.c1
        c2 = self.c2
        
        H_est = np.zeros((N, N), dtype=complex)
        
        # Identify significant taps (avoid spreading noise)
        tap_power = np.abs(h_tap) ** 2
        max_tap_power = np.max(tap_power) if np.max(tap_power) > 0 else 1.0
        threshold = max_tap_power * (10 ** (threshold_db / 10))
        significant_taps = np.where(tap_power > threshold)[0]
        
        if len(significant_taps) == 0:
            return H_est
        
        # Derive K_factor = 2*N*c1 = 2*k_max + 1 (from Algorithm 5.2.2)
        K_factor = max(int(np.round(2 * N * c1)), 1)
        k_max = (K_factor - 1) // 2
        
        # Pre-allocate column index array for vectorized synthesis
        n_arr = np.arange(N)
        
        for delta in significant_taps:
            # Step A: Parameter Extraction (Algorithm 5.2.2)
            val = (delta + k_max) % N
            l_i = val // K_factor
            # k_i = (val % K_factor) - k_max  # not needed for reconstruction
            
            # Step B: Phase Stripping — recover pure complex gain h_i
            h_obs = h_tap[delta]
            m_obs = (m0 + delta) % N
            
            phase_at_m0 = np.exp(1j * 2 * np.pi * (
                -c1 * (l_i ** 2) +
                c2 * (m_obs ** 2 - m0 ** 2) -
                (l_i * m0) / N
            ))
            h_i = h_obs / phase_at_m0  # |phase_at_m0| ≡ 1, always safe
            
            # Step C: Vectorized Analytical Synthesis via Eq. (3.39)
            # For all columns n simultaneously:
            #   m = (n + delta) mod N
            #   H_eff[m, n] += h_i * exp(j*2π*(c1*l² - c2*(m²-n²) - l*n/N))
            #
            # Note: n → (n+delta)%N is a bijection, so no duplicate indices.
            m_arr = (n_arr + delta) % N
            
            phase_reconst = np.exp(1j * 2 * np.pi * (
                -c1 * (l_i ** 2) +
                c2 * (m_arr.astype(np.float64) ** 2 - n_arr.astype(np.float64) ** 2) -
                (l_i * n_arr.astype(np.float64)) / N
            ))
            
            H_est[m_arr, n_arr] += h_i * phase_reconst
        
        return H_est
    
    def _dechirp(self, h_tap, m0=None):
        """
        De-chirp: remove the c2 quadratic phase term from h_tap.

        FIX: The correct phase to remove is from Eq. (3.39) evaluated at
        column n=m0. The c2-related phase per tap delta is:
            -c2 * (m_obs^2 - m0^2)
        where m_obs = (m0 + delta) % N.

        The old code only removed c2*delta^2, which missed the cross-term
        -2*c2*m0*delta, leaving a fast linear phase ramp that turned the
        2D grid into a high-frequency zebra pattern.

        Args:
            h_tap: 1D tap vector (N_total,), indexed by delta
            m0: Pilot position. If None, uses N//2 (default pilot location)
        """
        N = self.N_total
        if m0 is None:
            m0 = N // 2
        delta_arr = np.arange(N)
        m_obs_arr = (m0 + delta_arr) % N
        # Correct: remove -c2*(m_obs^2 - m0^2) → multiply by exp(+j*2π*c2*(m_obs^2-m0^2))
        dechirp_factor = np.exp(1j * 2 * np.pi * self.c2 * (
            m_obs_arr.astype(np.float64) ** 2 - float(m0) ** 2))
        return h_tap * dechirp_factor

    def _rechirp(self, h_tap_dechirped, m0=None):
        """
        Re-chirp: restore c2 quadratic phase after DNN prediction.

        Inverse of _dechirp: multiply by exp(-j*2π*c2*(m_obs^2 - m0^2)).

        Args:
            h_tap_dechirped: De-chirped tap vector (N_total,)
            m0: Pilot position. If None, uses N//2
        """
        N = self.N_total
        if m0 is None:
            m0 = N // 2
        delta_arr = np.arange(N)
        m_obs_arr = (m0 + delta_arr) % N
        rechirp_factor = np.exp(-1j * 2 * np.pi * self.c2 * (
            m_obs_arr.astype(np.float64) ** 2 - float(m0) ** 2))
        return h_tap_dechirped * rechirp_factor

    def _build_zc_correlation_matrix(self, alpha_override=None):
        """
        Precompute N × N Regularized Zero-Forcing (RZF) matrix W_match.

        Signal model (DAFT domain):
            y = V @ h_tap + data_interference + noise
            V[m, delta] = (phase_ch(m,l) / phase_m0(delta,l)) * sqrt(rho)*zc[(m-delta)%N]

        The Matched Filter (MF) approximation W = V^H / scale suffers from
        self-interference because ZC sequences are NOT orthogonal under the
        AFDM non-LTI channel (V^H V off-diag RMS ≈ 2.78 for typical params).
        Pure ZF (V^{-1}) amplifies the ~24% model error from the home_row
        nearest-center approximation (fractional delay) by cond(V) ≈ 93x.

        RZF adds Tikhonov regularization to balance model mismatch vs noise:
            W_match = (V^H V + α I)^{-1} V^H
            α = N * (1 - rho)   [data interference power, theory-motivated]

        Empirical validation (EVA, 30 km/h, 500 trials, 20 dB SNR):
            MF  H_eff NMSE = +4.91 dB  BER = 0.446
            RZF H_eff NMSE = -1.29 dB  BER = 0.389   (best NMSE, α = N*(1-ρ) = 70)
            Genie (perfect CSI)         BER = 0.001   (system ceiling)

        Phase convention (compatible with _dechirp / _reconstruct_H_eff):
            n_m      = (m - delta) % N
            phase_ch = exp(j2π(-c1·l² + c2·(m²-n²) - l·n/N))
            phase_m0 = exp(j2π(-c1·l² + c2·(m_obs²-m0²) - l·m0/N))
                       where m_obs = (m0+delta)%N, l = home_row[delta]

        Returns: W_match (N, N) complex128
        """
        N   = self.N_total
        c1  = self.c1
        c2  = self.c2
        rho = self.rho
        m0  = self._m0

        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        centers    = np.arange(L_max) * K_factor
        delta_all  = np.arange(N)[:, None]
        diffs      = np.abs(delta_all - centers[None, :])
        circ_dists = np.minimum(diffs, N - diffs)
        home_row   = np.argmin(circ_dists, axis=1)           # (N,) int

        m_arr    = np.arange(N, dtype=np.float64)            # (N,)
        x_p_full = np.sqrt(rho) * self._zc_seq              # (N,) pilot DAFT sequence

        # ── Build observation matrix V (N×N) ──────────────────────────────
        # V[:,delta] is the received pilot vector when h_tap = e_delta
        V = np.zeros((N, N), dtype=complex)
        for delta in range(N):
            l     = int(home_row[delta])
            n_arr = (np.arange(N, dtype=int) - delta) % N   # source indices
            n_f   = n_arr.astype(np.float64)

            # AFDM channel phase from source n_arr[m] to receive m
            phase_ch = np.exp(1j * 2 * np.pi * (
                -c1 * float(l)**2
                + c2 * (m_arr**2 - n_f**2)
                - float(l) * n_f / N
            ))

            # Normalise to column-m0 tap convention (compatible with _dechirp)
            m_obs = float((m0 + delta) % N)
            phase_m0 = np.exp(1j * 2 * np.pi * (
                -c1 * float(l)**2
                + c2 * (m_obs**2 - float(m0)**2)
                - float(l) * float(m0) / N
            ))

            V[:, delta] = (phase_ch / phase_m0) * x_p_full[n_arr]

        # ── Regularized ZF: W = (V^H V + α I)^{-1} V^H ───────────────────
        # Default α = N*(1-rho): equals expected data-interference power per tap;
        # empirically confirmed as NMSE-optimal via grid search over EVA/EPA.
        # alpha_override lets callers build Stage-2 (post-SIC) lighter matrices.
        alpha = alpha_override if alpha_override is not None else float(N) * (1.0 - rho)
        V_H = V.conj().T
        W_match = np.linalg.solve(V_H @ V + alpha * np.eye(N, dtype=complex), V_H)

        return W_match

    def _correlate_with_pilot(self, y_daft):
        """
        Regularized Zero-Forcing (RZF) pilot correlator: h_tap = W_match @ y_daft.

        W_match = (V^H V + α I)^{-1} V^H,  α = N*(1-rho)
        (see _build_zc_correlation_matrix for full derivation)

        Used by:
          - extract_dnn_features()  → DNN input features (training + inference)
          - improved_ls_estimation() → LS/MMSE baseline
          - _lmmse_detect_np()       → direct ZC+LMMSE equalizer

        Returns: h_tap (N,) complex — values compatible with _dechirp convention.
        """
        return self._W_match @ y_daft

    def _lmmse_detect_np(self, H_est, y_daft, x_p_frame, data_pos, sigma_w2):
        """
        NumPy LMMSE detection with robust regularization for imperfect CSI.

        After pilot cancellation the residual is:
            y_d = H_hat·x_data + ΔH·x_full + noise
        With imperfect channel estimation, the effective noise power is
        σ²_eff = σ²_w + ||ΔH||²_F / N (channel estimation error contribution).

        Standard LMMSE uses reg = σ²/P_data, which is optimal with perfect CSI.
        At high SNR, σ² → 0 but estimation error does not → LMMSE over-inverts.

        Fix: add a regularization floor proportional to channel energy to prevent
        condition-number explosion with imperfect CSI.  The floor ~ 1% of mean
        channel column energy is a practical proxy for the mismatched-CSI
        covariance (Medard 2000).

        H_est:     (N, N) complex — estimated effective channel
        y_daft:    (N,) complex  — received DAFT-domain signal
        x_p_frame: (N,) complex  — pilot-only frame (data positions = 0)
        data_pos:  (n_d,) int
        sigma_w2:  float

        Returns x_hat: (n_d,) complex — LMMSE estimated data symbols
        """
        P_data = 1.0 - self.rho                         # data symbol power
        y_d  = y_daft - H_est @ x_p_frame               # pilot cancellation
        H_d  = H_est[:, data_pos]                        # (N, n_d)
        n_d  = len(data_pos)

        # --- Robust MMSE regularisation ---
        # Nominal: σ²/P_data  (matches MATLAB at moderate SNR)
        reg_nominal = sigma_w2 / max(P_data, 1e-10)
        # Floor: 1% of mean channel column energy — prevents over-inversion
        # when channel estimation error >> thermal noise (high-SNR regime)
        mean_col_energy = np.real(np.sum(np.abs(H_d) ** 2)) / max(n_d, 1)
        reg_floor = 0.01 * mean_col_energy
        sigma_reg = max(reg_nominal, reg_floor)

        G    = H_d.conj().T @ H_d + sigma_reg * np.eye(n_d)
        rhs  = H_d.conj().T @ y_d
        return np.linalg.solve(G, rhs)                   # (n_d,)

    def _generate_clean_h_tap(self, H_eff, m0):
        """
        Extract clean h_tap (column m0 of H_eff) for use as DNN training target.
        
        This is the noise-free ground truth of the channel impulse response
        in the DAFT domain, indexed by delta = (m - m0) mod N.
        
        Args:
            H_eff: True effective channel matrix (N x N)
            m0: Pilot position index
            
        Returns:
            h_tap_clean: Clean tap vector (N,)
        """
        N = self.N_total
        h_col_m0 = H_eff[:, m0]  # m0-th column of H_eff
        
        # Vectorized: delta = (m - m0) % N is a bijection over m in [0,N)
        # so direct array assignment is safe (no collisions).
        m_arr     = np.arange(N)
        delta_arr = (m_arr - m0) % N
        h_tap_clean = np.zeros(N, dtype=complex)
        h_tap_clean[delta_arr] = h_col_m0
        return h_tap_clean
    
    # ================================================================
    # 2D Delay-Doppler grid mapping (for fractional Doppler CNN)
    # ================================================================

    def _get_2d_grid_params(self, pad_size=4):
        """
        Compute 2D grid dimensions.

        FIX: pad_size default raised from 2 → 4.

        Sinc sidelobe attenuation at offset p bins:
          p=1: -13 dB  (main lobe boundary)
          p=2: -18 dB  (marginal)
          p=3: -25 dB  (good)
          p=4: -31 dB  (recommended — covers >99% of Sinc energy)
          p=5: -35 dB  (diminishing returns for typical SNR)

        With K=7, k_max=3, pad=4: W = 2*(3+4)+1 = 15
        l_max_cap=4 → L_max = min(14, 5) = 5
        Total grid: 5 x 15 x 2 = 150 dim
        """
        N = self.N_total
        K_factor = max(int(np.round(2 * N * self.c1)), 1)
        k_max = (K_factor - 1) // 2
        L_max_raw = N // K_factor
        # L_max = min(L_max_raw=14, l_max_cap+1=5) = 5
        L_max = min(L_max_raw, self.l_max_cap + 1)
        W = 2 * (k_max + pad_size) + 1
        return K_factor, k_max, L_max, W, pad_size

    def map_1d_to_2d_grid(self, h_1d, pad_size=4):
        """
        Map 1D DAFT tap vector → 2D (Delay, Doppler) grid via delay-centric
        overlapping extraction.

        For each delay row l:
          center_delta = l * K_factor  (the delta where k=0 lives)
          Window: [center_delta - k_max - pad, center_delta + k_max + pad]
          (circular in delta, so no hard boundary cut)

        This ensures:
        - Fractional Doppler Sinc sidelobes are fully contained in the row
        - No energy is split across two different delay rows
        - Different delay rows have overlapping delta indices (by pad_size)
          but DNN sees the correct spatial arrangement

        Args:
            h_1d: 1D tap vector (N_total,), complex
            pad_size: Sinc tail capture margin (default 4)

        Returns:
            h_2d: 2D grid (L_max, W), complex
        """
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params(pad_size)
        N = self.N_total

        offsets   = np.arange(-(k_max + pad_size), k_max + pad_size + 1)  # (W,)
        centers   = np.arange(L_max) * K_factor                            # (L_max,)
        delta_idx = (centers[:, None] + offsets[None, :]) % N              # (L_max, W)
        return h_1d[delta_idx]

    def map_2d_grid_to_1d(self, h_2d, pad_size=4):
        """
        Map 2D (Delay, Doppler) grid → 1D DAFT tap vector.

        Inverse of map_1d_to_2d_grid. Overlapping delta indices
        (from pad regions of adjacent rows) are averaged.

        Args:
            h_2d: 2D grid (L_max, W), complex
            pad_size: Must match value used in map_1d_to_2d_grid

        Returns:
            h_1d: 1D tap vector (N_total,), complex
        """
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params(pad_size)
        assert h_2d.shape == (L_max, W), (
            f"map_2d_grid_to_1d shape mismatch: "
            f"h_2d.shape={h_2d.shape}, expected ({L_max},{W}). "
            f"Ensure pad_size matches the value used in map_1d_to_2d_grid.")
        N = self.N_total

        offsets   = np.arange(-(k_max + pad_size), k_max + pad_size + 1)  # (W,)
        centers   = np.arange(L_max) * K_factor                            # (L_max,)
        delta_idx = (centers[:, None] + offsets[None, :]) % N              # (L_max, W)
        h_1d  = np.zeros(N, dtype=complex)
        count = np.zeros(N, dtype=float)
        np.add.at(h_1d,  delta_idx.ravel(), h_2d.ravel())
        np.add.at(count, delta_idx.ravel(), 1.0)
        valid = count > 0
        h_1d[valid] /= count[valid]
        return h_1d

    def improved_ls_estimation(self, y_daft, pilot_pos, pilot_syms, guard_pos):
        """
        LS channel estimation for AFDM based on Bemani's embedded pilot scheme.
        
        In AFDM with single embedded pilot at m0:
        - The received signal in the observation window (pilot + guard positions)
          divided by the pilot symbol gives H_eff's m0-th column directly.
        - From this column, physical path parameters (l_i, k_i, h_i) are extracted
          using Algorithm 5.2.2, then H_eff is analytically reconstructed via Eq. (3.39).
        
        Steps:
        1. Extract H_eff[:, m0] from observation window: h_col[m] = y[m] / x_p
        2. Convert to tap representation: h_tap[delta] = h_col[(m0+delta)%N]
        3. Reconstruct full H_eff via parameter extraction + analytical synthesis
        
        Args:
            y_daft: DAFT-domain received signal (N_total,)
            pilot_pos: Pilot positions (should be [m0])
            pilot_syms: Pilot symbols (should be [x_p])
            guard_pos: Guard positions (indices around m0)
            
        Returns:
            H_est: Estimated channel matrix (N_total x N_total)
        """
        N  = self.N_total
        m0 = self._m0
        # Full-domain ZC matched filter: ~N processing gain vs. old single-tap LS
        h_tap = self._correlate_with_pilot(y_daft)
        return self._reconstruct_H_eff_from_taps(h_tap, m0)

    def improved_ls_estimation_2d(self, y_daft, pilot_pos, pilot_syms, guard_pos):
        """
        LS estimation using 2D home_row reconstruction (same path as DNN).

        Diagnostic method: isolates the effect of the reconstruction formula
        from the effect of DNN denoising.  Same tap extraction as
        improved_ls_estimation(), but calls _reconstruct_H_eff_from_taps_2d()
        (home_row nearest-center) instead of _reconstruct_H_eff_from_taps()
        (Algorithm 5.2.2 integer-division).
        """
        N  = self.N_total
        m0 = self._m0
        h_tap = self._correlate_with_pilot(y_daft)
        return self._reconstruct_H_eff_from_taps_2d(h_tap, m0)

    def traditional_mmse_estimation(self, y_daft, pilot_pos, pilot_syms,
                                     guard_pos, sigma_w_2):
        """
        MMSE channel estimation for AFDM.
        
        Refines LS tap estimates using per-tap Wiener filtering under WSSUS,
        then reconstructs H_eff via the same Bemani Eq. (3.39) synthesis.
        
        Steps:
        1. Extract LS tap estimates: h_tap_ls[delta] = y[(m0+delta)%N] / x_p
        2. Per-tap MMSE Wiener filtering (WSSUS: taps are uncorrelated)
        3. Reconstruct H_eff from filtered taps via Eq. (3.39)
        
        Args:
            y_daft: DAFT-domain received signal
            pilot_pos: Pilot positions
            pilot_syms: Pilot symbols  
            guard_pos: Guard positions
            sigma_w_2: Noise variance
            
        Returns:
            H_mmse: MMSE-estimated channel matrix (N_total x N_total)
        """
        N  = self.N_total
        m0 = self._m0
        # ── Full-domain ZC matched filter ─────────────────────────────
        h_tap_ls = self._correlate_with_pilot(y_daft)
        # Corrected noise: data interference (1-rho) + thermal, spread by ZC gain
        # noise_per_tap = ((1-rho) + sigma_w2) / (rho * N)
        noise_per_tap = ((1.0 - self.rho) + sigma_w_2) / (self.rho * N)
        h_tap_power_ls = np.abs(h_tap_ls) ** 2
        R_tap        = np.maximum(h_tap_power_ls - noise_per_tap, 0)
        # Vectorized Wiener filter: denom > 0 always (noise_per_tap > 0)
        wiener_gains = R_tap / (R_tap + noise_per_tap)
        h_tap_mmse   = wiener_gains * h_tap_ls
        return self._reconstruct_H_eff_from_taps(h_tap_mmse, m0)
    

    def _reconstruct_H_eff_from_taps_2d(self, h_tap, m0, threshold_db=-20):
        """
        2D-aware H_eff reconstruction compatible with fractional Doppler.

        Key difference from _reconstruct_H_eff_from_taps:
        - l_i is determined by the 2D ROW INDEX (l = delta // K_factor),
          NOT by Algorithm 5.2.2 integer division on the fractional-leakage delta.
        - Each tap in a given row shares the SAME physical delay l_i,
          even if its delta falls outside the "clean" integer-grid zone.
        - This eliminates the boundary cross-assignment bug that causes
          fractional Doppler sidelobes to be attributed to wrong delays.

        Args:
            h_tap: 1D tap vector (N,) after re-chirp
            m0: Pilot position index
            threshold_db: Noise gate (dB below peak)

        Returns:
            H_est: Estimated N x N effective channel matrix
        """
        N = self.N_total
        c1 = self.c1
        c2 = self.c2
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()
        # L_max is now min(14, 5) = 5  ← only physically valid rows

        H_est   = np.zeros((N, N), dtype=complex)
        tap_power = np.abs(h_tap) ** 2
        max_power = np.max(tap_power) if np.max(tap_power) > 0 else 1.0
        threshold = max_power * (10 ** (threshold_db / 10))
        n_arr   = np.arange(N, dtype=np.float64)

        # Precompute home row for every delta in [0, N-1]
        # using minimum circular distance to row centers.
        # Vectorized: (N,1) - (1,L_max) broadcast → (N, L_max) distance matrix.
        centers   = np.arange(L_max) * K_factor                       # (L_max,)
        delta_all = np.arange(N)[:, None]                              # (N, 1)
        diffs     = np.abs(delta_all - centers[None, :])               # (N, L_max)
        circ_dists = np.minimum(diffs, N - diffs)                      # circular
        home_row  = np.argmin(circ_dists, axis=1)                      # (N,)

        processed = set()
        for l_i in range(L_max):
            center_delta = l_i * K_factor
            for offset in range(-(k_max + pad_size), k_max + pad_size + 1):
                delta = (center_delta + offset) % N
                if home_row[delta] != l_i:
                    continue   # belongs to a different row
                if delta in processed:
                    continue
                processed.add(delta)

                if tap_power[delta] < threshold:
                    continue

                h_obs = h_tap[delta]
                m_obs = (m0 + delta) % N
                phase_at_m0 = np.exp(1j * 2 * np.pi * (
                    -c1 * float(l_i) ** 2
                    + c2 * (float(m_obs) ** 2 - float(m0) ** 2)
                    - float(l_i) * float(m0) / N
                ))
                h_i = h_obs / phase_at_m0

                m_arr   = (n_arr + delta) % N
                m_arr_i = m_arr.astype(int)
                phase_reconst = np.exp(1j * 2 * np.pi * (
                    -c1 * float(l_i) ** 2
                    + c2 * (m_arr ** 2 - n_arr ** 2)
                    - float(l_i) * n_arr / N
                ))
                H_est[m_arr_i, np.arange(N)] += h_i * phase_reconst

        return H_est
    
    
    def extract_dnn_features(self, y_daft, pilot_pos, pilot_syms, guard_pos,
                             pilot_density=None):
        """
        SP-mode feature extractor for the 2D-CNN channel estimator.

        In Superimposed Pilot mode, every sub-carrier carries a data symbol,
        so there are NO quiet guard taps.  The full-N raw tap observation is:

            h_raw[delta] = y[(m0+delta)%N] / x_p
                         ≈ H_eff[m,m0] / |x_p|²·x_p  +  data_interference/x_p  +  noise/x_p

        The 2D CNN is trained to suppress the data-interference (treated as
        structured coloured noise) and recover the clean channel grid.

        Auxiliary features (replace the EP quiet-tap SNR estimators):
          F1: log10(rho)          — pilot power fraction (tells CNN signal-to-data ratio)
          F2: mean received power — total scale of |y_daft|², normalised
          F3: peak-to-average     — peak |h_tap|² relative to all-grid mean
          F4: tap density         — fraction of grid cells above 1% of peak

        Returns:
            features: 1D feature vector (2*L_max*W + 4,)
        """
        N = self.N_total
        m0 = self._m0
        K_factor, k_max, L_max, W, pad_size = self._get_2d_grid_params()

        # ── Build ALL-grid delta set (same as before) ──────────────
        _gd_offs       = np.arange(-(k_max + pad_size), k_max + pad_size + 1)
        _gd_ctrs       = np.arange(L_max) * K_factor
        _gd_idx        = (_gd_ctrs[:, None] + _gd_offs[None, :]) % N   # (L_max, W)
        grid_delta_arr = np.unique(_gd_idx.ravel())                     # sorted unique
        n_grid         = len(grid_delta_arr)

        # ── Full-domain ZC matched filter (~20 dB processing gain) ─
        h_tap = self._correlate_with_pilot(y_daft)            # (N,) complex

        h_tap_dechirped = self._dechirp(h_tap, m0=m0)
        h_2d = self.map_1d_to_2d_grid(h_tap_dechirped, pad_size=pad_size)

        features = [
            np.real(h_2d).flatten(),
            np.imag(h_2d).flatten()
        ]

        # ── SP-specific auxiliary scalars ──────────────────────────
        rho = self.rho

        # Feature 1: pilot power fraction (log scale, normalised to [-1, 0])
        # rho ∈ (0,1) → log10(rho) ∈ (-∞, 0); typical range (-2, 0) → /2 ∈ (-1, 0)
        f1 = float(np.clip(np.log10(max(rho, 1e-4)) / 2.0, -1.0, 0.0))

        # Feature 2: mean received power per sub-carrier (log scale)
        # reflect total signal+noise scale; range ~[-2, 2] → /2 ∈ [-1, 1]
        mean_recv_pwr = float(np.mean(np.abs(y_daft) ** 2))
        f2 = float(np.clip(np.log10(max(mean_recv_pwr, 1e-10)) / 2.0, -1.0, 1.0))

        # Feature 3: peak-to-grid-average of |h_tap|² (channel gain indicator)
        # (peak - average) / average → large when channel has dominant path
        h_tap_power  = np.abs(h_tap[grid_delta_arr]) ** 2
        peak_pwr     = float(np.max(h_tap_power)) if len(h_tap_power) > 0 else 0.0
        mean_pwr     = float(np.mean(h_tap_power)) if len(h_tap_power) > 0 else 1.0
        mean_pwr     = max(mean_pwr, 1e-20)
        f3 = float(np.clip(np.log10(max(peak_pwr / mean_pwr, 1e-6)) / 4.0, 0.0, 1.0))

        # Feature 4: Doppler-spread density (unchanged from EP)
        h_all_power = np.abs(h_tap) ** 2
        n_sig_taps  = int(np.sum(h_all_power > 0.01 * max(peak_pwr, 1e-20)))
        tap_density = float(np.clip(n_sig_taps / max(n_grid, 1), 0.0, 1.0))

        features.append(np.array([f1, f2, f3, tap_density], dtype=np.float32))

        feat = np.concatenate(features)
        expected_dim = L_max * W * 2 + 4
        assert feat.shape[0] == expected_dim, (
            f"Feature dim mismatch: got {feat.shape[0]}, "
            f"expected {expected_dim} (L_max={L_max}, W={W}, pad_size={pad_size})")
        return feat
    
