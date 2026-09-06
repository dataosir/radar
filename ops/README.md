# ops/ — 可执行运维脚本

> **一键启动 / 安装 / 打包在仓库根目录**：`../start.sh`、`../install.sh`、`../build.sh`。

## 根目录脚本

```bash
./install.sh              # 首次安装 + 可选 setup 引导（给他人分发时用）
./start.sh                # 创建 venv、安装依赖、交互菜单（12 项）
./start.sh digest         # TG fetch + 微信 inbox/export/sync + 合并 digest
./build.sh                # selftest + wheel + bundle 归档（含 ops/）
```

`start.sh` 会自动：检查 Python 3.10+、创建 `.venv`、`pip install -e .`、从模板复制配置、创建 `data/` / `reports/` / `logs/` / 微信目录。

## 本目录脚本

| 脚本 | 用途 |
|---|---|
| `extract_wechat_keys.sh` | macOS 一次性提取 SQLCipher 密钥 → `data/wechat_keys.json` |
| `derive_wechat_keys.py` | 从已保存 passphrase 多账号派生密钥（需 sudo） |
| `install_launchd.sh` | 安装晨间 digest launchd 任务（默认 08:30） |
| `com.chat-radar.digest.plist.template` | launchd 模板 |

```bash
./ops/extract_wechat_keys.sh           # 菜单 11 也会调用
./ops/install_launchd.sh               # 菜单 12；可选 --with-fetch
./ops/install_launchd.sh --hour 9 --minute 0
```

文档说明见 [`docs/ops/02-operator-daily-sop.md`](../docs/ops/02-operator-daily-sop.md) 与 [`docs/ops/03-wechat-sop.md`](../docs/ops/03-wechat-sop.md)。

## 分发 bundle

```bash
./build.sh
# 产物: dist/chat-radar-0.1.0-bundle.tar.gz + INSTALL.txt
```

解压后：`chmod +x install.sh start.sh ops/*.sh && ./install.sh`
