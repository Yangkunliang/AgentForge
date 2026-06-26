"""Agent 基类和内置 Agent"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_forge.llm import LLMProvider, LLMConfig

logger = logging.getLogger("agent_forge.agents")


@dataclass
class AgentConfig:
    """Agent 配置"""

    id: str
    name: str
    capabilities: list[str] = field(default_factory=list)
    model: str = "gpt-4o"
    temperature: float = 0.7


@dataclass
class Bid:
    """竞标信息"""

    agent_id: str
    confidence: float
    estimated_time_ms: int
    reason: str = ""


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(
        self,
        config: AgentConfig,
        llm_provider: LLMProvider,
    ):
        self.config = config
        self.llm_provider = llm_provider

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def capabilities(self) -> list[str]:
        return self.config.capabilities

    async def evaluate_task(self, description: str, required_capabilities: list[str]) -> Bid:
        """评估任务并返回竞标信息"""
        # 1. 检查能力匹配
        matched_caps = set(self.capabilities) & set(required_capabilities)
        confidence = len(matched_caps) / len(required_capabilities) if required_capabilities else 0.5

        # 2. 使用 LLM 评估任务适合度
        evaluation_prompt = f"""评估 Agent '{self.name}' 是否适合执行以下任务：

任务描述：{description}
所需能力：{', '.join(required_capabilities)}
Agent 能力：{', '.join(self.capabilities)}

返回评估：
- 适合度评分（0-1）
- 预计执行时间（毫秒）
- 评估理由
"""
        try:
            response = await self.llm_provider.complete(
                evaluation_prompt,
                LLMConfig(model=self.config.model, temperature=0.3),
            )

            # 解析 LLM 响应（简化处理）
            estimated_time_ms = 5000  # 默认 5s
            reason = f"Matched capabilities: {', '.join(matched_caps)}"

            # 如果置信度低，使用降级值
            if confidence < 0.3:
                confidence = 0.3

            return Bid(
                agent_id=self.id,
                confidence=confidence,
                estimated_time_ms=estimated_time_ms,
                reason=reason,
            )
        except Exception as e:
            logger.error(f"Error evaluating task for agent {self.id}: {e}")
            return Bid(
                agent_id=self.id,
                confidence=0.5,
                estimated_time_ms=10000,
                reason="Fallback evaluation",
            )

    @abstractmethod
    async def execute(self, task: dict) -> dict:
        """执行任务"""
        pass


class CodeWriterAgent(BaseAgent):
    """代码生成 Agent（仅生成代码文本，不执行代码）。

    ⚠️  此 Agent 只负责用 LLM 生成代码内容，返回给调用方或用户。
        如需在沙箱中执行代码，请使用 agents/coder.py 中的 CoderAgent，
        或通过 skills/code_executor.py 中的 code_executor Skill。

        严禁在此 Agent 内直接执行代码——任何代码执行必须经过 SandboxManager。
    """

    def __init__(self, config: AgentConfig, llm_provider: LLMProvider):
        super().__init__(config, llm_provider)
        if "code" not in config.capabilities:
            config.capabilities.append("code")

    async def execute(self, task: dict) -> dict:
        """生成代码（不执行）。如需执行，使用 CoderAgent 或 code_executor Skill。"""
        prompt = f"""作为代码生成 Agent，根据以下任务生成代码：

{task}

请提供：
1. 代码实现
2. 测试用例
3. 复杂度分析
"""
        try:
            response = await self.llm_provider.complete(
                prompt,
                LLMConfig(model=self.config.model, temperature=self.config.temperature),
            )
            return {
                "status": "success",
                "result": response.content,
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
            }
        except Exception as e:
            logger.error(f"CodeWriterAgent execution error: {e}")
            return {"status": "error", "error": str(e)}


# 向后兼容别名，避免现有代码 import 失败
CodeAgent = CodeWriterAgent


class AnalysisAgent(BaseAgent):
    """分析 Agent"""

    def __init__(self, config: AgentConfig, llm_provider: LLMProvider):
        super().__init__(config, llm_provider)
        if "analysis" not in config.capabilities:
            config.capabilities.append("analysis")

    async def execute(self, task: dict) -> dict:
        """执行分析任务"""
        prompt = f"""作为分析 Agent，执行以下分析任务：

{task}

请提供：
1. 数据分析
2. 发现和洞察
3. 建议和结论
"""
        try:
            response = await self.llm_provider.complete(
                prompt,
                LLMConfig(model=self.config.model, temperature=self.config.temperature),
            )
            return {
                "status": "success",
                "result": response.content,
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
            }
        except Exception as e:
            logger.error(f"Analysis agent execution error: {e}")
            return {"status": "error", "error": str(e)}


class SearchAgent(BaseAgent):
    """搜索 Agent"""

    def __init__(self, config: AgentConfig, llm_provider: LLMProvider):
        super().__init__(config, llm_provider)
        if "search" not in config.capabilities:
            config.capabilities.append("search")

    async def execute(self, task: dict) -> dict:
        """执行搜索任务"""
        prompt = f"""作为搜索 Agent，执行以下搜索任务：

{task}

请提供：
1. 相关资源列表
2. 关键信息摘要
3. 可靠性评估
"""
        try:
            response = await self.llm_provider.complete(
                prompt,
                LLMConfig(model=self.config.model, temperature=self.config.temperature),
            )
            return {
                "status": "success",
                "result": response.content,
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
            }
        except Exception as e:
            logger.error(f"Search agent execution error: {e}")
            return {"status": "error", "error": str(e)}


def create_agent(agent_type: str, agent_id: str, name: str, llm_provider: LLMProvider) -> BaseAgent:
    """创建 Agent 工厂函数"""
    config = AgentConfig(
        id=agent_id,
        name=name,
        capabilities=[agent_type],
    )

    agents = {
        "code": CodeWriterAgent,
        "analysis": AnalysisAgent,
        "search": SearchAgent,
    }

    agent_class = agents.get(agent_type, BaseAgent)
    return agent_class(config, llm_provider)
