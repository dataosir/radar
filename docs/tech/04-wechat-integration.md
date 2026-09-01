# 04 · 微信接入技术方案

> 产品需求见 [`../prd/03-features/F06-wechat-ingest.md`](../prd/03-features/F06-wechat-ingest.md)。  
> 运营 SOP 见 [`../ops/03-wechat-sop.md`](../ops/03-wechat-sop.md)。

---

## 1. 背景与约束

| 维度 | 决策 |
|---|---|
| 母题 | indie-build-log **Idea 8**（社群群日报）· 招聘垂直自用变体 |
| 载体 | **不 Hook 个人微信号**；MVP 用导出解析 + inbox 手动落盘 |
| 合规 | 仅处理用户**主动导出/粘贴**的聊天内容；不爬未授权群 |
| 语言 | Python 3.10+，**零新增依赖**（纯 stdlib 解析） |
| 与 TG 关系 | 共享 `filter` + `reporting`；仅 `ingest` 层分源 |

### 1.1 为什么不 Hook 微信个人号

| 方案 | 可行性 | 风险 | MVP |
|---|---|---|---|
| PC 客户端 Hook（wcferry 等） | 技术可做 | 封号、ToS、仅 Windows | ❌ Phase 3 备选 |
| 本地 DB 解密读取 | 技术可做 | 密钥轮换、Mac/Win 差异大 | ❌ |
| **PC 导出 TXT 解析** | ✅ | 需用户手动导出 | ✅ **已实现** |
| **inbox 文件夹落盘** | ✅ | 用户复制粘贴有摩擦 | ✅ **已实现** |
| 企业微信 Bot | 官方 API | 需企业主体 | Phase 3 产品化 |
| 用户转发到服务号 | 合规 | 需公众号/企微 | Concierge 验证路径 |

---

## 2. 多源架构

```
                    ┌─────────────────┐
                    │  chat_radar_config │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
  ingest/telegram     ingest/wechat_*      ingest/...（未来）
  (Telethon P0-04)    export + inbox
         │                   │
         └─────────┬─────────┘
                   ▼
            RawMessage（统一模型）
                   ▼
         data/raw_messages.jsonl
                   ▼
            filter/RuleEngine
                   ▼
         reporting/digest → reports/
```

### 2.1 统一模型 `RawMessage`

| 字段 | Telegram | 微信 |
|---|---|---|
| `source` | `telegram` | `wechat` |
| `source_id` | channel_id | chat 哈希 |
| `message_id` | TG msg id | 内容哈希 |
| `sender` | — | 发言人昵称 |
| `chat_title` | channel title | 群名 |
| `link` | t.me 链接 | 导出文件 / inbox 路径 |

向后兼容：旧 JSONL 无 `source` 字段时视为 `telegram`。

---

## 3. 微信 MVP 实现

### 3.1 导出 TXT 解析（`wechat_export.py`）

**输入**：微信 PC 端「导出聊天记录」生成的 `.txt`

**格式**（每段消息）：

```
2026-09-01 10:30:15 张三
消息正文（可多行）

2026-09-01 10:31:00 李四
[图片]
```

**命令**：

```bash
python -m chat_radar wechat parse data/wechat_exports/招聘群.txt --chat "Java招聘群"
```

### 3.2 Inbox 落盘（`wechat_inbox.py`）

**用途**：手机复制重要群消息 → 粘贴到 `data/wechat_inbox/*.md`

**可选 YAML frontmatter**：

```markdown
---
chat: Java招聘群
sender: HR小王
date: 2026-09-01T10:30:00+08:00
---
招聘 Java 后端，远程优先
```

**命令**：

```bash
python -m chat_radar wechat inbox
```

### 3.3 微信 Digest

```bash
python -m chat_radar wechat digest --since 24
```

输出：`reports/DIGEST_wechat_YYYYMMDD_HHMMSS.md`

---

## 4. 配置段

```json
"wechat": {
  "enabled": true,
  "inbox_dir": "data/wechat_inbox",
  "export_dir": "data/wechat_exports",
  "default_chat": "招聘群"
}
```

`wechat.enabled=false` 时，所有 `wechat *` 命令拒绝执行。

---

## 5. 模块映射

| 模块 | 职责 |
|---|---|
| `core/models.py` | `RawMessage` 统一模型 |
| `ingest/wechat_export.py` | PC 导出 TXT 解析 |
| `ingest/wechat_inbox.py` | inbox 文件夹扫描 |
| `ingest/persist.py` | JSONL 追加 + 去重 |
| `runtime/wechat_runner.py` | CLI 编排 |

---

## 6. Phase 路线图

| Phase | 能力 | 依赖 | 状态 |
|---|---|---|---|
| **F06 MVP** | 导出解析 + inbox + digest | 无 | ✅ |
| F06-P2 | 导出后自动 watch 目录 | 无 | 📋 |
| F06-P3 | wcferry 实时监听（Windows） | `wcferry` 须获批 | 🔮 |
| F06-P4 | 企微 Bot 多群（产品化） | 企业主体 | 🔮 |

---

## 7. 与 Telegram 路径的合并点

未来 `digest` 总命令应：

1. `fetch`（TG）+ `wechat inbox`（微信）
2. 合并 `raw_messages.jsonl`
3. 统一过滤 → 一份 `DIGEST_*.md`（带来源标签）

当前：**分命令输出**（`digest` vs `wechat digest`），降低 P0-04 阻塞风险。

---

## 8. 安全红线（同步 RULES.md）

1. 不提交导出文件、inbox 内容到 git（已在 `.gitignore`）
2. 不实现自动登录微信、不存储微信密码
3. 日志 `redact_bodies=true` 时可脱敏消息正文
