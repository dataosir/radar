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

# 一键初始化（venv + 依赖 + 交互菜单 + selftest）
./start.sh

# 无参数时进入引导菜单（12 项）：
#   1) 首次配置（TG + 微信）
#   4) 生成 digest（TG + 微信全自动 ingest）
#   7–12) 微信状态 / 摘要 / sync / locate / 密钥 / launchd
```

也可直接运行子命令：

```bash
./install.sh                 # 给他人分发：安装 + 可选 setup
./start.sh setup             # 引导式配置（4/4 含微信）
./start.sh auth              # 首次登录
./start.sh fetch             # 增量拉取频道
./start.sh digest --since 24 # inbox + export + sync + TG fetch + 合并报告
./start.sh digest --skip-fetch  # 仅用本地数据重新生成报告
./start.sh status            # 双源状态概览
./start.sh 8                 # 菜单编号直达（等同 wechat-summary）
./start.sh wechat-summary    # 微信联系人 Markdown 摘要
./start.sh help              # 菜单编号与快捷命令对照
```

### 打包发布（给他人）

```bash
./build.sh                   # selftest + wheel + bundle（含 ops/ + INSTALL.txt）
# 解压 dist/chat-radar-*-bundle.tar.gz → ./install.sh
```

### 微信（已可用）

```bash
# 主路径：合并 TG + 微信 digest
./start.sh digest --since 24

# 微信专项（菜单 7–11 或 CLI）
python3 -m chat_radar wechat status
python3 -m chat_radar wechat import          # 扫描 export 目录新 TXT
python3 -m chat_radar wechat sync --since 24
python3 -m chat_radar wechat summary --from-db --since 0 --scope all
./ops/extract_wechat_keys.sh                 # macOS 一次性密钥
./ops/install_launchd.sh                     # 晨间自动 digest
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
├── install.sh            # 首次安装（分发用）
├── start.sh              # 一键启动
├── build.sh              # 一键打包
├── chat_radar_config.example.json
├── docs/                 # 知识库（prd / tech / ops）
├── ops/                  # 微信密钥 / launchd 脚本
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
