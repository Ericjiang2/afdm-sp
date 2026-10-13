%% acousticChannelEnhancedBasic.m
% Enhanced acoustic channel generator for UWA (complex taps + path attributes)
% This version uses only basic MATLAB functions (no toolboxes like Statistics Toolbox)
%
% Usage:
% [h, delay_bar, gain_tap, delay_idx_bar, path_var, doppler_a, Q, M] =
%     acousticChannelEnhancedBasic(setup, gain, delay, doppler)
%
% See conversation for design notes.

function [h, delay_bar, gain_tap, delay_idx_bar, path_var, doppler_a, Q, M] = acousticChannelEnhancedBasic(setup, gain, delay, doppler)
% Input checks
if ~isfield(setup,'Ts'); error('setup.Ts 必须提供'); end
if ~isfield(setup,'paths'); error('setup.paths 必须提供'); end
if ~isfield(setup,'delayspread'); error('setup.delayspread 必须提供'); end

P = setup.paths;

% 1) 延迟分布（指数分布）- 使用逆变换采样法
% 指数分布 CDF: F(x) = 1 - exp(-x/mu)
% 逆变换: x = -mu * ln(1 - U) = -mu * ln(U)  (由于 U 和 1-U 同分布)
u = rand(P, 1);
u(u == 0) = eps;  % 避免 log(0)
Dtau = -delay.mean * log(u);                  % 连续延迟增量（秒）
Dtau_index = max(1, ceil(Dtau / setup.Ts));   % 离散索引
delay_index = cumsum(Dtau_index);              % 每条路径的样本索引
delay_vec = (delay_index - 1) * setup.Ts;      % 每条路径的延迟（秒）

% 2) 增益功率模型（指数衰减）
alpha = log(10^(gain.attenuation/10)) / setup.delayspread;
path_var = exp(-alpha * delay_vec);  % 每径功率（方差）

% 生成瑞利幅度（实正）- 使用基础方法
% 瑞利分布: X = sigma * sqrt(-2*ln(U))，其中 U ~ Uniform(0,1)
% 这是从 Rayleigh 分布的逆变换采样法推导得到
% Rayleigh CDF: F(x) = 1 - exp(-x^2/(2*sigma^2))
% 逆变换: x = sigma * sqrt(-2*ln(1-U)) = sigma * sqrt(-2*ln(U))
sigma = sqrt(path_var * 2/(4 - pi));
u_rayl = rand(P, 1);
u_rayl(u_rayl == 0) = eps;  % 避免 log(0)
amp = sigma .* sqrt(-2 * log(u_rayl));  % 瑞利采样

% 可选归一化（默认 true）
normalize_flag = true;
if isfield(gain,'normalize') && isequal(gain.normalize,false)
    normalize_flag = false;
end
if normalize_flag
    if norm(amp) > 0
        amp = amp / norm(amp);
        % 为保持 path_var 的物理意义，path_var 仍保存原始值供后续参考
    end
end

% 随机相位 -> 复值 tap
phases = 2*pi*rand(size(amp));
gain_tap = amp .* exp(1j * phases);   % 复值 tap（列向量）

% 3) 多普勒缩放（缩放因子doppler_a = 运动速度/声速）
c = 1500; % m/s

switch lower(doppler.type)
    case 'none'             % none：无多普勒，比例因子 = 1
        doppler_a = zeros(P,1);
        Q = 1; M = 1;
    case 'uniform'          % uniform：所有路径的多普勒缩放因子（DSF）相同
        a_val = doppler.velocity / c;
        doppler_a = a_val * ones(P,1);
        a_max = max(doppler_a);
        [Q, M] = rat(1 + a_max);
    case 'non-uniform'      % non-uniform：每条路径的 DSF 不同，取最大值 a_max
        a_vec = doppler.velocity(:); % 应为长度 P
        if numel(a_vec) ~= P
            error('doppler.velocity 长度必须等于 setup.paths');
        end
        doppler_a = a_vec / c;
        a_max = max(doppler_a);
        [Q, M] = rat(1 + a_max);
    otherwise
        error('无效的 doppler.type');
end

% 4) 修正后的延迟索引（考虑缩放因子doppler_a）
delay_idx_bar = max(1, ceil(delay_index ./ (1 + doppler_a)));
delay_bar = (delay_idx_bar - 1) * setup.Ts;

% 5) 生成时域脉冲响应 h（复值）
h_len = max(delay_idx_bar);
h = zeros(h_len, 1);
h(delay_idx_bar) = gain_tap;

end
