#!/usr/bin/env bash
# CHAT-RADAR 一键打包：构建 wheel + 发布归档
#
# 用法:
#   ./build.sh              # selftest 通过后打包
#   ./build.sh --skip-test  # 跳过 selftest
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
PYTHON="${PYTHON:-python3}"
DIST="$ROOT/dist"
SKIP_TEST=0

die() {
  echo "错误: $*" >&2
  exit 1
}

for arg in "$@"; do
  case "$arg" in
    --skip-test) SKIP_TEST=1 ;;
    -h|--help)
      echo "用法: ./build.sh [--skip-test]"
      exit 0
      ;;
    *) die "未知参数: $arg" ;;
  esac
done

check_python() {
  if ! command -v "$PYTHON" >/dev/null 2>&1; then
    die "未找到 $PYTHON，请安装 Python 3.10+"
  fi
  "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "需要 Python 3.10+"
}

setup_venv() {
  if [[ ! -d "$VENV" ]]; then
    echo ">> 创建虚拟环境: $VENV"
    "$PYTHON" -m venv "$VENV"
  fi
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python -m pip install -q --upgrade pip setuptools wheel
  python -m pip install -q -e .
}

clean_dist() {
  rm -rf "$DIST" build chat_radar.egg-info
  mkdir -p "$DIST"
}

build_wheel() {
  echo ">> 构建 wheel..."
  python -m pip wheel . -w "$DIST" --no-deps -q
}

bundle_release() {
  local version
  version="$(python -c 'from chat_radar import __version__; print(__version__)')"
  local bundle="$DIST/chat-radar-${version}-bundle.tar.gz"
  echo ">> 打包发布归档: $bundle"
  tar -czf "$bundle" \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='data' \
    --exclude='reports' \
    --exclude='logs' \
    --exclude='dist' \
    --exclude='*.session' \
    --exclude='chat_radar_config.json' \
    --exclude='wechat_keys.json' \
    -C "$ROOT" \
    chat_radar pyproject.toml README.md RULES.md install.sh \
    chat_radar_config.example.json start.sh build.sh ops docs
  echo ">> 生成安装说明: $DIST/INSTALL.txt"
  cat > "$DIST/INSTALL.txt" <<EOF
CHAT-RADAR v${version} 安装步骤
================================

【环境要求】
  - Python 3.10+
  - macOS（微信本地库 / launchd 可选；Windows 仅 TG + export/inbox）

【安装】
1. 解压 bundle 到任意目录
2. cd chat-radar-${version}-bundle
3. chmod +x install.sh start.sh build.sh ops/*.sh
4. ./install.sh

【首次使用】
  ./start.sh              # 交互菜单
  菜单 1 → 2 → 4          # 配置 → TG 登录 → 每日 digest
  菜单 13                 # 添加/启用 Telegram 招聘频道

【日常使用】
  ./start.sh digest --since 24     # TG + 微信合并 digest
  ./start.sh status                # 双源健康检查
  ./start.sh help                  # 菜单编号与快捷命令

【macOS 微信（可选，读 PC 已同步聊天库）】
一次性配置（约 5 分钟，需 sudo）：
  1) ./start.sh 10                 # 探测微信目录
  2) ./start.sh 11                 # 提取密钥（会重签名微信，需重新登录一次）
  3) ./start.sh 9                  # 同步招聘群到本地 JSONL
  4) ./start.sh 4                  # digest 自动含微信

日常无需再登录微信；密钥失效（微信大版本升级后）重跑步骤 2。

降级方案（不碰密钥）：
  - 复制粘贴到 data/wechat_inbox/
  - 或 PC 导出 TXT 到 data/wechat_exports/
  digest 会自动扫描上述目录。

【联系人 Markdown 摘要（按需）】
  ./start.sh 8                     # 按人生成全量聊天记录 MD
  输出: reports/wechat_contacts/

【晨间自动化（macOS）】
  ./start.sh 12
  或: ./ops/install_launchd.sh

【14 天自用验证】
  见 docs/ops/04-self-use-validation.md

【Windows 用户】
  Telegram + 微信 export/inbox 可用；本地库 sync 不支持。

详细文档: docs/README.md
EOF
}

main() {
  check_python
  setup_venv
  if [[ "$SKIP_TEST" -eq 0 ]]; then
    echo ">> 运行 selftest..."
    python -m chat_radar selftest
  fi
  clean_dist
  build_wheel
  bundle_release
  echo ""
  echo "打包完成，产物目录: $DIST"
  ls -lh "$DIST"
}

main "$@"
