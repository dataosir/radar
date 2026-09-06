#!/usr/bin/env bash
# Auto-commit after agent session ends. Never pushes — user decides when to push.
# Commit messages are generated from staged diff (see generate_commit_message.py).
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/auto_commit.log"
MSG_FILE="$(mktemp "${TMPDIR:-/tmp}/chat-radar-commit-msg.XXXXXX")"
trap 'rm -f "$MSG_FILE"' EXIT

ts() { date '+%Y-%m-%d %H:%M:%S'; }

log() { echo "[$(ts)] $*" >> "$LOG_FILE"; }

# Consume stdin (required by Cursor hook protocol)
cat > /dev/null

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  log "skip: not a git repository"
  exit 0
fi

if [[ -z "$(git status --porcelain)" ]]; then
  log "skip: working tree clean"
  exit 0
fi

# Stage tracked changes and new files; .gitignore still applies
git add -A

if [[ -z "$(git diff --cached --name-only)" ]]; then
  log "skip: nothing staged after git add"
  exit 0
fi

GENERATOR="$ROOT/.cursor/hooks/generate_commit_message.py"
if [[ -x "$GENERATOR" ]] || [[ -f "$GENERATOR" ]]; then
  if python3 "$GENERATOR" > "$MSG_FILE" 2>>"$LOG_FILE"; then
    :
  else
    log "warn: generate_commit_message.py failed, using fallback"
    STAT="$(git diff --cached --shortstat)"
    {
      echo "auto: Agent 会话改动（$(date '+%Y-%m-%d %H:%M')）。"
      echo ""
      echo "$STAT"
    } > "$MSG_FILE"
  fi
else
  STAT="$(git diff --cached --shortstat)"
  {
    echo "auto: Agent 会话改动（$(date '+%Y-%m-%d %H:%M')）。"
    echo ""
    echo "$STAT"
  } > "$MSG_FILE"
fi

SUBJECT="$(head -1 "$MSG_FILE")"
if git commit -F "$MSG_FILE"; then
  SHA="$(git rev-parse --short HEAD)"
  log "committed ${SHA}: ${SUBJECT}"
else
  log "commit failed: ${SUBJECT}"
  exit 1
fi

exit 0
