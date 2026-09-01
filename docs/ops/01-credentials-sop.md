# 01 · Telegram 凭证管理 SOP

## 获取 API 凭证

1. 浏览器打开 https://my.telegram.org  
2. 用手机号登录 → **API development tools**  
3. 创建应用（名称随意，如 `tg-radar-personal`）  
4. 记录 `api_id`（数字）和 `api_hash`（字符串）

## 写入配置

```bash
cp tg_radar_config.example.json tg_radar_config.json
# 编辑 telegram.api_id / telegram.api_hash
```

**禁止**将 `tg_radar_config.json` 和 `*.session` 提交 git。

## 首次登录

```bash
python -m tg_radar auth
```

按提示输入手机号、验证码、二级密码（若有）。成功后生成 `tg_radar.session`。

## Session 备份

| 项 | 建议 |
|---|---|
| 备份位置 | 加密盘 / 1Password 附件 / 离线 U 盘 |
| 频率 | 首次登录后 + 每季度 |
| 丢失后果 | 需重新 `auth`；不影响已落盘 `data/` |

## 轮换与吊销

- 怀疑泄露：my.telegram.org 可 **Revoke** 旧 session  
- 轮换后：删除本地 `*.session`，重新 `auth`

## 多机使用

- **不要**两台机器同时跑同一 session（可能触发 Telegram 安全限制）  
- 若需多机：一台做主拉取，另一台只读 `data/` / `reports/`（rsync 或 git private）
