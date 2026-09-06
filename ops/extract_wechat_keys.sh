#!/usr/bin/env bash
# 一次性提取 macOS 微信 SQLCipher 密钥 → data/wechat_keys.json
# 依赖: wcdb-key-tool（/tmp/wcdb-key-tool）、Xcode CLT（lldb）、sudo
#
# 关键：必须先 kill 微信 → 重签名 → 再启动微信，否则 task_for_pid 会失败。
# 多账号：自动检测最近活跃账号；PBKDF2 失败时会遍历所有账号匹配。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

WCDB_TOOL="${WCDB_TOOL:-/tmp/wcdb-key-tool/wcdb_key_tool_macos.py}"
KEYS_OUT="$ROOT/data/wechat_keys.json"
LOG="$ROOT/data/wechat_key_extract.log"

mkdir -p "$ROOT/data"
exec > >(tee -a "$LOG") 2>&1

echo "=============================================="
echo " CHAT-RADAR · 微信密钥提取"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
echo "输出: $KEYS_OUT"
echo "日志: $LOG"
echo

if [[ ! -f "$WCDB_TOOL" ]]; then
  echo ">> 克隆 wcdb-key-tool ..."
  git clone --depth 1 https://github.com/TANGandXUE/wcdb-key-tool /tmp/wcdb-key-tool
fi

if ! command -v lldb >/dev/null 2>&1; then
  echo "错误: 未找到 lldb，请运行: xcode-select --install"
  exit 1
fi

# 自动检测最近活跃账号的 db_storage
DB_DIR="$("$PYTHON" -c "
from chat_radar.ingest.wechat_mac_paths import discover_mac_wechat, pick_active_account
d = discover_mac_wechat()
a = pick_active_account(d)
if a:
    print(a.db_storage)
else:
    print('')
")"
if [[ -z "$DB_DIR" ]]; then
  echo "错误: 未找到微信 db_storage 目录"
  exit 1
fi
echo "自动检测活跃账号 db_storage: $DB_DIR"
echo

# 若已有 passphrase，先尝试多账号派生（无需重新登录）
if [[ -f "$HOME/.wcdb-key-tool/wechat-passphrase.json" ]]; then
  echo ">> 检测到已保存的 passphrase，尝试多账号派生..."
  if sudo "$PYTHON" "$ROOT/ops/derive_wechat_keys.py" 2>/dev/null; then
    echo
    echo "=============================================="
    echo " 完成（复用已有 passphrase）: $KEYS_OUT"
    echo " 下一步:"
    echo "   python -m chat_radar wechat summary --from-db --since 0 --scope all"
    echo "=============================================="
    exit 0
  fi
  echo "    已有 passphrase 无法匹配，将重新捕获"
  echo
fi

echo ">> [1/4] 完全退出微信（旧进程会保留 Hardened Runtime，必须杀掉）"
if pgrep -x WeChat >/dev/null; then
  killall WeChat 2>/dev/null || true
  sleep 2
  if pgrep -x WeChat >/dev/null; then
    echo "错误: 无法退出微信，请手动 Cmd+Q 完全退出后重试"
    exit 1
  fi
  echo "    微信已退出"
else
  echo "    微信未运行"
fi

echo
echo ">> [2/4] 重签名微信（去除 Hardened Runtime，需输入 macOS 密码）"
sudo codesign --force --deep --sign - /Applications/WeChat.app
echo "    重签名完成"

echo
echo ">> [3/4] 启动微信（必须用新签名重新拉起进程）"
open -a WeChat
echo "    等待微信启动..."
for _ in $(seq 1 30); do
  if pgrep -x WeChat >/dev/null; then
    break
  fi
  sleep 1
done
if ! pgrep -x WeChat >/dev/null; then
  echo "错误: 微信未能启动，请手动打开微信并登录后重试"
  exit 1
fi
echo "    微信已启动 (PID=$(pgrep -x WeChat))，请确认已登录"

echo
echo ">> 验证 task_for_pid（需 sudo）..."
sudo python3 -c "
import ctypes, ctypes.util, subprocess, sys
lib = ctypes.CDLL(ctypes.util.find_library('System'))
pid = int(subprocess.check_output(['pgrep','-x','WeChat']).decode().strip())
task = ctypes.c_uint32(0)
kr = lib.task_for_pid(lib.mach_task_self(), ctypes.c_int(pid), ctypes.byref(task))
print(f'  pid={pid} kern_return={kr}')
if kr != 0:
    print('  [FAIL] task_for_pid 仍失败：请确认已完成重签名且微信是刚启动的新进程')
    sys.exit(1)
print('  [OK] 可以读取微信进程内存')
"

echo
echo ">> [4/4] 提取密钥（LLDB 断点，约 3 分钟）"
echo
echo "=============================================="
echo " 重要：接下来请在微信里操作"
echo "  1. 设置 → 退出登录（不是退出程序）"
echo "  2. 重新扫码/密码登录"
echo " 工具会等待最多 180 秒捕获 passphrase"
echo "=============================================="
echo
read -r -p "准备好后按 Enter 开始捕获（请立即去微信退出并重新登录）..."

# LLDB 捕获 passphrase（wcdb-tool 会保存到 ~/.wcdb-key-tool/wechat-passphrase.json）
sudo python3 "$WCDB_TOOL" extract \
  --db-dir "$DB_DIR" \
  --output "$KEYS_OUT" \
  --timeout 180 || EXTRACT_FAILED=1

# wcdb-tool 单账号 PBKDF2 可能失败（多账号错配），用我们的多账号派生兜底
if [[ "${EXTRACT_FAILED:-0}" == 1 ]] || [[ ! -f "$KEYS_OUT" ]]; then
  echo
  echo ">> wcdb-tool 单目录派生失败，尝试多账号自动匹配..."
  sudo "$PYTHON" "$ROOT/ops/derive_wechat_keys.py"
fi

if [[ ! -f "$KEYS_OUT" ]]; then
  echo "错误: 未生成 $KEYS_OUT"
  exit 1
fi

chmod 600 "$KEYS_OUT"
KEY_COUNT="$("$PYTHON" -c "import json; d=json.load(open('$KEYS_OUT')); print(sum(1 for k in d if not str(k).startswith('_')))")"
echo
echo "=============================================="
echo " 完成: $KEYS_OUT ($KEY_COUNT 个库密钥)"
echo " 下一步:"
echo "   python -m chat_radar wechat summary --from-db --since 0 --scope all"
echo "=============================================="
