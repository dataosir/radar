#!/usr/bin/env python3
"""Generate structured auto-commit messages from staged git changes.

Style reference: enterprise-kb-py — Chinese subject, feature IDs, concrete scope.
Output format:
  auto: [Fxx/Px-yy] 主题句。

  <shortstat>

  变更范围:
  - ...
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())


def _run(*args: str) -> str:
    return subprocess.check_output(list(args), text=True, cwd=ROOT).strip()


def staged_files() -> list[str]:
    out = _run("git", "diff", "--cached", "--name-only")
    return [line for line in out.splitlines() if line.strip()]


def shortstat() -> str:
    return _run("git", "diff", "--cached", "--shortstat")


def _changelog_added_lines() -> list[str]:
    if "docs/CHANGELOG.md" not in staged_files():
        return []
    try:
        diff = _run("git", "diff", "--cached", "--unified=0", "--", "docs/CHANGELOG.md")
    except subprocess.CalledProcessError:
        return []
    added: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return added


def detect_feature_ids(files: list[str]) -> list[str]:
    ids: set[str] = set()
    for path in files:
        m = re.search(r"/(F\d{2})[-_]", path)
        if m:
            ids.add(m.group(1))
        for tag in re.findall(r"\b(P\d-\d{2}|MP-\d{2}|E\d)\b", path):
            ids.add(tag)

    for line in _changelog_added_lines():
        for tag in re.findall(r"\*\*(F\d{2}|P\d-\d{2}|MP-\d{2}|E\d)", line):
            ids.add(tag)

    priority = {"F06", "F05", "F04", "F03", "F02", "F01", "MP-11", "P1-08", "P1-05", "P1-07"}
    ordered = sorted(ids, key=lambda x: (0 if x in priority else 1, x))
    return ordered[:4]


def categorize(files: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for path in files:
        p = Path(path)
        name = p.name
        if path.startswith("chat_radar/"):
            part = path.split("/")[1] if "/" in path else "core"
            buckets["代码"].append(f"{part}/{name}" if part != name else name)
        elif path.startswith("docs/prd/"):
            buckets["PRD"].append(name)
        elif path.startswith("docs/tech/"):
            buckets["Tech"].append(name)
        elif path.startswith("docs/ops/"):
            buckets["Ops"].append(name)
        elif path in ("docs/CHANGELOG.md", "docs/project-state.md", "docs/INDEX.md", "docs/README.md"):
            buckets["文档索引"].append(name)
        elif path.startswith("docs/"):
            buckets["文档"].append(name)
        elif path.startswith("tests/") or "selftest" in path:
            buckets["测试"].append(name)
        elif path.startswith(".cursor/"):
            buckets["开发工具"].append(name)
        elif path.startswith("ops/"):
            buckets["运维脚本"].append(name)
        elif name in ("start.sh", "install.sh", "build.sh", "RULES.md", ".cursorrules"):
            buckets["入口/规约"].append(name)
        else:
            buckets["其他"].append(path)
    for key in buckets:
        buckets[key] = sorted(set(buckets[key]))[:8]
    return dict(buckets)


def infer_themes(files: list[str]) -> list[str]:
    joined = " ".join(files).lower()
    themes: list[tuple[int, str]] = []

    rules: list[tuple[list[str], str]] = [
        (["wechat_person_summary", "wechat summary"], "微信联系人摘要"),
        (["wechat_db", "wechat_mac", "wechat_db_crypto", "wechat_db_reader"], "微信 macOS 本地库读取"),
        (["wechat_export", "wechat_inbox", "wechat_import"], "微信 ingest 链路"),
        (["interaction_log", "interactions.jsonl"], "交互节点结构化日志"),
        (["tg_runner", "run_digest", "merged_digest"], "统一 digest（TG + 微信）"),
        (["channels"], "Telegram 频道管理"),
        (["launchd", "install_launchd"], "晨间 launchd 调度"),
        (["auto_commit", "generate_commit_message", "hooks.json"], "自动 commit 钩子"),
        (["build.sh", "install.sh", "install.txt"], "一键打包与安装"),
        (["start.sh"], "start.sh 菜单与 CLI 快捷命令"),
        (["selftest"], "selftest 回归"),
        (["changelog", "project-state", "index.md"], "文档与项目状态同步"),
        (["setup"], "引导式 setup 配置"),
        (["preflight", "auth"], "Telegram 登录与预检"),
        (["filter/"], "过滤规则"),
        (["reporting/"], "报告渲染"),
    ]
    for patterns, label in rules:
        if any(p in joined for p in patterns):
            themes.append((0, label))

    if not themes:
        if any(f.startswith("docs/") for f in files):
            themes.append((1, "文档更新"))
        if any(f.startswith("chat_radar/") for f in files):
            themes.append((1, "代码迭代"))
    themes.sort(key=lambda x: x[0])
    seen: set[str] = set()
    out: list[str] = []
    for _, label in themes:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out[:3]


def changelog_hints() -> list[str]:
    hints: list[str] = []
    for line in _changelog_added_lines():
        if line.startswith("- **"):
            hint = re.sub(r"^\-\s*\*\*(.+?)\*\*.*", r"\1", line).strip()
            if hint:
                hints.append(hint)
            if len(hints) >= 3:
                break
    return hints


def build_subject(feature_ids: list[str], themes: list[str]) -> str:
    tag = "/".join(feature_ids) if feature_ids else ""
    if themes:
        core = "，".join(themes[:2])
        if len(themes) > 2:
            core += f"及{themes[2]}"
    else:
        core = "Agent 会话改动"

    if tag:
        return f"auto: [{tag}] {core}。"
    return f"auto: {core}。"


def format_message() -> str:
    files = staged_files()
    if not files:
        return "auto: 空改动快照。"

    stat = shortstat()
    feature_ids = detect_feature_ids(files)
    themes = infer_themes(files)
    buckets = categorize(files)
    hints = changelog_hints()

    lines = [build_subject(feature_ids, themes), "", stat, "", "变更范围:"]
    order = ["代码", "PRD", "Tech", "Ops", "文档索引", "文档", "测试", "运维脚本", "入口/规约", "开发工具", "其他"]
    for key in order:
        items = buckets.get(key)
        if not items:
            continue
        shown = ", ".join(items)
        if len(buckets[key]) > len(items):
            shown += ", …"
        lines.append(f"- {key}: {shown}")

    if hints:
        lines.extend(["", "CHANGELOG 摘要:"])
        for hint in hints:
            lines.append(f"- {hint}")

    if len(files) <= 30:
        lines.extend(["", f"共 {len(files)} 个文件"])
    else:
        lines.extend(["", f"共 {len(files)} 个文件（仅列主要模块）"])

    return "\n".join(lines)


def main() -> int:
    try:
        print(format_message())
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"auto: Agent 会话改动（消息生成失败: {exc}）。", file=sys.stderr)
        print("auto: Agent 会话改动。", file=sys.stdout)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
