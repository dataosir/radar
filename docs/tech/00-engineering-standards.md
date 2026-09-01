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
python -m tg_radar selftest
ruff check .                # 配置 ruff 后
python -m compileall -q tg_radar
```

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
