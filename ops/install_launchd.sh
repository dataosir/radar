#!/usr/bin/env bash
# 安装 macOS launchd 晨间 digest 任务（默认 08:30，跳过 TG fetch 仅用本地+微信）
#
# 用法: ./ops/install_launchd.sh [--hour 8] [--minute 30] [--with-fetch]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/ops/com.chat-radar.digest.plist.template"
PLIST_DEST="$HOME/Library/LaunchAgents/com.chat-radar.digest.plist"
LABEL="com.chat-radar.digest"

HOUR=8
MINUTE=30
WITH_FETCH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hour) HOUR="$2"; shift 2 ;;
    --minute) MINUTE="$2"; shift 2 ;;
    --with-fetch) WITH_FETCH=1; shift ;;
    -h|--help)
      echo "用法: ./ops/install_launchd.sh [--hour 8] [--minute 30] [--with-fetch]"
      exit 0
      ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "launchd 仅支持 macOS"
  exit 1
fi

if [[ ! -f "$TEMPLATE" ]]; then
  echo "缺少模板: $TEMPLATE"
  exit 1
fi

mkdir -p "$ROOT/logs" "$HOME/Library/LaunchAgents"

START_SH="$ROOT/start.sh"
sed \
  -e "s|__ROOT__|$ROOT|g" \
  -e "s|__START_SH__|$START_SH|g" \
  "$TEMPLATE" > "$PLIST_DEST"

if [[ "$WITH_FETCH" -eq 1 ]]; then
  /usr/bin/plutil -remove ProgramArguments.4 "$PLIST_DEST" 2>/dev/null || true
  /usr/bin/plutil -remove ProgramArguments.4 "$PLIST_DEST" 2>/dev/null || true
fi

/usr/bin/plutil -replace StartCalendarInterval.Hour -integer "$HOUR" "$PLIST_DEST"
/usr/bin/plutil -replace StartCalendarInterval.Minute -integer "$MINUTE" "$PLIST_DEST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL" 2>/dev/null || true

echo "已安装 launchd 任务: $PLIST_DEST"
echo "  时间: 每天 ${HOUR}:$(printf '%02d' "$MINUTE")"
if [[ "$WITH_FETCH" -eq 1 ]]; then
  echo "  命令: digest --since 24（含 Telegram fetch）"
else
  echo "  命令: digest --since 24 --skip-fetch（本地 JSONL + 微信 ingest）"
fi
echo "  日志: $ROOT/logs/launchd-digest.*.log"
echo ""
echo "卸载: launchctl bootout gui/$(id -u)/$LABEL && rm $PLIST_DEST"
