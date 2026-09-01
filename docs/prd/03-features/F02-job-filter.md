# F02 · 招聘帖过滤

## 目标

从 raw 消息中筛出与**我的求职 profile** 相关的招聘帖。

## MVP：规则引擎

### 正向词（include）

配置 `filter.include_keywords[]`，命中任一即 **候选**。

默认示例（可在配置中改）：

```
Java, Spring, 后端, Backend, GraalVM, Native Image,
远程, Remote, 全栈, 架构师, JVM, Kotlin
```

### 排除词（exclude）

命中任一则 **否决**（优先级高于 include）：

```
实习 only, 外包刷量, 日结, 刷单, 代理招聘
```

### 正则（可选）

`filter.include_patterns[]` — 如 `(?i)java.*(remote|远程)`

## Phase 2：LLM 评分

- 输入：候选帖正文 + 我的 profile 摘要  
- 输出：0–1 相关度 + 一句理由  
- 阈值：`filter.llm_min_score`（默认 0.7）  
- **须单独获批 API key 与依赖**

## 输出

- 命中帖写入 `data/jobs.jsonl`（`status: new`）
- 未命中不写 jobs，但 raw 仍保留（可复盘调规则）

## 验收

- [ ] 含 `Java` + `远程` 的帖命中  
- [ ] 含排除词 `日结` 的帖不命中  
- [ ] `matched_rules` 字段记录命中规则名
