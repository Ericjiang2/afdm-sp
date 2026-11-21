# EP 资格门的精确校准反例

在 H=[1]、y=[0]、复噪声方差 0.2、QPSK ±0.5±0.5j 的单符号系统，四个符号与观测距离相同，因此精确后验均匀，均值 0、复方差 0.5、两位 LLR 都为 0。

当前实数 EP 每维 cavity precision 为 10，moment-matched variance 为 0.25，提出的 site precision 为 4−10=−6。当前稳定化规则保留旧 site。实际 20/40 次输出均与枚举精确后验相同；更新残差为 0，输出逐元素相同，但 rejected_sites=2。因此 `_ep.converged` 仍为 false。

这证明“最终零拒绝 site”不是精确边缘量或数值固定点的必要条件。它是当前预冻结资格门额外施加的限制。不能仅因出现拒绝 site，就推断该样本的输出错误或迭代还没有稳定。

外部原始研究区分 Gaussian-projected EP 中可为 improper 的消息与必须 proper 的 beliefs，并用 BPSK、零 cavity mean、小 cavity variance 举出负消息方差的例子：[Zhao et al., Expectations in Expectation Propagation, §VI–VII](https://arxiv.org/html/2512.08034v1)。这支持检查门的含义，不能证明当前 AFDM 大系统 EP 已达到精确后验或更优接收。

原四块资格结果仍然保留为未通过：另有 LLR/均值/译码变化，不能靠上述反例消除这些失败。未修改任何容差、配置、源检测器、原资格结论或开发样本。今后若校准资格定义，必须留原结果、明确新门依据和新验证范围；禁止将既有失败直接改写成已通过。

证据：`ep-negative-site-contract-v1.json`，实际单符号检测调用和独立有限枚举；不是完整接收、开发或确认试验。
