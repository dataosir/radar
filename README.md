# CHAT-RADAR — 多源聊天历史个人雷达

> 把 Telegram、微信等主流 IM 的聊天记录，变成**每日可扫、可过滤、可复盘**的结构化 digest。  
> 首个垂直场景是招聘信息；引擎本身支持扩展至更多聊天平台（见 [`docs/prd/06-multi-platform-roadmap.md`](docs/prd/06-multi-platform-roadmap.md)）。

---

## 项目简介

这不是聊天机器人，是**信息雷达**：

1. **接入**：Telegram（Telethon API）+ 微信（导出 TXT / inbox 落盘）；未来 QQ、Discord、Slack…
2. **统一**：`RawMessage` 模型归一化多源消息
3. **过滤**：关键词 + 规则引擎筛出与你 profile 相关的内容
4. **去重**：按 `source + source_id + message_id` 游标，避免重复处理
5. **输出**：`reports/DIGEST_*.md` 日报 + `data/raw_messages.jsonl` 结构化存档

默认回答是「不相关」——只有命中规则或（未来）LLM 摘要过阈的消息才进入 digest。

### 与 indie-build-log 的关系

| 文档 | 关系 |
|------|------|
| Idea 8 社群群日报 | **同一 pipeline**：多 IM ingest → filter → digest |
| Idea 8-D2 Telegram 群摘要 | 招聘垂直变体（首个 profile） |
| Idea 4-C2 Telegram Bot 秘书 | 产品化可走 Bot；**自用阶段用 User API** |

---

## 快速开始

```bash
cd chat-radar   # 或你的 clone 目录名

# 一键初始化（venv + 依赖 + 配置模板 + selftest）
./ops/start.sh

# 或手动开发模式
cp chat_radar_config.example.json chat_radar_config.json
python3 -m chat_radar --help
python3 -m chat_radar selftest
```

### 微信（已可用）

```bash
# 解析 PC 导出的聊天记录
python3 -m chat_radar wechat parse data/wechat_exports/招聘群.txt --chat "Java招聘群"

# 扫描 inbox 落盘文件
python3 -m chat_radar wechat inbox

# 生成微信 digest
python3 -m chat_radar wechat digest --since 24
```

### Telegram API 凭证

1. 登录 https://my.telegram.org → API development tools
2. 创建应用，获得 `api_id` 与 `api_hash`
3. 写入 `chat_radar_config.json`（**勿提交 git**）
4. 首次 `chat_radar auth` 会生成 `*.session`（已在 gitignore）

---

## 目录结构

```
chat-radar/
├── RULES.md              # AI / 人工实现铁律
├── chat_radar_config.example.json
├── docs/                 # 知识库（prd / tech / ops）
├── ops/                  # 一键启动 / launchd 脚本
├── chat_radar/           # Python 包
│   ├── core/             # L0：路径、模型、原子写
│   ├── config/           # L0：配置
│   ├── ingest/           # L2：多源适配器（TG / 微信 / …）
│   ├── filter/           # L2：规则 / LLM 摘要
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
| [docs/prd/06-multi-platform-roadmap.md](docs/prd/06-multi-platform-roadmap.md) | **多平台接入路线图** |
| [docs/tech/01-architecture.md](docs/tech/01-architecture.md) | 技术选型与分层 |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | 变更记录 |

---

## 免责声明

本项目仅供个人学习与信息整理，不构成任何招聘推荐或投资建议。使用各 IM 平台 API 须遵守相应服务条款。请勿用于未授权爬取或商业群发。
