"""Unified language model factory supporting UIT and OpenAI Chat Completions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

import paths
from uit_chat_model import UITChatModel


@dataclass(frozen=True)
class ProviderConfig:
    """Parsed and validated configuration for the active LLM provider."""

    mode: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    path: str = "/v1/chat/completions"


def resolve_openai_base_url(base_url: str, path: str = "/v1/chat/completions") -> str:
    """Resolve the client base URL for OpenAI-compatible endpoints."""
    clean_base = (base_url or "").strip().rstrip("/")
    if not path or not path.strip():
        return clean_base

    clean_path = ("/" + path.strip().strip("/")).rstrip("/")
    if clean_path.endswith("/chat/completions"):
        prefix = clean_path[: -len("/chat/completions")].rstrip("/")
        if prefix and not clean_base.endswith(prefix):
            return f"{clean_base}{prefix}"
        return clean_base

    return f"{clean_base}{clean_path}"


def get_provider_config(mode_override: str | None = None) -> ProviderConfig:
    """Read and validate the LLM configuration from environment variables."""
    load_dotenv(paths.ENV_PATH, override=False)

    raw_mode = (mode_override or os.getenv("LLM_API_MODE", "UIT")).strip()
    norm_mode = raw_mode.lower()

    model = os.getenv("LLM_API_MODEL")
    if not model:
        raise ValueError("LLM_API_MODEL must be configured in environment.")

    base_url = os.getenv("LLM_API_BASEURL")
    api_key = os.getenv("LLM_API_KEY")
    path = os.getenv("LLM_API_PATH", "/v1/chat/completions")

    if norm_mode == "uit":
        return ProviderConfig(
            mode="UIT",
            model=model,
            base_url=base_url or "https://llm.uit.edu.vn/gemma",
            api_key=api_key,
            path=path,
        )

    if norm_mode in (
        "openai",
        "openai chat completions",
        "openai_chat_completions",
        "oai",
        "openai cc",
    ):
        return ProviderConfig(
            mode="OpenAI Chat Completions",
            model=model,
            base_url=base_url,
            api_key=api_key or "none",
            path=path,
        )

    raise ValueError(f"Unsupported LLM_API_MODE: '{raw_mode}'.")


def get_active_provider_info() -> dict[str, str]:
    """Return metadata describing the currently active LLM provider from .env."""
    config = get_provider_config()
    resolved = (
        resolve_openai_base_url(config.base_url, config.path)
        if config.base_url
        else ""
    )
    return {
        "mode": config.mode,
        "model": config.model,
        "base_url": resolved,
    }


def get_llm(
    model_type: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 65536,
) -> BaseChatModel:
    """Instantiate a configured ChatModel driven by environment configuration."""
    config = get_provider_config(model_type)

    env_max = os.getenv("LLM_API_MAX_TOKENS")
    effective_max = int(env_max.strip()) if env_max and env_max.strip().isdigit() else max_tokens

    if config.mode == "UIT":
        if not config.api_key:
            raise ValueError("LLM_API_KEY must be configured for UIT mode.")
        resolved_url = resolve_openai_base_url(config.base_url or "", config.path)
        return UITChatModel(
            base_url=resolved_url,
            api_key=config.api_key,
            model_name=config.model,
            temperature=temperature,
            max_tokens=effective_max,
        )

    if config.mode == "OpenAI Chat Completions":
        from langchain_openai import ChatOpenAI

        if not config.base_url:
            raise ValueError(
                "LLM_API_BASEURL is required for OpenAI Chat Completions mode."
            )

        resolved_url = resolve_openai_base_url(config.base_url, config.path)
        return ChatOpenAI(
            base_url=resolved_url,
            api_key=config.api_key or "none",
            model=config.model,
            temperature=temperature,
            max_tokens=effective_max,
        )

    raise ValueError(f"Unsupported LLM_API_MODE: '{config.mode}'.")
