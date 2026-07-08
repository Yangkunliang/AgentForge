"""AgentForge developer CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1"


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

    args = parser.parse_args(argv)
    if args.command == "mount":
        return _mount(args)
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


if __name__ == "__main__":
    raise SystemExit(main())
