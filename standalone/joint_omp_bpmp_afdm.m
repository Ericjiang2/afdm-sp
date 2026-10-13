% joint_omp_bpmp_afdm.m  —  Standalone AFDM + OMP + BP-MP joint iterative simulator.
%
% MATLAB twin of joint_omp_bpmp_afdm.py.  Identical parameters, identical
% algorithm (Python phase convention, c2 ≠ 0) so the two scripts are
% algorithmically bit-equivalent up to RNG — enabling tight statistical
% cross-validation of BER-SNR and channel NMSE-SNR curves.
%
% Pipeline per Monte-Carlo frame:
%   1. Draw UWA acoustic channel: 5 Rayleigh paths, exponential PDP.
%   2. Expand fractional Doppler with Dirichlet kernel (K_LEAK=2).
%   3. Build H_eff (N×N), Frobenius-normalised to sqrt(N).
%   4. SP frame: sqrt(1-rho)·QPSK + sqrt(rho)·ZC pilot.
%   5. y_daft = A * H_time * A' * x_full + n;   sigma^2 = 1/SNR.
%   6. Joint OMP↔BP-MP iterative receiver (n_outer=5).
%   7. Record BER (QPSK) and channel NMSE.
%
% Run: >> joint_omp_bpmp_afdm
% Writes: results/ber_nmse.mat, ber_waterfall.png, nmse_curve.png

function joint_omp_bpmp_afdm()

cfg = default_config();
rng(cfg.rng_seed);

snr_list  = cfg.snr_db_list;
n_frames  = cfg.n_frames;
n_snr     = numel(snr_list);
ber_arr   = zeros(1, n_snr);
nmse_arr  = zeros(1, n_snr);

fprintf('channel_type = %s,  pilot_type = %s,  use_frac_doppler = %d\n', ...
    cfg.channel_type, cfg.pilot_type, cfg.use_frac_doppler);
fprintf('# frames/SNR = %d,  N = %d,  rho = %.2f,  l_max = %d,  k_max = %d\n', ...
    n_frames, cfg.N, cfg.rho, cfg.l_max_cap, cfg.k_max_cap);
fprintf('%6s %12s %10s %8s\n', 'SNR_dB', 'BER', 'NMSE_dB', 'time_s');
t0 = tic;
for si = 1:n_snr
    t_snr = tic;
    b_sum = 0; m_sum = 0;
    for f = 1:n_frames
        [b, mse] = run_one_frame(cfg, snr_list(si));
        b_sum = b_sum + b; m_sum = m_sum + mse;
    end
    ber_arr(si)  = b_sum / n_frames;
    nmse_arr(si) = m_sum / n_frames;
    fprintf('%6d %12.4e %10.3f %8.1f\n', snr_list(si), ber_arr(si), ...
        10*log10(max(nmse_arr(si), 1e-30)), toc(t_snr));
end
fprintf('total wall time: %.1f s\n', toc(t0));

if ~exist(cfg.out_dir, 'dir'); mkdir(cfg.out_dir); end
save(fullfile(cfg.out_dir, 'ber_nmse.mat'), 'snr_list', 'ber_arr', 'nmse_arr', 'cfg');

% BER waterfall
fig = figure('Visible', 'off');
semilogy(snr_list, max(ber_arr, 1e-6), 'o-', 'LineWidth', 2); grid on;
xlabel('SNR (dB)'); ylabel('BER');
title('AFDM joint OMP + BP-MP (SP mode, QPSK)');
saveas(fig, fullfile(cfg.out_dir, 'ber_waterfall.png')); close(fig);

% NMSE-SNR
fig = figure('Visible', 'off');
plot(snr_list, 10*log10(max(nmse_arr, 1e-30)), 's-', 'LineWidth', 2); grid on;
xlabel('SNR (dB)'); ylabel('Channel NMSE (dB)');
title('Channel estimation NMSE vs SNR');
saveas(fig, fullfile(cfg.out_dir, 'nmse_curve.png')); close(fig);

fprintf('Saved: %s/ber_nmse.mat, ber_waterfall.png, nmse_curve.png\n', cfg.out_dir);
end

% ============================================================
%  CONFIG
% ============================================================
function cfg = default_config()

% --- scenario selectors ---
cfg.channel_type         = 'uwa';          % 'uwa' | 'leo_ntn'
cfg.pilot_type           = 'random_qpsk';           % 'zc' | 'random_qpsk'

% --- common (preset may fill more below) ---
cfg.rho                  = 0.5;
cfg.use_frac_doppler     = true;
cfg.k_leak               = 2;
cfg.frac_prune_rel_thres = 0.01;

% --- Joint iterative receiver ---
cfg.n_outer_iter         = 7;
cfg.bp_iter              = 20;
cfg.bp_threshold         = 1e-4;
cfg.bp_damp              = 0.5;
cfg.gamma_h              = 0.7;
cfg.gamma_x              = 0.6;
cfg.lambda_ls_factor     = 1e-3;
cfg.tau_h_factor         = 0.01;
cfg.tau_h_sigma_factor   = 0.1;
cfg.eps_stop_rel         = 1e-3;
cfg.update_sigma2        = true;

% --- Monte-Carlo sweep ---
cfg.snr_db_list          = [0 5 10 15 20 25];
cfg.n_frames             = 100;
cfg.rng_seed             = 20260422;
cfg.out_dir              = 'results_matlab';

cfg = resolve_cfg(cfg);
end


% ============================================================
%  Channel presets
% ============================================================
function cfg = resolve_cfg(cfg)
if strcmp(cfg.channel_type, 'uwa')
    preset = uwa_preset();
else
    preset = leo_preset();
end
fn = fieldnames(preset);
for i = 1:numel(fn)
    if ~isfield(cfg, fn{i})
        cfg.(fn{i}) = preset.(fn{i});
    end
end
end


function p = uwa_preset()
p.N                      = 256;
p.zc_root                = 5;
p.fc                     = 12e3;
p.fs                     = 8e3;
p.delta_f                = 15.0;
p.c_sound                = 1500.0;
p.P_paths                = 3;
p.tau_spread             = 10e-3;
p.tau_mean               = 0.8e-3;
p.att_dB                 = 20.0;
p.v_mean                 = 2.0;
p.v_std                  = 0.5;
p.l_max_cap              = 15;
p.k_max_cap              = 2;
p.k_guard                = 4;
p.k_v                    = 0;
p.uwa_resample_max_tries = 32;
end


function p = leo_preset()
p.N                       = 256;
p.zc_root                 = 5;
p.fc                      = 12e9;
p.delta_f                 = 15e3;
p.ntn_profile             = 'NTN-TDL-C';
p.use_dominant_2taps      = false;
p.H_sat                   = 600e3;
p.R_earth                 = 6371e3;
p.G_earth                 = 3.986e14;
p.alpha_min_deg           = 30.0;
p.ue_speed                = 0.0;
p.local_doppler_spread_hz = 50.0;
p.l_max_cap               = 1;
p.k_max_cap               = 16;
p.k_guard                 = 0;
p.k_v                     = 4;
p.P_paths                 = 2;
end


% ============================================================
%  Per-frame
% ============================================================
function [ber, ch_nmse] = run_one_frame(cfg, snr_db)
N = cfg.N; rho = cfg.rho;
[c1, c2] = chirp_params(N, cfg.k_max_cap, cfg.k_v);
[A, AH]  = build_daft_matrix(N, c1, c2);

[H_eff, H_time] = build_channel(cfg, c1, c2, A, AH);

[x_full, data_syms, pilot] = build_sp_frame(cfg);

s_t   = AH * x_full.';                  % AFDM modulate (col vector)
r_t   = H_time * s_t;
[r_n, sigma2] = add_awgn_fixed(r_t, snr_db);
y_d   = A * r_n;                        % DAFT demodulate (col)
y_daft = y_d.';                         % row for downstream consistency

qpsk      = [1+1j, 1-1j, -1+1j, -1-1j] / sqrt(2);
const_d   = sqrt(1.0 - rho) * qpsk;

[x_soft, H_est] = joint_omp_bpmp_iterative(y_daft, pilot, N, c1, c2, ...
    cfg.l_max_cap, cfg.k_max_cap, sigma2, const_d, cfg);

ber     = ber_qpsk(data_syms, x_soft);
ch_nmse = nmse_fn(H_eff, H_est);
end


% ============================================================
%  AFDM physics
% ============================================================
function [c1, c2] = chirp_params(N, k_max, k_v)
if nargin < 3, k_v = 0; end
c1 = (2*(k_max + k_v) + 1) / (2*N);
c2 = (sqrt(2) - 1) / (2 * N^2);
end


function [A, AH] = build_daft_matrix(N, c1, c2)
n = (0:N-1).';
F_N = exp(-1j*2*pi*(n*n.')/N) / sqrt(N);
L1  = diag(exp(1j*2*pi*c1*(n.^2)));
L2  = diag(exp(1j*2*pi*c2*(n.^2)));
A   = L2 * F_N * L1;
AH  = A';
end


function a = dirichlet_alpha(m, kappa, N)
x = m + kappa;
if abs(x) < 1e-12
    a = 1.0 + 0i; return;
end
denom = sin(pi*x/N);
if abs(denom) < 1e-12
    a = exp(1j*pi*(N-1)*x/N); return;
end
a = exp(1j*pi*(N-1)*x/N) * sin(pi*x) / (N*denom);
end


function H = gen_h_daft(N, c1, c2, gains, l_arr, k_arr)
K_factor = max(round(2*N*c1), 1);
H = zeros(N, N);
n_arr = (0:N-1).';        % column
for i = 1:numel(gains)
    l_i = l_arr(i); k_i = k_arr(i);
    delta = l_i * K_factor + k_i;
    m_arr = mod(n_arr + delta, N);
    phase = exp(1j*2*pi*( -c1*(l_i^2) + c2*(m_arr.^2 - n_arr.^2) - l_i*n_arr/N ));
    idx_lin = sub2ind([N N], m_arr+1, n_arr+1);   % +1 for MATLAB indexing
    H(idx_lin) = H(idx_lin) + gains(i) .* phase;
end
end


% ============================================================
%  UWA channel
% ============================================================
function [delays, gain_tap, delay_idx_bar, doppler_a] = generate_uwa_channel(cfg)
P  = cfg.P_paths;
Ts = 1.0 / cfg.fs;
N  = cfg.N;
delay_res = 1.0 / (N * cfg.delta_f);
max_supp  = floor(cfg.l_max_cap * delay_res / Ts) + 1;

for attempt = 1:cfg.uwa_resample_max_tries
    % Inline exprnd:  Exp(mu) sample = -log(U) * mu
    d_tau      = -log(rand(P, 1)) * cfg.tau_mean;
    d_tau_idx  = max(1, ceil(d_tau / Ts));
    delay_index = cumsum(d_tau_idx);
    delay_vec   = (delay_index - 1) * Ts;

    alpha    = log(10^(cfg.att_dB / 10)) / cfg.tau_spread;
    path_var = exp(-alpha * delay_vec);
    sigma    = sqrt(path_var * 2.0 / (4.0 - pi));
    % Inline raylrnd:  Rayleigh(σ) = σ * sqrt(-2*log(U))
    amp      = sigma .* sqrt(-2*log(rand(size(sigma))));
    nrm      = norm(amp);
    if nrm > 0
        amp = amp / nrm;
    end
    phases   = 2*pi * rand(P, 1);
    gain_tap = amp .* exp(1j*phases);

    velocities = abs(cfg.v_mean + cfg.v_std * randn(P, 1));
    doppler_a  = velocities / cfg.c_sound;
    delay_idx_bar = max(1, ceil(delay_index ./ (1.0 + doppler_a)));

    if max(delay_idx_bar) <= max_supp
        delays = (delay_idx_bar - 1) * Ts;
        return;
    end
end
delay_idx_bar = min(delay_idx_bar, max_supp);
delays        = (delay_idx_bar - 1) * Ts;
end


function [gains_ex, l_ex, k_ex] = expand_fractional_doppler(cfg, gain_tap, l_i, k_real)
N       = cfg.N;
k_leak  = cfg.k_leak;
k_clip  = min(cfg.k_max_cap, floor(N/2) - cfg.k_guard - 1);
k_real  = min(max(k_real, -k_clip), k_clip);
prune   = cfg.frac_prune_rel_thres;
m_range = -k_leak:k_leak;

if ~cfg.use_frac_doppler
    k_int    = min(max(round(k_real), -k_clip), k_clip);
    gains_ex = gain_tap(:);
    l_ex     = l_i(:);
    k_ex     = k_int(:);
    return;
end

gains_ex = []; l_ex = []; k_ex = [];
for i = 1:numel(gain_tap)
    k_base = round(k_real(i));
    kappa  = k_real(i) - k_base;
    a_vec  = zeros(numel(m_range), 1);
    for jj = 1:numel(m_range)
        a_vec(jj) = dirichlet_alpha(m_range(jj), kappa, N);
    end
    a_vec = a_vec / sqrt(sum(abs(a_vec).^2) + 1e-300);
    a_pow = abs(a_vec).^2;
    a_peak = max(a_pow);
    for jj = 1:numel(m_range)
        k_eff = k_base + m_range(jj);
        if abs(k_eff) > k_clip, continue; end
        if a_pow(jj) < prune * a_peak, continue; end
        gains_ex(end+1, 1) = gain_tap(i) * a_vec(jj);    %#ok<AGROW>
        l_ex(end+1, 1)     = l_i(i);                      %#ok<AGROW>
        k_ex(end+1, 1)     = k_eff;                       %#ok<AGROW>
    end
end
end


function [H_eff, H_time] = build_channel(cfg, c1, c2, A, AH)
N = cfg.N;
if strcmp(cfg.channel_type, 'leo_ntn')
    [gain_tap, l_i, k_real] = generate_leo_ntn_channel(cfg);
else
    [delays, gain_tap, ~, doppler_a] = generate_uwa_channel(cfg);
    delay_res = 1.0 / (N * cfg.delta_f);
    l_i = min(max(round(delays / delay_res), 0), cfg.l_max_cap);
    D_vals = doppler_a * cfg.fc / cfg.fs;
    k_real = D_vals * N;
end

[gains_ex, l_ex, k_ex] = expand_fractional_doppler(cfg, gain_tap, l_i, k_real);

if isempty(gains_ex)
    H_eff = zeros(N, N);
else
    H_eff = gen_h_daft(N, c1, c2, gains_ex, l_ex, k_ex);
end
fro = norm(H_eff, 'fro');
if fro > 0
    H_eff = H_eff * sqrt(N) / fro;
end
H_time = AH * H_eff * A;
end


% ============================================================
%  Frame / pilot / noise / metrics
% ============================================================
function zc = zc_sequence(N, root)
n  = 0:N-1;
zc = exp(-1j*pi*root*(n.^2)/N);
end


function [x_full, data_syms, pilot] = build_sp_frame(cfg)
N   = cfg.N; rho = cfg.rho;
qpsk  = [1+1j, 1-1j, -1+1j, -1-1j] / sqrt(2);
if strcmp(cfg.pilot_type, 'random_qpsk')
    pilot = sqrt(rho) * qpsk(randi(4, 1, N));
else
    pilot = sqrt(rho) * zc_sequence(N, cfg.zc_root);
end
idx   = randi(4, 1, N);
data_syms = qpsk(idx);
x_full    = sqrt(1.0 - rho) * data_syms + pilot;
end


function [y, sigma2] = add_awgn_fixed(signal, snr_db)
sigma2 = 10^(-snr_db / 10);
n = (randn(size(signal)) + 1j*randn(size(signal))) * sqrt(sigma2/2);
y = signal + n;
end


function ber = ber_qpsk(x_true, x_det)
err_i = mean((real(x_true) > 0) ~= (real(x_det) > 0));
err_q = mean((imag(x_true) > 0) ~= (imag(x_det) > 0));
ber = 0.5 * (err_i + err_q);
end


function val = nmse_fn(H_true, H_est)
num = norm(H_true - H_est, 'fro')^2;
den = norm(H_true, 'fro')^2;
if den > 0
    val = num / den;
else
    val = inf;
end
end


% ============================================================
%  OMP dictionary + solver + H reconstruction
% ============================================================
function Phi = construct_sensing_matrix(N, x_pilot, c1, c2, l_max, k_max)
K = 2*k_max + 1;
Q = (l_max + 1) * K;
q = (0:N-1).';
Phi = zeros(N, Q);
col = 1;
for l = 0:l_max
    for k = -k_max:k_max
        delta = l*K + k;
        p_arr = mod(q - delta, N);
        phase = exp(1j*2*pi*( -c1*(l^2) + c2*(q.^2 - p_arr.^2) - l*p_arr/N ));
        Phi(:, col) = phase .* x_pilot(p_arr + 1).';
        col = col + 1;
    end
end
end


function [h_est, support] = omp_sparse(y, Phi, sparsity)
Q = size(Phi, 2);
residual = y(:);
support  = [];
for it = 1:sparsity
    corr = abs(Phi' * residual);
    corr(support) = 0;
    [~, new_idx] = max(corr);
    support(end+1) = new_idx;     %#ok<AGROW>
    Phi_S = Phi(:, support);
    gains_S = Phi_S \ y(:);
    residual = y(:) - Phi_S * gains_S;
    if norm(residual) < 1e-10 * norm(y)
        break;
    end
end
h_est = zeros(Q, 1);
if ~isempty(support)
    Phi_S = Phi(:, support);
    g_final = Phi_S \ y(:);
    h_est(support) = g_final;
end
end


function H = reconstruct_H_from_support(N, c1, c2, k_max, sup_l, sup_k, gains)
if isempty(sup_l)
    H = zeros(N, N); return;
end
K = 2*k_max + 1;
n_arr = (0:N-1).';
H = zeros(N, N);
for i = 1:numel(sup_l)
    l_i = sup_l(i); k_i = sup_k(i);
    delta = l_i*K + k_i;
    m_arr = mod(n_arr + delta, N);
    phase = exp(1j*2*pi*( -c1*(l_i^2) + c2*(m_arr.^2 - n_arr.^2) - l_i*n_arr/N ));
    idx_lin = sub2ind([N N], m_arr+1, n_arr+1);
    H(idx_lin) = H(idx_lin) + gains(i) .* phase;
end
end


function a_col = build_da_ls_column(N, l_p, k_p, c1, c2, k_max, x_total)
K = 2*k_max + 1;
n_arr = (0:N-1).';
delta = l_p*K + k_p;
m_arr = mod(n_arr + delta, N);
phase = exp(1j*2*pi*( -c1*(l_p^2) + c2*(m_arr.^2 - n_arr.^2) - l_p*n_arr/N ));
a_col = zeros(N, 1);
a_col(m_arr + 1) = phase .* x_total(:);
end


% ============================================================
%  BP-MP (full belief-propagation) detector
% ============================================================
function x_est = mp_detect_bp(y, H, sigma2, constellation, n_iter, thresh, damp)
N = size(H, 1);
if N == 0, x_est = zeros(0, 1); return; end

mask = abs(H) >= thresh;
[row_idx, col_idx] = find(mask);
h_vals = H(sub2ind([N N], row_idx, col_idx));
E = numel(h_vals);
if E == 0, x_est = zeros(N, 1); return; end

row_edges = cell(N, 1); col_edges = cell(N, 1);
for e = 1:E
    row_edges{row_idx(e)}(end+1) = e; %#ok<AGROW>
    col_edges{col_idx(e)}(end+1) = e; %#ok<AGROW>
end

prior_mean = mean(constellation);
prior_var  = var(constellation);
mu_v2o  = prior_mean * ones(E, 1);
var_v2o = prior_var  * ones(E, 1);
mu_o2v  = zeros(E, 1);
var_o2v = ones(E, 1);

for it = 1:n_iter
    mu_old = mu_v2o;

    % Observation -> variable messages
    for d = 1:N
        edges = row_edges{d};
        if isempty(edges), continue; end
        h_d    = h_vals(edges);
        mu_in  = mu_v2o(edges);
        var_in = var_v2o(edges);
        z_total = y(d) - sum(h_d .* mu_in);
        V_total = sigma2 + sum((abs(h_d).^2) .* var_in);
        for li = 1:numel(edges)
            e     = edges(li);
            h_e   = h_d(li); mu_e = mu_in(li); var_e = var_in(li);
            z_ext = z_total + h_e * mu_e;
            V_ext = max(V_total - (abs(h_e)^2) * var_e, sigma2 * 0.1);
            if abs(h_e) > 1e-10
                var_o2v(e) = max(V_ext / (abs(h_e)^2), 1e-10);
                mu_o2v(e)  = z_ext / h_e;
            else
                var_o2v(e) = 1e10;
                mu_o2v(e)  = 0.0;
            end
        end
    end

    % Variable -> observation messages
    for n = 1:N
        edges = col_edges{n};
        if isempty(edges), continue; end
        var_in = var_o2v(edges);
        mu_in  = mu_o2v(edges);
        prec_total = 1.0/prior_var + sum(1.0 ./ var_in);
        mean_total = prior_mean/prior_var + sum(mu_in ./ var_in);
        for ii = 1:numel(edges)
            e = edges(ii);
            var_e = var_o2v(e); mu_e = mu_o2v(e);
            prec_ext = max(prec_total - 1.0/var_e, 1e-10);
            mean_ext = mean_total - mu_e/var_e;
            var_ext  = 1.0 / prec_ext;
            mu_ext   = var_ext * mean_ext;
            dist_sq  = abs(constellation - mu_ext).^2;
            log_prob = -dist_sq / (2.0 * var_ext);
            log_prob = log_prob - max(log_prob);
            prob = exp(log_prob); prob = prob / sum(prob);
            mu_new  = sum(prob .* constellation);
            var_new = max(sum(prob .* (abs(constellation).^2)) - abs(mu_new)^2, 1e-10);
            mu_v2o(e)  = (1.0 - damp) * mu_old(e) + damp * mu_new;
            var_v2o(e) = var_new;
        end
    end

    denom = max(norm(mu_v2o), 1e-10);
    if norm(mu_v2o - mu_old) / denom < 1e-4, break; end
end

x_est = zeros(N, 1);
for n = 1:N
    edges = col_edges{n};
    if isempty(edges)
        x_est(n) = prior_mean; continue;
    end
    var_in = var_o2v(edges); mu_in = mu_o2v(edges);
    prec_total = 1.0/prior_var + sum(1.0 ./ var_in);
    mean_total = prior_mean/prior_var + sum(mu_in ./ var_in);
    var_post = 1.0 / max(prec_total, 1e-10);
    mu_post  = var_post * mean_total;
    [~, mi] = min(abs(constellation - mu_post));
    x_est(n) = constellation(mi);
end
end


% ============================================================
%  Joint OMP + BP-MP iterative receiver
% ============================================================
function [x_soft, H_hat] = joint_omp_bpmp_iterative(y_daft, x_pilot, N, c1, c2, ...
    l_max, k_max, sigma2, constellation, cfg)

K = 2*k_max + 1;
n_paths      = cfg.P_paths;
n_outer      = cfg.n_outer_iter;
k_leak       = cfg.k_leak;
gamma_h      = cfg.gamma_h;
gamma_x      = cfg.gamma_x;
lambda_fac   = cfg.lambda_ls_factor;
tau_hfac     = cfg.tau_h_factor;
tau_sfac     = cfg.tau_h_sigma_factor;
eps_stop     = cfg.eps_stop_rel;
update_s2    = cfg.update_sigma2;

Phi = construct_sensing_matrix(N, x_pilot, c1, c2, l_max, k_max);

H_hat       = zeros(N, N);
x_soft      = zeros(1, N);
sigma2_eff  = sigma2;
lambda_ls   = max(1e-6, lambda_fac * sigma2_eff);
prev_resnorm = inf;

sup_l = []; sup_k = []; gains_S = [];

for outer = 1:n_outer

    % ---- (A) Channel estimation update ----
    if outer == 1
        [h_omp, sup_idx] = omp_sparse(y_daft(:), Phi, n_paths);
        s_l = zeros(numel(sup_idx), 1);
        s_k = zeros(numel(sup_idx), 1);
        s_g = zeros(numel(sup_idx), 1);
        for ii = 1:numel(sup_idx)
            idx = sup_idx(ii);
            s_g(ii) = h_omp(idx);
            l_dec = floor((idx - 1) / K);
            k_dec = mod(idx - 1, K) - k_max;
            s_l(ii) = l_dec;
            s_k(ii) = k_dec;
        end
        % Cluster expansion ±k_leak
        ex_l = []; ex_k = []; ex_g = [];
        for i = 1:numel(s_l)
            for m = -k_leak:k_leak
                k_new = s_k(i) + m;
                if abs(k_new) > k_max, continue; end
                ex_l(end+1, 1) = s_l(i);   %#ok<AGROW>
                ex_k(end+1, 1) = k_new;    %#ok<AGROW>
                if m == 0
                    ex_g(end+1, 1) = s_g(i); %#ok<AGROW>
                else
                    ex_g(end+1, 1) = 0.0;    %#ok<AGROW>
                end
            end
        end
        if ~isempty(ex_l)
            pairs = [ex_l, ex_k];
            [u_pairs, ~, ic] = unique(pairs, 'rows');
            merged = zeros(size(u_pairs, 1), 1);
            for i = 1:numel(ic)
                merged(ic(i)) = merged(ic(i)) + ex_g(i);
            end
            sup_l = u_pairs(:, 1);
            sup_k = u_pairs(:, 2);
            gains_S = merged;
        else
            sup_l = []; sup_k = []; gains_S = [];
        end
    else
        % Data-aided LS: x_total = pilot + hard-decided data
        x_hard = zeros(1, N);
        for n = 1:N
            [~, mi] = min(abs(x_soft(n) - constellation));
            x_hard(n) = constellation(mi);
        end
        x_total = x_pilot + x_hard;
        P = numel(sup_l);
        if P > 0
            A_tot = zeros(N, P);
            for p = 1:P
                A_tot(:, p) = build_da_ls_column(N, sup_l(p), sup_k(p), c1, c2, k_max, x_total);
            end
            AhA = A_tot' * A_tot;
            Ahy = A_tot' * y_daft(:);
            gains_S = (AhA + lambda_ls * eye(P)) \ (Ahy + lambda_ls * gains_S);
        end
    end

    H_new = reconstruct_H_from_support(N, c1, c2, k_max, sup_l, sup_k, gains_S);
    H_hat = (1.0 - gamma_h) * H_hat + gamma_h * H_new;

    max_h = max(abs(H_hat(:)));
    if max_h > 0
        tau = max(tau_hfac * max_h, tau_sfac * sqrt(sigma2_eff));
        H_hat(abs(H_hat) < tau) = 0.0;
    end

    % ---- (B) BP-MP detection ----
    y_data = y_daft(:) - H_hat * x_pilot(:);
    x_mp = mp_detect_bp(y_data, H_hat, sigma2_eff, constellation, ...
        cfg.bp_iter, cfg.bp_threshold, cfg.bp_damp);
    x_soft = (1.0 - gamma_x) * x_soft + gamma_x * x_mp.';

    % ---- (C) Adaptive sigma^2 ----
    if update_s2 && outer > 1
        x_hard_res = zeros(1, N);
        for n = 1:N
            [~, mi] = min(abs(x_soft(n) - constellation));
            x_hard_res(n) = constellation(mi);
        end
        x_tot_res = x_pilot + x_hard_res;
        resid = y_daft(:) - H_hat * x_tot_res(:);
        sigma2_new = sum(abs(resid).^2) / N;
        sigma2_eff = 0.7 * sigma2_eff + 0.3 * max(sigma2_new, 1e-12);
        lambda_ls  = max(1e-6, lambda_fac * sigma2_eff);
    end

    % ---- (D) Early stop ----
    x_hard_stop = zeros(1, N);
    for n = 1:N
        [~, mi] = min(abs(x_soft(n) - constellation));
        x_hard_stop(n) = constellation(mi);
    end
    x_tot_stop = x_pilot + x_hard_stop;
    curr_resnorm = sum(abs(y_daft(:) - H_hat * x_tot_stop(:)).^2);
    if isfinite(prev_resnorm)
        rel = (prev_resnorm - curr_resnorm) / max(curr_resnorm, 1e-12);
        if rel >= 0 && rel < eps_stop, break; end
    end
    prev_resnorm = curr_resnorm;
end
end


% ============================================================
%  3GPP TR 38.811 NTN-TDL profile + LEO channel
% ============================================================
function prof = get_ntn_tdl_profile(name)
switch upper(strrep(name, ' ', ''))
    case 'NTN-TDL-A'
        prof.tau_norm = [0; 1.0811; 2.8416];
        prof.p_db     = [0; -4.675; -6.482];
        prof.fad      = {'Rayleigh','Rayleigh','Rayleigh'};
        prof.K_db     = 0;
    case 'NTN-TDL-B'
        prof.tau_norm = [0; 0.7249; 1.0771; 1.9092];
        prof.p_db     = [0; -4.926; -6.902; -8.717];
        prof.fad      = {'Rayleigh','Rayleigh','Rayleigh','Rayleigh'};
        prof.K_db     = 0;
    case 'NTN-TDL-C'
        prof.tau_norm = [0; 0; 14.8124];
        prof.p_db     = [-0.394; -10.618; -23.373];
        prof.fad      = {'Rician','Rayleigh','Rayleigh'};
        prof.K_db     = 10.224;
    case 'NTN-TDL-D'
        prof.tau_norm = [0; 0; 0.5596; 7.3340];
        prof.p_db     = [0.016; -12.968; -9.887; -16.771];
        prof.fad      = {'Rician','Rayleigh','Rayleigh','Rayleigh'};
        prof.K_db     = 11.707;
    otherwise
        error('Unknown NTN-TDL profile: %s', name);
end
end


function prof = select_dominant_2taps(prof)
tau = prof.tau_norm;
p_db = prof.p_db;
fad = prof.fad;
idx0 = find(abs(tau) < 1e-12);
p0_lin = sum(10.^(p_db(idx0) / 10));
p0_db  = 10 * log10(p0_lin + 1e-300);
is_rician0 = any(strcmpi(fad(idx0), 'Rician'));
if is_rician0
    fad_first = 'Rician'; K_db_first = prof.K_db;
else
    fad_first = 'Rayleigh'; K_db_first = 0;
end
rem = setdiff(1:numel(tau), idx0);
if isempty(rem)
    prof.tau_norm = 0; prof.p_db = p0_db;
    prof.fad = {fad_first}; prof.K_db = K_db_first;
    return;
end
[~, bi] = max(p_db(rem));
best = rem(bi);
prof.tau_norm = [0; tau(best)];
prof.p_db     = [p0_db; p_db(best)];
prof.fad      = {fad_first, fad{best}};
prof.K_db     = K_db_first;
end


function [chan, l_i, k_real] = generate_leo_ntn_channel(cfg)
% Port of generate_NTN_TDL_channel_SISO.
prof = get_ntn_tdl_profile(cfg.ntn_profile);
if cfg.use_dominant_2taps
    prof = select_dominant_2taps(prof);
end
tau_norm = prof.tau_norm(:);
p_db     = prof.p_db(:);
fad      = prof.fad;
K_db     = prof.K_db;
P_phy    = numel(p_db);

% 1) delays → sample bins
N  = cfg.N;
Ts = 1.0 / (N * cfg.delta_f);
l_max_samp = cfg.l_max_cap;
if max(tau_norm) > 0
    ds_scale = (l_max_samp * Ts) / max(tau_norm);
else
    ds_scale = 0;
end
tau_sec = tau_norm * ds_scale;
l_i = min(max(round(tau_sec / Ts), 0), l_max_samp);

% 2) per-tap complex gain
p_lin = 10.^(p_db / 10);
p_lin = p_lin / sum(p_lin);
chan = zeros(P_phy, 1);
for i = 1:P_phy
    if strcmpi(fad{i}, 'Rician')
        K_lin = 10^(K_db / 10);
        los  = sqrt(p_lin(i) * K_lin / (K_lin + 1)) * exp(1j*2*pi*rand);
        nlos = sqrt(p_lin(i) / (K_lin + 1)) * (randn + 1j*randn) / sqrt(2);
        chan(i) = los + nlos;
    else
        chan(i) = sqrt(p_lin(i)) * (randn + 1j*randn) / sqrt(2);
    end
end

% 3) orbital-geometry Doppler
V_SAT = sqrt(cfg.G_earth / (cfg.R_earth + cfg.H_sat));
alpha_deg = cfg.alpha_min_deg + rand * (90 - cfg.alpha_min_deg);
c_light = 3e8;
v_rel = V_SAT * (cfg.R_earth / (cfg.R_earth + cfg.H_sat)) * cosd(alpha_deg);
f_d_sat = (v_rel / c_light) * cfg.fc;
f_d_ue  = (cfg.ue_speed / c_light) * cfg.fc;
sign_fd = 2*(rand > 0.5) - 1;
f_d_base = sign_fd * (f_d_sat + f_d_ue);
local_spread = cfg.local_doppler_spread_hz * (2*rand(P_phy, 1) - 1);
f_d_taps = f_d_base + local_spread;
k_real = f_d_taps / cfg.delta_f;
end
