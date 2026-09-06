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
| 更新日期 | 2026-09-06 |
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
| **微信** | **inbox + export + macOS 本地库** | 不 Hook 个人号；密钥外部提取 |
| 持久化 | JSON / JSONL 原子写 | 与 tea 一致 |
| 过滤 MVP | 关键词 + 正则规则 | 零 API 成本 |
| 调度 | macOS launchd | `ops/install_launchd.sh` |

**依赖变更须先汇报并获批**（见根目录 `RULES.md`）。

---

## 当前焦点

**可分发双源自用 MVP** — 一键 `install.sh` + `start.sh` 菜单闭环；下一步 14 天自用验证。

## 进行中

| ID | 事项 | 说明 |
|---|---|---|
| P0-01 | 文档体系 | prd / tech / ops / RULES / INDEX ✅ |
| P0-02 | 配置模板 | `chat_radar_config.example.json` ✅ |
| P0-03 | CLI 骨架 + selftest | ✅ 23/23 |
| P0-03b | 一键启动 + 引导菜单 | 根目录 `start.sh`（13 项菜单）✅ |
| P0-03c | 一键打包 | `build.sh` + `install.sh` + bundle ✅ |
| **P0-04** | **F01 Telegram ingest** | auth / fetch / digest / cursors ✅ |
| P0-05 | F06 微信 ingest | parse / inbox / import / sync / summary ✅ |
| **P0-06** | **F06-P2.5 macOS 本地库** | locate / sync ✅（需外部密钥工具） |
| **P0-07** | **F06-08 联系人 MD 摘要** | `wechat summary` ✅ |
| **P0-08** | **F06-09 健壮性** | status / keys validate / 读取统计 ✅ |
| **P0-09** | **MP-11 统一 digest** | inbox + export + sync + TG fetch → 一份报告 ✅ |
| **P0-10** | **setup 微信引导** | 4/4 步骤 ✅ |
| **P1-05** | **`channels` 增删启禁** | CLI + 菜单 13 ✅ |
| **P1-06** | **launchd 晨间调度** | 模板 + install 脚本 ✅ |
| **P1-07** | **14 天自用验证模板** | `ops/04-self-use-validation.md` ✅ |
| **P1-08** | **交互节点日志** | `interactions.jsonl` + `start_menu.log` ✅ |

## 明确不做（现在）

- 多租户 SaaS / 代登录他人账号  
- 微信个人号 Hook / wcferry 实时监听（Phase 3 备选）  
- 未获批前引入 LLM SDK 或数据库  
- Bot API 产品化（自用阶段不需要）

可执行脚本在仓库根 [`../../ops/`](../../ops/)（密钥提取、launchd 安装等）。

## 下一步计划

1. 解压 bundle → `./install.sh` → 给他人验证安装路径。
2. 按 [`04-self-use-validation.md`](ops/04-self-use-validation.md) 跑 14 天合并 digest（P1-07）。
3. 根据噪音/漏帖率决定是否 Phase 2（LLM / stats）。

---

## 文档健康

| 检查项 | 状态 |
|---|---|
| `docs/INDEX.md` | ✅ 含 F06 / tech/04 / ops/03 |
| `docs/prd/` | ✅ F01–F06 |
| `docs/tech/` | ✅ 00–04 |
| `docs/ops/` | ✅ 01–03 |
| `ops/` 脚本 | ✅ extract / derive / launchd |
