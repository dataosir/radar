# Changelog

本文件记录 CHAT-RADAR 已发生变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

### Added

- **F06 微信接入 MVP**：`wechat parse` / `wechat inbox` / `wechat digest` CLI
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
