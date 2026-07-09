"""Skill 管理路由：列表、安装、卸载、市场、启用/禁用"""

from __future__ import annotations

import logging
import os
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import get_async_session
from agent_forge.models import User
from agent_forge.skills.installer import SkillInstaller
from agent_forge.skills.manifest import SkillManifestError
from agent_forge.skills.manager import SkillManager
from middleware.auth import get_current_user, require_permission

router = APIRouter()
logger = logging.getLogger("agent_forge")


# ── Pydantic Schemas ──────────────────────────────────────────

class InstallSkillRequest(BaseModel):
    source: str
    version: str | None = None
    confirm_risk: bool = False

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """白名单验证：允许 GitHub HTTPS URL、PyPI 包名或存在的本地目录。"""
        if re.match(r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", v):
            return v
        if re.match(r"^git\+https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", v):
            return v
        if os.path.isdir(v):
            return v
        if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$", v):
            return v
        raise ValueError("Invalid source. Only GitHub HTTPS URLs, local directories, or PyPI package names allowed.")


class SkillResponse(BaseModel):
    name: str
    version: str
    description: str
    entry_point: str | None
    installed_at: str | None
    enabled: bool
    source_type: str | None
    icon_url: str | None
    tags: list[str]
    github_url: str | None
    manifest_hash: str | None = None
    permissions: list[str] = []
    runtime_spec: dict = Field(default_factory=dict)
    audit_level: str = "standard"


class InstallStatusResponse(BaseModel):
    install_id: str
    status: str
    log: str | None = None
    error: str | None = None


class InstallTaskCreated(BaseModel):
    install_id: str
    skill_name: str
    status: str
    manifest_hash: str | None = None
    permissions: list[str] = []
    risk_level: str | None = None


class SkillImportPreviewRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=500)
    version: str | None = None


class SkillImportInstallRequest(SkillImportPreviewRequest):
    confirm_risk: bool = False


class SkillImportToolPreview(BaseModel):
    name: str
    description: str
    parameters: dict = Field(default_factory=dict)


class SkillImportPreviewResponse(BaseModel):
    name: str
    version: str
    description: str
    source: str
    source_type: str
    manifest_hash: str
    permissions: list[str]
    tools: list[SkillImportToolPreview]
    risk_level: str
    requires_confirmation: bool
    audit_level: str = "standard"
    warnings: list[str] = []


class MarketplaceSkill(BaseModel):
    name: str
    description: str
    url: str
    author: str
    icon: str | None = None
    tags: list[str] = []
    version: str = "latest"
    stars: int = 0
    source: str = "github"  # github | clawhub | local


class MarketplaceResponse(BaseModel):
    marketplace: str
    total: int
    items: list[MarketplaceSkill]


# ── 已安装 Skill 列表 ─────────────────────────────────────────

@router.get("", summary="列出所有已安装 Skill")
async def list_skills(
    enabled_only: bool = Query(False, description="只返回已启用的 Skill"),
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_user),
) -> dict:
    skills = await SkillManager.list_skills(db, enabled_only=enabled_only)
    items = [
        SkillResponse(
            name=s.name,
            version=s.version or "0.0.0",
            description=s.description,
            entry_point=s.entry_point,
            installed_at=s.installed_at,
            enabled=s.enabled,
            source_type=s.source_type or "builtin",
            icon_url=s.icon_url,
            tags=s.tags or [],
            github_url=s.github_url,
            manifest_hash=s.manifest_hash,
            permissions=s.permissions or [],
            runtime_spec=s.runtime_spec or {},
            audit_level=s.audit_level,
        ).model_dump()
        for s in skills
    ]
    return {"total": len(items), "items": items}


# ── 第三方 Skill 导入 Preview / Install ───────────────────────

@router.post("/import/preview", response_model=SkillImportPreviewResponse, summary="预览第三方 Skill 导入风险")
async def preview_skill_import(
    body: SkillImportPreviewRequest,
    _: User = Depends(require_permission("admin")),
) -> dict:
    try:
        preview = await SkillInstaller.preview_import(body.source, body.version)
    except SkillManifestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return preview.to_dict()


@router.post("/import/install", status_code=status.HTTP_201_CREATED, summary="安装已预览的第三方 Skill")
async def install_skill_import(
    body: SkillImportInstallRequest,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(require_permission("admin")),
) -> dict:
    try:
        install_task = await SkillInstaller.install_from_source(
            db,
            body.source,
            body.version,
            confirm_risk=body.confirm_risk,
        )
    except SkillManifestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError:
        await _raise_skill_permission_confirmation_required(body.source, body.version)
    return InstallTaskCreated(
        install_id=install_task.id,
        skill_name=install_task.skill_name,
        status=install_task.status,
        manifest_hash=install_task.manifest_hash,
        permissions=install_task.permissions or [],
        risk_level=install_task.risk_level,
    ).model_dump()


# ── 安装进度查询 ──────────────────────────────────────────────

@router.get("/install/{install_id}", summary="查询 Skill 安装进度")
async def get_install_status(
    install_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_user),
) -> dict:
    task = await SkillInstaller.get_install_status(db, install_id)
    if not task:
        raise HTTPException(status_code=404, detail="Install task not found")
    return InstallStatusResponse(
        install_id=task.id,
        status=task.status,
        log=task.log,
        error=task.error,
    ).model_dump()


# ── 安装 Skill ────────────────────────────────────────────────

@router.post("/install", status_code=status.HTTP_202_ACCEPTED, summary="安装 Skill")
async def install_skill(
    body: InstallSkillRequest,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(require_permission("admin")),
) -> dict:
    """
    安装 Skill，自动识别 source 类型：

    - `https://github.com/owner/repo` → git clone 安装
    - `git+https://...` → git clone 安装
    - PyPI 包名（如 `agentforge-skill-calculator`）→ pip install
    - 本地路径（如 `/path/to/my-skill`）→ 本地目录注册
    """
    try:
        install_task = await SkillInstaller.install_from_source(
            db,
            body.source,
            body.version,
            confirm_risk=body.confirm_risk,
        )
    except SkillManifestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError:
        await _raise_skill_permission_confirmation_required(body.source, body.version)
    return InstallTaskCreated(
        install_id=install_task.id,
        skill_name=install_task.skill_name,
        status=install_task.status,
        manifest_hash=install_task.manifest_hash,
        permissions=install_task.permissions or [],
        risk_level=install_task.risk_level,
    ).model_dump()


@router.post("/install/url", status_code=status.HTTP_202_ACCEPTED, summary="从 GitHub URL 安装 Skill")
async def install_skill_from_url(
    body: InstallSkillRequest,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(require_permission("admin")),
) -> dict:
    if not body.source.startswith(("https://github.com/", "git+https://github.com/")):
        raise HTTPException(
            status_code=400,
            detail="GitHub URL 必须以 https://github.com/ 或 git+https://github.com/ 开头",
        )
    try:
        install_task = await SkillInstaller.install_from_source(
            db,
            body.source,
            body.version,
            confirm_risk=body.confirm_risk,
        )
    except SkillManifestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError:
        await _raise_skill_permission_confirmation_required(body.source, body.version)
    return InstallTaskCreated(
        install_id=install_task.id,
        skill_name=install_task.skill_name,
        status=install_task.status,
        manifest_hash=install_task.manifest_hash,
        permissions=install_task.permissions or [],
        risk_level=install_task.risk_level,
    ).model_dump()


async def _raise_skill_permission_confirmation_required(source: str, version: str | None) -> None:
    preview = await SkillInstaller.preview_import(source, version)
    raise HTTPException(
        status_code=409,
        detail={
            "code": "SKILL_PERMISSION_CONFIRMATION_REQUIRED",
            "message": "该 Skill 声明了高风险权限，需要用户确认后安装",
            "preview": preview.to_dict(),
        },
    )


# ── 启用 / 禁用 Skill ─────────────────────────────────────────

@router.post("/{skill_name}/enable", summary="启用 Skill")
async def enable_skill(
    skill_name: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(require_permission("admin")),
) -> dict:
    success = await SkillManager.set_enabled(db, skill_name, True)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return {"skill": skill_name, "enabled": True}


@router.post("/{skill_name}/disable", summary="禁用 Skill（不卸载）")
async def disable_skill(
    skill_name: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(require_permission("admin")),
) -> dict:
    success = await SkillManager.set_enabled(db, skill_name, False)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return {"skill": skill_name, "enabled": False}


# ── Skill 市场 ────────────────────────────────────────────────

@router.get("/marketplace", response_model=MarketplaceResponse, summary="浏览 Skill 市场")
async def get_marketplace_skills(
    source: str = Query("all", description="来源过滤: all | github | clawhub | local"),
    q: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_user),
) -> dict:
    """
    聚合多来源 Skill 市场列表：

    1. **clawhub.ai** — 若配置 `CLAWHUB_API_BASE` 则调用其 API
    2. **GitHub** — 查询 `topic:agentforge-skill` 仓库（公开 API，无需 Token）
    3. **本地** — 已安装的 Skill 列表

    source 参数可单独过滤某个来源。
    """
    items: list[dict] = []

    # ── 1. ClawhHub ──
    if source in ("all", "clawhub"):
        clawhub_items = await _fetch_clawhub(q)
        items.extend(clawhub_items)

    # ── 2. GitHub ──
    if source in ("all", "github"):
        github_items = await _fetch_github_skills(q)
        items.extend(github_items)

    # ── 3. 本地已安装 ──
    if source in ("all", "local"):
        skills = await SkillManager.list_skills(db)
        for s in skills:
            items.append(MarketplaceSkill(
                name=s.name,
                description=s.description or "",
                url=s.github_url or "",
                author="local",
                icon=s.icon_url,
                tags=s.tags or [],
                source="local",
            ).model_dump())

    # 关键词过滤（GitHub API 已过滤，这里处理其他来源）
    if q and source not in ("github",):
        q_lower = q.lower()
        items = [
            item for item in items
            if q_lower in item["name"].lower() or q_lower in item["description"].lower()
        ]

    # 去重（同名 skill 保留第一个）
    seen: set[str] = set()
    unique_items: list[dict] = []
    for item in items:
        key = item["name"].lower()
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    return {
        "marketplace": source,
        "total": len(unique_items),
        "items": unique_items,
    }


async def _fetch_clawhub(q: str) -> list[dict]:
    """从 clawhub.ai 获取 Skill 列表"""
    api_base = os.getenv("CLAWHUB_API_BASE", "")
    if not api_base:
        logger.debug("ClawhHub API base not configured, skipping")
        return []
    
    try:
        params: dict = {}
        if q:
            params["q"] = q
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{api_base}/api/v1/skills",
                params=params,
                headers={"User-Agent": "AgentForge/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    MarketplaceSkill(
                        name=item.get("name", ""),
                        description=item.get("description", ""),
                        url=item.get("github_url", item.get("url", "")),
                        author=item.get("author", "clawhub"),
                        icon=item.get("icon"),
                        tags=item.get("tags", []),
                        version=item.get("version", "latest"),
                        stars=item.get("stars", 0),
                        source="clawhub",
                    ).model_dump()
                    for item in data.get("items", [])
                ]
            elif resp.status_code == 404:
                logger.debug("ClawhHub API endpoint not found")
            else:
                logger.debug("ClawhHub API returned status %s", resp.status_code)
    except httpx.ConnectError:
        logger.debug("ClawhHub API connection failed: endpoint unreachable")
    except Exception as e:
        logger.debug("ClawhHub API unavailable: %s", e)
    return []


async def _fetch_github_skills(q: str) -> list[dict]:
    """
    通过 GitHub Search API 查询带 agentforge-skill topic 的仓库。
    无需 Token（公开 API，60 req/hour 限制）。
    配置 GITHUB_TOKEN 可提升到 5000 req/hour。
    """
    topic_query = "topic:agentforge-skill"
    if q:
        topic_query = f"{q} {topic_query}"

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AgentForge/1.0"}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": topic_query, "sort": "stars", "order": "desc", "per_page": 20},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = []
                for repo in data.get("items", []):
                    items.append(MarketplaceSkill(
                        name=_repo_to_skill_name(repo["name"]),
                        description=repo.get("description") or "",
                        url=repo["html_url"],
                        author=repo["owner"]["login"],
                        icon=repo["owner"].get("avatar_url"),
                        tags=repo.get("topics", []),
                        version=repo.get("default_branch", "main"),
                        stars=repo.get("stargazers_count", 0),
                        source="github",
                    ).model_dump())
                return items
            elif resp.status_code == 403:
                logger.warning("GitHub API rate limited. Set GITHUB_TOKEN env var to increase limit.")
    except Exception as e:
        logger.warning("GitHub API failed: %s", e)
    return []


def _repo_to_skill_name(repo_name: str) -> str:
    """将 GitHub repo 名转换为 Skill 名称（去除常见前缀）"""
    prefixes = ["agentforge-skill-", "agentforge-", "skill-"]
    name = repo_name.lower()
    for prefix in prefixes:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


# ── 卸载 Skill ────────────────────────────────────────────────

@router.delete("/{skill_name}", status_code=status.HTTP_204_NO_CONTENT, summary="卸载 Skill")
async def uninstall_skill(
    skill_name: str,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(require_permission("admin")),
) -> None:
    success = await SkillManager.unregister_skill(db, skill_name)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    await SkillInstaller.uninstall_skill(db, skill_name)
