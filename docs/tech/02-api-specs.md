# 02 · API 规格（CLI & 模块契约）

## CLI 入口

```
python -m tg_radar [command] [options]
# 或安装后：
tg_radar [command]
```

## 命令一览

| 命令 | 参数 | 说明 | 状态 |
|---|---|---|---|
| `(default)` | — | 打印 help | ✅ |
| `auth` | — | 交互登录 Telegram | 📋 |
| `fetch` | `--channel @x` | 拉取（可选单频道） | 📋 |
| `digest` | `--since hours` | fetch+filter+report | 📋 |
| `channels` | `list` | 频道与游标 | 📋 |
| `status` | — | 今日统计 | 📋 |
| `config` | `list/get/set` | 配置 | ✅ 骨架 |
| `selftest` | — | 离线自测 | ✅ 骨架 |

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
def run_digest(cfg) -> int:  # exit code
def run_selftest() -> int:
```

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 业务错误（配置缺、无频道） |
| 2 | Telegram / 网络错误 |
| 3 | selftest 失败 |
