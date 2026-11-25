#!/usr/bin/env bash
# 一键看进度与合流：只导 worktree-g 的 g 卡 + 云端已推送分支，重生成看板，打印待终审队列（含 JSON verdicts 核查）与最新一轮卡片方向。
# 用法：./ideas/progress.sh
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/repo.git
WT_BASE=/Users/guoyikun/Downloads/share/claode_birain
SK="$HOME/projects/personal-ai-workflow/skills/idea-funnel/scripts"

TMP_IMP=$(mktemp -d)
trap 'rm -rf "$TMP_IMP"' EXIT
for r in g h k m; do
  WT_R="$WT_BASE/afdm-funnel-$r/00_Inbox/AFDM-channel-estimation"
  if [ -d "$WT_R/ideas/cards" ] && ls "$WT_R"/ideas/cards/I-*-${r}[0-9]*.md >/dev/null 2>&1; then
    mkdir -p "$TMP_IMP/$r"
    cp "$WT_R"/ideas/cards/I-*-${r}[0-9]*.md "$TMP_IMP/$r"/
    echo "== worktree-$r (runner $r)"
    python3 "$SK/funnel.py" import ideas --src "$TMP_IMP/$r" | grep -v '^BOARD.md' || true
    if [ -f "$WT_R/ideas/runs-$r.md" ]; then
      echo "   $r 最近一行运行记录：$(tail -n 1 "$WT_R/ideas/runs-$r.md" | cut -c1-240)"
    fi
  fi
done

if [ -d "$REPO" ]; then
  for b in $(git --git-dir="$REPO" ls-remote --heads origin 'funnel/*' 2>/dev/null | awk '{print $2}' | sed 's#^refs/heads/##'); do
    case "$b" in
      funnel/20261121-c|funnel/20261122-c) continue ;;
    esac
    echo "== $b"
    "$SK/import_branch.sh" "$REPO" "$b" ideas | grep -v '^BOARD.md' || true
  done
fi

python3 "$SK/funnel.py" board ideas >/dev/null
sed -n '3p' ideas/BOARD.md
grep -E '^## ' ideas/BOARD.md

python3 - <<'PY'
import glob, json, re
from pathlib import Path

cards = sorted(Path("ideas/cards").glob("I-*.md"))
cmr, active_new = [], []
latest_stamp = max((p.stem.split("-")[1] for p in cards), default="")

for p in cards:
    txt = p.read_text(encoding="utf-8")
    f = {k: (re.search(rf"^{k}:\s*(.*)$", txt, re.M).group(1).strip() if re.search(rf"^{k}:", txt, re.M) else "")
         for k in ("id", "layer", "status", "track", "generator", "next_cost", "title")}
    if f["status"] == "active" and "cross-model review" in f["next_cost"]:
        jpaths = re.findall(r"(?:ideas/)?l2/[A-Za-z0-9_./-]*summary[A-Za-z0-9_./-]*\.json", txt.split("## 筛选记录", 1)[-1])
        verdict_str = "no-json"
        for rel in reversed(jpaths):
            sub = rel if rel.startswith("ideas/") else f"ideas/{rel}"
            r_tag = re.search(r"-([ghkm])\d+$", f["id"])
            cands = [Path(sub)]
            if r_tag:
                cands.append(Path(f"/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-{r_tag.group(1)}/00_Inbox/AFDM-channel-estimation") / sub)
            hit = next((c for c in cands if c.is_file()), None)
            if hit is not None:
                v = (json.loads(hit.read_text(encoding="utf-8")).get("verdicts") or {}).get("PASS_PRIMARY")
                verdict_str = f"{hit.name}:PASS_PRIMARY={v}"
                break
        cmr.append(f"  - {f['id']} [{f['track']}|{f['generator']}] ({verdict_str}): {f['title']}")
    if p.stem.startswith(f"I-{latest_stamp}-") and f["status"] == "active" and f["layer"] in ("L1", "L2", "L3"):
        active_new.append(f"  - {f['id']} [{f['layer']}|{f['track']}]: {f['title']}")

print(f"待第 8 步终审队列（{len(cmr)}）：")
print("\n".join(cmr) if cmr else "  （空）")
print(f"最新日期 ({latest_stamp}) 活跃卡方向预览（{len(active_new)}）：")
print("\n".join(active_new) if active_new else "  （暂无活跃新卡）")
PY
echo "本地 l 最近一行运行记录：$(tail -n 1 ideas/runs.md | cut -c1-240)"
