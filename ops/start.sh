#!/usr/bin/env bash
# CHAT-RADAR 一键启动：环境初始化 + 运行 CLI 子命令
#
# 用法:
#   ./ops/start.sh              # 初始化环境并跑 selftest
#   ./ops/start.sh digest       # 初始化后执行 digest
#   ./ops/start.sh auth         # 初始化后执行 auth
#   ./ops/start.sh selftest     # 仅跑离线自测
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
PYTHON="${PYTHON:-python3}"
CONFIG="$ROOT/chat_radar_config.json"
CONFIG_EXAMPLE="$ROOT/chat_radar_config.example.json"

die() {
  echo "错误: $*" >&2
  exit 1
}

check_python() {
  if ! command -v "$PYTHON" >/dev/null 2>&1; then
    die "未找到 $PYTHON，请安装 Python 3.10+ 或设置 PYTHON 环境变量"
  fi
  local ver
  ver="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "需要 Python 3.10+，当前为 $ver"
}

setup_venv() {
  if [[ ! -d "$VENV" ]]; then
    echo ">> 创建虚拟环境: $VENV"
    "$PYTHON" -m venv "$VENV"
  fi
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python -m pip install -q --upgrade pip
  python -m pip install -q -e .
}

ensure_config() {
  if [[ ! -f "$CONFIG" ]]; then
    if [[ ! -f "$CONFIG_EXAMPLE" ]]; then
      die "缺少配置模板: $CONFIG_EXAMPLE"
    fi
    cp "$CONFIG_EXAMPLE" "$CONFIG"
    echo ">> 已生成 ${CONFIG}（请编辑 telegram.api_id / api_hash 与 channels）"
  fi
}

ensure_dirs() {
  mkdir -p "$ROOT/data" "$ROOT/reports" "$ROOT/logs"
}

run_cli() {
  local cmd="${1:-selftest}"
  shift || true
  python -m chat_radar "$cmd" "$@"
}

main() {
  check_python
  setup_venv
  ensure_config
  ensure_dirs

  if [[ $# -eq 0 ]]; then
    echo ">> 运行离线自测..."
    run_cli selftest
    echo ""
    echo "环境就绪。下一步:"
    echo "  1. 编辑 chat_radar_config.json（api_id / api_hash / channels）"
    echo "  2. ./ops/start.sh auth    # 首次 Telegram 登录"
    echo "  3. ./ops/start.sh digest  # 生成每日 digest"
    return 0
  fi

  run_cli "$@"
}

main "$@"
