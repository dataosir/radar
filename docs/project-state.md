# CHAT-RADAR 项目全局状态（project-state）

> **每次开发任务 Step 1 必读；Step 4 必更新。**  
> 详细需求见 `prd/`；架构见 `tech/`。

---

## 元信息

| 项 | 值 |
|---|---|
| 产品 | CHAT-RADAR — Telegram / 微信 多源聊天雷达 |
| 代码版本 | `0.1.0`（`chat_radar.__version__`） |
| 文档框架 | 一人公司全栈：`prd` / `tech` / `ops` + CHANGELOG + 本文件 |
| 更新日期 | 2026-09-01 |
| 母题 | indie-build-log **Idea 8**（digest）· 招聘垂直自用 |

---

## 业务目标（记住这个）

1. **少漏机会**：Telegram 频道 + 微信群招聘帖，每天 5 分钟内扫完。  
2. **少噪音**：默认过滤掉无关帖（非 Java/后端/远程等）。  
3. **可复盘**：结构化落盘，能回答「这周哪些来源质量高」。  
4. **先自用后产品**：验证自己每天用 ≥2 周，再考虑 Bot SaaS。

## 技术选型（记住这个）

| 项 | 选型 | 理由 |
|---|---|---|
| 语言 | Python 3.10+ | 与 tea 栈一致；Telethon 生态成熟 |
| Telegram | **Telethon**（User MTProto） | 招聘频道通常不加 Bot |
| **微信** | **导出 TXT + inbox 落盘** | 不 Hook 个人号；零新依赖 |
| 持久化 | JSON / JSONL 原子写 | 与 tea 一致 |
| 过滤 MVP | 关键词 + 正则规则 | 零 API 成本 |
| 调度 | macOS launchd（后续） | 对齐 tea `ops/` 模式 |

**依赖变更须先汇报并获批**（见根目录 `RULES.md`）。

---

## 当前焦点

**F06 微信 MVP 已实现** — Telegram F01（P0-04）仍为下一步。

## 进行中

| ID | 事项 | 说明 |
|---|---|---|
| P0-01 | 文档体系 | prd / tech / ops / RULES / INDEX ✅ |
| P0-02 | 配置模板 | `chat_radar_config.example.json` ✅ |
| P0-03 | CLI 骨架 + selftest | ✅ 7/7 |
| P0-03b | 一键启动 | `ops/start.sh` ✅ |
| **P0-05** | **F06 微信 ingest** | parse / inbox / digest ✅ |
| P0-04 | F01 Telegram ingest | Telethon — **下一步** |

## 明确不做（现在）

- 多租户 SaaS / 代登录他人账号  
- 微信个人号 Hook / wcferry 实时监听（Phase 3 备选）  
- 未获批前引入 LLM SDK 或数据库  
- Bot API 产品化（自用阶段不需要）

## 下一步计划

1. 配置 `api_id` / `api_hash`，实现 `chat_radar auth` 登录。  
2. 实现 F01：Telegram 增量拉取 → 与微信共用 `raw_messages.jsonl`。  
3. 合并 `digest`：一条命令输出 TG + 微信命中。  
4. 自用 2 周：记录噪音/漏帖率。

---

## 文档健康

| 检查项 | 状态 |
|---|---|
| `docs/INDEX.md` | ✅ 含 F06 / tech/04 / ops/03 |
| `docs/prd/` | ✅ F01–F06 |
| `docs/tech/` | ✅ 00–04 |
| `docs/ops/` | ✅ 01–03 |
