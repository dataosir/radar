# 05 · Roadmap & Backlog

> 现行迭代优先级。**完成一项勾一项，并更新 `project-state.md`。**

---

## Phase 0 · 立项（2026-09-01）

| ID | 事项 | 状态 |
|---|---|---|
| P0-01 | 文档体系 prd/tech/ops + RULES + INDEX | ✅ |
| P0-02 | 配置模板 + .gitignore | ✅ |
| P0-03 | CLI 骨架 + selftest 占位 | ✅ |
| P0-04 | F01 Telethon auth + fetch | ⬜ 下一步 |

## Phase 1 · 自用 MVP（目标：1 周内可日用）

| ID | 事项 | 依赖 | 状态 |
|---|---|---|---|
| P1-01 | F01 频道增量拉取 | P0-04 | ⬜ |
| P1-02 | F02 关键词过滤 | P1-01 | ⬜ |
| P1-03 | F03 去重游标 | P1-01 | ⬜ |
| P1-04 | F04 Markdown digest | P1-02, P1-03 | ⬜ |
| P1-05 | `channels` 子命令 | P1-01 | ⬜ |
| P1-06 | launchd 晨间调度 | P1-04 | ⬜ |
| P1-07 | 自用 14 天记录（噪音/漏帖） | P1-04 | ⬜ |

## Phase 2 · 体验增强

| ID | 事项 | 状态 |
|---|---|---|
| P2-01 | F05 Saved Messages 提醒 | 🔮 |
| P2-02 | LLM 相关度评分 | 🔮 须获批 |
| P2-03 | `stats` 频道质量周报 | 🔮 |
| P2-04 | `star` / `dismiss` 反馈闭环 | 🔮 |

## Phase 3 · 产品化试探（仅当 Phase 1 验证通过）

| ID | 事项 | 说明 |
|---|---|---|
| P3-01 | Bot API 多用户 | 对齐 Idea 8-D2 |
| P3-02 | 付费 digest SaaS | Stripe；与 GraalVM 主线并行 |

## Kill 条件

- 自用 2 周：每天仍愿手动翻 TG 原频道 → **工具无价值，停更**  
- Telethon 频繁封号 / 限流不可接受 → 改「转发到 Bot」Concierge 路径  
- 过滤调参 3 次仍噪音 > 50% → 先上 LLM 或缩频道列表
