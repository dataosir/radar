# TG-RADAR — Telegram 招聘信息个人雷达

> 把你已订阅的 Telegram 招聘频道，变成**每日可扫、可过滤、可复盘**的结构化 digest。  
> 先解决自己的问题，再考虑是否产品化（对齐 indie-build-log Idea 8-D2 / Idea 4-C2）。

---

## 项目简介

这不是聊天机器人，是**信息雷达**：

1. **拉取**：从你已订阅的频道/群组增量读取新消息（Telethon User API）。
2. **过滤**：关键词 + 规则引擎筛出与你 profile 相关的招聘帖。
3. **去重**：按 `channel_id + message_id` 游标，避免重复处理。
4. **输出**：`reports/DIGEST_*.md` 日报 + `data/jobs.jsonl` 结构化存档。

默认回答是「不相关」——只有命中规则或（未来）LLM 评分过阈的帖才进入 digest。

### 与 indie-build-log 的关系

| 文档 | 关系 |
|------|------|
| Idea 8-D2 Telegram 群摘要 | 同一 pipeline 的 **招聘垂直变体** |
| Idea 4-C2 Telegram Bot 秘书 | 若产品化可走 Bot；**自用阶段用 User API** |
| Idea 8 社群群日报 | 共享「ingest → filter → digest」架构，不同 ICP |

---

## 快速开始（立项阶段）

当前为**文档 + 骨架**阶段，核心 ingest 尚未实现。开发顺序见 [`docs/prd/05-roadmap-backlog.md`](docs/prd/05-roadmap-backlog.md)。

```bash
cd tg-radar

# 一键初始化（venv + 依赖 + 配置模板 + selftest）
./ops/start.sh

# 或手动开发模式
cp tg_radar_config.example.json tg_radar_config.json
python3 -m tg_radar --help
python3 -m tg_radar selftest
```

### Telegram API 凭证

1. 登录 https://my.telegram.org → API development tools
2. 创建应用，获得 `api_id` 与 `api_hash`
3. 写入 `tg_radar_config.json`（**勿提交 git**）
4. 首次 `tg_radar auth` 会生成 `*.session`（已在 gitignore）

---

## 目录结构

```
tg-radar/
├── RULES.md              # AI / 人工实现铁律
├── .cursorrules          # Cursor 工作流约束
├── tg_radar_config.example.json
├── docs/                 # 知识库（prd / tech / ops）
├── ops/                  # launchd / cron 脚本（后续）
├── tg_radar/             # Python 包
│   ├── core/             # L0：路径、原子写、日志
│   ├── config/           # L0：配置
│   ├── ingest/           # L2：Telegram 拉取
│   ├── filter/           # L2：规则 / LLM 评分
│   ├── reporting/        # L3：Markdown digest
│   └── runtime/          # L4：CLI
├── data/                 # JSONL 运行时数据（gitignore）
├── reports/              # digest 报告（gitignore）
└── logs/                 # 日志（gitignore）
```

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | 知识库入口 + 4 步闭环 |
| [docs/INDEX.md](docs/INDEX.md) | 全库文件清单 |
| [docs/project-state.md](docs/project-state.md) | 当前焦点与下一步 |
| [docs/prd/00-product-overview.md](docs/prd/00-product-overview.md) | 产品定位 |
| [docs/tech/01-architecture.md](docs/tech/01-architecture.md) | 技术选型与分层 |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | 变更记录 |

---

## 免责声明

本项目仅供个人学习与求职信息整理，不构成任何招聘推荐或投资建议。使用 Telegram User API 须遵守 Telegram 服务条款。请勿用于未授权爬取或商业群发。
