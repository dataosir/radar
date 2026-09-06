#!/usr/bin/env bash
# CHAT-RADAR 一键启动：环境初始化 + 引导式菜单 / CLI 子命令
#
# 用法:
#   ./start.sh              # 初始化环境 + 交互菜单
#   ./start.sh 8            # 直接执行菜单项（1-12，等同菜单内选择）
#   ./start.sh wechat-summary
#   ./start.sh setup        # 引导式配置
#   ./start.sh auth         # Telegram 登录
#   ./start.sh fetch        # 增量拉取
#   ./start.sh digest       # 拉取 + 微信 ingest + 合并 digest
#   ./start.sh selftest     # 离线自测
#   ./start.sh help         # 菜单编号与快捷命令对照
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MENU_LOG="$ROOT/logs/start_menu.log"

log_menu() {
  mkdir -p "$ROOT/logs"
  local line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$line" | tee -a "$MENU_LOG"
}

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
    echo ">> 已生成配置文件，接下来将引导你完成设置"
  fi
}

ensure_dirs() {
  mkdir -p "$ROOT/data" "$ROOT/reports" "$ROOT/logs" \
    "$ROOT/data/wechat_inbox" "$ROOT/data/wechat_exports"
}

run_cli() {
  local cmd="${1:-selftest}"
  shift || true
  log_menu "CLI start: chat_radar $cmd $*"
  python -m chat_radar "$cmd" "$@"
  local rc=$?
  log_menu "CLI exit: chat_radar $cmd rc=$rc"
  return "$rc"
}

run_selftest() {
  echo ">> 运行离线自测..."
  run_cli selftest
}

show_menu() {
  echo ""
  echo "╔══════════════════════════════════════╗"
  echo "║         CHAT-RADAR  主菜单           ║"
  echo "╠══════════════════════════════════════╣"
  echo "║  1) 首次配置（TG + 微信引导）        ║"
  echo "║  2) Telegram 登录                    ║"
  echo "║  3) 拉取频道消息                     ║"
  echo "║  4) 生成每日 digest（TG + 微信）     ║"
  echo "║  5) 查看当前状态（双源）             ║"
  echo "║  6) 重新运行自测                     ║"
  echo "║  7) 微信状态检查                     ║"
  echo "║  8) 微信联系人摘要                   ║"
  echo "║  9) 微信同步招聘群（本地库）         ║"
  echo "║ 10) 探测微信目录 / 定位账号          ║"
  echo "║ 11) 提取微信密钥（macOS 一次性）     ║"
  echo "║ 12) 安装晨间自动 digest（launchd）   ║"
  echo "║ 13) 管理 Telegram 频道             ║"
  echo "║  0) 退出                             ║"
  echo "╚══════════════════════════════════════╝"
  echo ""
  echo "提示: 首次使用请按 1 → 2 → 4；macOS 微信需 11 → 9"
  echo "      退出菜单后可用: ./start.sh 8  或  ./start.sh help"
  echo -n "请选择 [0-13]: "
}

show_help() {
  cat <<'EOF'
CHAT-RADAR 快捷命令（菜单编号可直接作为参数）

  编号    快捷名                 说明
  ----    ------                 ----
   1      setup                  首次配置（TG + 微信）
   2      auth                   Telegram 登录
   3      fetch                  拉取频道消息
   4      digest                 生成每日 digest（TG + 微信）
   5      status                 查看当前状态（双源）
   6      selftest               离线自测
   7      wechat-status          微信状态检查
   8      wechat-summary         微信联系人 Markdown 摘要
   9      wechat-sync            微信同步招聘群（本地库）
  10      wechat-locate          探测微信目录 / 定位账号
  11      wechat-keys            提取微信密钥（macOS，需 sudo）
  12      launchd                安装晨间自动 digest
  13      channels               管理 Telegram 频道

示例:
  ./start.sh                 # 交互菜单
  ./start.sh 8               # 等同菜单选 8
  ./start.sh wechat-summary
  ./start.sh digest --since 24 --skip-fetch

注意: 在 shell 里直接输入 8 无效，必须带 ./start.sh 前缀。
EOF
}

resolve_menu_alias() {
  case "$1" in
    setup) echo 1 ;;
    auth) echo 2 ;;
    fetch) echo 3 ;;
    digest) echo 4 ;;
    status) echo 5 ;;
    selftest) echo 6 ;;
    wechat-status) echo 7 ;;
    wechat-summary) echo 8 ;;
    wechat-sync) echo 9 ;;
    wechat-locate) echo 10 ;;
    wechat-keys) echo 11 ;;
    launchd) echo 12 ;;
    channels) echo 13 ;;
    *) echo "" ;;
  esac
}

dispatch_menu_choice() {
  local choice="$1"
  log_menu "MENU choice=$choice start"
  local rc=0
  case "$choice" in
    1) run_cli setup ;;
    2) run_cli auth ;;
    3) run_cli fetch --fix ;;
    4) run_cli digest --fix ;;
    5) run_cli status ;;
    6) run_selftest ;;
    7) run_cli wechat status ;;
    8) run_wechat_summary ;;
    9) run_cli wechat sync --since 24 ;;
    10) run_cli wechat locate ;;
    11) run_extract_keys ;;
    12) run_install_launchd ;;
    13) run_channels_menu ;;
    *)
      echo "无效选项，请输入 0-13" >&2
      rc=1
      ;;
  esac
  rc=$?
  log_menu "MENU choice=$choice exit rc=$rc"
  return "$rc"
}

run_wechat_summary() {
  echo ">> 生成微信联系人 Markdown 摘要（默认：本地库全量 + 纯文本）"
  echo "   全量历史可能需数分钟，输出目录 reports/wechat_contacts/"
  echo -n "确认继续？[Y/n]: "
  read -r confirm
  case "${confirm:-Y}" in
    y|Y|yes|是|"")
      run_cli wechat summary --from-db --since 0 --scope all
      ;;
    *)
      echo "已取消。"
      ;;
  esac
}

run_extract_keys() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "微信密钥提取仅支持 macOS。"
    return 1
  fi
  if [[ ! -x "$ROOT/ops/extract_wechat_keys.sh" ]]; then
    die "缺少 ops/extract_wechat_keys.sh"
  fi
  echo ">> 将运行密钥提取脚本（需 sudo 密码，并在微信中重新登录）"
  echo -n "确认继续？[Y/n]: "
  read -r confirm
  case "${confirm:-Y}" in
    y|Y|yes|是|"")
      bash "$ROOT/ops/extract_wechat_keys.sh"
      ;;
    *)
      echo "已取消。"
      ;;
  esac
}

run_install_launchd() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "launchd 调度仅支持 macOS。"
    return 1
  fi
  if [[ ! -x "$ROOT/ops/install_launchd.sh" ]]; then
    die "缺少 ops/install_launchd.sh"
  fi
  bash "$ROOT/ops/install_launchd.sh"
}

run_channels_menu() {
  while true; do
    echo ""
    echo "── Telegram 频道管理 ──"
    run_cli channels list
    echo ""
    echo "  a) 添加频道"
    echo "  r) 删除频道"
    echo "  e) 启用频道"
    echo "  d) 禁用频道"
    echo "  0) 返回主菜单"
    echo -n "请选择 [a/r/e/d/0]: "
    read -r sub
    echo ""
    case "$sub" in
      a|A)
        echo -n "频道 @username（可省略 @）: "
        read -r ch_ref
        echo -n "备注（可选）: "
        read -r ch_note
        echo -n "立即启用？[Y/n]: "
        read -r ch_en
        args=(channels add "$ch_ref")
        if [[ -n "$ch_note" ]]; then
          args+=(--note "$ch_note")
        fi
        case "${ch_en:-Y}" in
          n|N|no|否) args+=(--disabled) ;;
        esac
        run_cli "${args[@]}"
        ;;
      r|R)
        echo -n "要删除的频道 @username: "
        read -r ch_ref
        run_cli channels remove "$ch_ref"
        ;;
      e|E)
        echo -n "要启用的频道 @username: "
        read -r ch_ref
        run_cli channels enable "$ch_ref"
        ;;
      d|D)
        echo -n "要禁用的频道 @username: "
        read -r ch_ref
        run_cli channels disable "$ch_ref"
        ;;
      0|q|Q)
        return 0
        ;;
      *)
        echo "无效选项"
        ;;
    esac
  done
}

interactive_menu() {
  run_selftest
  echo ""
  while true; do
    show_menu
    read -r choice
    echo ""
    case "$choice" in
      0|q|Q)
        echo "再见。"
        echo "提示: 下次可直接运行 ./start.sh 8  或  ./start.sh help 查看快捷命令"
        return 0
        ;;
      *)
        dispatch_menu_choice "$choice" || true
        ;;
    esac
    echo ""
  done
}

main() {
  check_python
  setup_venv
  ensure_config
  ensure_dirs

  if [[ $# -eq 0 ]]; then
    interactive_menu
    return 0
  fi

  local first="$1"
  if [[ "$first" == "help" || "$first" == "--help" || "$first" == "-h" ]]; then
    show_help
    return 0
  fi

  local mapped
  mapped="$(resolve_menu_alias "$first")"
  if [[ -n "$mapped" ]]; then
    shift || true
    if [[ $# -gt 0 ]]; then
      echo "提示: 菜单快捷命令不接受额外参数，已忽略: $*" >&2
    fi
    dispatch_menu_choice "$mapped"
    return 0
  fi

  if [[ "$first" =~ ^[0-9]+$ ]]; then
    if [[ "$first" == "0" ]]; then
      return 0
    fi
    if [[ "$first" -ge 1 && "$first" -le 13 ]]; then
      shift || true
      if [[ $# -gt 0 ]]; then
        echo "提示: 菜单编号不接受额外参数，已忽略: $*" >&2
      fi
      dispatch_menu_choice "$first"
      return 0
    fi
    die "无效菜单编号: $first（有效范围 1-13，运行 ./start.sh help 查看）"
  fi

  run_cli "$@"
}

main "$@"
