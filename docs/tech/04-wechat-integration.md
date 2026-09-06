# 04 · 微信接入技术方案

> 产品需求见 [`../prd/03-features/F06-wechat-ingest.md`](../prd/03-features/F06-wechat-ingest.md)。  
> 运营 SOP 见 [`../ops/03-wechat-sop.md`](../ops/03-wechat-sop.md)。

---

## 1. 背景与约束

| 维度 | 决策 |
|---|---|
| 母题 | indie-build-log **Idea 8**（社群群日报）· 招聘垂直自用变体 |
| 载体 | **不 Hook 个人微信号**；MVP 用导出解析 + inbox 手动落盘；macOS 可选读本机已同步库 |
| 合规 | 仅处理用户**本机已同步/主动导出/粘贴**的聊天内容；不爬未授权群、不上传 |
| 语言 | Python 3.10+，**零新增依赖**（纯 stdlib 解析） |
| 与 TG 关系 | 共享 `filter` + `reporting`；仅 `ingest` 层分源 |

### 1.1 为什么不 Hook 微信个人号

| 方案 | 可行性 | 风险 | MVP |
|---|---|---|---|
| PC 客户端 Hook（wcferry 等） | 技术可做 | 封号、ToS、仅 Windows | ❌ Phase 3 备选 |
| 本地 DB 解密读取 | 技术可做 | 密钥轮换、Mac/Win 差异大 | ⚠️ **F06-P2.5 macOS 可选** |
| **PC 导出 TXT 解析** | ✅ | 需用户手动导出 | ✅ **已实现** |
| **inbox 文件夹落盘** | ✅ | 用户复制粘贴有摩擦 | ✅ **已实现** |
| 企业微信 Bot | 官方 API | 需企业主体 | Phase 3 产品化 |
| 用户转发到服务号 | 合规 | 需公众号/企微 | Concierge 验证路径 |

---

## 2. 多源架构

```
                    ┌─────────────────┐
                    │  chat_radar_config │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
  ingest/telegram     ingest/wechat_*      ingest/...（未来）
  (Telethon P0-04)    export + inbox
         │                   │
         └─────────┬─────────┘
                   ▼
            RawMessage（统一模型）
                   ▼
         data/raw_messages.jsonl
                   ▼
            filter/RuleEngine
                   ▼
         reporting/digest → reports/
```

### 2.1 统一模型 `RawMessage`

| 字段 | Telegram | 微信 |
|---|---|---|
| `source` | `telegram` | `wechat` |
| `source_id` | channel_id | chat 哈希 |
| `message_id` | TG msg id | 内容哈希 |
| `sender` | — | 发言人昵称 |
| `chat_title` | channel title | 群名 |
| `link` | t.me 链接 | 导出文件 / inbox 路径 |

向后兼容：旧 JSONL 无 `source` 字段时视为 `telegram`。

---

## 3. 微信 MVP 实现

### 3.1 导出 TXT 解析（`wechat_export.py`）

**输入**：微信 PC 端「导出聊天记录」生成的 `.txt`

**格式**（每段消息）：

```
2026-09-01 10:30:15 张三
消息正文（可多行）

2026-09-01 10:31:00 李四
[图片]
```

**命令**：

```bash
python -m chat_radar wechat parse data/wechat_exports/招聘群.txt --chat "Java招聘群"
```

### 3.2 Inbox 落盘（`wechat_inbox.py`）

**用途**：手机复制重要群消息 → 粘贴到 `data/wechat_inbox/*.md`

**可选 YAML frontmatter**：

```markdown
---
chat: Java招聘群
sender: HR小王
date: 2026-09-01T10:30:00+08:00
---
招聘 Java 后端，远程优先
```

**命令**：

```bash
python -m chat_radar wechat inbox
```

### 3.3 微信 Digest

```bash
python -m chat_radar wechat digest --since 24
```

输出：`reports/DIGEST_wechat_YYYYMMDD_HHMMSS.md`

### 3.4 macOS 本地库同步（`wechat locate` / `wechat sync`）— F06-P2.5

**适用**：Mac + 微信 4.x，PC 已同步群聊，希望免手动导出。

**原理**：

1. 自动发现沙盒路径 `~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_*/db_storage`
2. 用户用外部工具（推荐 [wcdb-key-tool](https://github.com/TANGandXUE/wcdb-key-tool)）提取 SQLCipher 密钥 → `data/wechat_keys.json`
3. `wechat sync` 用 macOS CommonCrypto 解密 `message_*.db` / `contact.db`，读取群聊消息写入 JSONL

**命令**：

```bash
python -m chat_radar wechat locate          # 探测目录，写入 wechat.mac_data_dir
python -m chat_radar wechat sync --since 24 # 解密 + 导入（需 keys + enabled）
```

**限制**：

- 仅 macOS（CommonCrypto）；Windows 待 Phase 3
- 微信 4.1+ 密钥需 LLDB 断点提取，CHAT-RADAR **不内置**密钥提取（合规 + 维护成本）
- zstd 压缩消息需本机安装 `zstd` CLI（`brew install zstd`），否则跳过
- 默认只导入群聊（`@chatroom`）；可用 `wechat.watch_chats` 过滤群名

**配置**：

```json
"wechat": {
  "mac_data_dir": "",
  "keys_file": "data/wechat_keys.json",
  "decrypted_cache_dir": "data/wechat_decrypted",
  "watch_chats": [],
  "sync_scope": "groups"
}
```

**健康检查**：

```bash
python -m chat_radar wechat status          # 账号/密钥/zstd/缓存一览
python -m chat_radar wechat keys validate   # 密钥与当前账号是否匹配
```

解密/读取前自动校验密钥；`sync` / `summary --from-db` 结束时输出跳过统计（压缩消息、非纯文本等）。

### 3.5 按联系人维度摘要（`wechat summary`）— F06-08

**目标**：从账号本地备份（解密库或 JSONL）读取聊天记录，**按联系人**聚合，每人输出一份 Markdown。

**归并规则**：

| 会话类型 | 联系人维度 |
|---|---|
| 私聊 | 对方昵称/备注（`chat_title`） |
| 群聊 | 发言人（`sender`） |

**命令**：

```bash
# 推荐：直接从解密库读全量历史（无需先 sync 到 JSONL）
python -m chat_radar wechat summary --from-db --since 0 --scope all

# 或基于已入库 JSONL
python -m chat_radar wechat sync --scope all --since 0
python -m chat_radar wechat summary --since 0

# 仅生成某人
python -m chat_radar wechat summary --from-db --person "张三"
```

**输出**：`reports/wechat_contacts/index.md` + `{联系人}.md`

每份文档含：概览统计、涉及会话列表、按会话分组的时间线（L3 摘要，非 LLM）。

**配置**：

```json
"wechat": {
  "summary_scope": "all",
  "summary_output_dir": "reports/wechat_contacts",
  "summary_body_max_chars": 500,
  "summary_text_only": true,
  "self_display_name": "我",
  "sync_scope": "groups"
}
```

`summary_text_only=true`（默认）仅保留 `local_type=1` 纯文本，跳过图片/语音/链接/XML。

**归并规则补充**：

- 群聊 → 按发言人归档
- 私聊 → 按对方昵称/备注归档
- 同名联系人文件名冲突时自动加哈希后缀

---

## 3.6 健壮性与可观测性（F06-09）

| 能力 | 模块 | 说明 |
|---|---|---|
| 读取统计 | `ReadStats` | 跳过系统消息、压缩失败、非纯文本等计数 |
| 解密统计 | `DecryptStats` | 无密钥/解密失败/缓存命中 |
| 密钥检查 | `inspect_keys_file` | 账号匹配、salt 覆盖率 |
| 单库容错 | `wechat_db_reader` | 单表 SQLite 错误不中断全量读取 |
| 增量解密 | `decrypt_tree` | 源库 mtime 未变则复用缓存 |

**数据不完整时的常见原因**：

1. 未安装 `zstd` → 4.1 压缩消息跳过
2. `summary_text_only=true` → 图片/语音/链接不计入摘要
3. 消息未同步到 PC → 本地库本身缺失
4. 密钥账号与 `mac_data_dir` 不一致 → `keys validate` 报错

---

## 4. 配置段

```json
"wechat": {
  "enabled": true,
  "inbox_dir": "data/wechat_inbox",
  "export_dir": "data/wechat_exports",
  "default_chat": "招聘群"
}
```

`wechat.enabled=false` 时，所有 `wechat *` 命令拒绝执行。

---

## 5. 模块映射

| 模块 | 职责 |
|---|---|
| `core/models.py` | `RawMessage` 统一模型 |
| `ingest/wechat_export.py` | PC 导出 TXT 解析 |
| `ingest/wechat_inbox.py` | inbox 文件夹扫描 |
| `ingest/wechat_mac_paths.py` | macOS 微信目录自动发现 |
| `ingest/wechat_db_crypto.py` | SQLCipher 4 解密（macOS CommonCrypto） |
| `ingest/wechat_db_reader.py` | 解密后 SQLite 消息读取 + `ReadStats` |
| `ingest/wechat_keys.py` | 密钥派生 + `inspect_keys_file` 健康检查 |
| `reporting/wechat_person_summary.py` | 按联系人渲染 Markdown 摘要 |
| `ingest/persist.py` | JSONL 追加 + 去重 |
| `runtime/wechat_runner.py` | CLI 编排 |

---

## 6. Phase 路线图

| Phase | 能力 | 依赖 | 状态 |
|---|---|---|---|
| **F06 MVP** | 导出解析 + inbox + digest | 无 | ✅ |
| **F06-P2.5** | macOS 本地库 locate + sync | 外部密钥工具 + `zstd`（可选） | ✅ |
| **F06-08** | 按联系人 Markdown 摘要 | F06-P2.5 或 JSONL | ✅ |
| **F06-09** | status / keys validate + 读取统计 | F06-P2.5 | ✅ |
| F06-P2 | 导出后自动 watch 目录 | 无 | 📋 |
| F06-P3 | wcferry 实时监听（Windows） | `wcferry` 须获批 | 🔮 |
| F06-P4 | 企微 Bot 多群（产品化） | 企业主体 | 🔮 |

---

## 7. 与 Telegram 路径的合并点

`digest` 总命令（MP-11 ✅）：

1. `wechat inbox`（未 `--skip-wechat-inbox`）
2. `wechat import`（未 `--skip-wechat-export`）— 扫描 `export_dir` 新 TXT
3. `wechat sync`（未 `--skip-wechat-sync`；macOS + 密钥；失败 soft skip）
4. Telegram `fetch`（未 `--skip-fetch`）
5. 合并 `raw_messages.jsonl` 中 telegram + wechat → filter → 一份 `DIGEST_*.md`（概览含来源统计）

`wechat digest` 保留为单源调试；主路径走统一 `digest` 或 `./start.sh` 菜单选项 4。

### 7.1 交互日志（迭代排障）

| 文件 | 内容 |
|---|---|
| `logs/chat_radar.log` | 标准 Python 日志（fetch 频道、异常栈等） |
| `logs/interactions.jsonl` | 结构化交互节点：`command.start/done`、`digest.*`、`wechat.sync/inbox/import` 步骤与耗时 |
| `logs/start_menu.log` | `start.sh` 菜单选择与 CLI 调用（含 exit code） |

查看最近交互：

```bash
tail -20 logs/interactions.jsonl | python3 -m json.tool
tail -20 logs/start_menu.log
```

---

## 8. 安全红线（同步 RULES.md）

1. 不提交导出文件、inbox 内容、密钥、解密缓存、联系人摘要到 git（已在 `.gitignore`）
2. 不实现自动登录微信、不存储微信密码
3. 日志 `redact_bodies=true` 时可脱敏消息正文
4. **合规定位**：读取本机已同步数据 ≈ 用户自行导出；CHAT-RADAR 不内置 LLDB/内存扫描，密钥由用户本机外部工具一次性提取
