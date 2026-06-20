"""Harness Registry 测试"""

import pytest

from agent_forge.harness import AgentRegistry, SkillRegistry, Skill


class MockAgent:
    """模拟 Agent"""

    def __init__(self, id: str, name: str, capabilities: list[str] = None):
        self.id = id
        self.name = name
        self.capabilities = capabilities or []


class TestAgentRegistry:
    """Agent 注册中心测试"""

    def test_register_agent(self):
        """测试注册 Agent"""
        registry = AgentRegistry()
        agent = MockAgent("agent-1", "Test Agent", ["code", "analysis"])

        registry.register(agent)
        assert len(registry) == 1
        assert registry.get("agent-1") == agent

    def test_unregister_agent(self):
        """测试注销 Agent"""
        registry = AgentRegistry()
        agent = MockAgent("agent-1", "Test Agent")

        registry.register(agent)
        registry.unregister("agent-1")

        assert len(registry) == 0
        assert registry.get("agent-1") is None

    def test_list_all(self):
        """测试列出所有 Agent"""
        registry = AgentRegistry()
        registry.register(MockAgent("agent-1", "Agent 1"))
        registry.register(MockAgent("agent-2", "Agent 2"))

        agents = registry.list_all()
        assert len(agents) == 2

    def test_query_by_capability(self):
        """测试按能力查询"""
        registry = AgentRegistry()
        registry.register(MockAgent("agent-1", "Code Agent", ["code"]))
        registry.register(MockAgent("agent-2", "Analysis Agent", ["analysis"]))

        code_agents = registry.query_by_capability("code")
        assert len(code_agents) == 1
        assert code_agents[0].id == "agent-1"

    def test_query_by_capabilities(self):
        """测试按能力列表查询"""
        registry = AgentRegistry()
        registry.register(MockAgent("agent-1", "Full Agent", ["code", "analysis"]))
        registry.register(MockAgent("agent-2", "Partial Agent", ["code"]))

        agents = registry.query_by_capabilities(["code", "analysis"])
        assert len(agents) == 1
        assert agents[0].id == "agent-1"


class TestSkillRegistry:
    """Skill 注册中心测试"""

    def test_register_skill(self):
        """测试注册 Skill"""
        registry = SkillRegistry()
        skill = Skill("skill-1", "Test Skill")

        registry.register(skill)
        assert len(registry) == 1
        assert registry.get("skill-1") == skill

    def test_unregister_skill(self):
        """测试注销 Skill"""
        registry = SkillRegistry()
        skill = Skill("skill-1", "Test Skill")

        registry.register(skill)
        registry.unregister("skill-1")

        assert len(registry) == 0

    def test_list_all(self):
        """测试列出所有 Skill"""
        registry = SkillRegistry()
        registry.register(Skill("skill-1", "Skill 1"))
        registry.register(Skill("skill-2", "Skill 2"))

        skills = registry.list_all()
        assert len(skills) == 2