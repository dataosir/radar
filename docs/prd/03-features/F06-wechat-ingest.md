# F06 · 微信聊天记录接入

> 技术方案：[`../../tech/04-wechat-integration.md`](../../tech/04-wechat-integration.md)  
> 运营 SOP：[`../../ops/03-wechat-sop.md`](../../ops/03-wechat-sop.md)

---

## 1. 用户故事

作为求职者，我订阅了多个**微信群**里的招聘帖，但信息淹没在群聊中。我希望：

1. 把群聊导出或复制重要消息落盘；
2. 自动按 Java/远程等规则过滤；
3. 每天生成一份可扫的 digest。

## 2. 范围

### In Scope（MVP）

| ID | 能力 | 验收 |
|---|---|---|
| F06-01 | 解析微信 PC 导出 TXT | `wechat parse` 写入 `raw_messages.jsonl` |
| F06-02 | 扫描 inbox 文件夹 | `wechat inbox` 解析 `.txt`/`.md` |
| F06-03 | 微信 digest | `wechat digest` 输出 Markdown |
| F06-04 | 去重 | 同消息不重复入库 |
| F06-05 | 配置开关 | `wechat.enabled` 控制 |

### Out of Scope（MVP）

- Hook 个人微信号 / 实时监听
- 自动回复、群发
- 图片 OCR（`[图片]` 仅标记 `has_media`）
- 多用户 SaaS

## 3. 输入格式

### 3.1 PC 导出 TXT

用户操作：微信 PC → 聊天窗口 → 更多 → 导出聊天记录 → TXT

### 3.2 Inbox 手动落盘

路径：`data/wechat_inbox/`

支持纯文本或 YAML frontmatter（见 tech/04）。

## 4. 输出

- 持久化：`data/raw_messages.jsonl`（`source=wechat`）
- 报告：`reports/WECHAT_DIGEST_*.md`

## 5. CLI

```bash
chat_radar wechat parse <file> [--chat 群名]
chat_radar wechat inbox
chat_radar wechat digest [--since 24]
```

## 6. 与 Idea 8 关系

| Idea 8 能力 | F06 覆盖 |
|---|---|
| 群精华日报 | 部分 — MVP 为招聘过滤，非全量摘要 |
| 未回答问题清单 | Phase 2 + LLM |
| 企微 Bot | Phase 3 产品化 |

自用阶段：F06 解决「招聘群噪音过滤」；全量群日报需 Phase 2 LLM 摘要。

## 7. 成功度量

| 指标 | 目标 |
|---|---|
| 解析准确率 | 标准导出格式 ≥ 95% 消息正确切分 |
| 日操作耗时 | 导出 + parse + digest < 5 分钟 |
| 去重 | 重复运行不膨胀 JSONL |
