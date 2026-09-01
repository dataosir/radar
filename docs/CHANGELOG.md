# Changelog

本文件记录 TG-RADAR 已发生变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

### Added

- `ops/start.sh`：一键启动脚本（venv 初始化、依赖安装、配置模板、selftest、CLI 转发）

---

## [0.1.0] - 2026-09-01

### Added

- 项目立项：文档体系（prd / tech / ops）、`RULES.md`、`.cursorrules`（对齐 tea 约束）
- 技术选型：Python 3.10+、Telethon、JSONL 持久化、规则过滤 MVP
- PRD F01–F05 框架、领域模型、日循环 workflow
- Python 包骨架：`tg_radar`（core / config / runtime）
- 配置模板 `tg_radar_config.example.json`
- CLI 入口：`python -m tg_radar --help`、`selftest`

### Notes

- 关联 indie-build-log Idea 8-D2（Telegram 招聘 digest 自用变体）
- Telethon ingest 尚未实现，见 `prd/05-roadmap-backlog.md` P0-04
