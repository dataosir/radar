# 01 · 整体架构与技术选型

> 产品边界见 [`../prd/00-product-overview.md`](../prd/00-product-overview.md)。

---

## 1. 技术选型决策

### 1.1 为什么 Python

| 考量 | 结论 |
|---|---|
| 与 tea 栈一致 | 复用工程习惯（JSONL、CLI、launchd ops） |
| Telethon 生态 | Python MTProto 客户端最成熟 |
| 迭代速度 | 自用工具，先跑通再优化 |

### 1.2 为什么 Telethon（User API）而非 Bot API

| 方案 | 优点 | 缺点 | 决策 |
|---|---|---|---|
| **Telethon** | 读已订阅频道；招聘群通常不加 Bot | User session；ToS 需注意 | ✅ **自用 MVP** |
| python-telegram-bot | 官方 Bot 路径清晰 | 频道需主动加 Bot | 产品化 Phase 3 |
| Pyrogram | 类似 Telethon | 与 Telethon 二选一 | ❌ 不重复引入 |
| 网页爬 t.me/s | 无 SDK | 不稳定、易变 | ❌ |

### 1.3 持久化：JSON/JSONL

与 tea 相同理由：零运维、原子写、易 grep、适合单机自用。

**不引入** SQLite/Postgres，除非 jobs 量 > 100k 且查询变慢。

### 1.4 过滤：规则优先，LLM 延后

| 阶段 | 方案 | 成本 |
|---|---|---|
| MVP | 关键词 + 正则 | ¥0 |
| Phase 2 | OpenAI 兼容 API 打分 | 按 token |

### 1.5 已批准依赖

```toml
dependencies = ["telethon>=1.36"]
```

新增依赖（如 `openai`、`httpx`）须更新本文件 + 根 `RULES.md` + 先获批。

---

## 2. 分层依赖（单向向下）

```
runtime (L4)  →  CLI / runner
reporting (L3)→  digest Markdown
filter  (L2)  →  rules / (future) llm_score
ingest  (L2)  →  telethon client, cursors
core / config (L0) → paths, atomic_io, logging, defaults
```

**禁止**：下层 import 上层；`ingest` ↔ `filter` 互相调用（经 `runner` 编排）。

---

## 3. 核心数据流

```
tg_radar_config.json
    ↓
auth → session file
    ↓
fetch: Telethon → raw_messages.jsonl + cursors.json
    ↓
filter: rules → jobs.jsonl
    ↓
report: DIGEST_*.md
```

`digest` = `fetch` + `filter` + `report` 串联。

---

## 4. 包 ↔ PRD 映射

| 包 | PRD |
|---|---|
| `tg_radar/ingest/` | F01, F03 |
| `tg_radar/filter/` | F02 |
| `tg_radar/reporting/` | F04 |
| `tg_radar/runtime/` | CLI 全命令 |
| `tg_radar/config/` | 配置 |
| `tg_radar/selftest.py` | NFR |

---

## 5. 运行时路径

| 优先级 | 基准目录 |
|---|---|
| 1 | `$TG_RADAR_HOME` |
| 2 | 源码仓库根（CWD） |

其下：`data/`、`reports/`、`logs/`。  
配置：`$TG_RADAR_CONFIG` 或 `tg_radar_config.json`。

Session：`$TG_RADAR_HOME/tg_radar.session`（可配置 `telegram.session_name`）。

---

## 6. 与 indie-build-log 架构对齐

```
Idea 8 digest pipeline:
  输入适配器（Telegram / Slack / 微信转发）
       ↓ 统一 RawMessage
  过滤 + 摘要
       ↓
  Digest 输出
```

tg-radar 实现 **Telegram 输入适配器** 的招聘垂直版；未来若做 Idea 8 产品，抽取 `filter` + `reporting` 为共享库。
