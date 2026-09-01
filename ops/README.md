# ops/ — 可执行运维脚本

## 一键启动

```bash
./ops/start.sh              # 创建 venv、安装依赖、生成配置、跑 selftest
./ops/start.sh digest       # 初始化后执行 digest
./ops/start.sh auth         # 初始化后执行 Telegram 登录
```

`start.sh` 会自动：检查 Python 3.10+、创建 `.venv`、`pip install -e .`、从模板复制 `chat_radar_config.json`、创建 `data/` / `reports/` / `logs/`。

## 后续（Phase 1 完成后）

- `digest-cron.sh` — 晨间 digest 包装脚本  
- `com.chat-radar.digest.plist.template` — macOS launchd 模板  
- `install-launchd.sh` / `uninstall-launchd.sh`

文档说明见 [`docs/ops/02-operator-daily-sop.md`](../docs/ops/02-operator-daily-sop.md)。
