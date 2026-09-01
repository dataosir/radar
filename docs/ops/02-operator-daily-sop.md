# 02 · 每日运营 SOP

> 目标：每天 **≤ 5 分钟** 完成招聘信息扫读。命令细节见 [`../prd/02-daily-workflow.md`](../prd/02-daily-workflow.md)。

---

## 晨间 Checklist（08:30）

- [ ] 运行 `chat_radar digest`（或确认 launchd 已跑）
- [ ] 打开 `reports/` 最新 `DIGEST_*.md`
- [ ] 逐条点开链接：值得跟进 → 记到求职 tracker；误报 → 记下关键词
- [ ] 看 `status`：命中数是否异常（0 或暴增）

## 误报处理

1. 记下误报帖里的特征词  
2. 周末批量更新 `filter.exclude_keywords`  
3.  rerun `selftest` 确认规则无副作用

## 漏帖补救

1. 在 TG 原频道找到漏掉的帖  
2. 检查是否缺正向词 → 补 `filter.include_keywords`  
3. 检查频道是否在 `channels[]` 且 `enabled: true`  
4. 必要时 `chat_radar cursor reset @channel` 重拉（慎用）

## 每周复盘（周日 10 min）

- [ ] `reports/` 本周命中数趋势  
- [ ] 哪个频道噪音最高 → `enabled: false` 或单独调规则  
- [ ] 更新 [`../project-state.md`](../project-state.md) 的「自用验证」笔记

## Kill 信号

连续 3 天宁愿刷 TG 也不看 digest → 停更，回 indie-build-log 改方向。
