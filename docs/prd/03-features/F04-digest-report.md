# F04 · Digest 报告

## 目标

生成人类可读的每日 Markdown 摘要，5 分钟内扫完。

## 输出路径

`reports/DIGEST_YYYYMMDD_HHMMSS.md`

## 报告结构

```markdown
# CHAT-RADAR Digest · 2026-09-01 08:30

## 概览
- 扫描频道：3
- 新消息：47
- 命中招聘：5

## 命中列表（新 → 旧）

### 1. [Java 远程 · 某公司名称]
- **频道**：@remote_jobs_cn
- **时间**：2026-09-01 07:12
- **规则**：include:Java, include:远程
- **链接**：https://t.me/...
- **摘要**：正文前 300 字…

---
```

## 排序

默认按 `date` 降序（最新的在上面）。

## 非目标

- 不做 HTML / PDF 导出（Phase 2 可加）  
- 不自动发 Telegram（见 F05）

## 验收

- [ ] `digest` 后 `reports/` 有新文件  
- [ ] 每条命中含链接 + 命中规则 + 摘要
