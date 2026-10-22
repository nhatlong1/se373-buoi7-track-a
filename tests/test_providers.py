"""Tests for the provider layer: mode resolution, base URL normalization, error handling."""

from __future__ import annotations

import pytest
from langchain_openai import ChatOpenAI

from providers import (
    ProviderConfig,
    get_llm,
    get_provider_config,
    resolve_openai_base_url,
)
from uit_chat_model import UITChatModel


def test_resolve_openai_base_url_table():
    """Verify the five reference base-URL resolution cases."""
    assert (
        resolve_openai_base_url("https://llm.uit.edu.vn/gemma", "/v1/chat/completions")
        == "https://llm.uit.edu.vn/gemma/v1"
    )
    assert (
        resolve_openai_base_url("https://llm.uit.edu.vn/gemma/v1", "/v1/chat/completions")
        == "https://llm.uit.edu.vn/gemma/v1"
    )
    assert (
        resolve_openai_base_url("http://ai", "/v1/chat/completions")
        == "http://ai/v1"
    )
    assert (
        resolve_openai_base_url("http://ai/", "v1/chat/completions")
        == "http://ai/v1"
    )
    assert resolve_openai_base_url("http://ai", "") == "http://ai"


def test_provider_mode_aliases(agent_dirs, monkeypatch):
    """Verify accepted alias variations for OpenAI Chat Completions and UIT."""
    monkeypatch.setenv("LLM_API_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_BASEURL", "http://ai")

    for alias in ["openai", "OpenAI Chat Completions", "openai_chat_completions", "oai", "OPENAI CC"]:
        monkeypatch.setenv("LLM_API_MODE", alias)
        cfg = get_provider_config()
        assert cfg.mode == "OpenAI Chat Completions"
        assert cfg.model == "test-model"

    for alias in ["uit", "UIT"]:
        monkeypatch.setenv("LLM_API_MODE", alias)
        cfg = get_provider_config()
        assert cfg.mode == "UIT"


def test_missing_model_error(agent_dirs, monkeypatch):
    monkeypatch.delenv("LLM_API_MODEL", raising=False)
    with pytest.raises(ValueError, match="LLM_API_MODEL must be configured in environment."):
        get_provider_config()


def test_unsupported_mode_error(agent_dirs, monkeypatch):
    monkeypatch.setenv("LLM_API_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_MODE", "anthropic_claude")
    with pytest.raises(ValueError, match="Unsupported LLM_API_MODE: 'anthropic_claude'."):
        get_provider_config()


def test_uit_requires_api_key(agent_dirs, monkeypatch):
    monkeypatch.setenv("LLM_API_MODEL", "gemma-4-26b")
    monkeypatch.setenv("LLM_API_MODE", "UIT")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(ValueError, match="LLM_API_KEY must be configured for UIT mode."):
        get_llm()


def test_openai_requires_base_url(agent_dirs, monkeypatch):
    monkeypatch.setenv("LLM_API_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_API_MODE", "OpenAI Chat Completions")
    monkeypatch.delenv("LLM_API_BASEURL", raising=False)
    with pytest.raises(ValueError, match="LLM_API_BASEURL is required for OpenAI Chat Completions mode."):
        get_llm()


def test_get_llm_factory(agent_dirs, monkeypatch):
    monkeypatch.setenv("LLM_API_MODEL", "qwen-3.8-flash")
    monkeypatch.setenv("LLM_API_MODE", "OpenAI Chat Completions")
    monkeypatch.setenv("LLM_API_BASEURL", "http://ai")
    llm = get_llm()
    assert isinstance(llm, ChatOpenAI)
    assert llm.max_tokens == 65536

    monkeypatch.setenv("LLM_API_MODE", "UIT")
    monkeypatch.setenv("LLM_API_KEY", "secret-uit-token")
    uit_llm = get_llm()
    assert isinstance(uit_llm, UITChatModel)
    assert uit_llm.max_tokens == 65536
