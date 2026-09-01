# TG-RADAR 项目全局状态（project-state）

> **每次开发任务 Step 1 必读；Step 4 必更新。**  
> 详细需求见 `prd/`；架构见 `tech/`。

---

## 元信息

| 项 | 值 |
|---|---|
| 产品 | TG-RADAR — Telegram 招聘信息个人雷达 |
| 代码版本 | `0.1.0`（`tg_radar.__version__`） |
| 文档框架 | 一人公司全栈：`prd` / `tech` / `ops` + CHANGELOG + 本文件 |
| 更新日期 | 2026-09-01 |
| 母题 | indie-build-log **Idea 8-D2**（Telegram digest）· 招聘垂直自用 |

---

## 业务目标（记住这个）

1. **少漏机会**：已订阅频道的新招聘帖，每天 5 分钟内扫完。  
2. **少噪音**：默认过滤掉无关帖（非 Java/后端/远程等）。  
3. **可复盘**：结构化落盘，能回答「这周哪些频道质量高」。  
4. **先自用后产品**：验证自己每天用 ≥2 周，再考虑 Bot SaaS。

## 技术选型（记住这个）

| 项 | 选型 | 理由 |
|---|---|---|
| 语言 | Python 3.10+ | 与 tea 栈一致；Telethon 生态成熟 |
| Telegram | **Telethon**（User MTProto） | 招聘频道通常不加 Bot；自用读已订阅频道 |
| 持久化 | JSON / JSONL 原子写 | 与 tea 一致；无 SQL 运维负担 |
| 过滤 MVP | 关键词 + 正则规则 | 零 API 成本；LLM 评分放 Phase 2 |
| 调度 | macOS launchd（后续） | 对齐 tea `ops/` 模式 |
| LLM（可选） | OpenAI 兼容 API | 相关度打分；**须单独获批依赖** |

**依赖变更须先汇报并获批**（见根目录 `RULES.md`）。

---

## 当前焦点

**立项 + 文档骨架 + 包结构** — 尚未实现 Telethon ingest。

## 进行中

| ID | 事项 | 说明 |
|---|---|---|
| P0-01 | 文档体系 | prd / tech / ops / RULES / INDEX ✅ |
| P0-02 | 配置模板 | `tg_radar_config.example.json` ✅ |
| P0-03 | CLI 骨架 | `python -m tg_radar --help` / `selftest` ✅ |
| P0-03b | 一键启动 | `ops/start.sh`（venv + 配置 + selftest）✅ |
| P0-04 | F01 ingest | Telethon 增量拉取 — **下一步** |

## 明确不做（现在）

- 多租户 SaaS / 代登录他人账号  
- 自动投递简历 / 自动回复 HR  
- 微信/QQ 适配（见 Idea 8 主 wedge）  
- 未获批前引入 LLM SDK 或数据库  
- Bot API 产品化（自用阶段不需要）

## 下一步计划

1. 配置 `api_id` / `api_hash`，实现 `tg_radar auth` 登录。  
2. 实现 F01：按频道列表增量拉取 → `data/raw_messages.jsonl`。  
3. 实现 F02–F04：规则过滤 → 去重 → 输出首份 `reports/DIGEST_*.md`。  
4. 自用 2 周：记录「节省时间 vs 漏帖率」，再决定是否对齐 Idea 8-D2 产品化。

---

## 文档健康

| 检查项 | 状态 |
|---|---|
| `docs/INDEX.md` | ✅ 已建 |
| `docs/prd/` | ✅ F01–F05 框架 |
| `docs/tech/` | ✅ 00–03 |
| `docs/ops/` | ✅ 01–02 |
