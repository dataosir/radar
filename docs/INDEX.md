# TG-RADAR 文档总索引（权威清单）

> **增删改 `docs/` 内任意 `.md` 时，必须同步更新本文件。**  
> 入口与 4 步闭环见 [`README.md`](README.md)；实现铁律见 [`../RULES.md`](../RULES.md)。

---

## 根（`docs/`）

| 文件 | 职责 |
|---|---|
| [`README.md`](README.md) | 知识库入口 + 分层说明 + 4 步闭环 |
| [`INDEX.md`](INDEX.md) | **本文件**：全库文件清单权威源 |
| [`project-state.md`](project-state.md) | 当前版本 / 进行中 / 下一步（必读必写） |
| [`CHANGELOG.md`](CHANGELOG.md) | 变更日志（关联 Fxx / tech） |

仓库根另有 [`../RULES.md`](../RULES.md)（实现铁律权威源，不在 `docs/` 内）。

---

## 产品层 `prd/`

| 文件 | 职责 | 关联 |
|---|---|---|
| [`prd/README.md`](prd/README.md) | PRD 层导读与 F01–F05 表 | — |
| [`prd/00-product-overview.md`](prd/00-product-overview.md) | 定位 / 非目标 / 用户场景 | — |
| [`prd/01-domain-model.md`](prd/01-domain-model.md) | 消息、招聘帖、游标、digest | — |
| [`prd/02-daily-workflow.md`](prd/02-daily-workflow.md) | 日循环时间线与命令映射 | — |
| [`prd/03-features/F01-channel-ingest.md`](prd/03-features/F01-channel-ingest.md) | Telegram 频道增量拉取 | F01 |
| [`prd/03-features/F02-job-filter.md`](prd/03-features/F02-job-filter.md) | 关键词 / 规则过滤 | F02 |
| [`prd/03-features/F03-dedup-cursor.md`](prd/03-features/F03-dedup-cursor.md) | 去重与游标 | F03 |
| [`prd/03-features/F04-digest-report.md`](prd/03-features/F04-digest-report.md) | Markdown digest 输出 | F04 |
| [`prd/03-features/F05-alert-notify.md`](prd/03-features/F05-alert-notify.md) | 即时提醒（可选） | F05 |
| [`prd/04-nfr-constraints.md`](prd/04-nfr-constraints.md) | 非功能硬约束 | NFR |
| [`prd/05-roadmap-backlog.md`](prd/05-roadmap-backlog.md) | 现行迭代 backlog | backlog |

---

## 技术层 `tech/`

| 文件 | 职责 | 关联 |
|---|---|---|
| [`tech/README.md`](tech/README.md) | 技术层导读 | — |
| [`tech/RULES.md`](tech/RULES.md) | 指针 → 根 `RULES.md`（防双源） | 铁律 |
| [`tech/00-engineering-standards.md`](tech/00-engineering-standards.md) | 工程规范 + 铁律摘要 | tech/00 |
| [`tech/01-architecture.md`](tech/01-architecture.md) | 分层 / 数据流 / 技术选型 | tech/01 |
| [`tech/02-api-specs.md`](tech/02-api-specs.md) | CLI / 模块调用契约 | tech/02 |
| [`tech/03-db-schema.md`](tech/03-db-schema.md) | JSON/JSONL 持久化 | tech/03 |

---

## 运营层 `ops/`

| 文件 | 职责 |
|---|---|
| [`ops/README.md`](ops/README.md) | 运营层导读 |
| [`ops/01-credentials-sop.md`](ops/01-credentials-sop.md) | Telegram API 凭证与 session 管理 |
| [`ops/02-operator-daily-sop.md`](ops/02-operator-daily-sop.md) | 每日扫帖 SOP |

仓库根 [`../ops/`](../ops/) 放 launchd / cron 可执行脚本（后续）。

---

## 归档 `archive/`（只读）

| 文件 | 职责 |
|---|---|
| [`archive/README.md`](archive/README.md) | 归档说明 |

现行 backlog 以 [`prd/05-roadmap-backlog.md`](prd/05-roadmap-backlog.md) 为准。
