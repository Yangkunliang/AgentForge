"""AgentForge developer CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1"

# ── Skill 脚手架模板 ──────────────────────────────────────────
SKILL_YAML_TEMPLATE = """\
name: {name}
version: 1.0.0
description: "TODO: 用一句话描述这个 Skill 的能力"
permissions: []
executor:
  kind: python
  entry_point: executor:run
audit:
  level: standard
tools:
  - type: function
    function:
      name: {tool_name}_hello
      description: "TODO: 描述这个工具做什么"
      parameters:
        type: object
        properties:
          name:
            type: string
            description: 示例参数
        required:
          - name
"""

EXECUTOR_TEMPLATE = '''\
"""AgentForge Skill executor.

每个 skill 必须暴露一个 async 函数作为 executor 入口，其参数与
agentforge-skill.yaml 中 tools[].function.parameters 对应，返回字符串
（或可被 JSON 序列化的对象）。
"""


async def run(name: str) -> str:
    """对应 agentforge-skill.yaml 里 entry_point: executor:run 的 run 函数。"""
    return f"Hello, {name}! 这是来自 skill 的响应。"
'''

README_TEMPLATE = """\
# {name}

一个 AgentForge Skill 脚手架。

## 结构

- `agentforge-skill.yaml` — 技能清单（声明 tools 与 executor 入口）
- `executor.py` — 工具真正执行的代码（`entry_point: executor:run`）

## 使用

1. 编辑 `agentforge-skill.yaml`：补充 `description`、按需增减 `tools`。
2. 在 `executor.py` 的 `run` 函数里实现你的逻辑（参数对应 tools 的 parameters）。
3. 把本目录 push 到 GitHub 公开仓库，即可在 AgentForge 的 Skill 市场被搜索并一键安装。

> 字段约定：最少需声明 1 个 tool，否则安装时会报错。
"""


def build_mount_payload(
    path: str | Path,
    *,
    display_name: str | None,
    role: str,
) -> dict[str, Any]:
    root = Path(path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Mount path must be an existing directory: {root}")
    name = (display_name or root.name).strip()
    if not name:
        raise ValueError("Mount display name cannot be empty")
    return {
        "mount_type": "local",
        "display_name": name,
        "locator": str(root),
        "role": role,
        "status": "connected",
        "metadata": {
            "root_path": str(root),
            "bridge": "agentforge-cli",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentforge", description="AgentForge local developer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mount_parser = subparsers.add_parser("mount", help="authorize a local repository path for a project")
    mount_parser.add_argument("path", help="local repository directory")
    mount_parser.add_argument("--project-id", required=True, help="AgentForge project id")
    mount_parser.add_argument("--api-url", default=os.getenv("AGENTFORGE_API_URL", DEFAULT_API_URL))
    mount_parser.add_argument("--token", default=os.getenv("AGENTFORGE_TOKEN"))
    mount_parser.add_argument("--name", default=None, help="display name shown in AgentForge")
    mount_parser.add_argument("--role", choices=["primary", "reference", "docs"], default="primary")

    # ── skill：创建与管理 AgentForge Skill ──
    skill_parser = subparsers.add_parser("skill", help="create and manage AgentForge skills")
    skill_sub = skill_parser.add_subparsers(dest="skill_command", required=True)

    skill_init_parser = skill_sub.add_parser("init", help="scaffold a new skill repository")
    skill_init_parser.add_argument("name", help="skill name (also used as the created directory name)")
    skill_init_parser.add_argument(
        "-o", "--output-dir", default=".",
        help="parent directory to create the skill in (default: current directory)",
    )
    skill_init_parser.add_argument("--force", action="store_true", help="overwrite existing files")

    args = parser.parse_args(argv)
    if args.command == "mount":
        return _mount(args)
    if args.command == "skill":
        if args.skill_command == "init":
            return _skill_init(args)
        parser.error("unknown skill command")
    parser.error("unknown command")
    return 2


def _mount(args: argparse.Namespace) -> int:
    if not args.token:
        print("Missing token. Pass --token or set AGENTFORGE_TOKEN.", file=sys.stderr)
        return 2

    try:
        payload = build_mount_payload(args.path, display_name=args.name, role=args.role)
        created = _post_json(
            f"{args.api_url.rstrip('/')}/projects/{args.project_id}/mounts",
            payload,
            token=args.token,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Mount failed: HTTP {exc.code} {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Mount failed: {exc.reason}", file=sys.stderr)
        return 1

    print(json.dumps(created, ensure_ascii=False, indent=2))
    return 0


def _post_json(url: str, payload: dict[str, Any], *, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        data = response.read().decode("utf-8")
        return json.loads(data)


def _skill_init(args: argparse.Namespace) -> int:
    base = Path(args.output_dir).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)

    skill_dir = base / args.name
    if skill_dir.exists() and not args.force:
        print(f"Directory already exists: {skill_dir}\nUse --force to overwrite.", file=sys.stderr)
        return 2

    skill_dir.mkdir(parents=True, exist_ok=True)
    tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", args.name)

    (skill_dir / "agentforge-skill.yaml").write_text(
        SKILL_YAML_TEMPLATE.format(name=args.name, tool_name=tool_name), encoding="utf-8"
    )
    (skill_dir / "executor.py").write_text(EXECUTOR_TEMPLATE, encoding="utf-8")
    (skill_dir / "README.md").write_text(
        README_TEMPLATE.format(name=args.name), encoding="utf-8"
    )

    print(f"Created skill scaffold at: {skill_dir}")
    print("Next steps:")
    print("  1. 编辑 agentforge-skill.yaml 的 description / tools")
    print("  2. 在 executor.py 实现你的工具函数")
    print("  3. 把目录 push 到 GitHub 公开仓库，即可在 Skill 市场被搜索并一键安装")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
