#!/usr/bin/env bash
# Import cards a cloud runner pushed to a branch, keeping local eric: marks (protocol: ../SKILL.md, "Where it runs").
# Usage: import_branch.sh <bare repo> <branch> <local funnel folder> [funnel path inside the repo, default: ideas]
set -euo pipefail
REPO=$1; BRANCH=$2; LOCAL=$3; INNER=${4:-ideas}
HERE=$(cd "$(dirname "$0")" && pwd)
git --git-dir="$REPO" fetch -q origin "refs/heads/$BRANCH:refs/heads/$BRANCH"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
git --git-dir="$REPO" archive "$BRANCH" "$INNER/cards" | tar -x -C "$TMP"
python3 "$HERE/funnel.py" import "$LOCAL" --src "$TMP/$INNER/cards"
