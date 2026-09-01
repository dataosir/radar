# 00 · 产品概览

## 1. 产品定位

**CHAT-RADAR**（原 TG-RADAR）是面向**个人用户**的**多源聊天历史雷达**，不是聊天机器人、不是 HR 工具、不是群发 Bot。

引擎默认回答是「不相关」。只有当消息命中**过滤规则**（未来可加 LLM 摘要），才进入每日 digest。

> 一句话：不替你聊天，只回答——**今天哪些聊天内容值得我花 30 秒看完？**

**首个垂直场景**仍是招聘信息（Telegram 频道 + 微信招聘群），但架构已支持扩展至 QQ、Discord、Slack 等主流 IM。

## 2. 目标用户与场景

| 角色 | 场景 |
|---|---|
| **我（founder / 求职者）** | 订阅多个 TG 频道 + 加入多个微信招聘群，信息过载 |
| 未来：同类用户 | 多 IM 信息整理、社群日报、垂直 digest 产品 |

## 3. 核心价值主张

1. **多源接入**：Telegram API 增量拉取；微信/QQ 导出解析 + inbox 落盘（见 [`06-multi-platform-roadmap.md`](06-multi-platform-roadmap.md)）。  
2. **统一模型**：`RawMessage` 归一化，共享过滤与摘要管线。  
3. **可配置过滤**：关键词 / 正则；招聘 profile 为默认，可替换。  
4. **可审计**：每条入选消息带来源、命中规则、摘要。  
5. **低维护**：单机 CLI + launchd；无数据库。

## 4. 非目标（明确不做）

| 不做 | 原因 |
|---|---|
| 代投简历 / 自动私信 HR | 产品边界；合规风险 |
| 爬取未订阅频道 / 未授权群 | ToS / 隐私 |
| Hook 微信个人号（MVP 阶段） | 封号风险；见 tech/04 |
| 多租户 SaaS（现阶段） | 先验证自用价值 |
| 保证拿到 offer | 工具只整理信息，非结果承诺 |

## 5. 成功度量（自用阶段）

| 指标 | 说明 | 目标 |
|---|---|---|
| 日扫描耗时 | `digest` 命令端到端 | < 3 分钟（双源） |
| 噪音率 | digest 里「点开即关」占比 | < 30% |
| 漏帖率 | 事后发现相关消息未进 digest | < 5% |
| 连续使用 | 是否每天主动跑 | ≥ 14 天 |
| 支持源数 | 实际日用的 IM 平台 | ≥ 2 |

## 6. 系统边界图

```
多源 ingest（Telegram / 微信 / …）
        ↓  RawMessage
规则过滤(F02) + 去重(F03)
        ↓
Digest 报告(F04) → reports/
        ↓
可选提醒(F05)
配置 · selftest 横切全链路
```

## 7. 相关文档

- 多平台路线图：[`06-multi-platform-roadmap.md`](06-multi-platform-roadmap.md)  
- 领域模型：[`01-domain-model.md`](01-domain-model.md)  
- 日循环：[`02-daily-workflow.md`](02-daily-workflow.md)  
- 技术架构：[`../tech/01-architecture.md`](../tech/01-architecture.md)  
- 全局状态：[`../project-state.md`](../project-state.md)
