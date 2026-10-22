"""Personal Agent: LangChain create_agent with multi-provider model and memory-augmented system prompt."""

from __future__ import annotations
from langchain_core.tools.base import BaseTool

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.language_models.chat_models import BaseChatModel

from config import MODEL_CALL_LIMIT, TOOL_CALL_LIMIT
from memory_catalog import render_memory_context, scan_memory
from observer import ObserverMiddleware
import paths
from prompts import build_system_prompt
from providers import get_llm
from skill_catalog import Catalog, render_catalog, scan_skills
from tools import (
    list_files,
    memory_delete,
    memory_list,
    memory_read,
    memory_write,
    read_file,
    use_skill,
    write_file,
)

TOOLS: list[BaseTool] = [
    list_files,
    read_file,
    write_file,
    use_skill,
    memory_list,
    memory_read,
    memory_write,
    memory_delete,
]


def build_model(config=None) -> BaseChatModel:
    """Instantiate the active LLM via the unified provider layer."""
    return get_llm()


def load_catalog() -> Catalog:
    """Scan and return the current workspace skills catalog."""
    return scan_skills(paths.WORKSPACE_DIR)


def load_memory_context() -> str:
    """Scan and render active memory context for the prompt."""
    return render_memory_context(paths.MEMORY_DIR)


def system_prompt() -> str:
    """Construct dynamic system prompt with active skills and memory context."""
    catalog = load_catalog()
    return build_system_prompt(
        catalog_block=render_catalog(catalog),
        memory_block=load_memory_context(),
    )


def capabilities() -> dict:
    """Summary of agent capabilities and registered resources."""
    catalog = load_catalog()
    memories = scan_memory(paths.MEMORY_DIR)
    return {
        "tools": [t.name for t in TOOLS],
        "skills": catalog.metadata(),
        "skill_diagnostics": catalog.diagnostics,
        "memory_count": len(memories),
    }


def build_agent(model: BaseChatModel):
    """Build LangChain Agent with limits and observer middleware."""
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=system_prompt(),
        middleware=[
            ModelCallLimitMiddleware(run_limit=MODEL_CALL_LIMIT, exit_behavior="end"),
            ToolCallLimitMiddleware(run_limit=TOOL_CALL_LIMIT),
            ObserverMiddleware(),
        ],
    )
