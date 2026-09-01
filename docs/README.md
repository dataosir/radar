# CHAT-RADAR 文档总入口（一人公司全栈迭代框架）

> 本目录是长期 AI 自动化迭代的**唯一知识库入口**。  
> **全库文件清单**见 [`INDEX.md`](INDEX.md)（增删改 docs 内 md 时必同步维护）。  
> 产品「做什么」在 `prd/`；技术「怎么做」在 `tech/`；运营在 `ops/`；当前状态在 `project-state.md`。  
> **实现铁律**权威源在仓库根目录 [`../RULES.md`](../RULES.md)。

---

## 分层一览

| 层 | 路径 | 职责 |
|---|---|---|
| 铁律 | [`../RULES.md`](../RULES.md) | 依赖 / 分层 / KISS / 安全红线 / 文档同步 |
| 清单 | [`INDEX.md`](INDEX.md) | **权威文件表**（一行一文） |
| 产品 | [`prd/`](prd/README.md) | 定位、领域模型、日常流程、F01–F05、NFR、backlog |
| 技术 | [`tech/`](tech/README.md) | 工程规范、架构、模块契约、持久化 |
| 运营 | [`ops/`](ops/README.md) | 日 SOP、调度、凭证管理 |
| 状态 | [`project-state.md`](project-state.md) | 当前焦点与下一步（每次迭代必读必写） |
| 变更 | [`CHANGELOG.md`](CHANGELOG.md) | 已发生事实；条目宜标注 Fxx / tech |
| 归档 | [`archive/`](archive/README.md) | 历史实验；只读 |

---

## 每次开发任务的 4 步闭环（强制）

1. **Step 1 · Sync** — 读 `project-state.md` + 相关 `prd/` / `tech/`  
2. **Step 2 · Plan** — 输出 Plan（PRD 是否调整、技术方案、触及文件、不做事项），**确认后再动手**  
3. **Step 3 · Code & Doc** — 实现 + 同步 prd/tech；动 docs 清单 → 更新 `INDEX.md`  
4. **Step 4 · Log** — 追加 `CHANGELOG.md`，更新 `project-state.md`

---

现行 backlog：[`prd/05-roadmap-backlog.md`](prd/05-roadmap-backlog.md)。
