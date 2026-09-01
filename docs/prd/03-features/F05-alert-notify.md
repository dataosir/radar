# F05 · 即时提醒（Phase 2）

## 目标

高匹配帖在 `digest` 之外**即时**通知，减少漏看。

## 候选方案

| 方案 | 优点 | 缺点 | 优先级 |
|---|---|---|---|
| 转发到 Saved Messages | 零额外依赖 | 仍要打开 TG | P1 |
| macOS 通知 (`osascript`) | 本地即时 | 仅 macOS | P2 |
| 邮件摘要 | 跨设备 | 延迟 | P3 |
| 独立 Bot 推送到私聊 | 产品化路径 | 需 Bot Token | 未来 SaaS |

## 触发条件

- `filter.alert_rules[]` — 比 digest 更严的规则（如同时命中 `GraalVM` + `远程`）  
- 或 `score >= filter.alert_min_score`（LLM 阶段）

## 状态

🔮 **未启动** — 自用 MVP 先跑通 F01–F04，观察是否真需要即时提醒。
