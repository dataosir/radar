# F03 · 去重与游标

## 目标

保证每条消息只处理一次；重启 / 重复运行安全。

## 去重键

```
dedup_key = f"{channel_id}:{message_id}"
```

## 游标语义

- `cursors[channel_id].last_message_id` = 已成功拉取并落 raw 的最大 ID  
- **只增不减**（除非手动 `chat_radar cursor reset @channel` 运维命令）

## raw 层去重

写入 `raw_messages.jsonl` 前检查内存索引或扫描末 N 行（MVP 可全文件 scan，频道量小可接受）。

## jobs 层去重

同一 `dedup_key` 已在 `jobs.jsonl` 则跳过（允许 `status` 更新命令单独处理）。

## 验收

- [ ] 连续两次 `digest` 不产生重复 jobs  
- [ ] `cursor reset` 后重新拉取不 corrupt 已有 jobs
