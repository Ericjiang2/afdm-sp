#!/usr/bin/env bash
# 一键看进度：把云端 runner 已推送的卡导入本地（本地放行过的、你写过批示的都不会被覆盖），重生成看板，打印概况。
# 用法：ideas/progress.sh     然后打开 ideas/BOARD.md（"等你看"一栏有白话、类比、去壳三句）。
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/repo.git
SK="$HOME/projects/personal-ai-workflow/skills/idea-funnel/scripts"
for b in $(git --git-dir="$REPO" ls-remote --heads origin 'funnel/*' | awk '{print $2}' | sed 's#^refs/heads/##'); do
  echo "== $b"; "$SK/import_branch.sh" "$REPO" "$b" ideas | grep -v '^BOARD.md'
  echo "   云端最近一行运行记录："; git --git-dir="$REPO" show "$b:ideas/runs.md" 2>/dev/null | tail -n 1 | cut -c1-300
done
python3 "$SK/funnel.py" board ideas >/dev/null
sed -n '3p' ideas/BOARD.md
grep -E '^## ' ideas/BOARD.md
echo "本地最近一行运行记录："; tail -n 1 ideas/runs.md | cut -c1-300
