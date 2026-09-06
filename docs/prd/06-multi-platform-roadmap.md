# 06 · 多平台聊天接入与历史摘要路线图

> **产品从 TG-RADAR 升级为 CHAT-RADAR**：不再绑定单一 Telegram，而是统一接入主流 IM，对聊天历史做过滤与摘要。  
> 架构原则见 [`../tech/01-architecture.md`](../tech/01-architecture.md)；微信 MVP 见 [`../tech/04-wechat-integration.md`](../tech/04-wechat-integration.md)。

---

## 1. 产品愿景（升级后）

**CHAT-RADAR** 是面向个人的**多源聊天历史雷达**：

- **接入**：Telegram、微信等主流 IM（API 拉取 / 导出解析 / 手动 inbox）
- **统一**：所有消息归一为 `RawMessage`，写入 `data/raw_messages.jsonl`
- **过滤**：关键词 / 正则规则（招聘垂直为默认 profile，可换）
- **摘要**：按时间窗口生成 Markdown digest；Phase 2 加 LLM 线程级摘要

> 一句话：**把你分散在各 IM 的聊天记录，变成每天 5 分钟能扫完的结构化摘要。**

招聘场景仍是**首个垂直 profile**（Java / 远程 / GraalVM 等），但引擎本身与垂直解耦。

---

## 2. 统一架构（Adapter 模式）

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Telegram   │  │   微信      │  │   QQ/Discord│  │  Slack/…    │
│  Telethon   │  │ export/inbox│  │  export/API │  │  export/API │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┴────────┬───────┴────────────────┘
                                 ▼
                    ingest/* implements Ingestor
                                 ▼
                         RawMessage（core/models）
                                 ▼
                    data/raw_messages.jsonl + cursors.json
                                 ▼
                         filter/RuleEngine
                                 ▼
              reporting/digest → reports/DIGEST_*.md
```

**扩展新平台只需**：

1. 新增 `ingest/<platform>_*.py` 实现 `Ingestor`
2. 在 `runtime/` 增加子命令或纳入统一 `fetch`
3. 配置段 `chat_radar_config.json` 增加 `<platform>` 块
4. 更新本路线图与 `docs/INDEX.md`

---

## 3. 平台矩阵与优先级

| 平台 | 接入方式 | 实时性 | 合规风险 | 优先级 | 状态 |
|---|---|---|---|---|---|
| **Telegram** | Telethon User API | 增量拉取 | 中（User session） | **P0** | ✅ P0-04 |
| **微信** | PC 导出 TXT + inbox 落盘 | 手动/半自动 | 低（用户主动导出） | **P1** | ✅ F06 MVP |
| **QQ** | PC 导出 TXT（格式类似微信） | 手动 | 低 | P2 | 📋 |
| **Discord** | Bot API / 频道导出 JSON | 准实时 | 低（Bot 需加群） | P2 | 📋 |
| **Slack** | Export ZIP / API token | 日级 | 低（workspace 授权） | P3 | 🔮 |
| **WhatsApp** | 聊天导出 .txt | 手动 | 低 | P3 | 🔮 |
| **飞书 / 钉钉** | 开放平台 Bot / 导出 | 准实时 | 中（企业主体） | P3 | 🔮 |
| **iMessage** | macOS 备份解析 | 手动 | 中（本地 only） | P4 | 🔮 |
| **Email** | IMAP 招聘列表 | 日级 | 低 | P4 | 🔮 |

### 3.1 接入方式分类

| 类型 | 说明 | 适用平台 |
|---|---|---|
| **A · API 增量** | 官方/MTProto SDK，游标去重 | Telegram、Discord Bot、Slack |
| **B · 导出解析** | 用户导出文件 → 解析器 | 微信、QQ、WhatsApp |
| **C · Inbox 落盘** | 复制粘贴到约定目录 | 全平台兜底 |
| **D · Concierge** | 用户转发到统一 Bot/服务号 | 产品化 Phase 3 |

**原则**：自用 MVP 优先 **A + B + C**；Hook 个人号客户端（wcferry 等）放 Phase 3 且须单独获批。

---

## 4. 聊天历史「摘要」能力分层

| 层级 | 能力 | 阶段 | 说明 |
|---|---|---|---|
| L1 | **规则过滤** | MVP | 关键词命中 → 进入 digest 列表 |
| L2 | **截断摘要** | MVP | `summary_max_chars` 截取正文前 N 字 |
| L3 | **按会话/联系人聚合** | P1 | 同一联系人合并为时间线块（`wechat summary`） |
| L4 | **LLM 线程摘要** | P2 | OpenAI 兼容 API，每线程 3–5 句摘要 |
| L5 | **跨源日报** | P2 | 一份 `DIGEST_*.md` 含 TG + 微信 + … 带来源标签 |
| L6 | **周报 / 趋势** | P3 | 频道质量、高频词、未读积压 |

---

## 5. 分阶段 Backlog（多平台）

### Phase 0 · 品牌与骨架（当前）

| ID | 事项 | 状态 |
|---|---|---|
| MP-00 | 品牌更名 TG-RADAR → **CHAT-RADAR** | ✅ |
| MP-01 | `RawMessage` + `Ingestor` 协议 | ✅ |
| MP-02 | 微信 F06 MVP（export / inbox / digest） | ✅ |
| MP-03 | 本路线图文档 | ✅ |

### Phase 1 · 双源日用（2 周内）

| ID | 事项 | 依赖 |
|---|---|---|
| MP-10 | F01 Telegram Telethon ingest | P0-04 |
| MP-11 | 统一 `digest`：合并 TG + 微信输出 | MP-10 | ✅ |
| MP-12 | `status` 展示各源消息量 / 游标 | MP-10 |
| MP-13 | QQ 导出解析器（复用微信解析逻辑） | MP-02 |

### Phase 2 · 摘要增强

| ID | 事项 | 说明 |
|---|---|---|
| MP-20 | 按 `chat_title` 线程聚合 | 减少 digest 碎片 |
| MP-21 | LLM 线程摘要（须获批依赖） | 替代 L2 截断 |
| MP-22 | Discord Bot ingest | 开源社区招聘频道 |
| MP-23 | 导出目录 watch（fswatch / polling） | 自动 ingest 新导出 |

### Phase 3 · 产品化试探

| ID | 事项 | 说明 |
|---|---|---|
| MP-30 | 企微 / 飞书 Bot 多群 | 需企业主体 |
| MP-31 | 用户转发 Concierge 路径 | 对齐 Idea 8 主 wedge |
| MP-32 | 付费多源 digest SaaS | Stripe |

---

## 6. 配置演进（多源）

```json
{
  "meta": { "profile_summary": "Java 后端 / 远程优先" },
  "sources": {
    "telegram": { "enabled": true },
    "wechat": { "enabled": true },
    "qq": { "enabled": false },
    "discord": { "enabled": false }
  },
  "telegram": { "api_id": 0, "api_hash": "REPLACE_ME" },
  "wechat": { "enabled": true, "inbox_dir": "data/wechat_inbox" },
  "filter": { "include_keywords": ["Java", "远程"] },
  "report": { "summary_max_chars": 300, "merge_sources": true }
}
```

当前仍用扁平 `wechat` / `telegram` 段；`digest` 在 `wechat.enabled=true` 时自动合并双源（MP-11 ✅）。

---

## 7. 明确不做（跨平台）

| 不做 | 原因 |
|---|---|
| Hook 微信/QQ 个人号（MVP） | 封号与合规；见 tech/04 §1.1 |
| 未授权爬取他人群聊 | 隐私与 ToS |
| 多租户代登录 | 先自用验证 |
| 引入数据库（现阶段） | JSONL 足够；见 tech/03 |

---

## 8. 成功度量（多源阶段）

| 指标 | 目标 |
|---|---|
| 支持源数量 | ≥ 2（TG + 微信）日用 |
| 日 digest 耗时 | < 3 分钟（含双源） |
| 跨源重复率 | < 5%（同帖多群转发） |
| 摘要可读性 | 无需回原文即可判断是否点开 |

---

## 9. 相关文档

- 产品概览：[`00-product-overview.md`](00-product-overview.md)  
- 领域模型：[`01-domain-model.md`](01-domain-model.md)  
- 微信技术：[`../tech/04-wechat-integration.md`](../tech/04-wechat-integration.md)  
- 全局 backlog：[`05-roadmap-backlog.md`](05-roadmap-backlog.md)
