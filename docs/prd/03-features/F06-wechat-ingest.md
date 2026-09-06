# F06 · 微信聊天记录接入

> 技术方案：[`../../tech/04-wechat-integration.md`](../../tech/04-wechat-integration.md)  
> 运营 SOP：[`../../ops/03-wechat-sop.md`](../../ops/03-wechat-sop.md)

---

## 1. 用户故事

作为求职者，我订阅了多个**微信群**里的招聘帖，但信息淹没在群聊中。我希望：

1. 把群聊导出或复制重要消息落盘；
2. 自动按 Java/远程等规则过滤；
3. 每天生成一份可扫的 digest。

## 2. 范围

### In Scope（MVP）

| ID | 能力 | 验收 |
|---|---|---|
| F06-01 | 解析微信 PC 导出 TXT | `wechat parse` 写入 `raw_messages.jsonl` |
| F06-02 | 扫描 inbox 文件夹 | `wechat inbox` 解析 `.txt`/`.md` |
| F06-03 | 微信 digest | `wechat digest` 单源调试；主路径 `digest` 合并 TG+微信 |
| F06-04 | 去重 | 同消息不重复入库 |
| F06-05 | 配置开关 | `wechat.enabled` 控制 |
| F06-06 | macOS 本地库探测 | `wechat locate` 自动发现 wxid 目录 |
| F06-07 | macOS 本地库同步 | `wechat sync` 解密并导入群聊（需密钥文件） |
| F06-08 | 按联系人维度摘要 | `wechat summary` 输出每人一份 MD + index |
| F06-09 | 健康检查与密钥校验 | `wechat status` / `wechat keys validate` |
| F06-10 | 统一 digest（MP-11） | `digest` 自动 inbox + export + sync + 合并双源报告 |
| F06-11 | export 目录半自动 | `wechat import`；digest 前扫描新 TXT |
| F06-12 | inbox/export 游标 | 已处理文件不再重复解析 |
| F06-13 | 分发安装 | `install.sh` + `build.sh` bundle |

### Out of Scope（MVP）

- Hook 个人微信号 / 实时监听
- 自动回复、群发
- 图片 OCR（`[图片]` 仅标记 `has_media`）
- 多用户 SaaS

## 3. 输入格式

### 3.1 PC 导出 TXT

用户操作：微信 PC → 聊天窗口 → 更多 → 导出聊天记录 → TXT

### 3.2 Inbox 手动落盘

路径：`data/wechat_inbox/`

支持纯文本或 YAML frontmatter（见 tech/04）。

## 4. 输出

- 持久化：`data/raw_messages.jsonl`（`source=wechat`）
- 招聘报告：统一 `reports/DIGEST_*.md`（含 telegram + wechat）；`wechat digest` 仍可单源输出
- 联系人摘要：`reports/wechat_contacts/{联系人}.md` + `index.md`

## 5. CLI

```bash
chat_radar wechat parse <file> [--chat 群名]
chat_radar wechat inbox
chat_radar wechat locate          # macOS：探测微信数据目录
chat_radar wechat status          # 健康检查（密钥/zstd/账号）
chat_radar wechat keys derive     # 从 passphrase 派生密钥
chat_radar wechat keys validate   # 校验密钥与账号匹配
chat_radar wechat sync [--since 24] [--scope groups|private|all]  # macOS：解密本地库并导入
chat_radar wechat summary [--since 24] [--scope all] [--from-db] [--person 张三]  # 按联系人生成 MD
chat_radar wechat digest [--since 24]   # 单源调试

# 主路径（合并 TG + 微信）
chat_radar digest [--since 24] [--skip-fetch] [--skip-wechat-inbox]
./start.sh digest
```

## 6. 与 Idea 8 关系

| Idea 8 能力 | F06 覆盖 |
|---|---|
| 群精华日报 | 部分 — MVP 为招聘过滤，非全量摘要 |
| 未回答问题清单 | Phase 2 + LLM |
| 企微 Bot | Phase 3 产品化 |

自用阶段：F06 解决「招聘群噪音过滤」；**联系人维度聊天记录摘要**（L3）通过 `wechat summary` 实现；全量 LLM 群日报需 Phase 2。

## 7. 成功度量

| 指标 | 目标 |
|---|---|
| 解析准确率 | 标准导出格式 ≥ 95% 消息正确切分 |
| 日操作耗时 | 导出 + parse + digest < 5 分钟 |
| 去重 | 重复运行不膨胀 JSONL |
| 联系人摘要 | 纯文本默认开启；`wechat status` 可诊断不完整数据 |

## 8. 已知限制（接受）

- **本地库非 100% 完整**：部分消息为 zstd 压缩、分库分表、未同步到 PC 等，MVP 接受「链路通 + 可诊断」
- **合规边界**：仅读取用户本机已同步数据；不 Hook、不爬服务器、不上传
- **密钥维护**：微信升级后可能需重新提取 passphrase
