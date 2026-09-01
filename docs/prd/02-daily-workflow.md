# 02 · 日循环工作流

## 时间线（建议）

| 时刻 | 动作 | 命令 | 说明 |
|---|---|---|---|
| 08:30 | 晨间 digest | `chat_radar digest` | launchd 或手动；拉取 + 过滤 + 出报告 |
| 12:30 | 午间补扫（可选） | `chat_radar digest` | 招聘频道白天更新多时可开 |
| 20:00 | 回顾 | 打开 `reports/` 最新 MD | 标记 `starred`（Phase 2 CLI） |
| 每周日 | 频道质量复盘 | `chat_radar stats` | 哪个频道命中率高 / 噪音大 |

## 命令映射（规划）

| 命令 | 说明 | PRD |
|---|---|---|
| `auth` | 首次 Telegram 登录，生成 session | F01 |
| `channels list` | 列出配置频道 + 游标状态 | F01 |
| `fetch` | 仅拉取，不出报告 | F01 |
| `digest` | 拉取 + 过滤 + 出 MD 报告 | F01–F04 |
| `status` | 今日拉取/命中统计 | F04 |
| `config list/get/set` | 配置读写 | — |
| `selftest` | 离线自测（不联网） | NFR |

## 典型一日

```bash
# 早上一条命令
chat_radar digest

# 输出示例
# → 拉取 3 个频道，新增 47 条，命中 5 条
# → 报告：reports/DIGEST_20260901_083012.md
```

打开报告，逐条点链接判断是否值得跟进。误报记在纸上，周末调 `filter.include` / `filter.exclude`。

## 与 ops 的衔接

- 凭证管理：[`../ops/01-credentials-sop.md`](../ops/01-credentials-sop.md)  
- 日 SOP：[`../ops/02-operator-daily-sop.md`](../ops/02-operator-daily-sop.md)
