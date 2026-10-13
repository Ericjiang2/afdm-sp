"""Summarize audited A-01 geometry; regenerate public singular spectra only."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

from afdm_sp_joint_unrolled.bandlimited_basis import (
    BasisGeometry, basis_from_public_band, normalized_geometry,
)


def main():
    here = Path(__file__).resolve().parent
    root = Path("afdm_sp_joint_unrolled/outputs_unified_exploration_20260914")
    path = root/"runs/a01-v2/a01/summary.json"
    summary = json.loads(path.read_text())
    audit = json.loads((root/"runs/a01-v2/audit.json").read_text())
    assert audit["status"] == "PASS"
    assert audit["summary_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert summary["status"] == "COMPLETE" and summary["calls"] == {"A": 17}
    manifest = json.loads((root/"source-a01-v1/source-manifest.json").read_text())
    basis_path = Path("afdm_sp_joint_unrolled/bandlimited_basis.py")
    assert manifest[basis_path.name] == hashlib.sha256(basis_path.read_bytes()).hexdigest()
    spectra = []
    time = np.arange(256)
    pilots = {"p0": np.sqrt(.5)*np.exp(-1j*np.pi*7*time*time/256),
              "pZ": np.sqrt(128)*np.eye(1, 256, dtype=complex)[0]}
    for row in summary["static_rows"]:
        basis = basis_from_public_band(row["family"], 256, row["q"], 4000., 16.)
        geom = BasisGeometry(basis, c1=5/512, c2=(np.sqrt(2)-1)/(2*256**2),
                             delay_cap=24, prefix_length=32)
        spectra.append(dict(family=row["family"], q=row["q"], pilot=row["pilot"],
            orthogonality_error=float(np.max(abs(basis.conj().T@basis-np.eye(row["q"])))),
            full=normalized_geometry(geom.sensing(pilots[row["pilot"]])),
            fixed=normalized_geometry(geom.sensing(pilots[row["pilot"]], np.arange(0,25,3)))))
    grouped = defaultdict(list)
    for row in summary["legal_rows"]:
        grouped[row["family"],row["q"],row["pilot"]].append(row)
    aggregates = []
    for (family,q,pilot), rows in grouped.items():
        legal = [r["legal_geometry"] for r in rows]
        oracle = [r["oracle_geometry"] for r in rows]
        aggregates.append(dict(family=family,q=q,pilot=pilot,n=len(rows),
            legal_qualified=sum(g["qualified"] for g in legal),
            legal_columns=sorted(set(g["columns"] for g in legal)),
            legal_condition_max=max(g["condition"] for g in legal),
            rejected=sum(len(r["rejected_groups"]) for r in rows),
            oracle_qualified=sum(g["qualified"] for g in oracle),
            oracle_columns=sorted(set(g["columns"] for g in oracle)),
            oracle_condition_max=max((g["condition"] for g in oracle if g["condition"] is not None),default=None)))
    report = dict(status="A01_GEOMETRY_PASS",receiver_calls=0,
        production_summary_sha256=audit["summary_sha256"],
        source_manifest_sha256=summary["source_sha256"],
        contract_sha256=summary["contract_sha256"],
        direct_projection_rows=summary["static_rows"],spectra=spectra,aggregates=aggregates,
        records=summary["records"],review_independence="weak",
        scope="old 16-channel geometry, with local deterministic public singular-spectrum regeneration",
        exact_fourier_q7_pZ_max_rank=127,
        rank_note="Reported LAPACK epsilon ranks can exceed exact rank due to chirp/FFT roundoff; the frozen condition <=1e8 gate rejects these full dictionaries. No tolerance was loosened.")
    (here/"a01-results-v1.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    lines = ["# A-01 几何核验", "", "裁决：九配置均进入 A-02；仅证明当前几何可计算，不证明 BER 或成本。", "",
        "服务器独立进程回读通过：17A、576 合法选择、0F/0D。16 个旧信道（含旧工程数据），非新科学样本。主会话自审，独立性 weak。", "",
        "## 同维表示投影", "", "| 基 | q | 随机角度均值 | 平坦谱均值 | 公开频带网格最大值 |", "|---|---:|---:|---:|---:|"]
    for r in summary["static_rows"]:
        if r["pilot"]=="p0":
            lines.append(f"| {r['family']} | {r['q']} | {r['angle_error_direct']:.8g} | {r['flat_spectrum_error']:.8g} | {r['grid_max_error']:.8g} |")
    lines += ["", "4096 点角度直接投影与协方差 trace 对账；2048/4096 求积收敛在 producer 中验证。平坦谱设计和随机角度评价明确分开。DPSS 的表示优势尚不代表估计优势。", "",
        "## 公共导频与合法支撑", "", "| 基/q/pilot | 全字典数值秩/列数 | 全字典条件数 | 固定时延条件数 | 合法最大条件数 | 排除组次数 |", "|---|---:|---:|---:|---:|---:|"]
    for r,a in zip(summary["static_rows"],aggregates):
        assert (r["family"],r["q"],r["pilot"])==(a["family"],a["q"],a["pilot"])
        g=r["full_dictionary"]; cond="秩不足" if g["condition"] is None else f"{g['condition']:.5g}"
        lines.append(f"| {r['family']}/{r['q']}/{r['pilot']} | {g['rank']}/{g['columns']} | {cond} | {r['public_fixed_delays']['condition']:.5g} | {a['legal_condition_max']:.5g} | {a['rejected']} |")
    lines += ["", "完整 pZ/q7 字典均不通过冻结门；活动字典全部通过。Fourier/q7 的精确碰撞上界为秩127，浮点默认 epsilon 数值秩为150：微小奇异值来自 chirp/FFT 舍入，不视为额外可辨识方向。归一化条件数门仍为1e8。完整奇异谱与列范数见 JSON。", "",
        "## Oracle 时延（仅外部诊断）", "", "| 基/q/pilot | 合格次数/32 | 列数集合 | 最大有限条件数 |", "|---|---:|---|---:|"]
    for a in aggregates:
        cond="无" if a['oracle_condition_max'] is None else f"{a['oracle_condition_max']:.5g}"
        lines.append(f"| {a['family']}/{a['q']}/{a['pilot']} | {a['oracle_qualified']}/{a['n']} | {a['oracle_columns']} | {cond} |")
    lines += ["", "Oracle 不能进入合法组选择；不同表的支撑维数不等。合法配置均使用公开预算 floor(60/q)，记录60次候选排除。", "",
        "## 证据与失败", "", "- 原始数组留远端；各 record 路径和 SHA256 在 a01-results-v1.json，record 内继续绑定 NPZ 的 dtype/shape/内容哈希。", "- 独立进程审计 summary SHA256：`"+audit["summary_sha256"]+"`。", "- 本地与服务器16项数学/边界测试通过；服务器 unit-v1 缺 pytest、producer-v1 导入失败均保留日志。两次失败无生产 A/F 数据。", "- producer-v2 实际18.009秒，audit-v2实际16.606秒；不是完整接收成本。", "- 验收覆盖：归一化、q3/5/7投影、CPP负时间相位、独立传播闭合、矩阵/作用一致、组内旋转不变性、秩耗尽、公开/合法/oracle分表。", "- 后续按冻结合同运行 A-02 的带噪估计；禁止凭本表选择 BER 获胜臂。", ""]
    (here/"a01-results-v1.md").write_text("\n".join(lines))
    print(json.dumps(dict(status=report["status"],legal=576,spectra=len(spectra),receiver_calls=0)))


if __name__ == "__main__":
    main()
