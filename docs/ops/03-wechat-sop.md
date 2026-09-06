# 03 · 微信 ingest 运营 SOP

> 技术背景见 [`../tech/04-wechat-integration.md`](../tech/04-wechat-integration.md)。

---

## 1. 目录准备

```bash
mkdir -p data/wechat_inbox data/wechat_exports
```

确保 `chat_radar_config.json` 中：

```json
"wechat": { "enabled": true }
```

---

## 2. 路径 A：PC 导出（推荐批量）

1. 打开微信 PC 客户端，进入目标招聘群
2. 聊天窗口右上角 `…` → **导出聊天记录**
3. 选择 **TXT**，保存到 `data/wechat_exports/招聘群.txt`
4. 运行：

```bash
python -m chat_radar wechat parse data/wechat_exports/招聘群.txt --chat "Java招聘群"
python -m chat_radar wechat digest --since 168
```

> Mac 版微信导出能力因版本而异；若无法导出，用路径 B。

---

## 3. 路径 B：Inbox 手动落盘（推荐日常）

1. 手机/PC 复制重要招聘消息
2. 新建 `data/wechat_inbox/2026-09-01-hr.md`：

```markdown
---
chat: Java招聘群
sender: HR小王
date: 2026-09-01T10:30:00+08:00
---
招聘 Java 后端，Spring Boot，远程优先
```

3. 运行：

```bash
python -m chat_radar wechat inbox
python -m chat_radar wechat digest
```

---

## 3. 路径 C：macOS 本地库同步（免导出，推荐 Mac 用户）

> 微信 4.1+ 数据库加密，需先用外部工具提取密钥。CHAT-RADAR 不内置密钥提取。

### 3.1 一次性准备

```bash
# 1. 探测微信数据目录（自动写入 wechat.mac_data_dir）
python -m chat_radar wechat locate

# 2. 安装 wcdb-key-tool（见 https://github.com/TANGandXUE/wcdb-key-tool）
#    推荐: ./ops/extract_wechat_keys.sh（自动检测活跃账号 + 多账号匹配）
#    若已捕获 passphrase: sudo .venv/bin/python ops/derive_wechat_keys.py

# 3. 可选：brew install zstd  （解压压缩消息）
# 4. 配置 wechat.enabled=true
```

### 3.2 日循环

```bash
python -m chat_radar wechat sync --since 24
python -m chat_radar wechat digest --since 24
```

可选：在配置中设置 `wechat.watch_chats: ["Java招聘群"]` 只同步指定群。

### 3.3 生成联系人摘要（按人维度 MD）

```bash
# 全量历史 + 群聊与私聊（推荐 Mac 本地库直读）
python -m chat_radar wechat summary --from-db --since 0 --scope all

# 健康检查
python -m chat_radar wechat status
python -m chat_radar wechat keys validate
```

输出目录：`reports/wechat_contacts/`
- `index.md` — 联系人索引
- `张三.md` — 该联系人所有相关消息时间线

`--since 0` 表示不限制时间窗口（全量）。`--person` 可只生成单人。默认 `summary_text_only=true` 仅保留纯文本。

---

## 4. 日循环（与 Telegram 合并）

| 时间 | 动作 |
|---|---|
| 晨间 | `./start.sh digest` 或 `chat_radar digest`（自动 TG fetch + 微信 inbox + 合并报告） |
| 周度 | 导出群聊 → `wechat parse`；或 `wechat sync` 增量同步本地库 |
| 复盘 | `./start.sh` 菜单 8 → 微信联系人摘要；菜单 7 → 微信状态检查 |

`wechat.enabled=false` 时 `digest` 仅含 Telegram。

---

## 5. 隐私与 git

以下目录**不得提交**：

- `data/wechat_inbox/`
- `data/wechat_exports/`
- `data/wechat_keys.json`
- `data/wechat_decrypted/`
- `reports/wechat_contacts/`
- `data/raw_messages.jsonl`（含聊天内容）

---

## 6. 故障排查

| 现象 | 处理 |
|---|---|
| `wechat.enabled 未开启` | 配置 `wechat.enabled: true` |
| 解析 0 条 | 检查导出格式是否为 `YYYY-MM-DD HH:MM:SS 昵称` |
| digest 无命中 | 调 `filter.include_keywords` |
| 重复消息 | 正常 — dedup 会跳过；无需手动删 JSONL |
| 摘要消息偏少 | 运行 `wechat status`；检查 zstd、纯文本过滤、密钥覆盖率 |
| 密钥账号不匹配 | `wechat keys validate`；重新 `derive` 或 `extract_wechat_keys.sh` |
| PBKDF2 0/N 验证 | 多账号时确认活跃账号；用 `derive_wechat_keys.py` 自动匹配 |

---

## 7. 不做的事

- ❌ 不提供微信扫码登录脚本
- ❌ 不代管他人微信号
- ❌ 不自动爬群（无授权）
