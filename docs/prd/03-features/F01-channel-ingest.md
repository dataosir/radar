# F01 · 频道增量拉取

## 目标

从用户**已订阅**的 Telegram 频道/群组，增量读取新消息并落盘。

## 输入

- `chat_radar_config.json` → `channels[]`（`@username` 或 numeric id）
- `data/cursors.json` → 每频道 `last_message_id`
- Telethon session 文件（`auth` 后生成）

## 输出

- `data/raw_messages.jsonl` append
- 更新 `data/cursors.json`

## 行为规格

1. **幂等**：同一 `channel_id + message_id` 不重复写入 raw。  
2. **增量**：只拉 `message_id > last_message_id` 的消息。  
3. **冷启动**：游标为空时，默认只拉最近 **N 条**（配置 `ingest.bootstrap_limit`，默认 50），不扫全历史。  
4. **限流**：遇 `FloodWaitError` 按 Telegram 要求 sleep，写日志，不吞异常。  
5. **媒体帖**：无 `text` 时记 `has_media: true`，正文为空；若 caption 有文字则取 caption。

## 非目标

- 不拉取未订阅频道  
- 不下载大文件（仅元数据 + 文本）

## 验收

- [x] `chat_radar auth` 成功登录  
- [x] `chat_radar fetch` 对 1 个测试频道写入 raw + 更新游标  
- [x] 重复 `fetch` 无新增时不写重复行
