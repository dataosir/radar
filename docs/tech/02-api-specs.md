# 02 · API 规格（CLI & 模块契约）

## CLI 入口

```
python -m chat_radar [command] [options]
# 或安装后：
chat_radar [command]
```

## 命令一览

| 命令 | 参数 | 说明 | 状态 |
|---|---|---|---|
| `(default)` | — | 打印 help | ✅ |
| `auth` | — | 交互登录 Telegram | ✅ |
| `fetch` | `--channel @x` | 拉取（可选单频道） | ✅ |
| `digest` | `--since hours` `--skip-fetch` `--skip-wechat-inbox` `--skip-wechat-export` `--skip-wechat-sync` | TG fetch + 微信 ingest 链 + 合并 filter/report | ✅ |
| `channels` | `list` `add` `remove` `enable` `disable` | 频道与游标管理 | ✅ |
| `status` | — | 今日统计 | 📋 |
| `config` | `list/get/set` | 配置 | ✅ 骨架 |
| `wechat parse` | `<file> [--chat]` | 解析微信导出 TXT | ✅ |
| `wechat inbox` | — | 扫描 inbox 新文件（游标去重） | ✅ |
| `wechat import` | — | 扫描 export 目录新 TXT（游标去重） | ✅ |
| `wechat locate` | — | macOS：探测微信本地数据目录 | ✅ |
| `wechat status` | — | 微信模块健康检查 | ✅ |
| `wechat keys derive` | — | 从 passphrase 派生密钥 | ✅ |
| `wechat keys validate` | — | 校验密钥与账号匹配 | ✅ |
| `wechat sync` | `--since hours` `--scope groups\|private\|all` | macOS：解密本地库并导入 | ✅ |
| `wechat summary` | `--since hours` `--scope` `--from-db` `--person` | 按联系人生成 MD 摘要（默认纯文本） | ✅ |
| `wechat digest` | `--since hours` | 微信消息过滤 + 报告 | ✅ |

## 模块契约

### `ingest.client.TelegramIngestor`

```python
class TelegramIngestor:
    async def connect(self) -> None: ...
    async def fetch_channel(self, channel: str, *, limit: int | None) -> list[RawMessage]: ...
    async def disconnect(self) -> None: ...
```

### `filter.rules.RuleEngine`

```python
class RuleEngine:
    def evaluate(self, text: str) -> FilterResult:
        """FilterResult: matched: bool, rules: list[str], reason: str"""
```

### `reporting.digest.write_digest`

```python
def write_digest(jobs: list[JobPost], meta: DigestMeta, out_dir: Path) -> Path:
    """返回写入的 md 路径"""
```

### `runtime.runner`

```python
def run_digest(cfg, *, since_hours, skip_fetch=False, skip_wechat_inbox=False, skip_wechat_export=False, skip_wechat_sync=False, fix=False) -> int: ...
def run_selftest() -> int:
```

### 微信模块（F06）

```python
def parse_export_file(path: Path, *, chat_title: str | None, timezone_name: str) -> list[RawMessage]: ...
def scan_inbox_dir(inbox_dir: Path, *, default_chat: str, timezone_name: str) -> list[RawMessage]: ...
def run_wechat_parse(cfg, file_path: str, *, chat_title: str | None) -> int: ...
def run_wechat_inbox(cfg) -> int: ...
def run_wechat_locate(cfg) -> int: ...
def run_wechat_status(cfg) -> int: ...
def run_wechat_keys_derive(cfg) -> int: ...
def run_wechat_keys_validate(cfg) -> int: ...
def run_wechat_sync(cfg, *, since_hours: int | None, scope: str | None) -> int: ...
def run_wechat_summary(cfg, *, since_hours: int | None, scope: str | None, from_db: bool, person: str | None) -> int: ...
def run_wechat_digest(cfg, *, since_hours: int | None) -> int: ...
def inspect_keys_file(keys_path: Path, account: WeChatMacAccount | None) -> KeysInspection: ...
def read_messages_from_decrypted(..., stats: ReadStats | None) -> list[RawMessage]: ...
```

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 业务错误（配置缺、无频道） |
| 2 | Telegram / 网络错误 |
| 3 | selftest 失败 |
