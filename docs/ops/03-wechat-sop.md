# 03 · 微信 ingest 运营 SOP

> 技术背景见 [`../tech/04-wechat-integration.md`](../tech/04-wechat-integration.md)。

---

## 1. 目录准备

```bash
mkdir -p data/wechat_inbox data/wechat_exports
```

确保 `chat_radar_config.json` 中：

```json
"wechat": { "enabled": true }
```

---

## 2. 路径 A：PC 导出（推荐批量）

1. 打开微信 PC 客户端，进入目标招聘群
2. 聊天窗口右上角 `…` → **导出聊天记录**
3. 选择 **TXT**，保存到 `data/wechat_exports/招聘群.txt`
4. 运行：

```bash
python -m chat_radar wechat parse data/wechat_exports/招聘群.txt --chat "Java招聘群"
python -m chat_radar wechat digest --since 168
```

> Mac 版微信导出能力因版本而异；若无法导出，用路径 B。

---

## 3. 路径 B：Inbox 手动落盘（推荐日常）

1. 手机/PC 复制重要招聘消息
2. 新建 `data/wechat_inbox/2026-09-01-hr.md`：

```markdown
---
chat: Java招聘群
sender: HR小王
date: 2026-09-01T10:30:00+08:00
---
招聘 Java 后端，Spring Boot，远程优先
```

3. 运行：

```bash
python -m chat_radar wechat inbox
python -m chat_radar wechat digest
```

---

## 4. 日循环（与 Telegram 并行）

| 时间 | 动作 |
|---|---|
| 晨间 | `wechat inbox`（若有新粘贴） |
| 周度 | 导出群聊 → `wechat parse` |
| 随时 | `wechat digest --since 24` |

Telegram 路径就绪后，两条线可合并为统一 `digest`。

---

## 5. 隐私与 git

以下目录**不得提交**：

- `data/wechat_inbox/`
- `data/wechat_exports/`
- `data/raw_messages.jsonl`（含聊天内容）

---

## 6. 故障排查

| 现象 | 处理 |
|---|---|
| `wechat.enabled 未开启` | 配置 `wechat.enabled: true` |
| 解析 0 条 | 检查导出格式是否为 `YYYY-MM-DD HH:MM:SS 昵称` |
| digest 无命中 | 调 `filter.include_keywords` |
| 重复消息 | 正常 — dedup 会跳过；无需手动删 JSONL |

---

## 7. 不做的事

- ❌ 不提供微信扫码登录脚本
- ❌ 不代管他人微信号
- ❌ 不自动爬群（无授权）
