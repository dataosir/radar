# 00 · 工程规范

> 技术层硬规矩。文档总入口见 [`../README.md`](../README.md)；全库清单见 [`../INDEX.md`](../INDEX.md)。

## 技术迭代铁律（摘要）

实现、重构与架构变更必须遵守仓库根目录 [`../../RULES.md`](../../RULES.md)。要点：

| 红线 | 要求 |
|---|---|
| 依赖 | **禁止擅自**引入第三方库；已批准：`telethon`；LLM SDK 须单独获批 |
| 分层 | 严禁跨层调用与循环依赖 |
| KISS | 只做需求内核心逻辑 |
| 异常 | 核心路径显式处理；**禁止空 catch** |
| 可观测 | 关键流程结构化日志 → `logs/` |
| 文档同步 | 接口/数据结构变更 → 更新 `docs/tech/` + `INDEX.md` |
| 安全 | session / api_hash 不入库 |

## 提交前自查

```bash
python -m chat_radar selftest
ruff check .                # 配置 ruff 后
python -m compileall -q chat_radar
```

## Git hooks（运行时产物拦截）

`ops/git-hooks/pre-commit` 会在 commit 前检查 staged 文件，**拒绝**提交以下路径（含 `git add -f` 强推）：

| 拦截路径 | 原因 |
|---|---|
| `reports/` | digest / 联系人 MD 等运行时产物 |
| `data/` | JSONL、微信密钥、游标 |
| `logs/` | 运行日志、交互日志 |
| `chat_radar_config.json` | 本地配置 |
| `*.session` | Telegram 会话 |
| `.env` / `secrets/` | 凭证 |

安装：`./ops/install_git_hooks.sh`（`install.sh` 已自动调用）。

## 自动 commit 消息（Agent 钩子）

- 生成器：`.cursor/hooks/generate_commit_message.py`
- **变更范围规则**：`.cursor/hooks/commit_scope.json`（可编辑，无需改 Python）
  - `groups[]`：`patterns`（glob）、`label`、`priority`（越小越靠前）、可选 `item` 模板（如 `{module}/{basename}`）
  - `fallback`：未匹配文件按 `path_prefix` + `depth` 自动分组
  - 排序：`priority` → staged 中首次出现顺序 → 标签字母序
- 新增目录/模块时：在 JSON 加一条 rule，或依赖 fallback 自动归类

## 代码风格

- **配置走 `config_store`**：`cfg.get("段.键", 默认)`，不硬编码阈值  
- **文件写入走 `core.utils` 原子写**  
- **CLI 不放业务逻辑**：`runtime/cli.py` 只解析参数，逻辑在 `runner.py` 与子包  
- **注释与文案中文**  
- 行宽 110

## 新增模块放哪里

```
runtime (L4)  → CLI / runner
reporting (L3)→ Markdown digest（只呈现）
filter (L2)   → 规则 / LLM 评分
ingest (L2)   → Telethon 拉取
core/config (L0)→ 路径、原子写、日志、配置
```

依赖方向严格单向向下。

## 加新参数的顺序

1. `config_store.py` `DEFAULTS` 加默认值  
2. 模块内 `cfg.get(...)` 读取  
3. `selftest.py` 补断言  
4. 若影响行为，更新对应 PRD Fxx
