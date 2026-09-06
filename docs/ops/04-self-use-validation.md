# 04 · 14 天自用验证（P1-07）

> **目标**：连续 14 天使用 CHAT-RADAR 合并 digest，记录噪音率与漏帖率，决定是否继续迭代或 Kill。  
> 关联：[`02-operator-daily-sop.md`](02-operator-daily-sop.md)、[`prd/05-roadmap-backlog.md`](../prd/05-roadmap-backlog.md) P1-07。

---

## 1. 验证前准备

- [ ] `./install.sh` 或 `./start.sh setup` 完成 TG + 微信配置
- [ ] `./start.sh auth` Telegram 已登录
- [ ] macOS 微信（可选）：菜单 11 密钥 → 9 sync
- [ ] `./start.sh 13` 添加并启用 ≥3 个招聘频道
- [ ] `./start.sh digest --since 24` 能生成 `reports/DIGEST_*.md`

建议安装晨间调度（菜单 12），默认每天 08:30 自动 digest。

---

## 2. 每日记录模板

复制下表到 `data/self_use_log.md`（或 Notion / 表格），每天填一行：

| 日期 | digest 是否跑通 | TG 命中 | 微信命中 | 有用帖数 | 噪音帖数 | 漏帖（手动发现） | 备注 |
|---|---|---|---|---|---|---|---|
| Day 1 | Y/N | | | | | | |
| Day 2 | | | | | | | |
| … | | | | | | | |
| Day 14 | | | | | | | |

**字段说明**：

| 字段 | 定义 |
|---|---|
| 有用帖数 | digest 里你真正会点开的招聘帖 |
| 噪音帖数 | 命中但无关（外包、日结、非 Java 等） |
| 漏帖 | 你在原频道/群里看到、但 digest 没出现的帖 |

**计算公式（第 14 天汇总）**：

```
噪音率 = 噪音帖总数 / (有用帖 + 噪音帖)
漏帖率 = 漏帖总数 / (有用帖 + 漏帖)   # 分母为「应被捕获的相关帖」
```

---

## 3. 通过 / Kill 标准

| 结果 | 条件 | 行动 |
|---|---|---|
| **通过** | 14 天内 ≥10 天愿用 digest 代替翻频道；噪音率 < 40%；漏帖率 < 20% | 继续 Phase 2（stats / LLM 等） |
| **观察** | 噪音 40–50% 或漏帖 20–30% | 调 filter 关键词、缩频道/群列表，再跑 7 天 |
| **Kill** | 每天仍愿手动翻 TG；或噪音 > 50% 且调参 3 次无效 | 停更或改 Concierge 路径（见 roadmap Kill 条件） |

---

## 4. 调参备忘

噪音高时优先：

1. 增加 `filter.exclude_keywords`（如「日结」「纯实习」）
2. 禁用低质量频道（`./start.sh 13` → 禁用）
3. 微信侧收紧 `wechat.watch_chats` 只留招聘群

漏帖高时优先：

1. 检查 TG 是否未登录 / fetch 失败（`./start.sh status`）
2. 微信 sync 是否跳过（密钥失效 → 菜单 11）
3. 扩大 `filter.include_keywords` 或 `--since` 窗口

---

## 5. 14 天结束 checklist

- [ ] 汇总噪音率、漏帖率
- [ ] 更新 [`project-state.md`](../project-state.md)「下一步计划」
- [ ] 在 [`CHANGELOG.md`](../CHANGELOG.md) 记录验证结论（一行即可）
- [ ] 决定是否立项 Phase 2（LLM 摘要 / stats 周报）
