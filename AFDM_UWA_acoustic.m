%% AFDM_UWA_acoustic.m - AFDM with Underwater Acoustic Channel (acousticChannelEnhanced)
% This file integrates the acousticChannelEnhanced.m function for UWA channel modeling
% Key modifications from AFDM_LEO.m:
%   1. Physical parameters changed to UWA: fc=12 kHz, B=4 kHz, c=1500 m/s
%   2. Uses acousticChannelEnhanced for channel generation
%   3. Builds H_physical using delay+Doppler structure (DFS model)
%   4. Optional: time-correlated channels via generateTimeSeriesChannel
%
% Author: Adapted from AFDM_LEO.m

clear; clc; close all;
rng(1)

%% ====================================================================== %%
%                        PARALLEL POOL SETUP                               %
%% ====================================================================== %%
desired_workers = 6;
threads_per_worker = 2;

pool = gcp('nocreate');
if isempty(pool)
    c = parcluster('local');
    c.NumThreads = threads_per_worker;
    fprintf('Starting parallel pool with %d workers (Threads per worker: %d)...\n', ...
        desired_workers, threads_per_worker);
    parpool(c, desired_workers);
else
    if pool.NumWorkers ~= desired_workers
        fprintf('Restarting pool to change worker count...\n');
        delete(pool);
        c = parcluster('local');
        c.NumThreads = threads_per_worker;
        parpool(c, desired_workers);
    else
        pctRunOnAll(['maxNumCompThreads(' num2str(threads_per_worker) ')']);
        fprintf('Parallel pool already running. Threads set to %d via pctRunOnAll.\n', threads_per_worker);
    end
end

%% ====================================================================== %%
%                       UNDERWATER ACOUSTIC PARAMETERS                     %
%% ====================================================================== %%

% Physical constants
c_sound = 1500;              % Speed of sound in seawater (m/s)

% System parameters (UWA typical values)
fc = 12e3;                   % Carrier frequency: 12 kHz
B = 4e3;                     % Bandwidth: 4 kHz
fs = 2 * B;                  % Sampling rate: 8 kHz
Ts = 1 / fs;                 % Sampling period
delta_f = 15;                % Subcarrier spacing: 15 Hz
T = 1 / delta_f;             % Symbol period: ~66.7 ms

% Modulation parameters
M_mod = 4;                   % QPSK
bps = log2(M_mod);
N = 1024;                    % Subcarriers (larger for UWA)

%% ====================================================================== %%
%                      UWA CHANNEL CONFIGURATION                           %
%% ====================================================================== %%

% Acoustic channel parameters for acousticChannelEnhanced
P_paths = 10;                       % Number of multipath components
tau_spread = 10e-3;                 % Delay spread: 10 ms
att_dB = 20;                        % Attenuation in dB over delay spread
tau_mean = 0.8e-3;                  % Mean delay increment (s) - controls max delay

% Doppler settings
doppler_type = 'non-uniform';       % 'uniform', 'non-uniform', or 'none'
v_mean = 2.0;                       % Mean velocity (m/s)
v_std = 0.5;                        % Velocity std (m/s) for non-uniform

% Generate velocity vector for non-uniform Doppler
switch lower(doppler_type)
    case 'uniform'
        v_vec = v_mean;
    case 'non-uniform'
        v_vec = abs(v_mean + v_std * randn(P_paths, 1));  % Positive velocities
    case 'none'
        v_vec = 0;
end

%% ====================================================================== %%
%                          SIMULATION PARAMETERS                           %
%% ====================================================================== %%

SNR_dB = 0:5:25;
sigma_2 = 1 ./ (10.^(SNR_dB / 10));
N_frame = 5000;                     % Number of frames

% Adaptive frame control
ADAPTIVE_FRAME_ENABLE = true;
MIN_ERROR_BITS = 1000;
MIN_FRAMES = 200;
CHECK_INTERVAL = 50;

% MP detection parameters
num_iter_MP = 20;
threshold_MP = 1e-4;

% Power allocation (superimposed pilot)
power_levels = [0.5, 0.5];          % [data, pilot]

% Joint iteration parameters
NUM_OUTER_ITS = 3;                  % Number of outer iterations
GAMMA_H_DAMP = 0.7;                 % Channel damping factor
GAMMA_X_DAMP = 0.6;                 % Symbol damping factor
EPS_STOP_REL = 1e-3;                % Early stop threshold
UPDATE_SIGMA2_EACH_OUTER = true;    % Update noise variance each iteration
LAMBDA_LS_FACTOR = 1e-3;            % LS regularization factor
TAU_H_FACTOR = 0.01;                % Sparsification threshold (relative)
TAU_H_SIGMA_FACTOR = 0.1;           % Sparsification threshold (noise-based)

% Debug flag
DEBUG_PRINT_FLAG = false;

%% ====================================================================== %%
%                             TEST MODE TOGGLES                           %
%% ====================================================================== %%
% 启用测试模式以加速出图验证（显著减少SNR点、帧数与迭代次数）
TEST_MODE = false;                   % 设为 true 启用快速测试模式

% 测试模式参数（仅在 TEST_MODE=true 时生效）
TEST_SNR_dB = [5 10 15 20];               % 更少的SNR点
TEST_N_FRAME = 50;                    % 更少的帧数
TEST_MIN_FRAMES = 10;                 % 自适应提前停止的最小帧数
TEST_CHECK_INTERVAL = 5;              % 自适应检查间隔
TEST_MIN_ERROR_BITS = 50;             % 自适应最少错误比特
TEST_NUM_OUTER_ITS = 3;               % Joint外层迭代次数（>=2才能体现迭代增益）
TEST_NUM_ITER_MP = 10;                % MP迭代次数（适当保留以保证收敛）
TEST_P_PATHS = 5;                     % 降低路径数以提速

if TEST_MODE
    SNR_dB = TEST_SNR_dB;
    sigma_2 = 1 ./ (10.^(SNR_dB / 10));
    N_frame = TEST_N_FRAME;
    MIN_FRAMES = TEST_MIN_FRAMES;
    CHECK_INTERVAL = TEST_CHECK_INTERVAL;
    MIN_ERROR_BITS = TEST_MIN_ERROR_BITS;
    NUM_OUTER_ITS = TEST_NUM_OUTER_ITS;
    num_iter_MP = TEST_NUM_ITER_MP;
    P_paths = min(P_paths, TEST_P_PATHS);

    % 重新生成 v_vec 以匹配修改后的 P_paths
    switch lower(doppler_type)
        case 'uniform'
            v_vec = v_mean;
        case 'non-uniform'
            v_vec = abs(v_mean + v_std * randn(P_paths, 1));
        case 'none'
            v_vec = 0;
    end

    fprintf('TEST_MODE: using SNR=%s, N_frame=%d, P_paths=%d, NUM_OUTER_ITS=%d, num_iter_MP=%d\n', ...
        mat2str(SNR_dB), N_frame, P_paths, NUM_OUTER_ITS, num_iter_MP);
end

%% ====================================================================== %%
%                    GENERATE TEST CHANNEL FOR PARAMETER SETUP             %
%% ====================================================================== %%

% Setup structures for acousticChannelEnhanced
setup_test.Ts = Ts;
setup_test.paths = P_paths;
setup_test.delayspread = tau_spread;

gain_test.attenuation = att_dB;
gain_test.normalize = true;

delay_test.mean = tau_mean;

doppler_test.type = doppler_type;
doppler_test.velocity = v_vec;

% Generate test channel to determine parameter bounds
[h_test, ~, ~, delay_idx_bar_test, ~, doppler_a_test, ~, ~] = ...
    acousticChannelEnhanced(setup_test, gain_test, delay_test, doppler_test);

% Compute max delay and Doppler from channel
maxDelay_samples = max(delay_idx_bar_test) - 1;
a_max = max(abs(doppler_a_test));
D_max = a_max * fc / fs;                  % Normalized Doppler (cycles/sample)
maxDoppler_bins = ceil(N * D_max);

% Validate delay constraint
if max(delay_idx_bar_test) > N
    error('最大延迟样点 (%d) 超过 N (%d)：请减小 delay.mean/paths，或增大 N', ...
        max(delay_idx_bar_test), N);
end

% AFDM parameters
k_v = 4;                                   % Guard Doppler bins
CPP_len = maxDelay_samples;
N_data = N - CPP_len;

% Orthogonality check: 2(K+G)(L+1)+L <= N_data
required_N = 2 * (maxDoppler_bins + k_v) * (maxDelay_samples + 1) + maxDelay_samples;
if required_N > N_data
    warning('AFDM 正交条件不满足: required=%d > N_data=%d，自动调整 N', required_N, N_data);
    N = required_N + CPP_len + 100;
    N_data = N - CPP_len;
end

c1 = (2 * (maxDoppler_bins + k_v) + 1) / (2 * N_data);

% Print parameter summary
fprintf('\n');
fprintf('======== UWA-AFDM Parameter Summary ========\n');
fprintf('Carrier frequency: %.1f kHz\n', fc / 1e3);
fprintf('Bandwidth: %.1f kHz, Sampling rate: %.1f kHz\n', B / 1e3, fs / 1e3);
fprintf('Symbol period: %.1f ms\n', T * 1e3);
fprintf('Paths: %d, Delay spread: %.1f ms, Mean delay incr: %.2f ms\n', ...
    P_paths, tau_spread * 1e3, tau_mean * 1e3);
fprintf('Max delay: %d samples (%.2f ms)\n', maxDelay_samples, maxDelay_samples * Ts * 1e3);
fprintf('Max Doppler factor: %.2e, Max Doppler bins: %d\n', a_max, maxDoppler_bins);
fprintf('N=%d, N_data=%d, CPP_len=%d, c1=%.6f\n', N, N_data, CPP_len, c1);
fprintf('AFDM orthogonality: required=%d <= N_data=%d (OK=%d)\n', required_N, N_data, required_N <= N_data);
fprintf('============================================\n\n');

%% ====================================================================== %%
%                           PRE-ALLOCATE RESULTS                           %
%% ====================================================================== %%

% BER arrays
ber_perfect_CSI = zeros(1, length(SNR_dB));
ber_perfect_CSI_MP = zeros(1, length(SNR_dB));
ber_OMP_MMSE = zeros(1, length(SNR_dB));
ber_OMP_MP = zeros(1, length(SNR_dB));
ber_joint = zeros(1, length(SNR_dB));

% MSE arrays
MSE_channel_OMP = zeros(1, length(SNR_dB));
MSE_channel_joint = zeros(1, length(SNR_dB));

% Actual frames used
actual_frames_used = zeros(1, length(SNR_dB));

% Iteration BER history for convergence analysis
% Shape: (NUM_OUTER_ITS, N_frame, length(SNR_dB))
ber_iter_joint_history = nan(NUM_OUTER_ITS, N_frame, length(SNR_dB));

% Target SNRs for plotting iteration convergence curve (two SNR points)
target_snr_for_iter_1 = 15;  % First SNR point (dB)
target_snr_for_iter_2 = 20;  % Second SNR point (dB)

%% ====================================================================== %%
%                              MAIN SIMULATION                             %
%% ====================================================================== %%

fprintf('Starting simulation: %d SNR points, up to %d frames each\n\n', length(SNR_dB), N_frame);

parfor iesn0 = 1:length(SNR_dB)
    sigma2_current = sigma_2(iesn0);
    % MMSE regularization: For superimposed pilot, data power = P_data = power_levels(1)
    % Correct form: (H'H + sigma2/P_data * I)^{-1} H'
    P_data = power_levels(1);   % Data symbol power (0.5 for superimposed pilot)
    reg_eye = (sigma2_current / P_data) * eye(N_data);

    % Error counters
    err_count_perfect = 0;
    err_count_perfect_mp = 0;
    err_count_omp_mmse = 0;
    err_count_omp_mp = 0;
    err_count_joint = 0;

    % MSE accumulator
    mse_values_omp = [];
    mse_values_joint = [];

    % Local iteration BER history
    ber_iter_history_local = nan(NUM_OUTER_ITS, N_frame);

    % Frame control
    frames_processed = 0;

    for iframe = 1:N_frame
        %% =============== GENERATE UWA CHANNEL =============== %%
        % Setup structures (use struct() for parfor compatibility)
        setup_ch = struct('Ts', Ts, 'paths', P_paths, 'delayspread', tau_spread);
        gain_ch = struct('attenuation', att_dB, 'normalize', true);
        delay_ch = struct('mean', tau_mean);

        % Re-sample velocity for each frame (to get different realizations)
        switch lower(doppler_type)
            case 'uniform'
                v_frame = v_mean;
            case 'non-uniform'
                v_frame = abs(v_mean + v_std * randn(P_paths, 1));
            case 'none'
                v_frame = 0;
        end
        doppler_ch = struct('type', doppler_type, 'velocity', v_frame);

        % Generate channel
        [~, ~, gain_tap, delay_idx_bar, ~, doppler_a, ~, ~] = ...
            acousticChannelEnhanced(setup_ch, gain_ch, delay_ch, doppler_ch);

        % Check delay constraint for this realization
        if max(delay_idx_bar) > N
            warning('Frame %d: max delay (%d) exceeds N (%d), skipping', ...
                iframe, max(delay_idx_bar), N);
            continue;
        end

        % Build H_physical using buildUWA_H
        H_physical = buildUWA_H(N_data, delay_idx_bar, gain_tap, doppler_a, fc, fs);

        % Extract delay/Doppler parameters for AFDM framework
        % Map to integer delay/Doppler for AFDM channel matrix
        delay_taps = delay_idx_bar - 1;  % 0-indexed delay
        D_vals = doppler_a * fc / fs;     % Normalized Doppler
        doppler_taps = round(D_vals * N_data);  % Quantized to integer bins

        % Clip Doppler to avoid exceeding bounds
        max_k = floor(N_data / 2) - k_v - 1;
        doppler_taps = max(min(doppler_taps, max_k), -max_k);

        % Generate AFDM effective channel matrix (for comparison/estimation)
        H_DAFT = GEN_H_DAFT(N_data, gain_tap, delay_taps, doppler_taps, c1);

        %% =============== GENERATE DATA & PILOT SYMBOLS =============== %%
        x_idx = randi([0, M_mod-1], N_data, 1);
        x_qam = qammod(x_idx, M_mod, 'gray', 'UnitAveragePower', true);
        x_bit_data = de2bi(x_idx, bps, 'left-msb');

        x_pilot_idx = randi([0, M_mod-1], N_data, 1);
        x_pilot_qam = qammod(x_pilot_idx, M_mod, 'gray', 'UnitAveragePower', true);

        %% =============== AFDM TRANSMISSION =============== %%
        % Superimposed signal
        x_da_combined = x_qam * sqrt(power_levels(1)) + x_pilot_qam * sqrt(power_levels(2));

        % Transmit through channel
        Y_DA_noiseless = H_DAFT * x_da_combined;
        noise_da = sqrt(sigma2_current / 2) * (randn(N_data, 1) + 1j * randn(N_data, 1));
        Y_DA = Y_DA_noiseless + noise_da;

        %% =============== DETECTION: PERFECT CSI =============== %%
        H_DAFT_full = full(H_DAFT);
        HtH_perfect = H_DAFT_full' * H_DAFT_full;
        Wmmse_perfect = (HtH_perfect + reg_eye) \ H_DAFT_full';
        Y_data_perfect = Y_DA - H_DAFT * x_pilot_qam * sqrt(power_levels(2));
        x_hat_perfect = Wmmse_perfect * Y_data_perfect;
        x_est_symbols_perfect = x_hat_perfect / sqrt(power_levels(1));
        x_est_idx_perfect = qamdemod(x_est_symbols_perfect, M_mod, 'gray', 'UnitAveragePower', true);
        err_count_perfect = err_count_perfect + biterr(de2bi(x_est_idx_perfect, bps, 'left-msb'), x_bit_data);

        %% =============== DETECTION: PERFECT CSI + MP =============== %%
        Y_DA_data_only_mp = Y_DA - H_DAFT * x_pilot_qam * sqrt(power_levels(2));
        x_mp_perfect = MP_detection_optimized(Y_DA_data_only_mp, H_DAFT, sigma2_current, ...
            num_iter_MP, threshold_MP, M_mod, sqrt(power_levels(1)));
        x_mp_perfect_normalized = x_mp_perfect / sqrt(power_levels(1));
        x_est_idx_perfect_mp = qamdemod(x_mp_perfect_normalized, M_mod, 'gray', 'UnitAveragePower', true);
        err_count_perfect_mp = err_count_perfect_mp + biterr(de2bi(x_est_idx_perfect_mp, bps, 'left-msb'), x_bit_data);

        %% =============== CHANNEL ESTIMATION: OMP =============== %%
        % Compute local maxDelay/maxDoppler for sensing matrix
        local_maxDelay = max(delay_taps);
        local_maxDoppler = max(abs(doppler_taps));
        Q_local = (2 * local_maxDoppler + 1) * (local_maxDelay + 1);

        Phi = construct_afdm_sensing_matrix(N_data, x_pilot_qam, c1, Q_local, ...
            local_maxDelay, local_maxDoppler, 1, 1);
        Phi_scaled = Phi * sqrt(power_levels(2));

        [h_OMP, ~] = OMP(Y_DA, Phi_scaled, P_paths);
        [delays_omp, dopplers_omp, gains_omp] = extract_delay_doppler_from_h(h_OMP, ...
            P_paths, local_maxDelay, local_maxDoppler, 1, 1);
        H_DAFT_est_omp = GEN_H_DAFT(N_data, gains_omp, delays_omp, dopplers_omp, c1);

        % MSE - store LINEAR value (not dB) for proper averaging
        mse_val = norm(full(H_DAFT_est_omp) - H_DAFT_full, 'fro')^2 / ...
            norm(H_DAFT_full, 'fro')^2;
        mse_values_omp = [mse_values_omp, mse_val];

        %% =============== DETECTION: OMP + MMSE =============== %%
        H_omp_full = full(H_DAFT_est_omp);
        HtH_omp = H_omp_full' * H_omp_full;
        Wmmse_omp = (HtH_omp + reg_eye) \ H_omp_full';
        Y_data_omp = Y_DA - H_DAFT_est_omp * x_pilot_qam * sqrt(power_levels(2));
        x_hat_omp = Wmmse_omp * Y_data_omp;
        x_est_idx_omp = qamdemod(x_hat_omp / sqrt(power_levels(1)), M_mod, 'gray', 'UnitAveragePower', true);
        err_count_omp_mmse = err_count_omp_mmse + biterr(de2bi(x_est_idx_omp, bps, 'left-msb'), x_bit_data);

        %% =============== DETECTION: OMP + MP =============== %%
        x_mp_omp = MP_detection_optimized(Y_data_omp, H_DAFT_est_omp, sigma2_current, ...
            num_iter_MP, threshold_MP, M_mod, sqrt(power_levels(1)));
        x_mp_omp_normalized = x_mp_omp / sqrt(power_levels(1));
        x_est_idx_omp_mp = qamdemod(x_mp_omp_normalized, M_mod, 'gray', 'UnitAveragePower', true);
        err_count_omp_mp = err_count_omp_mp + biterr(de2bi(x_est_idx_omp_mp, bps, 'left-msb'), x_bit_data);

        %% =============== DETECTION: JOINT OMP↔MP =============== %%
        [x_est_idx_joint, ~, mse_joint, ber_hist_joint] = joint_omp_mp_ls_sparse(...
            Y_DA, H_DAFT_est_omp, x_pilot_qam, x_bit_data, H_DAFT, ...
            N_data, M_mod, bps, sigma2_current, power_levels, c1, ...
            local_maxDelay, local_maxDoppler, P_paths, num_iter_MP, threshold_MP, ...
            NUM_OUTER_ITS, GAMMA_H_DAMP, GAMMA_X_DAMP, ...
            LAMBDA_LS_FACTOR, EPS_STOP_REL, UPDATE_SIGMA2_EACH_OUTER, ...
            TAU_H_FACTOR, TAU_H_SIGMA_FACTOR, false);
        err_count_joint = err_count_joint + biterr(de2bi(x_est_idx_joint, bps, 'left-msb'), x_bit_data);
        mse_values_joint = [mse_values_joint, mse_joint];
        ber_iter_history_local(:, iframe) = ber_hist_joint;

        frames_processed = iframe;

        %% =============== ADAPTIVE EARLY STOP =============== %%
        if ADAPTIVE_FRAME_ENABLE && iframe >= MIN_FRAMES && mod(iframe, CHECK_INTERVAL) == 0
            if err_count_perfect >= MIN_ERROR_BITS
                break;
            end
        end
    end

    actual_frames_used(iesn0) = frames_processed;

    %% =============== COMPUTE BER/MSE =============== %%
    total_bits = N_data * bps * frames_processed;

    ber_perfect_CSI(iesn0) = err_count_perfect / total_bits;
    ber_perfect_CSI_MP(iesn0) = err_count_perfect_mp / total_bits;
    ber_OMP_MMSE(iesn0) = err_count_omp_mmse / total_bits;
    ber_OMP_MP(iesn0) = err_count_omp_mp / total_bits;
    ber_joint(iesn0) = err_count_joint / total_bits;

    % MSE: average in LINEAR domain, then convert to dB
    MSE_channel_OMP(iesn0) = 10 * log10(mean(mse_values_omp));
    MSE_channel_joint(iesn0) = 10 * log10(mean(mse_values_joint));

    % Store iteration history
    ber_iter_joint_history(:, :, iesn0) = ber_iter_history_local;

    fprintf('SNR=%2ddB | Frames=%4d | Perfect: %.4e | OMP+MP: %.4e | Joint: %.4e | MSE_OMP: %.2f dB | MSE_Joint: %.2f dB\n', ...
        SNR_dB(iesn0), frames_processed, ber_perfect_CSI(iesn0), ...
        ber_OMP_MP(iesn0), ber_joint(iesn0), MSE_channel_OMP(iesn0), MSE_channel_joint(iesn0));
end

%% ====================================================================== %%
%                             SAVE & PLOT RESULTS                          %
%% ====================================================================== %%

% Print frame usage summary
fprintf('\n========== Adaptive Frame Usage Summary ==========\n');
for iesn0 = 1:length(SNR_dB)
    fprintf('SNR=%2ddB:  Used %4d/%4d frames (%.1f%%)\n', ...
        SNR_dB(iesn0), actual_frames_used(iesn0), N_frame, ...
        100 * actual_frames_used(iesn0) / N_frame);
end
fprintf('===================================================\n');

% Save results
results_dir = 'results';
if ~exist(results_dir, 'dir')
    mkdir(results_dir);
end
timestamp = datestr(now, 'yyyymmdd_HHMMSS');
save_file = fullfile(results_dir, ['AFDM_UWA_acoustic_sim_' timestamp '.mat']);
save(save_file, 'SNR_dB', 'ber_perfect_CSI', 'ber_perfect_CSI_MP', ...
    'ber_OMP_MMSE', 'ber_OMP_MP', 'ber_joint', 'MSE_channel_OMP', 'MSE_channel_joint', ...
    'ber_iter_joint_history', 'NUM_OUTER_ITS', 'target_snr_for_iter_1', 'target_snr_for_iter_2', ...
    'fc', 'B', 'fs', 'P_paths', 'N', 'N_data', 'N_frame', 'actual_frames_used', ...
    'tau_spread', 'tau_mean', 'att_dB', 'doppler_type', 'v_mean');

% Plot BER comparison
figure('Position', [100, 100, 900, 600]);

semilogy(SNR_dB, ber_perfect_CSI, 'b-o', 'LineWidth', 2, 'MarkerSize', 8, 'DisplayName', 'Perfect CSI + MMSE');
hold on;
semilogy(SNR_dB, ber_perfect_CSI_MP, 'b--s', 'LineWidth', 2, 'MarkerSize', 8, 'DisplayName', 'Perfect CSI + MP');
semilogy(SNR_dB, ber_OMP_MMSE, 'r-^', 'LineWidth', 2, 'MarkerSize', 8, 'DisplayName', 'OMP + MMSE');
semilogy(SNR_dB, ber_OMP_MP, 'r--d', 'LineWidth', 2, 'MarkerSize', 8, 'DisplayName', 'OMP + MP');
semilogy(SNR_dB, ber_joint, 'g-p', 'LineWidth', 2, 'MarkerSize', 10, 'DisplayName', 'Joint OMP\leftrightarrowMP');

grid on;
xlabel('SNR (dB)', 'FontSize', 12);
ylabel('Bit Error Rate', 'FontSize', 12);
title(sprintf('AFDM-UWA: f_c=%.0f kHz, B=%.0f kHz, P=%d paths, \\tau_{spread}=%.0f ms', ...
    fc / 1e3, B / 1e3, P_paths, tau_spread * 1e3), 'FontSize', 14);
legend('Location', 'southwest', 'FontSize', 10);
ylim([1e-5, 1]);

savefig(fullfile(results_dir, ['AFDM_UWA_acoustic_BER_' timestamp '.fig']));
saveas(gcf, fullfile(results_dir, ['AFDM_UWA_acoustic_BER_' timestamp '.png']));

% Plot MSE comparison
figure('Position', [100, 100, 700, 500]);
plot(SNR_dB, MSE_channel_OMP, 'r-o', 'LineWidth', 2, 'MarkerSize', 8, 'DisplayName', 'OMP');
hold on;
plot(SNR_dB, MSE_channel_joint, 'g-s', 'LineWidth', 2, 'MarkerSize', 8, 'DisplayName', 'Joint');
grid on;
xlabel('SNR (dB)', 'FontSize', 12);
ylabel('Channel MSE (dB)', 'FontSize', 12);
title('Channel Estimation MSE: OMP vs Joint', 'FontSize', 14);
legend('Location', 'northeast', 'FontSize', 10);

savefig(fullfile(results_dir, ['AFDM_UWA_acoustic_MSE_' timestamp '.fig']));
saveas(gcf, fullfile(results_dir, ['AFDM_UWA_acoustic_MSE_' timestamp '.png']));

%% ====== Plot Iteration Convergence Curve ====== %%
% Extract iteration BER curves for two target SNRs
idx_snr_1 = find(SNR_dB == target_snr_for_iter_1, 1);
idx_snr_2 = find(SNR_dB == target_snr_for_iter_2, 1);

ber_iter_curve_1 = [];
ber_iter_curve_2 = [];

if ~isempty(idx_snr_1)
    slice_1 = squeeze(ber_iter_joint_history(:, :, idx_snr_1));
    valid_cols_1 = any(~isnan(slice_1), 1);
    if any(valid_cols_1)
        ber_iter_curve_1 = mean(slice_1(:, valid_cols_1), 2, 'omitnan');
    end
end

if ~isempty(idx_snr_2)
    slice_2 = squeeze(ber_iter_joint_history(:, :, idx_snr_2));
    valid_cols_2 = any(~isnan(slice_2), 1);
    if any(valid_cols_2)
        ber_iter_curve_2 = mean(slice_2(:, valid_cols_2), 2, 'omitnan');
    end
end

has_curve_1 = ~isempty(ber_iter_curve_1) && any(~isnan(ber_iter_curve_1));
has_curve_2 = ~isempty(ber_iter_curve_2) && any(~isnan(ber_iter_curve_2));

if has_curve_1 || has_curve_2
    iterations = (1:NUM_OUTER_ITS).';

    figure('Position', [100, 100, 700, 500]);
    hold on;

    if has_curve_1
        semilogy(iterations, ber_iter_curve_1, 'b-o', 'LineWidth', 2, 'MarkerSize', 10, ...
            'MarkerFaceColor', 'b', 'DisplayName', sprintf('SNR = %d dB', target_snr_for_iter_1));
    end

    if has_curve_2
        semilogy(iterations, ber_iter_curve_2, 'r-s', 'LineWidth', 2, 'MarkerSize', 10, ...
            'MarkerFaceColor', 'r', 'DisplayName', sprintf('SNR = %d dB', target_snr_for_iter_2));
    end

    grid on;
    xlabel('Outer Iteration Number', 'FontSize', 12);
    ylabel('Bit Error Rate', 'FontSize', 12);
    title('Joint OMP\leftrightarrowMP Iteration Convergence', 'FontSize', 14);
    legend('Location', 'northeast', 'FontSize', 10);
    xlim([1, NUM_OUTER_ITS]);
    xticks(1:NUM_OUTER_ITS);
    set(gca, 'YScale', 'log');
    ylim([1e-5, 1e-1]);
    yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1]);

    savefig(fullfile(results_dir, ['AFDM_UWA_acoustic_IterConv_' timestamp '.fig']));
    saveas(gcf, fullfile(results_dir, ['AFDM_UWA_acoustic_IterConv_' timestamp '.png']));

    fprintf('Iteration convergence plot saved.\n');
else
    fprintf('Warning: No valid iteration data for convergence plot (target SNRs: %d, %d dB not found).\n', ...
        target_snr_for_iter_1, target_snr_for_iter_2);
end

fprintf('\nSimulation complete. Results saved to: %s\n', save_file);


%% ====================================================================== %%
%                           HELPER FUNCTIONS                               %
%% ====================================================================== %%

function H = buildUWA_H(N, delay_idx_bar, gain_tap, doppler_a, fc, fs)
%BUILDUWA_H Build N x N channel matrix from UWA tap/delay/Doppler
%   Implements: y[n] = sum_i gain_tap(i) * x[n-l_i] * exp(j*2*pi*D_i*n)
%
% Inputs:
%   N            - Block size
%   delay_idx_bar- Delay indices (samples)
%   gain_tap     - Complex path gains
%   doppler_a    - Doppler factors (a_i = v_i / c)
%   fc           - Carrier frequency (Hz)
%   fs           - Sampling frequency (Hz)
%
% Output:
%   H            - N x N channel matrix (sparse-like structure)

P = numel(gain_tap);
n = (0:N-1).';
H = complex(zeros(N, N));

I = eye(N);

for i = 1:P
    l = mod(delay_idx_bar(i) - 1, N);       % Delay in samples (0-indexed, wrapped)
    D = (doppler_a(i) * fc) / fs;           % Normalized Doppler (cycles/sample)
    Delta = diag(exp(1j * 2 * pi * D * n)); % Phase rotation on output time index
    Pi = circshift(I, l, 1);                % Cyclic shift: y = Pi*x gives y[n]=x[n-l]
    H = H + gain_tap(i) * (Delta * Pi);
end

% Normalize to stabilize average energy
H_energy = mean(abs(H(:)).^2);
if H_energy > 0
    H = H / sqrt(H_energy);
end
end


function H_DAFT = GEN_H_DAFT(N, chan_coef, Delay_Index, Doppler_Index, c1)
%GEN_H_DAFT Generate AFDM effective channel matrix (sparse)
%   Based on the analytically derived AFDM input-output relation
%
% Inputs:
%   N             - Number of subcarriers
%   chan_coef     - Path gains (P x 1)
%   Delay_Index   - Delay indices (P x 1)
%   Doppler_Index - Doppler indices (P x 1)
%   c1            - AFDM chirp parameter
%
% Output:
%   H_DAFT        - N x N effective channel matrix (sparse)

P = length(chan_coef);
total_nnz = N * P;
rows = zeros(total_nnz, 1);
cols = zeros(total_nnz, 1);
vals = zeros(total_nnz, 1);

idx_counter = 0;
q_vec = (0:N-1).';
c2 = 0;

for i = 1:P
    h_i = chan_coef(i);
    l_i = Delay_Index(i);
    k_i = Doppler_Index(i);

    % Location shift: loc = k + 2*N*c1*l
    loc_val = k_i + 2 * N * c1 * l_i;

    % Receive index: p = (q - loc) mod N
    p_vec = mod(round(q_vec - loc_val), N);

    % Phase computation
    term1 = N * c1 * (l_i^2);
    term2 = -q_vec * l_i;
    term3 = N * c2 * (q_vec.^2 - p_vec.^2);
    total_phase = (2 * pi / N) * (term1 + term2 + term3);

    H_vals = h_i * exp(1j * total_phase);

    % Fill sparse triplets
    current_indices = (1:N) + idx_counter;
    rows(current_indices) = p_vec + 1;
    cols(current_indices) = q_vec + 1;
    vals(current_indices) = H_vals;

    idx_counter = idx_counter + N;
end

H_DAFT = sparse(rows, cols, vals, N, N);
end


function Phi = construct_afdm_sensing_matrix(N, x_pilot, c1, Q, max_delay, max_doppler, delay_res, doppler_res)
%CONSTRUCT_AFDM_SENSING_MATRIX Build OMP sensing dictionary
%
% Inputs:
%   N            - Block size
%   x_pilot      - Pilot symbols (N x 1)
%   c1           - AFDM chirp parameter
%   Q            - Dictionary size
%   max_delay    - Maximum delay index
%   max_doppler  - Maximum Doppler index
%   delay_res    - Delay resolution
%   doppler_res  - Doppler resolution
%
% Output:
%   Phi          - N x Q sensing matrix

Phi = zeros(N, Q);
q_vec = (0:N-1).';
c2 = 0;

col_idx = 1;
for l = 0:delay_res:max_delay
    for k = -max_doppler:doppler_res:max_doppler
        if col_idx > Q
            break;
        end

        loc_val = k + 2 * N * c1 * l;
        p_vec = mod(round(q_vec - loc_val), N);

        term1 = N * c1 * (l^2);
        term2 = -q_vec * l;
        term3 = N * c2 * (q_vec.^2 - p_vec.^2);
        total_phase = (2 * pi / N) * (term1 + term2 + term3);

        H_vals = exp(1j * total_phase);

        y_col = zeros(N, 1);
        for qi = 1:N
            p_idx = p_vec(qi) + 1;
            y_col(p_idx) = y_col(p_idx) + H_vals(qi) * x_pilot(qi);
        end

        Phi(:, col_idx) = y_col;
        col_idx = col_idx + 1;
    end
    if col_idx > Q
        break;
    end
end
end


function [delays, dopplers, gains] = extract_delay_doppler_from_h(h, P, max_delay_index, max_doppler_index, delay_res, doppler_res)
%EXTRACT_DELAY_DOPPLER_FROM_H Extract top P paths from sparse vector
%
% Inputs:
%   h                - Sparse channel vector
%   P                - Number of paths to extract
%   max_delay_index  - Maximum delay index
%   max_doppler_index- Maximum Doppler index
%   delay_res        - Delay resolution
%   doppler_res      - Doppler resolution
%
% Outputs:
%   delays           - Extracted delay indices (P x 1)
%   dopplers         - Extracted Doppler indices (P x 1)
%   gains            - Extracted path gains (P x 1)

[~, sorted_indices] = sort(abs(h), 'descend');
topP_indices = sorted_indices(1:min(P, length(h)));
gains = h(topP_indices);
num_dopplers = round((2 * max_doppler_index) / doppler_res + 1);
delays = zeros(length(topP_indices), 1);
dopplers = zeros(length(topP_indices), 1);

for i = 1:length(topP_indices)
    idx = topP_indices(i) - 1;
    delay_idx = floor(idx / num_dopplers);
    doppler_idx_from_zero = mod(idx, num_dopplers);
    doppler_idx = doppler_idx_from_zero - max_doppler_index / doppler_res;
    delays(i) = delay_idx * delay_res;
    dopplers(i) = doppler_idx * doppler_res;
end
end


function [h_i, Omega] = OMP(y, P, S)
%OMP Orthogonal Matching Pursuit
%
% Inputs:
%   y - Observation vector (N x 1)
%   P - Sensing matrix (N x K)
%   S - Sparsity level
%
% Outputs:
%   h_i   - Recovered sparse vector (K x 1)
%   Omega - Support set indices

N = size(y, 1);
K = size(P, 2);

err = 1e-3;
h_i = zeros(K, 1);
y_i = y - P * h_i;

it = 0;
stop = 0;
P_s = [];
pos_array = [];
P_working = P;

while ~stop
    product = zeros(K, 1);
    for ntl = 1:K
        product(ntl) = abs(P_working(:, ntl)' * y_i);
    end

    [~, pos] = max(product);
    P_s = [P_s, P(:, pos)];
    pos_array = [pos_array, pos];
    P_working(:, pos) = zeros(N, 1);
    h_s = (P_s' * P_s) \ (P_s' * y);
    y_i = y - P_s * h_s;

    it = it + 1;

    if (it >= S) || norm(y_i) <= err * norm(y)
        stop = 1;
    end
end

h_i(pos_array) = (P_s' * P_s) \ (P_s' * y);
Omega = pos_array;
end


function x_est = MP_detection_optimized(y, H, sigma2, num_iter, threshold, M_mod, scale_factor)
%MP_DETECTION_OPTIMIZED Message Passing detection (optimized)
%
% Inputs:
%   y            - Received signal (N x 1)
%   H            - Channel matrix (N x N), sparse or full
%   sigma2       - Noise variance
%   num_iter     - Max iterations
%   threshold    - Edge sparsification threshold
%   M_mod        - Modulation order
%   scale_factor - Symbol scaling factor
%
% Output:
%   x_est        - Detected symbols (N x 1)

N = size(H, 1);

constellation = qammod((0:M_mod-1)', M_mod, 'gray', 'UnitAveragePower', true) * scale_factor;

if ~issparse(H)
    H = sparse(H);
end

[row_idx, col_idx, h_vals] = find(H);
mask = abs(h_vals) >= threshold;
row_idx = row_idx(mask);
col_idx = col_idx(mask);
h_vals = h_vals(mask);

E = length(h_vals);

if E == 0
    x_est = zeros(N, 1);
    return;
end

% Build CSR structure
[sorted_by_row, ~] = sortrows([row_idx, (1:E)']);
row_sorted = sorted_by_row(:, 1);
edge_id_by_row = sorted_by_row(:, 2);

row_ptr = zeros(N + 1, 1);
row_ptr(1) = 1;
current_row = 1;
for e = 1:E
    while current_row < row_sorted(e)
        row_ptr(current_row + 1) = e;
        current_row = current_row + 1;
    end
end
for r = current_row:N
    row_ptr(r + 1) = E + 1;
end

% Build CSC structure
[sorted_by_col, ~] = sortrows([col_idx, (1:E)']);
col_sorted = sorted_by_col(:, 1);
edge_id_by_col = sorted_by_col(:, 2);

col_ptr = zeros(N + 1, 1);
col_ptr(1) = 1;
current_col = 1;
for e = 1:E
    while current_col < col_sorted(e)
        col_ptr(current_col + 1) = e;
        current_col = current_col + 1;
    end
end
for c = current_col:N
    col_ptr(c + 1) = E + 1;
end

% Initialize messages
mu_v2o = zeros(E, 1);
var_v2o = ones(E, 1);
mu_o2v = zeros(E, 1);
var_o2v = ones(E, 1);

prior_mean = mean(constellation);
prior_var = var(constellation);

mu_v2o(:) = prior_mean;
var_v2o(:) = prior_var;

damp = 0.5;

% Message passing iterations
for iter = 1:num_iter
    mu_v2o_old = mu_v2o;

    % O2V update
    for d = 1:N
        edge_start = row_ptr(d);
        edge_end = row_ptr(d + 1) - 1;

        if edge_start > edge_end
            continue;
        end

        edges_d = edge_id_by_row(edge_start:edge_end);
        h_d = h_vals(edges_d);
        mu_in = mu_v2o(edges_d);
        var_in = var_v2o(edges_d);

        z_total = y(d) - sum(h_d .* mu_in);
        V_total = sigma2 + sum(abs(h_d).^2 .* var_in);

        for local_e = 1:length(edges_d)
            e = edges_d(local_e);
            h_e = h_d(local_e);
            mu_e = mu_in(local_e);
            var_e = var_in(local_e);

            z_ext = z_total + h_e * mu_e;
            V_ext = V_total - abs(h_e)^2 * var_e;
            V_ext = max(V_ext, sigma2 * 0.1);

            if abs(h_e) > 1e-10
                var_o2v(e) = V_ext / abs(h_e)^2;
                mu_o2v(e) = z_ext / h_e;
            else
                var_o2v(e) = 1e10;
                mu_o2v(e) = 0;
            end
            var_o2v(e) = max(var_o2v(e), 1e-10);
        end
    end

    % V2O update
    for n = 1:N
        edge_start = col_ptr(n);
        edge_end = col_ptr(n + 1) - 1;

        if edge_start > edge_end
            continue;
        end

        edges_n = edge_id_by_col(edge_start:edge_end);
        mu_in = mu_o2v(edges_n);
        var_in = var_o2v(edges_n);

        prec_total = 1 / prior_var + sum(1 ./ var_in);
        mean_total = prior_mean / prior_var + sum(mu_in ./ var_in);

        for local_e = 1:length(edges_n)
            e = edges_n(local_e);
            mu_e = mu_in(local_e);
            var_e = var_in(local_e);

            prec_ext = prec_total - 1 / var_e;
            mean_ext = mean_total - mu_e / var_e;

            prec_ext = max(prec_ext, 1e-10);
            var_ext = 1 / prec_ext;
            mu_ext = var_ext * mean_ext;

            dist_sq = abs(constellation - mu_ext).^2;
            log_prob = -dist_sq / (2 * var_ext);
            log_prob = log_prob - max(log_prob);
            prob = exp(log_prob);
            prob = prob / sum(prob);

            mu_v2o_new = sum(prob .* constellation);
            var_v2o_new = sum(prob .* abs(constellation).^2) - abs(mu_v2o_new)^2;
            var_v2o_new = max(var_v2o_new, 1e-10);

            mu_v2o(e) = (1 - damp) * mu_v2o_old(e) + damp * mu_v2o_new;
            var_v2o(e) = var_v2o_new;
        end
    end

    if norm(mu_v2o - mu_v2o_old) / max(norm(mu_v2o), 1e-10) < 1e-4
        break;
    end
end

% Final estimates
x_est = zeros(N, 1);
for n = 1:N
    edge_start = col_ptr(n);
    edge_end = col_ptr(n + 1) - 1;

    if edge_start > edge_end
        x_est(n) = prior_mean;
        continue;
    end

    edges_n = edge_id_by_col(edge_start:edge_end);
    mu_in = mu_o2v(edges_n);
    var_in = var_o2v(edges_n);

    prec_total = 1 / prior_var + sum(1 ./ var_in);
    mean_total = prior_mean / prior_var + sum(mu_in ./ var_in);

    var_post = 1 / prec_total;
    mu_post = var_post * mean_total;

    [~, min_idx] = min(abs(constellation - mu_post));
    x_est(n) = constellation(min_idx);
end
end


function [x_est_idx, H_final, mse_final, ber_iter_history] = joint_omp_mp_ls_sparse(...
    Y_DA, H_init, x_pilot, x_bit_data, H_true, ...
    N_data, M_mod, bps, sigma2_init, power_levels, c1, ...
    l_max, k_max, taps, num_iter_MP, threshold_MP, ...
    NUM_OUTER_ITS, GAMMA_H_DAMP, GAMMA_X_DAMP, ...
    lambda_ls_factor, EPS_STOP_REL, UPDATE_SIGMA2_EACH_OUTER, ...
    TAU_H_FACTOR, TAU_H_SIGMA_FACTOR, debug_flag)
%JOINT_OMP_MP_LS_SPARSE Joint OMP↔MP iterative receiver (sparse version)
%
% Core algorithm:
%   - Iteration 1: OMP determines support, MP detects data
%   - Iterations 2+: Data-Aided LS updates gains, MP re-detects
%   - Damping + sparsification for stability
%
% Output:
%   ber_iter_history - BER at each outer iteration (NUM_OUTER_ITS x 1)

%% Initialization
if ~issparse(H_init)
    Hhat = sparse(H_init);
else
    Hhat = H_init;
end

x_soft_scaled = zeros(N_data, 1);
sigma2_eff = sigma2_init;

% BER history for each iteration
ber_iter_history = nan(NUM_OUTER_ITS, 1);

% Support set
support_delays = [];
support_dopplers = [];
gains_S = [];

% Pilot (scaled domain)
x_p_scaled = x_pilot * sqrt(power_levels(2));

% Tikhonov regularization
lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff);

prev_resnorm = Inf;

if debug_flag
    fprintf('\n========== Joint OMP↔MP with DA-LS (Sparse) ==========\n');
end

for it = 1:NUM_OUTER_ITS

    %% ===== (A) Channel Estimation Update ===== %%
    if it == 1
        % First iteration: OMP to determine support
        Q = (2*k_max+1) * (l_max + 1);
        Phi_pilot = construct_afdm_sensing_matrix(N_data, x_pilot, c1, Q, l_max, k_max, 1, 1);
        Phi_pilot_scaled = Phi_pilot * sqrt(power_levels(2));

        [h_new, ~] = OMP(Y_DA, Phi_pilot_scaled, taps);
        [support_delays, support_dopplers, gains_S] = extract_delay_doppler_from_h(...
            h_new, taps, l_max, k_max, 1, 1);

        if debug_flag
            fprintf('  [Iter 1] OMP determined support: %d paths\n', length(support_delays));
        end

    else
        % Subsequent iterations: Data-Aided LS with hard decision
        x_soft_unit = x_soft_scaled / sqrt(power_levels(1));
        x_hard_idx = qamdemod(x_soft_unit, M_mod, 'gray', 'UnitAveragePower', true);
        x_hard_unit = qammod(x_hard_idx, M_mod, 'gray', 'UnitAveragePower', true);
        x_hard_scaled = x_hard_unit * sqrt(power_levels(1));

        % Total signal (pilot + hard decision data)
        x_total_scaled = x_p_scaled + x_hard_scaled;

        % Build dictionary columns
        S_l = support_delays(:);
        S_k = support_dopplers(:);
        num_paths = length(S_l);

        A_total = zeros(N_data, num_paths);
        for p = 1:num_paths
            A_total(:, p) = gen_path_col(N_data, S_l(p), S_k(p), c1, x_total_scaled);
        end

        % Data-Aided LS
        g_new = weighted_ls(A_total, Y_DA, [], lambda_ls, gains_S);
        gains_S = g_new;

        if debug_flag
            fprintf('  [Iter %d] DA-LS updated gains\n', it);
        end
    end

    % Reconstruct channel from support + gains
    H_new = GEN_H_DAFT(N_data, gains_S, support_delays, support_dopplers, c1);

    % Damping
    Hhat = (1 - GAMMA_H_DAMP) * Hhat + GAMMA_H_DAMP * H_new;

    % Sparsification threshold
    max_h_val = max(abs(nonzeros(Hhat)));
    if isempty(max_h_val)
        max_h_val = 1;
    end
    tau_h_relative = TAU_H_FACTOR * max_h_val;
    tau_h_sigma = TAU_H_SIGMA_FACTOR * sqrt(sigma2_eff);
    tau_h = max(tau_h_relative, tau_h_sigma);

    % Apply sparsification
    [row_h, col_h, val_h] = find(Hhat);
    mask_h = abs(val_h) >= tau_h;
    Hhat = sparse(row_h(mask_h), col_h(mask_h), val_h(mask_h), N_data, N_data);

    %% ===== (B) Data Detection: MP with new channel ===== %%
    Y_for_det = Y_DA - Hhat * x_p_scaled;

    x_mp_scaled = MP_detection_optimized(Y_for_det, Hhat, sigma2_eff, ...
        num_iter_MP, threshold_MP, M_mod, sqrt(power_levels(1)));

    % Damping on symbol estimates
    x_soft_scaled = (1 - GAMMA_X_DAMP) * x_soft_scaled + GAMMA_X_DAMP * x_mp_scaled;

    %% ===== Record BER for this iteration ===== %%
    x_iter_unit = x_soft_scaled / sqrt(power_levels(1));
    x_iter_idx = qamdemod(x_iter_unit, M_mod, 'gray', 'UnitAveragePower', true);
    x_iter_bits = de2bi(x_iter_idx, bps, 'left-msb');
    ber_iter_history(it) = sum(sum(x_iter_bits ~= x_bit_data)) / numel(x_bit_data);

    %% ===== (C) Adaptive Noise Estimation ===== %%
    if UPDATE_SIGMA2_EACH_OUTER
        x_soft_unit_for_res = x_soft_scaled / sqrt(power_levels(1));
        x_hard_idx_for_res = qamdemod(x_soft_unit_for_res, M_mod, 'gray', 'UnitAveragePower', true);
        x_hard_unit_for_res = qammod(x_hard_idx_for_res, M_mod, 'gray', 'UnitAveragePower', true);
        x_hard_scaled_for_res = x_hard_unit_for_res * sqrt(power_levels(1));

        x_total_for_res = x_p_scaled + x_hard_scaled_for_res;
        res = Y_DA - Hhat * x_total_for_res;
        sigma2_new = real(sum(abs(res).^2)) / N_data;
        sigma2_eff = 0.7 * sigma2_eff + 0.3 * max(sigma2_new, 1e-12);

        lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff);
    end

    %% ===== (D) Early Stop Criterion ===== %%
    x_soft_unit_for_stop = x_soft_scaled / sqrt(power_levels(1));
    x_hard_idx_for_stop = qamdemod(x_soft_unit_for_stop, M_mod, 'gray', 'UnitAveragePower', true);
    x_hard_unit_for_stop = qammod(x_hard_idx_for_stop, M_mod, 'gray', 'UnitAveragePower', true);
    x_hard_scaled_for_stop = x_hard_unit_for_stop * sqrt(power_levels(1));

    x_total_for_stop = x_p_scaled + x_hard_scaled_for_stop;
    curr_resnorm = norm(Y_DA - Hhat * x_total_for_stop)^2;

    if prev_resnorm < Inf
        rel_improve = (prev_resnorm - curr_resnorm) / max(curr_resnorm, 1e-12);
        if rel_improve < EPS_STOP_REL && rel_improve >= 0
            if debug_flag
                fprintf('  [Iter %d] Early stop (rel_improve=%.4e < %.4e)\n', ...
                    it, rel_improve, EPS_STOP_REL);
            end
            break;
        end
    end
    prev_resnorm = curr_resnorm;
end

if debug_flag
    fprintf('========== Joint OMP↔MP with DA-LS End ==========\n\n');
end

%% Final Output
H_final = Hhat;
H_true_full = full(H_true);
H_final_full = full(H_final);
mse_final = norm(H_final_full - H_true_full, 'fro')^2 / norm(H_true_full, 'fro')^2;  % LINEAR

x_final_unit = x_soft_scaled / sqrt(power_levels(1));
x_est_idx = qamdemod(x_final_unit, M_mod, 'gray', 'UnitAveragePower', true);
end


function a_col = gen_path_col(N, l, k, c1, x_scaled)
%GEN_PATH_COL Generate single path dictionary column (consistent with GEN_H_DAFT)

q_vec = (0:N-1).';
c2 = 0;

% Location shift: loc = k + 2*N*c1*l
loc_val = k + 2 * N * c1 * l;

% Receive index: p = (q - loc) mod N
p_vec = mod(round(q_vec - loc_val), N);

% Phase computation
term1 = N * c1 * (l^2);
term2 = -q_vec * l;
term3 = N * c2 * (q_vec.^2 - p_vec.^2);
total_phase = (2 * pi / N) * (term1 + term2 + term3);

H_vals = exp(1j * total_phase);

% Output vector
a_col = zeros(N, 1);
for qi = 1:N
    p_idx = p_vec(qi) + 1;
    a_col(p_idx) = a_col(p_idx) + H_vals(qi) * x_scaled(qi);
end
end


function g = weighted_ls(A, y, w, lambda, g_prev)
%WEIGHTED_LS Weighted least squares with Tikhonov regularization
%
% Inputs:
%   A      - Dictionary matrix (N x P)
%   y      - Observation vector (N x 1)
%   w      - Optional weight vector (N x 1), empty for standard LS
%   lambda - Tikhonov regularization coefficient
%   g_prev - Previous gain estimate (for regularization)
%
% Output:
%   g      - New gain estimate (P x 1)

if nargin < 5 || isempty(g_prev)
    g_prev = zeros(size(A, 2), 1);
end

if isempty(w)
    % Standard LS
    W2 = speye(length(y));
else
    % Weighted LS
    W2 = spdiags(w.^2, 0, length(w), length(w));
end

% (A^H W^2 A + λI)^{-1} (A^H W^2 y + λ g_prev)
g = (A' * W2 * A + lambda * eye(size(A, 2))) \ (A' * W2 * y + lambda * g_prev);
end
