"""Samling af agent-relaterede utilities."""

from .registry import AgentConfig, AgentRegistry, get_agent_registry
from .research_agent import create_research_agent, run_research_agent
from .quick_check_agent import create_quick_check_agent, run_quick_check_agent

# Modern LangGraph implementations
from .research_agent_langgraph import (
    ResearchOrchestrator,
    create_research_orchestrator,
    run_research_agent as run_research_agent_langgraph
)

__all__ = [
    "AgentConfig",
    "AgentRegistry",
    "get_agent_registry",
    # Legacy implementations
    "create_research_agent",
    "run_research_agent",
    "create_quick_check_agent",
    "run_quick_check_agent",
    # Modern LangGraph implementations
    "ResearchOrchestrator",
    "create_research_orchestrator",
    "run_research_agent_langgraph",
]
