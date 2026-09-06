#!/usr/bin/env bash
# Install tracked git hooks into .git/hooks/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_SRC="$ROOT/ops/git-hooks"
HOOKS_DST="$(git -C "$ROOT" rev-parse --git-dir)/hooks"

if [[ ! -d "$HOOKS_SRC" ]]; then
  echo "错误: 未找到 $HOOKS_SRC" >&2
  exit 1
fi

mkdir -p "$HOOKS_DST"

installed=0
for hook in "$HOOKS_SRC"/*; do
  [[ -f "$hook" ]] || continue
  name="$(basename "$hook")"
  target="$HOOKS_DST/$name"
  cp "$hook" "$target"
  chmod +x "$target"
  echo ">> 已安装 git hook: $name"
  installed=$((installed + 1))
done

if [[ "$installed" -eq 0 ]]; then
  echo "警告: ops/git-hooks/ 下没有可安装的 hook" >&2
  exit 1
fi

echo "git hooks 安装完成（$installed 个）。"
