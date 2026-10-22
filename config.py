"""Project configuration: UI constants, execution limits, and settings loader."""

from __future__ import annotations

from providers import ProviderConfig, get_provider_config

PROJECT_NAME = "personal-agent"
APP_TITLE = "Personal Agent"
CAPABILITY_TEXT = (
    "Tools: list_files, read_file, write_file, use_skill, memory_list, memory_read, "
    "memory_write, memory_delete. Multi-provider LLM layer. File-system memory. No shell execution."
)

MODEL_CALL_LIMIT = 1000
TOOL_CALL_LIMIT = 1000
RECURSION_LIMIT = 1000


def load_settings() -> tuple[ProviderConfig | None, list[str]]:
    """Load and validate provider settings.

    Returns (config, []) on success or (None, [error_message]) on failure.
    """
    try:
        config = get_provider_config()
        return config, []
    except ValueError as exc:
        return None, [str(exc)]
