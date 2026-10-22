"""LangChain BaseChatModel adapter for UIT vLLM endpoints.

This module provides UITChatModel, adapting vLLM instances hosted at https://llm.uit.edu.vn/*
for LangChain without relying on unsupported automatic tool-call parser flags.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from openai import OpenAI
from pydantic import Field, PrivateAttr

from uit_middleware import UITToolMiddleware


class UITChatModel(BaseChatModel):
    """Custom LangChain chat model wrapping UIT-hosted vLLM endpoints with middleware."""

    base_url: str = "https://llm.uit.edu.vn/gemma/v1"
    api_key: str = Field(..., description="API key required at initialisation")
    model_name: str = "gemma-4-26b"
    temperature: float = 0.0
    max_tokens: int = 512
    bound_tools: list[dict[str, Any]] = Field(default_factory=list)
    _client: OpenAI | None = PrivateAttr(None)

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def bind_tools(self, tools: Any, **_: Any) -> "UITChatModel":
        """Bind tool definitions to the model instance."""
        formatted_tools: list[dict[str, Any]] = []
        for t in tools:
            if hasattr(t, "name") and hasattr(t, "description"):
                param_spec = {}
                if hasattr(t, "args_schema") and t.args_schema:
                    try:
                        param_spec = t.args_schema.model_json_schema()
                    except Exception:
                        param_spec = getattr(t, "args", {})
                else:
                    param_spec = getattr(t, "args", {})

                schema = {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": param_spec,
                    },
                }
                formatted_tools.append(schema)
            elif isinstance(t, dict):
                formatted_tools.append(t)

        return self.__class__(
            base_url=self.base_url,
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            bound_tools=formatted_tools,
        )

    def _convert_messages_to_dicts(
        self, messages: list[BaseMessage]
    ) -> list[dict[str, Any]]:
        """Convert LangChain message sequence into OpenAI payload format."""
        dicts: list[dict[str, Any]] = []
        for m in messages:
            if isinstance(m, SystemMessage):
                dicts.append({"role": "system", "content": m.content})
            elif isinstance(m, HumanMessage):
                dicts.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage):
                content = m.content or ""
                if getattr(m, "tool_calls", None):
                    for tc in m.tool_calls:
                        content += (
                            f"\n<tool_call>\n"
                            f'{{"name": "{tc["name"]}", "arguments": {json.dumps(tc["args"])}}}\n'
                            f"</tool_call>"
                        )
                dicts.append({"role": "assistant", "content": content})
            elif isinstance(m, ToolMessage):
                dicts.append(
                    {
                        "role": "user",
                        "content": f"[Tool Result for {m.tool_call_id or 'tool'}]: {m.content}",
                    }
                )
            else:
                dicts.append({"role": "user", "content": str(m.content)})
        return dicts

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Execute inference request against UIT vLLM endpoint with middleware transformation."""
        client = self._get_client()
        raw_msgs = self._convert_messages_to_dicts(messages)

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": raw_msgs,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.bound_tools:
            payload["tools"] = self.bound_tools

        prepared = UITToolMiddleware.prepare_request(payload, self.base_url)

        resp = client.chat.completions.create(
            model=prepared["model"],
            messages=prepared["messages"],
            temperature=prepared.get("temperature", self.temperature),
            max_tokens=prepared.get("max_tokens", self.max_tokens),
        )

        content = resp.choices[0].message.content or ""
        tool_calls, cleaned = UITToolMiddleware.parse_tool_calls_from_text(content)

        if tool_calls:
            lc_calls: list[dict[str, Any]] = []
            for tc in tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                try:
                    args_dict = json.loads(args) if isinstance(args, str) else args
                except Exception:
                    args_dict = {"raw": args}
                lc_calls.append(
                    {
                        "name": fn.get("name"),
                        "args": args_dict,
                        "id": tc.get("id"),
                    }
                )
            ai_msg = AIMessage(content=cleaned or "", tool_calls=lc_calls)
        else:
            ai_msg = AIMessage(content=content)

        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        """Not supported for UITChatModel."""
        raise NotImplementedError("with_structured_output is not supported on UITChatModel")

    @property
    def _llm_type(self) -> str:
        """Type identifier for the model."""
        return "uit-vllm-chat-model"
