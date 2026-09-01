# 01 · 领域模型

## 核心实体

### Channel（频道）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | Telegram 频道 ID（配置可用 `@username` 解析） |
| `username` | str? | `@channel` 句柄 |
| `title` | str | 显示名（运行时填充） |
| `enabled` | bool | 是否参与拉取 |

### RawMessage（原始消息）

| 字段 | 类型 | 说明 |
|---|---|---|
| `channel_id` | int | 来源频道 |
| `message_id` | int | Telegram 消息 ID（频道内单调递增） |
| `date` | ISO8601 | 发送时间（UTC 存，展示转本地） |
| `text` | str | 纯文本（无 text 的媒体帖记 `has_media`） |
| `link` | str | `t.me/c/...` 或公开链接 |
| `fetched_at` | ISO8601 | 拉取时间 |

持久化：`data/raw_messages.jsonl`（append-only）

### JobPost（招聘帖 · 过滤后）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | `{channel_id}:{message_id}` |
| `title` | str | 首行或规则提取的标题 |
| `summary` | str | 截断正文（≤ 500 字） |
| `matched_rules` | list[str] | 命中的规则名 |
| `score` | float? | LLM 评分（Phase 2） |
| `status` | enum | `new` / `seen` / `starred` / `dismissed` |

持久化：`data/jobs.jsonl`

### Cursor（游标）

| 字段 | 类型 | 说明 |
|---|---|---|
| `channel_id` | int | 频道 |
| `last_message_id` | int | 已处理的最大 message_id |
| `updated_at` | ISO8601 | 更新时间 |

持久化：`data/cursors.json`

### Digest（日报）

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | YYYY-MM-DD | 报告日期（本地时区） |
| `total_fetched` | int | 本次拉取条数 |
| `total_matched` | int | 命中条数 |
| `items` | list[JobPost] | 按时间倒序 |

输出：`reports/DIGEST_YYYYMMDD_HHMMSS.md`

## 状态机（JobPost）

```
new → seen（进入 digest 即 seen）
new → starred（用户标记重点）
new → dismissed（误报，写入 exclude 学习 — Phase 2）
```

## 与 tea 的类比

| tea | tg-radar |
|---|---|
| 种子 `seed_records` | `jobs.jsonl` |
| `trade_plan.json` | `cursors.json` |
| `SEED_*.md` 报告 | `DIGEST_*.md` |
| 道/法/术 串联否决 | 拉取 → 去重 → 规则过滤 |
