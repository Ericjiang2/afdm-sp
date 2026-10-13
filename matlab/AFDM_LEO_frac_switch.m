clear; clc; close all;
rng(1)
% addpath("Algorithms\")
% addpath("Utils\");
% addpath("latest\trunk\code\main\");
% addpath("latest\trunk\code\VAMP\");

% %% 并行池设置 %%
%% 并行池设置（设置每个 Worker 使用 2 线程） %%
desired_workers = 4;      % 并行进程数
threads_per_worker = 1;   % 每个进程占用的线程数

pool = gcp('nocreate');
if isempty(pool)
    % 获取本地集群对象
    c = parcluster('local');
    
    % 设置每个 Worker 的线程数
    % 这将允许每个 Worker 调用 BLAS/LAPACK 等库时使用 2 个线程
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
        % 如果池已存在，强制在所有运行中的 Worker 上设置线程数
        pctRunOnAll(['maxNumCompThreads(' num2str(threads_per_worker) ')']);
        fprintf('Parallel pool already running. Threads set to %d via pctRunOnAll.\n', threads_per_worker);
    end
end
%% Debug & Simulation Controls %%
DEBUG_PRINT_FLAG = true;

% ====== 整数/分数多普勒统一开关 ======
USE_FRAC_DOPPLER = false;   % true: 分数多普勒模式; false: 整数多普勒模式
INTEGER_DOPPLER_FLAG = ~USE_FRAC_DOPPLER;  % 保持向后兼容

% ====== 分数多普勒(Frac-Doppler)仿真控制参数 ======
K_LEAK = 5;          % 分数多普勒泄漏半宽(整数栅格个数). K_LEAK=4 => 每条物理径用9个整数多普勒近似
USE_3GPP_NTN_TDL = true;              % true: 使用3GPP TR 38.811 的 NTN-TDL 参数; false: 使用原先随机LEO信道
NTN_TDL_PROFILE = 'NTN-TDL-C';        % {'NTN-TDL-A','NTN-TDL-B','NTN-TDL-C','NTN-TDL-D'}
TDL_USE_DOMINANT_2TAPS = false;        % true: 仅取最强两条tap (兼容原论文P=2); false: 使用完整profile

% ====== 3GPP NTN 物理参数 (用于计算多普勒) ======
H_SAT = 600e3;                       % 卫星高度 (m), 600km LEO
R_EARTH = 6371e3;                    % 地球半径 (m)
G_EARTH = 3.986e14;                  % 地球引力常数 GM (m^3/s^2)
V_SAT = sqrt(G_EARTH / (R_EARTH + H_SAT));  % 卫星轨道速度 (m/s), ~7.56 km/s
ALPHA_MIN_DEG = 30;                  % 最小仰角 (degree), 用于计算最大多普勒
UE_SPEED = 0;                        % UE 速度(若需要可>0, 用于局部散射多普勒扩展)
LOCAL_DOPPLER_SPREAD_HZ = 50;        % 局部散射/移动引起的额外Doppler扩展 (Hz)

%% System parameters %%
M_mod = 4;
N = 256;
bps = log2(M_mod);
delta_f = 15*10^3;
T = 1/delta_f;
SNR_dB = 0:  5: 25;
sigma_2 = 1./(10.^(SNR_dB/10));
N_frame = 11000;  % 最大帧数
target_snr_for_iter = 10;
target_snr_for_iter_2 = 15;
target_snr_for_iter_3 = 20;
target_snr_for_iter_4 = 25;

%% ====== 根据 3GPP TR 38.811 计算 k_max (审稿人5要求) ====== %%
% 选择载频：要得到 k_max≈16，需要较高的载频
% f_c = 2 GHz  => k_max ≈ 3-4
% f_c = 12 GHz => k_max ≈ 16-20 (Ku波段，典型 LEO 通信频段)
% f_c = 20 GHz => k_max ≈ 30+   (Ka波段)
car_fre = 12e9;  % 载频 12 GHz 

c_light = 3e8;
% 3GPP TR 38.811 公式: f_d = (v_sat/c) * f_c * (R/(R+h)) * cos(alpha)
v_rel_max = V_SAT * (R_EARTH / (R_EARTH + H_SAT)) * cosd(ALPHA_MIN_DEG);
f_d_max = (v_rel_max / c_light) * car_fre;  % 最大多普勒频移 (Hz)
nu_max = f_d_max / delta_f;                 % 归一化多普勒
k_max_calc = ceil(nu_max);                  % 整数多普勒索引上界

% 打印计算结果
fprintf('\n========== 3GPP NTN Doppler Calculation ==========\n');
fprintf('  Carrier frequency: %.2f GHz\n', car_fre/1e9);
fprintf('  Satellite altitude: %.0f km\n', H_SAT/1000);
fprintf('  Satellite velocity: %.2f km/s\n', V_SAT/1000);
fprintf('  Min elevation angle: %.0f deg\n', ALPHA_MIN_DEG);
fprintf('  Max relative velocity: %.2f m/s\n', v_rel_max);
fprintf('  Max Doppler shift: %.2f kHz\n', f_d_max/1000);
fprintf('  Normalized Doppler (nu_max): %.2f\n', nu_max);
fprintf('  Calculated k_max: %d\n', k_max_calc);
fprintf('===================================================\n\n');

%% LEO Satellite Channel Parameters %%
% 使用计算得到的 k_max，或手动指定（取较大值以留余量）
%k_max = max(k_max_calc, 16);  % 确保至少为16以覆盖可能的变化
k_max = k_max_calc;
l_max = 2;                    % 最大时延抽头数（由 NTN-TDL 时延缩放决定）
taps = 2;                     % 物理路径数（若 TDL_USE_DOMINANT_2TAPS=true）
rician_fac = 10;              % Rician K因子 (dB)，用于非3GPP模式
power_levels = [0.5, 0.5];    % 数据/导频功率分配

%% ====== 自适应帧数配置 ====== %%
ADAPTIVE_FRAME_ENABLE = true;        % 是否启用自适应帧数
MIN_ERROR_BITS = 1000;               % 最小错误比特数（保证置信度）
MIN_FRAMES = 30;                     % 最小帧数（避免过早停止）
CHECK_INTERVAL = 100;                % 每100帧检查一次是否可以早停

%% MP parameters %%
num_iter_MP = 20;
threshold_MP = 1e-4;

%% ====== 联合迭代配置（最终优化版）====== %%
NUM_OUTER_ITS      = 5;
GAMMA_H_DAMP       = 0.7;
GAMMA_X_DAMP       = 0.6;
EPS_STOP_REL       = 1e-3;
UPDATE_SIGMA2_EACH_OUTER = true;

LAMBDA_LS_FACTOR = 1e-3;

%% ====== 稀疏化门限配置 ====== %%
TAU_H_FACTOR = 0.01;
TAU_H_SIGMA_FACTOR = 0.1;

%% AFDM parameters %%
max_Doppler = k_max;
max_delay = l_max - 1;
CPP_len = max_delay;
N_data = N - CPP_len;
k_v = 4;
if (2*(max_Doppler+k_v)*(max_delay+1)+max_delay) > N_data
    error('subcarrier orthogonality is not satisfied');
end
c1 = (2*(max_Doppler+k_v)+1) / (2*N_data);

%% 预计算正则化矩阵 %%
reg_matrices = cell(1, length(SNR_dB));
for iesn0 = 1:length(SNR_dB)
    reg_matrices{iesn0} = sigma_2(iesn0) * eye(N_data);
end

%% 初始化统计变量 %%
% 串行方法
ber_perfect_CSI = zeros(1, length(SNR_dB));
ber_perfect_CSI_MP = zeros(1, length(SNR_dB));
ber_LS_MMSE = zeros(1, length(SNR_dB));
ber_superimposed_pilot_OMP = zeros(1, length(SNR_dB));
ber_superimposed_pilot_OMP_MP = zeros(1, length(SNR_dB));

% 联合方法
ber_joint = zeros(1, length(SNR_dB));

% MSE
MSE_channel_LS = zeros(1, length(SNR_dB));
MSE_channel_OMP = zeros(1, length(SNR_dB));
MSE_channel_joint = zeros(1, length(SNR_dB));

% BER-iteration tracking (SNR-dependent slices)
ber_iter_joint_history = nan(NUM_OUTER_ITS, N_frame, length(SNR_dB));

% 记录实际使用的帧数
actual_frames_used = zeros(1, length(SNR_dB));

parfor iesn0 = 1:length(SNR_dB)
    sigma2_current = sigma_2(iesn0);
    reg_eye = reg_matrices{iesn0};

    % 误码计数
    err_count_perfect = 0;
    err_count_perfect_mp = 0;
    err_count_ls_mmse = 0;
    err_count_pilot_omp = 0;
    err_count_pilot_omp_mp = 0;
    err_count_joint = 0;

    % MSE 记录
    mse_values_ls = [];
    mse_values_omp = [];
    mse_values_joint = [];
    ber_iter_history_local = nan(NUM_OUTER_ITS, N_frame);
    
    % 自适应帧数控制变量
    frames_processed = 0;
    early_stop_triggered = false;

    for iframe = 1:N_frame
        %% Generate Channel (Integer / Fractional Doppler Switchable) %%
        if USE_3GPP_NTN_TDL
            % 每帧随机化仰角 (在 ALPHA_MIN_DEG ~ 90 度之间)
            alpha_this_frame = ALPHA_MIN_DEG + rand * (90 - ALPHA_MIN_DEG);
            [chan_coef, delay_taps, Doppler_taps] = generate_NTN_TDL_channel_SISO( ...
                taps, l_max, k_max, car_fre, delta_f, N_data, ...
                INTEGER_DOPPLER_FLAG, NTN_TDL_PROFILE, TDL_USE_DOMINANT_2TAPS, K_LEAK, ...
                alpha_this_frame, V_SAT, UE_SPEED, LOCAL_DOPPLER_SPREAD_HZ, R_EARTH, H_SAT);
        else
            [chan_coef, delay_taps, Doppler_taps] = generate_LEO_channel_SISO_integer( ...
                taps, l_max, k_max, rician_fac, car_fre, N_data, T);
        end
        
        % 获取实际路径数（分数模式下可能比 taps 多）
        P_actual = length(chan_coef);

        
        %% Generate data and pilot symbols %%
        x_idx = randi([0, M_mod-1], N_data, 1);
        x_qam = qammod(x_idx, M_mod, 'gray', 'UnitAveragePower', true);
        
        x_pilot_idx = randi([0, M_mod-1], N_data, 1);
        x_pilot_qam = qammod(x_pilot_idx, M_mod, 'gray', 'UnitAveragePower', true);
        
        x_bit_data = de2bi(x_idx, bps, 'left-msb');

        %% AFDM Modulation & Transmission %%
        x_da_combined = x_qam*sqrt(power_levels(1)) + x_pilot_qam*sqrt(power_levels(2));
        H_DAFT = GEN_H_DAFT(N_data, chan_coef, delay_taps, Doppler_taps, c1);
        
        Y_DA_noiseless = H_DAFT * x_da_combined;
        noise_da = sqrt(sigma_2(iesn0)/2) * (randn(N_data,1) + 1j*randn(N_data,1));
        Y_DA = Y_DA_noiseless + noise_da;

        %% ========== 1. 传统基准算法 (Perfect / LS / OMP) ========== %%
        
        % --- A. Perfect CSI + MMSE (作为性能上界和早停基准) ---
        H_DAFT_full = full(H_DAFT);
        HtH_perfect = H_DAFT_full' * H_DAFT_full;
        Wmmse_perfect = (HtH_perfect + reg_eye) \ H_DAFT_full';
        Y_data_perfect = Y_DA - H_DAFT * x_pilot_qam * sqrt(power_levels(2));
        x_hat_perfect = Wmmse_perfect * Y_data_perfect;
        x_est_symbols_perfect = x_hat_perfect / sqrt(power_levels(1));
        x_est_idx_perfect = qamdemod(x_est_symbols_perfect, M_mod, 'gray', 'UnitAveragePower', true);
        err_count_perfect = err_count_perfect + biterr(de2bi(x_est_idx_perfect, bps, 'left-msb'), x_bit_data);

        % --- B. Perfect CSI + MP ---
        Y_DA_data_only_perfect_mp = Y_DA - H_DAFT * x_pilot_qam * sqrt(power_levels(2));
        x_mp_perfect = MP_detection_optimized(Y_DA_data_only_perfect_mp, H_DAFT, sigma2_current, num_iter_MP, threshold_MP, M_mod, sqrt(power_levels(1)));
        x_mp_perfect_normalized = x_mp_perfect / sqrt(power_levels(1));
        x_est_idx_perfect_mp = qamdemod(x_mp_perfect_normalized, M_mod, 'gray', 'UnitAveragePower', true);
        err_count_perfect_mp = err_count_perfect_mp + biterr(de2bi(x_est_idx_perfect_mp, bps, 'left-msb'), x_bit_data);

        %% Channel Estimation %%
        Q = (2*k_max+1) * l_max;
        Phi = construct_afdm_sensing_matrix(N_data, x_pilot_qam, c1, Q, l_max-1, k_max, 1, 1);
        Phi_scaled = Phi * sqrt(power_levels(2));
        
        % --- C. LS 信道估计 ---
        lambda_ridge = 1e-2 * sigma2_current * N_data;
        h_LS = (Phi_scaled' * Phi_scaled + lambda_ridge * eye(Q)) \ (Phi_scaled' * Y_DA);

        if ~INTEGER_DOPPLER_FLAG
            % 理论上每条径泄漏范围是 2*K_LEAK + 1
            ls_extract_count = taps * (2 * K_LEAK + 1); 
        else
            ls_extract_count = taps;
        end

        [delays_ls, dopplers_ls, gains_ls] = extract_delay_doppler_from_h(h_LS, ls_extract_count, l_max-1, k_max, 1, 1);
        H_DAFT_est_ls = GEN_H_DAFT(N_data, gains_ls, delays_ls, dopplers_ls, c1);
        mse_values_ls = [mse_values_ls, 10*log10(norm(H_DAFT_est_ls - H_DAFT, 'fro')^2 / norm(H_DAFT, 'fro')^2)];
        
        % --- LS + MMSE 检测 ---
        H_ls_full = full(H_DAFT_est_ls);
        HtH_ls = H_ls_full' * H_ls_full;
        Wmmse_ls = (HtH_ls + reg_eye) \ H_ls_full';
        Y_data_ls = Y_DA - H_DAFT_est_ls * x_pilot_qam * sqrt(power_levels(2));
        x_hat_ls = Wmmse_ls * Y_data_ls;
        x_est_idx_ls = qamdemod(x_hat_ls / sqrt(power_levels(1)), M_mod, 'gray', 'UnitAveragePower', true);
        err_count_ls_mmse = err_count_ls_mmse + biterr(de2bi(x_est_idx_ls, bps, 'left-msb'), x_bit_data);
        
        % --- D. OMP 信道估计 ---
        % OMP 稀疏度：整数模式用 taps，分数模式用物理路径数
        omp_sparsity = taps;
        if ~INTEGER_DOPPLER_FLAG
            % 分数模式下，物理路径经 Dirichlet 分解后路径数增多
            omp_sparsity = min(P_actual, taps * (2*K_LEAK + 1));
        end
        [h_OMP, ~] = OMP(Y_DA, Phi_scaled, omp_sparsity);
        [delays_omp, dopplers_omp, gains_omp] = extract_delay_doppler_from_h(h_OMP, omp_sparsity, l_max-1, k_max, 1, 1);
        H_DAFT_est_omp = GEN_H_DAFT(N_data, gains_omp, delays_omp, dopplers_omp, c1);
        mse_values_omp = [mse_values_omp, 10*log10(norm(H_DAFT_est_omp - H_DAFT, 'fro')^2 / norm(H_DAFT, 'fro')^2)];
        
        %% --- E. OMP + MMSE 检测 ---
        H_DAFT_est_omp_full = full(H_DAFT_est_omp);
        HtH_omp = H_DAFT_est_omp_full' * H_DAFT_est_omp_full;
        Wmmse_DAFT_omp = (HtH_omp + reg_eye) \ H_DAFT_est_omp_full';
        Y_data_omp = Y_DA - H_DAFT_est_omp * x_pilot_qam * sqrt(power_levels(2));
        x_hat_omp = Wmmse_DAFT_omp * Y_data_omp;
        y_omp_normalized = x_hat_omp / sqrt(power_levels(1));
        x_est_idx_omp = qamdemod(y_omp_normalized, M_mod, 'gray', 'UnitAveragePower', true);
        err_count_pilot_omp = err_count_pilot_omp + biterr(de2bi(x_est_idx_omp, bps, 'left-msb'), x_bit_data);

        % --- F. OMP + MP ---
        Y_DA_data_only_mp_omp = Y_DA - H_DAFT_est_omp * x_pilot_qam * sqrt(power_levels(2));
        x_mp_omp = MP_detection_optimized(Y_DA_data_only_mp_omp, H_DAFT_est_omp, sigma2_current, num_iter_MP, threshold_MP, M_mod, sqrt(power_levels(1)));
        x_mp_omp_normalized = x_mp_omp / sqrt(power_levels(1));
        x_est_idx_omp_mp = qamdemod(x_mp_omp_normalized, M_mod, 'gray', 'UnitAveragePower', true);
        err_count_pilot_omp_mp = err_count_pilot_omp_mp + biterr(de2bi(x_est_idx_omp_mp, bps, 'left-msb'), x_bit_data);

        %% ========== 2. 联合迭代接收机 ========== %%
        % 联合迭代中使用的路径数
        taps_joint = omp_sparsity;
        [x_est_idx_joint, ~, mse_joint, ber_hist_joint] = joint_omp_mp_ls_sparse(... 
            Y_DA, H_DAFT_est_omp, x_pilot_qam, x_bit_data, H_DAFT, ... 
            N_data, M_mod, bps, sigma2_current, power_levels, c1, ... 
            l_max, k_max, taps_joint, num_iter_MP, threshold_MP, ... 
            NUM_OUTER_ITS, GAMMA_H_DAMP, GAMMA_X_DAMP, ... 
            LAMBDA_LS_FACTOR, EPS_STOP_REL, UPDATE_SIGMA2_EACH_OUTER, ...
            TAU_H_FACTOR, TAU_H_SIGMA_FACTOR, ...
            INTEGER_DOPPLER_FLAG, K_LEAK, ...
            DEBUG_PRINT_FLAG && iframe==1 && iesn0==1);
        err_count_joint = err_count_joint + biterr(de2bi(x_est_idx_joint, bps, 'left-msb'), x_bit_data);
        mse_values_joint = [mse_values_joint, mse_joint];
        ber_iter_history_local(: , iframe) = ber_hist_joint;

        frames_processed = iframe;
        
        %% ====== 自适应早停检查 ====== %%
        if ADAPTIVE_FRAME_ENABLE && iframe >= MIN_FRAMES && mod(iframe, CHECK_INTERVAL) == 0
            % 检查 Perfect CSI 的错误比特数是否达到阈值
            if err_count_perfect >= MIN_ERROR_BITS
                early_stop_triggered = true;
                if iesn0 == 1  % 只在第一个SNR点打印（避免parfor输出混乱）
                    fprintf('[SNR=%2ddB] Early stop at frame %d (err_bits=%d >= %d)\n', ...
                        SNR_dB(iesn0), iframe, err_count_perfect, MIN_ERROR_BITS);
                end
                break;
            end
        end
    end

    actual_frames_used(iesn0) = frames_processed;
    
    %% 填充未使用的帧（用于迭代历史记录）
    if frames_processed < N_frame
        ber_iter_history_local(: , frames_processed+1:end) = nan;
    end
    
    ber_iter_joint_history(: , : , iesn0) = ber_iter_history_local;
    
    %% 统计结果 %%
    total_bits = N_data * bps * frames_processed;
    
    ber_perfect_CSI(iesn0) = err_count_perfect / total_bits;
    ber_perfect_CSI_MP(iesn0) = err_count_perfect_mp / total_bits;
    ber_LS_MMSE(iesn0) = err_count_ls_mmse / total_bits;
    ber_superimposed_pilot_OMP(iesn0) = err_count_pilot_omp / total_bits;
    ber_superimposed_pilot_OMP_MP(iesn0) = err_count_pilot_omp_mp / total_bits;
    ber_joint(iesn0) = err_count_joint / total_bits;

    MSE_channel_LS(iesn0) = mean(mse_values_ls);
    MSE_channel_OMP(iesn0) = mean(mse_values_omp);
    MSE_channel_joint(iesn0) = mean(mse_values_joint);
    
    fprintf('SNR=%2ddB | Frames=%4d | Perfect:  %. 4e | LS+MMSE: %.4e | OMP+MMSE: %.4e | OMP+MP: %.4e | Joint: %.4e\n', ...
        SNR_dB(iesn0), frames_processed, ber_perfect_CSI(iesn0), ber_LS_MMSE(iesn0), ...
        ber_superimposed_pilot_OMP(iesn0), ber_superimposed_pilot_OMP_MP(iesn0), ber_joint(iesn0));
end

%% 打印帧数使用统计
fprintf('\n========== Adaptive Frame Usage Summary ==========\n');
for iesn0 = 1:length(SNR_dB)
    fprintf('SNR=%2ddB:  Used %4d/%4d frames (%.1f%%)\n', ...
        SNR_dB(iesn0), actual_frames_used(iesn0), N_frame, ... 
        100*actual_frames_used(iesn0)/N_frame);
end
fprintf('===================================================\n');

%% 提取迭代曲线数据
% 提取 SNR 1 的迭代曲线
idx_snr1 = find(SNR_dB == target_snr_for_iter, 1);
ber_iter_curve_1 = [];
if ~isempty(idx_snr1)
    slice1 = squeeze(ber_iter_joint_history(: , : , idx_snr1));
    valid_cols_1 = any(~isnan(slice1), 1);
    if any(valid_cols_1)
        ber_iter_curve_1 = mean(slice1(: , valid_cols_1), 2, 'omitnan');
    end
end

% 提取 SNR 2 的迭代曲线
idx_snr2 = find(SNR_dB == target_snr_for_iter_2, 1);
ber_iter_curve_2 = [];
if ~isempty(idx_snr2)
    slice2 = squeeze(ber_iter_joint_history(:, :, idx_snr2));
    valid_cols_2 = any(~isnan(slice2), 1);
    if any(valid_cols_2)
        ber_iter_curve_2 = mean(slice2(:, valid_cols_2), 2, 'omitnan');
    end
end

% 提取 SNR 3 的迭代曲线
idx_snr3 = find(SNR_dB == target_snr_for_iter_3, 1);
ber_iter_curve_3 = [];
if ~isempty(idx_snr3)
    slice3 = squeeze(ber_iter_joint_history(:, :, idx_snr3));
    valid_cols_3 = any(~isnan(slice3), 1);
    if any(valid_cols_3)
        ber_iter_curve_3 = mean(slice3(:, valid_cols_3), 2, 'omitnan');
    end
end

% 提取 SNR 4 的迭代曲线
idx_snr4 = find(SNR_dB == target_snr_for_iter_4, 1);
ber_iter_curve_4 = [];
if ~isempty(idx_snr4)
    slice4 = squeeze(ber_iter_joint_history(:, :, idx_snr4));
    valid_cols_4 = any(~isnan(slice4), 1);
    if any(valid_cols_4)
        ber_iter_curve_4 = mean(slice4(:, valid_cols_4), 2, 'omitnan');
    end
end
iterations = (1:NUM_OUTER_ITS).';

%% ========== Save data + plot ==========
results_dir = 'results';
if ~exist(results_dir, 'dir')
    mkdir(results_dir);
end
timestamp = datestr(now, 'yyyymmdd_HHMMSS');

sim_file = fullfile(results_dir, ['AFDM_LEO_sim_' timestamp '.mat']);
save(sim_file, 'SNR_dB', 'ber_perfect_CSI', 'ber_perfect_CSI_MP', 'ber_LS_MMSE', ...
    'ber_superimposed_pilot_OMP', 'ber_superimposed_pilot_OMP_MP', 'ber_joint', ...
    'MSE_channel_LS', 'MSE_channel_OMP', 'MSE_channel_joint', 'ber_iter_joint_history', ...
    'NUM_OUTER_ITS', 'N_frame', 'actual_frames_used', ...
    'target_snr_for_iter', 'target_snr_for_iter_2', 'target_snr_for_iter_3', 'target_snr_for_iter_4', ...
    'USE_FRAC_DOPPLER', 'K_LEAK', 'USE_3GPP_NTN_TDL', 'NTN_TDL_PROFILE', ...
    'car_fre', 'k_max', 'l_max', 'H_SAT', 'V_SAT', 'ALPHA_MIN_DEG');

P = struct();
P.SNR_dB = SNR_dB;
P.ber_perfect_CSI = ber_perfect_CSI;
P.ber_perfect_CSI_MP = ber_perfect_CSI_MP;
P.ber_LS_MMSE = ber_LS_MMSE;
P.ber_superimposed_pilot_OMP = ber_superimposed_pilot_OMP;
P.ber_superimposed_pilot_OMP_MP = ber_superimposed_pilot_OMP_MP;
P.ber_joint = ber_joint;
P.MSE_channel_LS = MSE_channel_LS;
P.MSE_channel_OMP = MSE_channel_OMP;
P.MSE_channel_joint = MSE_channel_joint;
P.ber_iter_curve_1 = ber_iter_curve_1;
P.ber_iter_curve_2 = ber_iter_curve_2;
P.ber_iter_curve_3 = ber_iter_curve_3;
P.ber_iter_curve_4 = ber_iter_curve_4;
P.iterations = iterations;
P.NUM_OUTER_ITS = NUM_OUTER_ITS;
P.target_snr_for_iter = target_snr_for_iter;
P.target_snr_for_iter_2 = target_snr_for_iter_2;
P.target_snr_for_iter_3 = target_snr_for_iter_3;
P.target_snr_for_iter_4 = target_snr_for_iter_4;

plot_file = fullfile(results_dir, ['AFDM_LEO_plot_' timestamp '.mat']);
save(plot_file, 'P');

plot_afdm_leo_results(P);

% =========================================================================
% ========================== 优化后的 MP 检测函数 =========================
% =========================================================================
function x_est = MP_detection_optimized(y, H, sigma2, num_iter, threshold, M_mod, scale_factor)
%MP_DETECTION_OPTIMIZED 优化后的消息传递检测
%
% 主要优化：
%   1. 使用排序+指针切片构建 CSR/CSC，避免 O(N·E) 扫描
%   2. 方差计算增加数值保护，确保 var >= 0
%   3. 启用 threshold 参数进行边稀疏化
%
% 输入：
%   y            - 接收信号 (N x 1)
%   H            - 信道矩阵 (N x N)，可以是 sparse 或 full
%   sigma2       - 噪声方差
%   num_iter     - 最大迭代次数
%   threshold    - 边稀疏化门限（|H_ij| < threshold 的边被删除）
%   M_mod        - 调制阶数
%   scale_factor - 符号缩放因子
%
% 输出：
%   x_est        - 检测到的符号 (N x 1)

    N = size(H, 1);
    
    %% 生成 QAM 星座点
    constellation = qammod((0:M_mod-1)', M_mod, 'gray', 'UnitAveragePower', true) * scale_factor;
    
    %% 稀疏化信道矩阵：删除 |H_ij| < threshold 的边
    if ~issparse(H)
        H = sparse(H);
    end
    
    % 应用门限稀疏化
    [row_idx, col_idx, h_vals] = find(H);
    mask = abs(h_vals) >= threshold;
    row_idx = row_idx(mask);
    col_idx = col_idx(mask);
    h_vals = h_vals(mask);
    
    E = length(h_vals);  % 边数
    
    if E == 0
        % 如果没有边，返回 MMSE 估计
        x_est = zeros(N, 1);
        return;
    end
    
    %% 使用排序构建 CSR/CSC 结构（优化后的 O(E log E) 复杂度）
    % CSR:  按行排序，用于观测节点到变量节点的消息
    [sorted_by_row, sort_idx_row] = sortrows([row_idx, (1:E)']);
    row_sorted = sorted_by_row(: , 1);
    edge_id_by_row = sorted_by_row(:, 2);
    
    % 构建行指针 (CSR)
    row_ptr = zeros(N + 1, 1);
    row_ptr(1) = 1;
    current_row = 1;
    for e = 1:E
        while current_row < row_sorted(e)
            row_ptr(current_row + 1) = e;
            current_row = current_row + 1;
        end
    end
    for r = current_row: N
        row_ptr(r + 1) = E + 1;
    end
    
    % CSC: 按列排序，用于变量节点到观测节点的消息
    [sorted_by_col, sort_idx_col] = sortrows([col_idx, (1:E)']);
    col_sorted = sorted_by_col(:, 1);
    edge_id_by_col = sorted_by_col(:, 2);
    
    % 构建列指针 (CSC)
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
    
    %% 初始化消息
    % 变量节点到观测节点的消息：均值和方差
    mu_v2o = zeros(E, 1);           % E[x] 消息
    var_v2o = ones(E, 1);           % Var[x] 消息
    
    % 观测节点到变量节点的消息
    mu_o2v = zeros(E, 1);
    var_o2v = ones(E, 1);
    
    % 先验：均匀分布
    prior_mean = mean(constellation);
    prior_var = var(constellation);
    
    mu_v2o(: ) = prior_mean;
    var_v2o(:) = prior_var;
    
    %% 阻尼系数
    damp = 0.5;
    
    %% 迭代消息传递
    for iter = 1:num_iter
        mu_v2o_old = mu_v2o;
        
        %% Step 1: 观测节点 -> 变量节点 (O2V)
        for d = 1:N
            % 获取连接到观测节点 d 的所有边
            edge_start = row_ptr(d);
            edge_end = row_ptr(d + 1) - 1;
            
            if edge_start > edge_end
                continue;  % 该观测节点没有连接的边
            end
            
            edges_d = edge_id_by_row(edge_start:edge_end);
            num_edges_d = length(edges_d);
            
            % 获取这些边对应的列索引和信道值
            cols_d = col_idx(edges_d);
            h_d = h_vals(edges_d);
            
            % 计算总均值和总方差（来自所有 V2O 消息）
            mu_in = mu_v2o(edges_d);
            var_in = var_v2o(edges_d);
            
            % 计算 z_d = y_d - sum(h_ij * mu_ij)
            z_total = y(d) - sum(h_d .* mu_in);
            
            % 计算总方差 V_total = sigma2 + sum(|h_ij|^2 * var_ij)
            V_total = sigma2 + sum(abs(h_d).^2 .* var_in);
            
            % 对每条边计算外消息
            for local_e = 1:num_edges_d
                e = edges_d(local_e);
                h_e = h_d(local_e);
                mu_e = mu_in(local_e);
                var_e = var_in(local_e);
                
                % 外消息：排除当前边的贡献
                z_ext = z_total + h_e * mu_e;
                V_ext = V_total - abs(h_e)^2 * var_e;
                
                % 数值保护：确保方差为正
                V_ext = max(V_ext, sigma2 * 0.1);
                
                % 计算 O2V 消息
                if abs(h_e) > 1e-10
                    var_o2v(e) = V_ext / abs(h_e)^2;
                    mu_o2v(e) = z_ext / h_e;
                else
                    var_o2v(e) = 1e10;
                    mu_o2v(e) = 0;
                end
                
                % 数值保护
                var_o2v(e) = max(var_o2v(e), 1e-10);
            end
        end
        
        %% Step 2: 变量节点 -> 观测节点 (V2O)
        for n = 1:N
            % 获取连接到变量节点 n 的所有边
            edge_start = col_ptr(n);
            edge_end = col_ptr(n + 1) - 1;
            
            if edge_start > edge_end
                continue;  % 该变量节点没有连接的边
            end
            
            edges_n = edge_id_by_col(edge_start:edge_end);
            num_edges_n = length(edges_n);
            
            % 获取 O2V 消息
            mu_in = mu_o2v(edges_n);
            var_in = var_o2v(edges_n);
            
            % 计算后验：结合先验和所有 O2V 消息
            % 使用高斯乘积公式
            prec_total = 1 / prior_var + sum(1 ./ var_in);
            mean_total = prior_mean / prior_var + sum(mu_in ./ var_in);
            
            var_post = 1 / prec_total;
            mu_post = var_post * mean_total;
            
            % 对每条边计算外消息
            for local_e = 1:num_edges_n
                e = edges_n(local_e);
                mu_e = mu_in(local_e);
                var_e = var_in(local_e);
                
                % 外消息：排除当前边的贡献
                prec_ext = prec_total - 1 / var_e;
                mean_ext = mean_total - mu_e / var_e;
                
                % 数值保护
                prec_ext = max(prec_ext, 1e-10);
                var_ext = 1 / prec_ext;
                mu_ext = var_ext * mean_ext;
                
                % 映射到星座点（软判决）
                % 计算每个星座点的概率
                dist_sq = abs(constellation - mu_ext).^2;
                log_prob = -dist_sq / (2 * var_ext);
                log_prob = log_prob - max(log_prob);  % 数值稳定性
                prob = exp(log_prob);
                prob = prob / sum(prob);
                
                % 计算均值和方差
                mu_v2o_new = sum(prob .* constellation);
                var_v2o_new = sum(prob .* abs(constellation).^2) - abs(mu_v2o_new)^2;
                
                % 数值保护：确保方差为正
                var_v2o_new = max(var_v2o_new, 1e-10);
                
                % 阻尼更新
                mu_v2o(e) = (1 - damp) * mu_v2o_old(e) + damp * mu_v2o_new;
                var_v2o(e) = var_v2o_new;
            end
        end
        
        %% 检查收敛
        if norm(mu_v2o - mu_v2o_old) / max(norm(mu_v2o), 1e-10) < 1e-4
            break;
        end
    end
    
    %% 最终估计：对每个变量节点做 MAP 判决
    x_est = zeros(N, 1);
    
    for n = 1:N
        edge_start = col_ptr(n);
        edge_end = col_ptr(n + 1) - 1;
        
        if edge_start > edge_end
            % 没有边连接，使用先验
            x_est(n) = prior_mean;
            continue;
        end
        
        edges_n = edge_id_by_col(edge_start:edge_end);
        
        % 获取 O2V 消息
        mu_in = mu_o2v(edges_n);
        var_in = var_o2v(edges_n);
        
        % 计算后验
        prec_total = 1 / prior_var + sum(1 ./ var_in);
        mean_total = prior_mean / prior_var + sum(mu_in ./ var_in);
        
        var_post = 1 / prec_total;
        mu_post = var_post * mean_total;
        
        % 硬判决：映射到最近的星座点
        [~, min_idx] = min(abs(constellation - mu_post));
        x_est(n) = constellation(min_idx);
    end
end


% =========================================================================
% ========================== 联合迭代函数（稀疏版）========================
% =========================================================================
function [x_est_idx, H_final, mse_final, ber_iter_history] = joint_omp_mp_ls_sparse(...   
    Y_DA, H_init, x_pilot, x_bit_data, H_true, ...   
    N_data, M_mod, bps, sigma2_init, power_levels, c1, ...   
    l_max, k_max, taps, num_iter_MP, threshold_MP, ...  
    NUM_OUTER_ITS, GAMMA_H_DAMP, GAMMA_X_DAMP, ...   
    lambda_ls_factor, EPS_STOP_REL, UPDATE_SIGMA2_EACH_OUTER, ... 
    TAU_H_FACTOR, TAU_H_SIGMA_FACTOR, INTEGER_DOPPLER_FLAG, K_LEAK, debug_flag)
%JOINT_OMP_MP_LS_SPARSE 联合 OMP↔MP 迭代（保持稀疏性版本）
%
% 核心改进：
%   - 保持 Hhat 为稀疏矩阵
%   - 每轮阻尼后做门限稀疏化
%   - 使用优化后的 MP 检测

    %% 初始化
    % 确保初始信道矩阵为稀疏
    if ~issparse(H_init)
        Hhat = sparse(H_init);
    else
        Hhat = H_init;
    end
    
    x_soft_scaled = zeros(N_data, 1);
    sigma2_eff = sigma2_init;
    
    % 支持集
    support_delays = [];
    support_dopplers = [];
    gains_S = [];
    
    % 导频（缩放域）
    x_p_scaled = x_pilot * sqrt(power_levels(2));
    
    % Tikhonov 正则化系数
    lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff); 
    
    prev_resnorm = Inf;
    ber_iter_history = nan(NUM_OUTER_ITS, 1);
    
    if debug_flag
        fprintf('\n========== Joint OMP↔MP with DA-LS (Sparse Version) ==========\n');
    end
    
    for it = 1:NUM_OUTER_ITS
        
        %% ===== (A) 信道估计更新 ===== %%
        if it == 1
            % ===== 第1次外迭：仅导频 OMP，确定支持集 ===== %
            Q = (2*k_max+1) * l_max;
            Phi_pilot = construct_afdm_sensing_matrix(N_data, x_pilot, c1, Q, l_max-1, k_max, 1, 1);
            Phi_pilot_scaled = Phi_pilot * sqrt(power_levels(2));
            
            [h_new, ~] = OMP(Y_DA, Phi_pilot_scaled, taps);
            [support_delays, support_dopplers, gains_S] = extract_delay_doppler_from_h(...  
                h_new, taps, l_max-1, k_max, 1, 1);
            % ===== 分数多普勒：对 OMP 支持集做“多普勒泄漏”扩展 (Cluster Support) =====
            if ~INTEGER_DOPPLER_FLAG
                [support_delays, support_dopplers, gains_S] = expand_support_doppler( ...
                    support_delays, support_dopplers, gains_S, k_max, K_LEAK);
            end

            if debug_flag
                fprintf('  [Iter 1] OMP determined support:\n');
                for p = 1:length(support_delays)
                    fprintf('    Path %d: (l=%2d, k=%3d), Gain=%.4f+%.4fi\n', ...
                        p, support_delays(p), support_dopplers(p), real(gains_S(p)), imag(gains_S(p)));
                end
            end
            
        else
            % ===== 后续外迭：固定支持，Data-Aided LS（带硬判决能量校正）===== %
            
            % Step 1: 软符号 -> 单位功率域
            x_soft_unit = x_soft_scaled / sqrt(power_levels(1));
            
            % Step 2: 硬判决（映射到最近的 QAM 星座点）
            x_hard_idx = qamdemod(x_soft_unit, M_mod, 'gray', 'UnitAveragePower', true);
            x_hard_unit = qammod(x_hard_idx, M_mod, 'gray', 'UnitAveragePower', true);
            
            % Step 3: 缩放回数据功率域
            x_hard_scaled = x_hard_unit * sqrt(power_levels(1));
            
            % Step 4: 构造"全信号"（导频 + 硬判决数据）
            x_total_scaled = x_p_scaled + x_hard_scaled;
            
            % Step 5: 构造字典列（基于全信号）
            S_l = support_delays(: );
            S_k = support_dopplers(:);
            num_paths = length(S_l);
            
            A_total = zeros(N_data, num_paths);
            for p = 1:num_paths
                A_total(:, p) = gen_path_col(N_data, S_l(p), S_k(p), c1, x_total_scaled);
            end
            
            % Step 6: Data-Aided LS
            g_new = weighted_ls(A_total, Y_DA, [], lambda_ls, gains_S);
            
            % Step 7: 更新增益
            gains_S = g_new;
            
            if debug_flag
                fprintf('  [Iter %d] DA-LS (Hard Decision):\n', it);
                for p = 1:num_paths
                    fprintf('    Path %d: (l=%2d, k=%3d), Gain=%.4f+%.4fi (Mag=%.4f)\n', ... 
                        p, S_l(p), S_k(p), real(gains_S(p)), imag(gains_S(p)), abs(gains_S(p)));
                end
            end
        end
        
        % 由固定支持 + 最新增益组装信道矩阵（保持稀疏）
        H_new = GEN_H_DAFT(N_data, gains_S, support_delays, support_dopplers, c1);
        % H_new 已经是稀疏矩阵，不需要转换
        
        % 外层对信道做阻尼平滑（稀疏矩阵运算）
        Hhat = (1 - GAMMA_H_DAMP) * Hhat + GAMMA_H_DAMP * H_new;
        
        % ===== 稀疏化门限处理 ===== %
        % 计算门限：结合相对门限和基于噪声的门限
        max_h_val = max(abs(nonzeros(Hhat)));
        if isempty(max_h_val)
            max_h_val = 1;
        end
        tau_h_relative = TAU_H_FACTOR * max_h_val;
        tau_h_sigma = TAU_H_SIGMA_FACTOR * sqrt(sigma2_eff);
        tau_h = max(tau_h_relative, tau_h_sigma);
        
        % 应用门限稀疏化
        [row_h, col_h, val_h] = find(Hhat);
        mask_h = abs(val_h) >= tau_h;
        Hhat = sparse(row_h(mask_h), col_h(mask_h), val_h(mask_h), N_data, N_data);
        
        % 统计边数
        num_edges = nnz(Hhat);
        if debug_flag
            fprintf('  [Iter %d] Sparsification:  tau_h=%.4e, edges=%d (%.2f%% of N^2)\n', ...
                it, tau_h, num_edges, 100*num_edges/N_data^2);
        end
        
        %% ===== (B) 数据检测更新：用新信道做 MP ===== %%
        Y_for_det = Y_DA - Hhat * x_p_scaled;
        
        % 使用优化后的 MP 检测（传入稀疏化门限）
        x_mp_scaled = MP_detection_optimized(Y_for_det, Hhat, sigma2_eff, ...   
                        num_iter_MP, threshold_MP, M_mod, sqrt(power_levels(1)));
        
        % 外层对符号软估计做阻尼平滑
        x_soft_scaled = (1 - GAMMA_X_DAMP) * x_soft_scaled + GAMMA_X_DAMP * x_mp_scaled;
        
        %% ===== (C) 自适应噪声估计 ===== %%
        if UPDATE_SIGMA2_EACH_OUTER
            % 使用硬判决数据计算残差
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
        
        %% ===== (D) 外层早停判据 ===== %%
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
                    fprintf('  [Iter %d] Early stop (rel_improve=%.4e < %. 4e)\n', ...  
                        it, rel_improve, EPS_STOP_REL);
                end
                x_iter = x_soft_scaled / sqrt(power_levels(1));
                x_idx_iter = qamdemod(x_iter, M_mod, 'gray', 'UnitAveragePower', true);
                ber_iter = biterr(de2bi(x_idx_iter, bps, 'left-msb'), x_bit_data) / (N_data * bps);
                ber_iter_history(it: end) = ber_iter;
                break;
            end
        end
        prev_resnorm = curr_resnorm;
        
        %% ===== (E) 记录本次迭代 BER ===== %%
        x_iter = x_soft_scaled / sqrt(power_levels(1));
        x_idx_iter = qamdemod(x_iter, M_mod, 'gray', 'UnitAveragePower', true);
        ber_iter = biterr(de2bi(x_idx_iter, bps, 'left-msb'), x_bit_data) / (N_data * bps);
        ber_iter_history(it) = ber_iter;
        
        if debug_flag
            H_true_full = full(H_true);
            Hhat_full = full(Hhat);
            mse_test = 10*log10(norm(Hhat_full - H_true_full, 'fro')^2 / norm(H_true_full, 'fro')^2);
            fprintf('  [Iter %d] BER=%.4e | MSE=%.2f dB | ResNorm=%.4e | sigma2_eff=%.4e\n', ...  
                it, ber_iter, mse_test, curr_resnorm, sigma2_eff);
        end
    end
    
    if debug_flag
        fprintf('========== Joint OMP↔MP with DA-LS (Sparse) End ==========\n\n');
    end
    
    %% 最终输出
    H_final = Hhat;
    H_true_full = full(H_true);
    H_final_full = full(H_final);
    mse_final = 10*log10(norm(H_final_full - H_true_full, 'fro')^2 / norm(H_true_full, 'fro')^2);
    
    x_final_unit = x_soft_scaled / sqrt(power_levels(1));
    x_est_idx = qamdemod(x_final_unit, M_mod, 'gray', 'UnitAveragePower', true);
    
    % 填充未完成的 BER 历史
    last_valid = find(~isnan(ber_iter_history), 1, 'last');
    if isempty(last_valid)
        final_ber = biterr(de2bi(x_est_idx, bps, 'left-msb'), x_bit_data) / (N_data * bps);
        ber_iter_history(: ) = final_ber;
    else
        ber_iter_history(last_valid+1:end) = ber_iter_history(last_valid);
    end
end


% =========================================================================
% ========================== 辅助函数部分 =================================
% =========================================================================

function a_col = gen_path_col(N, l, k, c1, x_scaled)
%GEN_PATH_COL 生成单条路径的字典列（与 GEN_H_DAFT 一致）

    q_vec = (0:N-1).';
    c2 = 0;
    
    % 1. 位移量 loc = k + 2*N*c1*l
    loc_val = k + 2 * N * c1 * l;
    
    % 2. 接收索引 p = (q - loc)_N
    p_vec = mod(round(q_vec - loc_val), N);
    
    % 3. 相位计算
    term1 = N * c1 * (l^2);
    term2 = -q_vec * l;
    term3 = N * c2 * (q_vec.^2 - p_vec.^2);
    total_phase = (2 * pi / N) * (term1 + term2 + term3);
    
    H_vals = exp(1j * total_phase);
    
    % 4. 输出向量
    a_col = zeros(N, 1);
    for qi = 1:N
        p_idx = p_vec(qi) + 1;
        a_col(p_idx) = a_col(p_idx) + H_vals(qi) * x_scaled(qi);
    end
end

function g = weighted_ls(A, y, w, lambda, g_prev)
%WEIGHTED_LS 带可选权重的最小二乘（含 Tikhonov 正则化）
%
% 输入：
%   A - 字典矩阵 (N x P)
%   y - 观测向量 (N x 1)
%   w - 可选权重向量 (N x 1)，若为空则退化为普通 LS
%   lambda - Tikhonov 正则化系数
%   g_prev - 前次增益估计（用于正则化）
%
% 输出：
%   g - 新增益估计 (P x 1)

    if nargin < 5 || isempty(g_prev)
        g_prev = zeros(size(A, 2), 1);
    end
    
    if isempty(w)
        % 普通 LS
        W2 = speye(length(y));
    else
        % 加权 LS
        W2 = spdiags(w.^2, 0, length(w), length(w));
    end
    
    % (A^H W^2 A + λI)^{-1} (A^H W^2 y + λ g_prev)
    g = (A' * W2 * A + lambda * eye(size(A, 2))) \ (A' * W2 * y + lambda * g_prev);
end


function [chan_coef, delay_taps, doppler_taps] = generate_LEO_channel_SISO_integer(taps, l_max, k_max, rician_fac, fc, N, T)
%GENERATE_LEO_CHANNEL_SISO_INTEGER 生成整数多普勒的LEO信道
    f_ref = 1e9;
    f_dop_hz = 2e4 + 4e4 * rand(taps, 1);
    f_dop_hz = f_dop_hz * (fc / f_ref);
    doppler_taps = round(f_dop_hz * T);
    doppler_taps = max(min(doppler_taps, k_max), -k_max);
    delay_taps = randi([0, l_max-1], 1, taps);
    delay_taps = sort(delay_taps);
    
    % Rician 增益生成
    if taps > 1
        num_nlos_paths = taps - 1;
        g_nlos = sqrt(0.5) * (randn(num_nlos_paths, 1) + 1j * randn(num_nlos_paths, 1));
    else
        num_nlos_paths = 0;
        g_nlos = [];
    end
    g_los = exp(1j * 2 * pi * rand);
    los_power = rician_fac / (rician_fac + 1);
    nlos_power = 1 / (rician_fac + 1);
    g_los_scaled = g_los * sqrt(los_power);
    if taps > 1
        g_nlos_scaled = g_nlos * sqrt(nlos_power / num_nlos_paths);
        chan_coef = [g_los_scaled; g_nlos_scaled];
    else
        chan_coef = g_los_scaled;
    end
    chan_coef = chan_coef(randperm(taps));
end


function H_DAFT = GEN_H_DAFT(N, chan_coef, Delay_Index, Doppler_Index, c1)
%GEN_H_DAFT 基于解析公式构造 AFDM 等效信道矩阵（已验证）
%
% 公式来源:  Eq. 2-61 (交叉验证通过)
% 位移:  loc = k + 2*N*c1*l
% 索引: p = (q - loc)_N
% 相位: exp(j*2π/N * (N*c1*l² - q*l))
%
% 输入: 
%   N            - 子载波数
%   chan_coef    - 信道增益向量 (P x 1)
%   Delay_Index  - 延迟索引向量 (P x 1)
%   Doppler_Index- 多普勒索引向量 (P x 1)
%   c1           - AFDM chirp 参数
%
% 输出: 
%   H_DAFT       - N x N 等效信道矩阵（稀疏）

    P = length(chan_coef);
    total_nnz = N * P;
    rows = zeros(total_nnz, 1);
    cols = zeros(total_nnz, 1);
    vals = zeros(total_nnz, 1);
    
    idx_counter = 0;
    q_vec = (0:N-1).';  % 发射索引 (0-based)
    
    % c2 = 0 for standard AFDM (Bemani)
    c2 = 0;
    
    for i = 1:P
        h_i = chan_coef(i);
        l_i = Delay_Index(i);
        k_i = Doppler_Index(i);
        
        % 1. 计算位移量 loc = k + 2*N*c1*l (验证通过的公式)
        loc_val = k_i + 2 * N * c1 * l_i;
        
        % 2. 计算接收索引 p = (q - loc)_N (验证通过的公式)
        p_vec = mod(round(q_vec - loc_val), N);
        
        % 3. 计算相位 (Eq. 2-61)
        % term1: N*c1*l^2
        term1 = N * c1 * (l_i^2);
        
        % term2: -q*l
        term2 = -q_vec * l_i;
        
        % term3: N*c2*(q^2 - p^2)，当 c2=0 时此项为 0
        term3 = N * c2 * (q_vec.^2 - p_vec.^2);
        
        total_phase = (2 * pi / N) * (term1 + term2 + term3);
        
        % 4.  计算矩阵元素值
        H_vals = h_i * exp(1j * total_phase);
        
        % 5. 填入稀疏矩阵三元组 (转为 1-based 索引)
        current_indices = (1:N) + idx_counter;
        rows(current_indices) = p_vec + 1;
        cols(current_indices) = q_vec + 1;
        vals(current_indices) = H_vals;
        
        idx_counter = idx_counter + N;
    end
    
    % 构造稀疏矩阵（自动处理多径叠加）
    H_DAFT = sparse(rows, cols, vals, N, N);
end


function Phi = construct_afdm_sensing_matrix(N, x_pilot, c1, Q, max_delay, max_doppler, delay_res, doppler_res)
%CONSTRUCT_AFDM_SENSING_MATRIX 构建 OMP 感知字典（与 GEN_H_DAFT 一致）

    Phi = zeros(N, Q);
    q_vec = (0:N-1).';
    c2 = 0;
    
    col_idx = 1;
    for l = 0 : delay_res :  max_delay
        for k = -max_doppler : doppler_res : max_doppler
            
            % 1. 位移量 loc = k + 2*N*c1*l
            loc_val = k + 2 * N * c1 * l;
            
            % 2.  接收索引 p = (q - loc)_N
            p_vec = mod(round(q_vec - loc_val), N);
            
            % 3. 相位计算
            term1 = N * c1 * (l^2);
            term2 = -q_vec * l;
            term3 = N * c2 * (q_vec.^2 - p_vec.^2);
            total_phase = (2 * pi / N) * (term1 + term2 + term3);
            
            H_vals = exp(1j * total_phase);
            
            % 4. 构造该列:  y[p] = H[p,q] * x[q]
            y_col = zeros(N, 1);
            for qi = 1:N
                p_idx = p_vec(qi) + 1;
                y_col(p_idx) = y_col(p_idx) + H_vals(qi) * x_pilot(qi);
            end
            
            Phi(:, col_idx) = y_col;
            col_idx = col_idx + 1;
        end
    end
end

function [delays, dopplers, gains] = extract_delay_doppler_from_h(h, P, max_delay_index, max_doppler_index, delay_res, doppler_res)
%EXTRACT_DELAY_DOPPLER_FROM_H 从稀疏向量 h 中提取前 P 个最强的路径参数
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

function [h_i, Omega] = OMP(y,P,S)      
 N=size(y,1);
 K= size(P,2);

 err= 1e-3;  
h_i = zeros(K, 1);  % Initialize the recovery signal
y_i = y - P * h_i;    % residual error

it=0;
stop = 0;
P_s = [];
pos_array=[];
while ~stop                     
           for ntl=1:1:K
                product(ntl)=abs(P(:,ntl)'*y_i);      %  Step 1): calculate the correlation between the (1+(l-1)*Nt)-th  to (l*Nt)-th  columns and the residual signal 
           end
            
             y_i_before=y_i;    
            [val,pos]=max(product);                       %  Step 2): find the value and position of the most matching columns           
            P_s=[P_s,P(:,pos)];  pos_array= [pos_array,pos];  %  Step 3): update the argment matrix and record the position,
            P(:,pos)=zeros(N,1);                        %           remove the column just selected
            h_s=(P_s'*P_s)^(-1)*P_s'*y; 
%             h_s = P_s\y;                       %  Step 4): solve the LS problem to obatain a new signal estimate
            y_i = y - P_s*h_s;                          %  Step 5): Calculate the new residual
                                              
           it = it + 1;                                  %Iteration counter              
                                                     
    %Check Halting Condition
    if (it >= S  )  ||  norm(y_i) <=err*norm(y) 
      stop = 1;
    end
%     ||  norm(y_i) <=err*norm(y) 
%     ||norm( y_i) >= norm( y_i_before)
end
  h_i(pos_array) = (P_s'*P_s)^(-1)*P_s'*y;    %  Step 7): get the recovered signal
 %End CoSaMP iteration
%  used_iter = it;
  Omega=pos_array;                    
end



% =========================================================================
% ============ 3GPP TR 38.811 NTN-TDL Channel (Integer / Fractional) =======
% =========================================================================
function [chan_coef, delay_taps, Doppler_taps] = generate_NTN_TDL_channel_SISO( ...
    taps_phy, l_max, k_max, fc, delta_f, N_data, ...
    INTEGER_DOPPLER_FLAG, profile_name, use_dominant_2taps, K_LEAK, ...
    alpha_model_deg, v_sat, ue_speed, local_doppler_spread_hz, R_earth, h_sat)
%GENERATE_NTN_TDL_CHANNEL_SISO 生成 3GPP TR 38.811 NTN-TDL 信道(支持整数/分数多普勒)
%
% 输出 (chan_coef, delay_taps, Doppler_taps) 可直接送入 GEN_H_DAFT()
% - INTEGER_DOPPLER_FLAG=true  : 输出整数 Doppler_Index (与现有代码完全兼容)
% - INTEGER_DOPPLER_FLAG=false : 将每条物理 tap 用 Dirichlet 核分解为 (2*K_LEAK+1) 条“整数多普勒tap”，
%                               从而在不改 GEN_H_DAFT 结构的前提下模拟分数多普勒导致的泄漏(Cluster-sparse)

    % ---- 1) 读取 NTN-TDL 归一化延迟/功率/衰落类型 ----
    prof = get_NTN_TDL_profile(profile_name);
    tau_norm = prof.tau_norm(:);
    p_db = prof.p_db(:);
    fad_type = prof.fading_type;
    K_db = prof.K_db;   % 仅对 LOS 模型(C/D)有效(第一tap)

    % ---- 2) 为了尽量保持你原论文的 P=taps_phy (常用=2) 不变，可只取最强两条 tap ----
    if use_dominant_2taps
        [tau_norm, p_db, fad_type, K_db] = select_dominant_2taps(tau_norm, p_db, fad_type, K_db);
    end
    P_phy = length(p_db);
    if nargin >= 1 && ~isempty(taps_phy)
        % 若 taps_phy 与 profile tap 数不一致，优先以 profile 选出的为准
        taps_phy = P_phy;
    end

    % ---- 3) 延迟量纲化: TR 38.811 说明 normalized delay 可按 TR 38.901 方法缩放到目标 RMS DS ----
    % 这里为了“尽量不推翻你现有参数(l_max)”，采用: 让最大延迟映射到 max_delay = l_max-1 个采样
    Ts = 1/(N_data * delta_f);
    max_delay_samp = l_max - 1;
    if max(tau_norm) > 0
        DS_scale_sec = (max_delay_samp * Ts) / max(tau_norm);
    else
        DS_scale_sec = 0;
    end
    tau_sec = tau_norm * DS_scale_sec;
    delay_taps_phy = round(tau_sec / Ts);
    delay_taps_phy = min(max(delay_taps_phy, 0), max_delay_samp);

    % ---- 4) tap 平均功率归一化 ----
    p_lin = 10.^(p_db/10);
    p_lin = p_lin / sum(p_lin);

    % ---- 5) 生成 tap 复增益 ----
    chan_coef_phy = zeros(P_phy,1);
    for ii = 1:P_phy
        if strcmpi(fad_type{ii}, 'Rician')
            K_lin = 10^(K_db/10);
            los = sqrt(p_lin(ii) * K_lin/(K_lin+1)) * exp(1j*2*pi*rand);
            nlos = sqrt(p_lin(ii) * 1/(K_lin+1)) * (randn+1j*randn)/sqrt(2);
            chan_coef_phy(ii) = los + nlos;
        else
            chan_coef_phy(ii) = sqrt(p_lin(ii)) * (randn+1j*randn)/sqrt(2);
        end
    end

    % ---- 6) 3GPP/LEO Doppler: 卫星运动引起的额外多普勒(对所有 tap 共同) + (可选)局部散射扩展 ----
    c = 3e8;
    v_rel = v_sat * (R_earth/(R_earth + h_sat)) * cosd(alpha_model_deg);
    f_d_sat = (v_rel/c) * fc;   % Hz
    % UE 自身运动造成的最大多普勒(可选)
    f_d_ue = (ue_speed/c) * fc;

    % 基础多普勒(符号可正可负，这里每帧随机符号以覆盖两种情况)
    sign_fd = 2*(rand>0.5)-1;
    f_d_base = sign_fd * (f_d_sat + f_d_ue);

    % 每个 tap 的 doppler (加一点点扩展，防止所有tap doppler 完全相同导致过于理想)
    f_d_taps = f_d_base + local_doppler_spread_hz*(2*rand(P_phy,1)-1);
    k_real = f_d_taps / delta_f;   % 真实(可分数) Doppler index

    if INTEGER_DOPPLER_FLAG
        % ================== 整数多普勒版本 ==================
        Doppler_taps = round(k_real);
        Doppler_taps = min(max(Doppler_taps, -k_max), k_max);
        delay_taps  = delay_taps_phy;
        chan_coef   = chan_coef_phy;
    else
        % ================== 分数多普勒版本(Cluster-sparse) ==================
        % 思路: k_real = k_int + kappa, 其中 kappa ∈ (-0.5,0.5]
        % 将分数移位算子用 Dirichlet 系数分解为若干个整数移位的线性组合(只保留 ±K_LEAK 邻域)
        chan_coef = []; delay_taps = []; Doppler_taps = [];
        for ii = 1:P_phy
            k_int = round(k_real(ii));
            k_int = min(max(k_int, -k_max), k_max);
            kappa = k_real(ii) - k_int;
            m_vec = (-K_LEAK:K_LEAK).';
            a_vec = zeros(length(m_vec),1);
            for mm = 1:length(m_vec)
                a_vec(mm) = dirichlet_alpha(m_vec(mm), kappa, N_data);
            end
            % 能量归一化(避免不同 kappa 导致截断后总功率变化，保证对比公平)
            a_vec = a_vec / sqrt(sum(abs(a_vec).^2) + eps);

            for mm = 1:length(m_vec)
                k_eff = k_int + m_vec(mm);
                if k_eff < -k_max || k_eff > k_max
                    continue;  % 超出搜索窗就丢弃(也可选择 wrap)
                end
                Doppler_taps = [Doppler_taps; k_eff];
                delay_taps   = [delay_taps; delay_taps_phy(ii)];
                chan_coef    = [chan_coef; chan_coef_phy(ii) * a_vec(mm)];
            end
        end
    end
end

function prof = get_NTN_TDL_profile(profile_name)
%GET_NTN_TDL_PROFILE 3GPP TR 38.811 Table 6.9.2-1/2 的 NTN-TDL 参数(归一化延迟/功率)
% 说明:
% - NTN-TDL-A/B: NLOS, Rayleigh
% - NTN-TDL-C/D: LOS, Rician (K factor 分别为 10.224 dB / 11.707 dB)

    switch upper(strrep(profile_name,' ',''))
        case 'NTN-TDL-A'
            prof.tau_norm = [0; 1.0811; 2.8416];
            prof.p_db = [0; -4.675; -6.482];
            prof.fading_type = {'Rayleigh','Rayleigh','Rayleigh'};
            prof.K_db = 0;
        case 'NTN-TDL-B'
            prof.tau_norm = [0; 0.7249; 1.0771; 1.9092];
            prof.p_db = [0; -4.926; -6.902; -8.717];
            prof.fading_type = {'Rayleigh','Rayleigh','Rayleigh','Rayleigh'};
            prof.K_db = 0;
        case 'NTN-TDL-C'
            % 注意: 38.811 表中 delay=0 处同时给了 LOS/Rayleigh 两个分量
            % 为了通用，这里原样给出三个分量(后续可选择 dominant-2taps 合并)
            prof.tau_norm = [0; 0; 14.8124];
            prof.p_db = [-0.394; -10.618; -23.373];
            prof.fading_type = {'Rician','Rayleigh','Rayleigh'};
            prof.K_db = 10.224;
        case 'NTN-TDL-D'
            prof.tau_norm = [0; 0; 0.5596; 7.3340];
            prof.p_db = [0.016; -12.968; -9.887; -16.771];
            prof.fading_type = {'Rician','Rayleigh','Rayleigh','Rayleigh'};
            prof.K_db = 11.707;
        otherwise
            error('Unknown profile_name. Use NTN-TDL-A/B/C/D');
    end
end

function [tau2, p2, fad2, K_db2] = select_dominant_2taps(tau_norm, p_db, fad_type, K_db)
%SELECT_DOMINANT_2TAPS 保持物理 tap 数尽量为2(贴合你原论文 P=2 的设定)
% 规则:
% 1) 若存在 delay=0 的多个分量(如 TDL-C/D)，先把它们合并成一个等效 Rician tap(功率求和)
% 2) 再从剩余(非0 delay)中选择功率最大的一个 tap 作为第二tap

    % ---- 合并 delay=0 的分量 ----
    idx0 = find(abs(tau_norm) < 1e-12);
    p0_lin = sum(10.^(p_db(idx0)/10));
    p0_db  = 10*log10(p0_lin + eps);

    % 第一tap: delay=0
    tau_first = 0;
    % 如果 delay=0 里有 Rician 分量，则第一tap 设为 Rician; 否则 Rayleigh
    if any(strcmpi(fad_type(idx0), 'Rician'))
        fad_first = {'Rician'};
        K_db2 = K_db;
    else
        fad_first = {'Rayleigh'};
        K_db2 = 0;
    end

    % ---- 选择第二tap: 从非0 delay 中选最大功率 ----
    idx_rem = setdiff(1:length(tau_norm), idx0);
    if isempty(idx_rem)
        % 退化情况：只有一个tap
        tau2 = tau_first; p2 = p0_db; fad2 = fad_first;
        return;
    end
    [~, idx_best_rel] = max(p_db(idx_rem));
    idx_best = idx_rem(idx_best_rel);

    tau2 = [tau_first; tau_norm(idx_best)];
    p2   = [p0_db; p_db(idx_best)];
    fad2 = [fad_first; {fad_type{idx_best}}];
end

function a = dirichlet_alpha(m, kappa, N)
%DIRICHLET_ALPHA Dirichlet 核系数: a_m(kappa) = (1/N) * sum_{n=0}^{N-1} exp(j*2*pi*(m+kappa)*n/N)
    x = m + kappa;
    if abs(x) < 1e-12
        a = 1 + 0j;
        return;
    end
    denom = sin(pi * x / N);
    if abs(denom) < 1e-12
        % x 逼近 N 的整数倍时，用极限避免数值问题
        a = exp(1j*pi*(N-1)*x/N);
    else
        a = exp(1j*pi*(N-1)*x/N) * sin(pi*x) / (N * denom);
    end
end

function [delays_ex, dopplers_ex, gains_ex] = expand_support_doppler(delays, dopplers, gains, k_max, K_LEAK)
%EXPAND_SUPPORT_DOPPLER 将 OMP 得到的 (l,k) 支持集在 Doppler 维做 ±K_LEAK 扩展，用于近似分数多普勒泄漏
    delays_ex = []; dopplers_ex = []; gains_ex = [];
    for ii = 1:length(delays)
        for m = -K_LEAK:K_LEAK
            k_new = dopplers(ii) + m;
            if k_new < -k_max || k_new > k_max
                continue;
            end
            delays_ex   = [delays_ex; delays(ii)];
            dopplers_ex = [dopplers_ex; k_new];
            if m == 0
                gains_ex = [gains_ex; gains(ii)];
            else
                gains_ex = [gains_ex; 0];
            end
        end
    end
    % 合并重复的 (l,k)
    pairs = [delays_ex(:), dopplers_ex(:)];
    [pairs_u, ~, ic] = unique(pairs, 'rows');
    gains_u = accumarray(ic, gains_ex(:));
    delays_ex = pairs_u(:,1);
    dopplers_ex = pairs_u(:,2);
    gains_ex = gains_u;
end