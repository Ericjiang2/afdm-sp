#!/usr/bin/env bash
set -eu

readonly SOURCE_ROOT="${1:?usage: launch_cost_screen.sh FINAL_SOURCE_ROOT}"
readonly EVIDENCE="/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/cost_screen_20260921"
readonly SESSION="g_spafdm_cost_screen_20260921"
readonly PREFLIGHT="$EVIDENCE/preflight_cost_screen"

printf '%s\n' "$SOURCE_ROOT" | grep -Eq \
  '^/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/[A-Za-z0-9._-]+$' || {
  echo "source root must be a simple-name directory in the compliant /data experiments root" >&2
  exit 92
}

mkdir -p "$PREFLIGHT"
date -u +%Y-%m-%dT%H:%M:%SZ > "$PREFLIGHT/utc.txt"
free -b > "$PREFLIGHT/memory.txt"
df -B1 /data/guoyikun > "$PREFLIGHT/disk.txt"
tmux list-sessions -F '#S' > "$PREFLIGHT/tmux_sessions.txt" 2>/dev/null || true
pgrep -af '[r]un_local.py|[r]un_memory_arm.py|[t]est_[A-Za-z0-9_]*\.py' \
  > "$PREFLIGHT/numerical_processes.txt" || true
test ! -s "$PREFLIGHT/numerical_processes.txt" || exit 88
test ! -s "$PREFLIGHT/tmux_sessions.txt" || ! grep -q '^g_' "$PREFLIGHT/tmux_sessions.txt" || exit 89
test -x "$EVIDENCE/run_cost_screen.sh"
test -f "$SOURCE_ROOT/src/run_local.py"
test ! -e "$EVIDENCE/cost_screen_run"
test ! -e "$EVIDENCE/cost_screen_command"

printf '%s\n' "$SOURCE_ROOT" > "$PREFLIGHT/source_root.txt"
tmux new-session -d -s "$SESSION" "$EVIDENCE/run_cost_screen.sh \"$SOURCE_ROOT\""
tmux list-panes -t "$SESSION" -F 'pid=#{pane_pid} dead=#{pane_dead} command=#{pane_current_command}' \
  > "$PREFLIGHT/launched_pane.txt"
cat "$PREFLIGHT/launched_pane.txt"
