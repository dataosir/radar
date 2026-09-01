# 03 · 持久化 Schema

> 全部 JSON/JSONL；写入必须原子（`core.utils.atomic_write_json`）。

---

## `data/cursors.json`

```json
{
  "1234567890": {
    "last_message_id": 4521,
    "updated_at": "2026-09-01T08:30:00+08:00"
  }
}
```

键：字符串化的 `channel_id`。

---

## `data/raw_messages.jsonl`

每行一条 JSON：

```json
{
  "channel_id": 1234567890,
  "message_id": 4522,
  "date": "2026-09-01T07:12:00+00:00",
  "text": "招聘 Java 后端，远程…",
  "link": "https://t.me/c/1234567890/4522",
  "has_media": false,
  "fetched_at": "2026-09-01T08:30:01+08:00"
}
```

---

## `data/jobs.jsonl`

```json
{
  "id": "1234567890:4522",
  "channel_id": 1234567890,
  "message_id": 4522,
  "title": "招聘 Java 后端",
  "summary": "…",
  "matched_rules": ["include:Java", "include:远程"],
  "score": null,
  "status": "new",
  "link": "https://t.me/c/1234567890/4522",
  "date": "2026-09-01T07:12:00+00:00",
  "created_at": "2026-09-01T08:30:02+08:00"
}
```

---

## `chat_radar_config.json`（见根目录 example）

主要段：

| 段 | 说明 |
|---|---|
| `telegram.api_id` | my.telegram.org |
| `telegram.api_hash` | 密钥 |
| `telegram.session_name` | session 文件名 |
| `channels[]` | `{ "username": "@xxx", "enabled": true }` |
| `ingest.bootstrap_limit` | 冷启动拉取条数 |
| `filter.include_keywords` | 正向词 |
| `filter.exclude_keywords` | 排除词 |
| `filter.include_patterns` | 正则列表 |
| `report.summary_max_chars` | 摘要长度 |

---

## `reports/DIGEST_*.md`

纯 Markdown，无 schema 约束；格式见 F04 PRD。

---

## 日志 `logs/chat_radar.log`

文本行；建议格式：

```
2026-09-01 08:30:01 INFO fetch channel=@remote_jobs_cn new=12
```
