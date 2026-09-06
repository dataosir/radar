#!/usr/bin/env bash
# CHAT-RADAR 首次安装：Python 检查 + venv + 配置模板 + 可选引导
#
# 用法:
#   ./install.sh           # 安装并进入 setup 引导
#   ./install.sh --quick   # 仅安装，不跑 setup
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
QUICK=0

for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    -h|--help)
      echo "用法: ./install.sh [--quick]"
      exit 0
      ;;
    *) echo "未知参数: $arg" >&2; exit 1 ;;
  esac
done

echo "=============================================="
echo " CHAT-RADAR 安装"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "错误: 未找到 $PYTHON，请安装 Python 3.10+" >&2
  exit 1
fi
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || { echo "错误: 需要 Python 3.10+" >&2; exit 1; }

echo ">> Python: $($PYTHON --version)"

bash "$ROOT/start.sh" selftest

if [[ ! -f "$ROOT/chat_radar_config.json" ]]; then
  cp "$ROOT/chat_radar_config.example.json" "$ROOT/chat_radar_config.json"
  echo ">> 已生成 chat_radar_config.json"
fi

mkdir -p "$ROOT/data/wechat_inbox" "$ROOT/data/wechat_exports" "$ROOT/reports" "$ROOT/logs"

echo ""
echo "安装完成。"
echo "  交互菜单: ./start.sh"
echo "  每日 digest: ./start.sh digest --since 24"
if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "  macOS 微信密钥: ./ops/extract_wechat_keys.sh"
  echo "  晨间调度: ./start.sh  → 菜单 12"
fi

if [[ "$QUICK" -eq 0 ]]; then
  echo ""
  echo -n "是否现在运行引导配置 setup？[Y/n]: "
  read -r confirm
  case "${confirm:-Y}" in
    y|Y|yes|是|"")
      bash "$ROOT/start.sh" setup
      ;;
    *)
      echo "可稍后运行: ./start.sh setup"
      ;;
  esac
fi
