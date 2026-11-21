# 编辑备注（不进正文 / Editor's notes）

> 给排版与生成 Word 用，正式版不包含本文件。正文见 `00_MATERIAL_DATABASE.md`。

## 章节与编号（5 章，对照董方莹范文）
1. Introduction｜2. Literature Review｜3. Methodology（系统模型 + 接收机 + 学习头 + 复杂度合并）｜4. Results｜5. Conclusion。

- **公式**（display 5 条）：(3-1) IDAFT、(3-2) 模型、(3-3) Dirichlet、(3-4) SP 帧、(3-5) 干扰方差。导频投影（原 3-5）已内联为文字；残差/DA-LS/MP-BP（原 3-7/3-8/3-9）已进 Algorithm 1；训练损失（原 3-10）已文字化。
- **图**：Figure 1-1（系统总览，待画）、3-1（学习头集成框图）、4-1（BER+NMSE）、4-2（oracle headroom）；Algorithm 1（图片，紧凑版）。
- **小节合并**：原 §3.7 Complexity 已删，核心句（O(PN²) 类、头加 O(N²)）并入 §4.4 Complexity（结果章），全篇复杂度只留一处。方法章现为 3.1–3.6。
- **已删的图（可放回）**：Dirichlet 图 `assets/fig_dirichlet.png`（应你要求删）；support recall 图 `assets/fig_support_recall.png`（早先删）。
- **表**：仅 Table 4-1（复杂度）。字典表已删；仿真参数已行内化（§4.1）。

## 图源（assets/ 内已就位）
| 图号 | assets 文件 |
|---|---|
| Figure 1-1 | **待画** |
| Figure 3-1 | `assets/fig_dirichlet.png` |
| Algorithm 1 | `assets/fig_algorithm1.png`（+ .pdf/.tex 源） |
| Figure 4-1 | `assets/fig_ber_waterfall.png` |
| Figure 4-2 | `assets/fig_oracle_headroom.png` |

## 备用素材（本轮为控页数移出正文，需要可放回）
- **Figure（support recall）**：`assets/fig_support_recall.png` —— OMP-once 召回图，已移出正文（召回 ≈95% 数字仍在 §3.5/§4.3）。需要可作 Figure 4-2、原 oracle headroom 顺延 4-3。
- 注：学习头集成框图（`assets/fig_head_integration.png`）应你要求**已放回正文** = Figure 3-2。
- **Table（BER 瀑布）**：你已自删；数据全在 Figure 4-1。若要放回：SNR 10/15/20/25/30 → Serial 7.1/4.3/4.1/4.1/4.1×10⁻²，ClassicalJoint 4.8×10⁻²/1.9×10⁻²/5.0×10⁻⁴/1.0×10⁻⁴/1.8×10⁻⁵，Learned 4.5×10⁻²/1.7×10⁻²/3.1×10⁻⁴/6.0×10⁻⁵/1.1×10⁻⁵，Δ −2.2/−7.4/−37.7/−40.2/−37.6%。
- **Table（oracle headroom）**：你已自删；数据在 Figure 4-2。若要放回：15/20/25 dB → Classical 1.98×10⁻²/3.89×10⁻⁴/3.46×10⁻⁴，oracle 1.21×10⁻²/0/0，Learned 1.51×10⁻²/7.39×10⁻⁵/5.58×10⁻⁶，Gap closed 61/81/98%。
- **外迭代收敛图/表**、**wall-clock 运行时表（含 RTX 4090）**：短版已省略（report 腔，且占页数）。

## 数字溯源（防幻觉，均对照 FYP）
- 来源：`paper/sections/Section3.tex`（结果四实验）、`Section5.tex`（结论）。
- 关键数：−37.7/−40.2/−37.6%（20/25/30 dB 配对 BER 降幅，p<10⁻⁶）；61/81/98%（oracle gap closed）；≈95% 召回、67–71% 帧有漏；−11.3 dB NMSE 冻结、≈5×10⁻² 串行平台；MAC 14.0/18.6/20.1/48.6 M、Dense ≈2.7 G（≈145×）；Jaccard >0.94。

## 取材来源
正文文字沿用 `paper/sections/*.tex`（FYP-full，最终态约 4/28，轻量润色到 5/7）。旧素材库见 `00_MATERIAL_DATABASE_v1_backup.md`。
