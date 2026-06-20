"""Harness Layer 3: Registry - Agent 和 Skill 注册中心"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

if TYPE_CHECKING:
    from agent_forge.models import Agent


logger = logging.getLogger("agent_forge.harness.registry")


class AgentRegistry:
    """Agent 注册中心"""

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        """注册 Agent"""
        self._agents[agent.id] = agent
        logger.info(f"Registered agent: {agent.id} ({agent.name})")

    def unregister(self, agent_id: str) -> None:
        """注销 Agent"""
        if agent_id in self._agents:
            agent = self._agents.pop(agent_id)
            logger.info(f"Unregistered agent: {agent_id} ({agent.name})")

    def get(self, agent_id: str) -> Agent | None:
        """获取 Agent"""
        return self._agents.get(agent_id)

    def list_all(self) -> list[Agent]:
        """列出所有 Agent"""
        return list(self._agents.values())

    def query_by_capability(self, capability: str) -> list[Agent]:
        """按能力查询 Agent"""
        result = []
        for agent in self._agents.values():
            if capability in (agent.capabilities or []):
                result.append(agent)
        logger.debug(f"Found {len(result)} agents with capability '{capability}'")
        return result

    def query_by_capabilities(self, capabilities: list[str]) -> list[Agent]:
        """按能力列表查询 Agent（匹配所有能力）"""
        result = []
        for agent in self._agents.values():
            agent_caps = agent.capabilities or []
            if all(cap in agent_caps for cap in capabilities):
                result.append(agent)
        logger.debug(f"Found {len(result)} agents with capabilities {capabilities}")
        return result

    def __len__(self) -> int:
        return len(self._agents)


class Skill:
    """Skill 基类"""

    def __init__(self, id: str, name: str, description: str = ""):
        self.id = id
        self.name = name
        self.description = description

    async def execute(self, input_data: dict) -> dict:
        """执行 Skill"""
        raise NotImplementedError("Subclasses must implement execute()")


class SkillRegistry:
    """Skill 注册中心（支持热加载）"""

    def __init__(self, skills_dir: str = "skills"):
        self._skills: dict[str, Skill] = {}
        self._skills_dir = skills_dir
        self._observer: Observer | None = None

    def register(self, skill: Skill) -> None:
        """注册 Skill"""
        self._skills[skill.id] = skill
        logger.info(f"Registered skill: {skill.id} ({skill.name})")

    def unregister(self, skill_id: str) -> None:
        """注销 Skill"""
        if skill_id in self._skills:
            skill = self._skills.pop(skill_id)
            logger.info(f"Unregistered skill: {skill_id} ({skill.name})")

    def get(self, skill_id: str) -> Skill | None:
        """获取 Skill"""
        return self._skills.get(skill_id)

    def list_all(self) -> list[Skill]:
        """列出所有 Skill"""
        return list(self._skills.values())

    def query(self, skill_id: str) -> Skill | None:
        """查询 Skill（便捷方法）"""
        return self.get(skill_id)

    def start_hot_reload(self) -> None:
        """启动热加载（watchdog 文件监听）"""
        if self._observer is not None:
            logger.warning("Hot reload already started")
            return

        self._observer = Observer()
        event_handler = SkillFileHandler(self)
        self._observer.schedule(event_handler, self._skills_dir, recursive=True)
        self._observer.start()
        logger.info(f"Started hot reload watching: {self._skills_dir}")

    def stop_hot_reload(self) -> None:
        """停止热加载"""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Stopped hot reload")

    def reload_skill(self, skill_id: str) -> None:
        """重新加载指定 Skill"""
        # 这里可以实现动态重新加载逻辑
        logger.info(f"Reloading skill: {skill_id}")

    def __len__(self) -> int:
        return len(self._skills)


class SkillFileHandler(FileSystemEventHandler):
    """Skill 文件变化处理器"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def on_modified(self, event: FileSystemEvent) -> None:
        """文件修改事件"""
        if event.is_directory:
            return
        if event.src_path.endswith(".py"):
            logger.info(f"Skill file modified: {event.src_path}")
            # 提取 skill_id（简化处理）
            skill_id = event.src_path.split("/")[-1].replace(".py", "")
            self.registry.reload_skill(skill_id)

    def on_created(self, event: FileSystemEvent) -> None:
        """文件创建事件"""
        if event.is_directory:
            return
        if event.src_path.endswith(".py"):
            logger.info(f"New skill file created: {event.src_path}")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """文件删除事件"""
        if event.is_directory:
            return
        if event.src_path.endswith(".py"):
            skill_id = event.src_path.split("/")[-1].replace(".py", "")
            logger.info(f"Skill file deleted: {event.src_path}")


# 全局注册中心实例
_global_agent_registry: AgentRegistry | None = None
_global_skill_registry: SkillRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """获取全局 Agent 注册中心"""
    global _global_agent_registry
    if _global_agent_registry is None:
        _global_agent_registry = AgentRegistry()
    return _global_agent_registry


def get_skill_registry() -> SkillRegistry:
    """获取全局 Skill 注册中心"""
    global _global_skill_registry
    if _global_skill_registry is None:
        _global_skill_registry = SkillRegistry()
    return _global_skill_registry