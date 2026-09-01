# 04 · 非功能约束（NFR）

## 性能

| 项 | 目标 |
|---|---|
| 单频道增量拉取 | < 10s（正常网络） |
| 全 pipeline `digest` | < 2 min（≤ 30 频道） |
| 内存 | < 200MB 常驻 |

## 可靠性

- 所有文件写入**原子**（`.tmp` + `rename`）  
- Telethon 断线可重试；FloodWait 尊重等待时间  
- `selftest` 不联网，覆盖过滤 / 去重 / 报告纯逻辑

## 安全

- 凭证与 session **不入 git**  
- 日志不打印完整 message 正文（可配置 `log.redact_bodies: true`）  
- 仅读取已订阅频道

## 可维护性

- 依赖最小化：MVP 仅 `telethon`；LLM 可选  
- Python 3.10+；与 tea 工程习惯对齐  
- 配置单文件 `tg_radar_config.json`

## 可移植性

- 开发机 macOS；数据目录可用 `TG_RADAR_HOME` 覆盖

## 质量门禁

```bash
python -m tg_radar selftest   # 必须全绿
ruff check .                  # 无告警（引入后）
```
