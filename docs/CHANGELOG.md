# Changelog

本文件记录 CHAT-RADAR 已发生变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

### Added

- **commit 变更范围配置化**：`.cursor/hooks/commit_scope.json` 声明式分组规则（patterns / priority / item 模板）；未匹配文件按路径前缀自动分组；排序由 priority + staged 出现顺序决定，不再硬编码 `order` 列表
- **pre-commit 运行时产物拦截**：`ops/git-hooks/pre-commit` 拒绝 staged `reports/`、`data/`、`logs/` 等敏感路径；`ops/install_git_hooks.sh`；`install.sh` 自动安装
- **自动 commit 消息生成**：`.cursor/hooks/generate_commit_message.py` 按 staged diff 生成中文主题 + 功能号 + 变更范围（参考 enterprise-kb-py 提交风格）；`auto_commit.sh` 改用 `-F` 写入完整 message

### Added (prior)

- **交互节点结构化日志**：`logs/interactions.jsonl` 记录 command/digest/wechat 步骤；`logs/start_menu.log` 记录菜单与 CLI 调用
- **P1-05 channels 管理**：`channels add/remove/enable/disable`；`start.sh` 菜单 13 交互管理
- **P1-07 自用验证模板**：`docs/ops/04-self-use-validation.md`（14 天噪音/漏帖记录表）
- **分发安装说明增强**：`build.sh` 生成完整 `INSTALL.txt`（微信密钥步骤、Windows 说明、14 天验证）

### Added (prior)

- **E1 digest 自动 wechat sync**：`digest` 在 inbox 后自动 `wechat sync`（macOS + 密钥可用；失败 soft skip）
- **E6 export 目录半自动**：`wechat import` + digest 前自动扫描 `data/wechat_exports/` 新 TXT
- **E7 inbox/export 游标**：`wechat_inbox_processed.json` / `wechat_export_processed.json` 避免重复解析
- **E5 统一 status**：`status` 展示 Telegram + 微信密钥/inbox 摘要
- **E3 setup 微信步骤 4/4**：引导启用微信、创建目录、locate、watch_chats
- **E2 launchd 晨间调度**：`ops/com.chat-radar.digest.plist.template` + `ops/install_launchd.sh`；菜单 12
- **E4 start.sh 扩展菜单**：9 微信 sync、10 locate、11 密钥提取
- **一键分发**：根目录 `install.sh`；`build.sh` bundle 含 `ops/` + `INSTALL.txt`

### Changed

- `start.sh` 菜单扩展至 13 项（频道管理）；支持 `./start.sh 13` / `./start.sh channels`
- `start.sh` 支持菜单编号与快捷名直达（`./start.sh 8`、`./start.sh wechat-summary`）；新增 `help` 子命令
- `digest` 支持 `--skip-wechat-export` / `--skip-wechat-sync`
- selftest 扩展至 23 项（含 `channels_crud`）

### Added (prior)

- **MP-11 统一 digest**：`digest` 合并 Telegram + 微信为一份 `DIGEST_*.md`；`wechat.enabled` 时自动扫描 inbox

- **F06-08 联系人摘要**：`wechat summary` 按联系人聚合聊天记录，输出 `reports/wechat_contacts/{人}.md` + `index.md`
- `wechat sync --scope groups|private|all`；`--since 0` 表示全量历史
- 新模块 `reporting/wechat_person_summary.py`；`wechat_db_reader` 支持私聊与 `self_wxid`
- **多账号密钥派生**：`wechat keys derive` + `ops/derive_wechat_keys.py`；`wechat locate` 显示最近活跃账号
- selftest 扩展至 16 项

### Fixed

- **微信密钥提取多账号错配**：`extract_wechat_keys.sh` 自动检测活跃账号；PBKDF2 失败时遍历所有账号匹配 passphrase

### Added (prior)

- **F06-P2.5 macOS 本地库**：`wechat locate` 自动发现微信沙盒目录；`wechat sync` 解密 SQLCipher 库并导入群聊消息
- 新模块：`wechat_mac_paths` / `wechat_db_crypto` / `wechat_db_reader`（零 pip 依赖，CommonCrypto）
- selftest 扩展至 14 项（含本地库 reader 模拟）
- **引导式配置**：`setup` 命令 + `./start.sh` 交互菜单（无需手改 JSON）
- `digest --skip-fetch`：离线仅用本地数据生成报告
- `commit_fetch_cursor`：落盘成功后再推进游标
- selftest 扩展至 12 项（游标落盘顺序、session 路径）
- **登录前置检查**：`preflight` 命令；`fetch`/`digest --fix` 未登录时引导完成 auth
- `status` / `config` 显示 Telegram 登录状态
- `setup` 完成后可选立即登录

### Fixed

- **未登录 fetch 报错不明确**：改为友好提示并指引 setup → auth → fetch 步骤
- **游标提前写入**：改为 `append_messages` 成功后再 `commit_fetch_cursor`
- **`iter_messages` FloodWait**：`_collect_messages` 遇限流自动等待重试
- **`digest` 离线模式**：未配置 API 时不再报错，跳过 fetch 继续生成

### Added (prior)
- `core/models.RawMessage` 多源统一模型
- `ingest/wechat_export.py`、`wechat_inbox.py`、`persist.py`
- `docs/prd/06-multi-platform-roadmap.md`：主流 IM 接入与聊天摘要路线图
- selftest 扩展至 7 项（含微信解析与去重）

### Changed

- **品牌升级**：TG-RADAR → **CHAT-RADAR**；Python 包 `chat_radar`；配置 `chat_radar_config.json`
- 产品定位扩展：多源聊天历史雷达（招聘为首个垂直 profile）
- 多源架构：Telegram + 微信共享 filter / reporting 层
- digest 渲染支持 `source` / `sender` 字段
- 环境变量向后兼容：`TG_RADAR_HOME` / `TG_RADAR_CONFIG`

---

## [0.1.0] - 2026-09-01（早期）

### Added

- `ops/start.sh`：一键启动脚本（venv 初始化、依赖安装、配置模板、selftest、CLI 转发）
