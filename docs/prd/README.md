# PRD 层导读

> 产品「做什么」。技术实现见 [`../tech/`](../tech/README.md)。

## F01–F05 一览

| ID | 名称 | 一句话 | 状态 |
|---|---|---|---|
| F01 | 频道增量拉取 | 从已订阅 Telegram 频道读新消息 | ✅ |
| F02 | 招聘帖过滤 | 关键词 / 正则 / 排除词 | ✅ |
| F03 | 去重与游标 | `channel_id + message_id` 幂等 | ✅ |
| F04 | Digest 报告 | 每日 Markdown 摘要 | ✅ |
| F05 | 即时提醒 | 高匹配帖推送（Saved Messages / 终端） | 🔮 Phase 2 |

## 阅读顺序

1. [`00-product-overview.md`](00-product-overview.md) — 定位与非目标  
2. [`01-domain-model.md`](01-domain-model.md) — 核心概念  
3. [`02-daily-workflow.md`](02-daily-workflow.md) — 你怎么每天用  
4. `03-features/Fxx` — 各功能规格  
5. [`05-roadmap-backlog.md`](05-roadmap-backlog.md) — 迭代优先级
