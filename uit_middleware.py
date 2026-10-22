"""Middleware for adapting OpenAI-compatible requests and responses for UIT vLLM endpoints.

This module provides request payload transformation and response tool-call parsing
tailored for vLLM instances deployed at https://llm.uit.edu.vn/*, which do not
support standard automatic tool parsing flags.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any


class UITToolMiddleware:
    """Middleware adapting OpenAI tool-calling payloads for UIT vLLM instances."""

    @staticmethod
    def is_uit_endpoint(base_url: str) -> bool:
        """Check if the given endpoint base URL points to a UIT LLM service."""
        return "llm.uit.edu.vn" in (base_url or "").lower()

    @staticmethod
    def format_system_prompt_with_tools(
        system_content: str | None,
        tools: list[dict[str, Any]],
    ) -> str:
        """Inject tool schemas and formatting instructions into the system prompt."""
        tool_defs: list[dict[str, Any]] = []
        for t in tools:
            if t.get("type") == "function" and "function" in t:
                tool_defs.append(t["function"])
            else:
                tool_defs.append(t)

        tools_json = json.dumps(tool_defs, indent=2)

        instruction = (
            "You have access to the following tools:\n\n"
            f"{tools_json}\n\n"
            "When you need to call a tool, format each tool call strictly inside "
            "<tool_call> and </tool_call> tags in valid JSON:\n"
            "<tool_call>\n"
            '{"name": "function_name", "arguments": {"param_name": "value"}}\n'
            "</tool_call>\n\n"
            "Rules:\n"
            "- You may invoke multiple tools by outputting multiple consecutive <tool_call>...</tool_call> blocks.\n"
            "- Only call tools if necessary. If no tool is needed, respond directly with your answer."
        )

        if system_content and system_content.strip():
            return f"{system_content.strip()}\n\n{instruction}"
        return instruction

    @classmethod
    def prepare_request(
        cls,
        payload: dict[str, Any],
        base_url: str = "",
    ) -> dict[str, Any]:
        """Intercept an OpenAI chat completion payload to strip 'tools' and inject prompt guidance.

        Never mutates the input payload; returns a shallow copy.
        Identity when tools is empty or the host is not UIT.
        """
        modified = dict(payload)
        tools = modified.get("tools")

        if tools and (not base_url or cls.is_uit_endpoint(base_url)):
            messages = list(modified.get("messages", []))

            system_idx = next(
                (i for i, m in enumerate(messages) if m.get("role") == "system"), None
            )
            if system_idx is not None:
                orig_system = messages[system_idx].get("content", "")
                new_system = cls.format_system_prompt_with_tools(orig_system, tools)
                messages[system_idx] = dict(messages[system_idx], content=new_system)
            else:
                new_system = cls.format_system_prompt_with_tools(None, tools)
                messages.insert(0, {"role": "system", "content": new_system})

            modified["messages"] = messages
            modified.pop("tools", None)
            modified.pop("tool_choice", None)

        return modified

    @classmethod
    def parse_tool_calls_from_text(
        cls,
        text: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Parse tool calls from raw assistant text content.

        Tries, in order:
        1. <tool_call> blocks containing JSON
        2. <tool_call> blocks containing Qwen XML (<function=...> / <parameter=...>)
        3. Gemma call:name{...} markers
        4. Whole-message JSON object
        """
        if not text:
            return [], None

        tool_calls: list[dict[str, Any]] = []

        # 1 & 2: <tool_call>...</tool_call>
        tag_pattern = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
        matches = list(tag_pattern.finditer(text))

        if matches:
            for m in matches:
                body = m.group(1).strip()
                if body.startswith("```"):
                    body = re.sub(r"^```(?:json)?\s*", "", body)
                    body = re.sub(r"\s*```$", "", body)
                    body = body.strip()

                try:
                    data = json.loads(body)
                    if isinstance(data, dict) and "name" in data:
                        args = data.get("arguments", {})
                        args_str = args if isinstance(args, str) else json.dumps(args)
                        tool_calls.append(
                            {
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "type": "function",
                                "function": {
                                    "name": data["name"],
                                    "arguments": args_str,
                                },
                            }
                        )
                        continue
                except Exception:
                    pass

                # Qwen XML
                fn_match = re.search(
                    r"<function=([^>]+)>(.*?)</function>", body, re.DOTALL
                )
                if fn_match:
                    func_name = fn_match.group(1).strip()
                    param_body = fn_match.group(2)
                    params: dict[str, Any] = {}
                    for p in re.finditer(
                        r"<parameter=([^>]+)>(.*?)</parameter>", param_body, re.DOTALL
                    ):
                        k = p.group(1).strip()
                        v = p.group(2).strip()
                        try:
                            params[k] = json.loads(v)
                        except Exception:
                            params[k] = v
                    tool_calls.append(
                        {
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": json.dumps(params),
                            },
                        }
                    )

            cleaned_text = tag_pattern.sub("", text).strip()
            return tool_calls, (cleaned_text or None)

        # 3: Gemma call:name{...}
        gemma_call_match = list(
            re.finditer(r"call:([a-zA-Z0-9_-]+)\{(.*?)\}", text, re.DOTALL)
        )
        if gemma_call_match:
            for gm in gemma_call_match:
                func_name = gm.group(1).strip()
                raw_args = gm.group(2).strip()
                args_dict: dict[str, Any] = {}
                try:
                    args_dict = json.loads("{" + raw_args + "}")
                except Exception:
                    for pair in re.split(r",\s*(?=[a-zA-Z0-9_-]+[:=])", raw_args):
                        if ":" in pair:
                            k, v = pair.split(":", 1)
                        elif "=" in pair:
                            k, v = pair.split("=", 1)
                        else:
                            continue
                        k = k.strip()
                        cleaned_val = v.strip().strip("'\"").lower()
                        if cleaned_val.isdigit():
                            args_dict[k] = int(cleaned_val)
                        elif cleaned_val == "true":
                            args_dict[k] = True
                        elif cleaned_val == "false":
                            args_dict[k] = False
                        else:
                            args_dict[k] = cleaned_val

                tool_calls.append(
                    {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": func_name,
                            "arguments": json.dumps(args_dict),
                        },
                    }
                )
            cleaned_text = re.sub(
                r"call:[a-zA-Z0-9_-]+\{.*?\}", "", text, flags=re.DOTALL
            ).strip()
            return tool_calls, (cleaned_text or None)

        # 4: Whole-message JSON object
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                if isinstance(data, dict) and "name" in data:
                    args = data.get("arguments", {})
                    args_str = args if isinstance(args, str) else json.dumps(args)
                    tool_calls.append(
                        {
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {
                                "name": data["name"],
                                "arguments": args_str,
                            },
                        }
                    )
                    return tool_calls, None
            except Exception:
                pass

        return [], text

    @classmethod
    def process_response(cls, response: dict[str, Any]) -> dict[str, Any]:
        """Process an OpenAI chat completion response dictionary to extract parsed tool calls."""
        resp_copy = dict(response)
        choices = resp_copy.get("choices", [])
        if not choices:
            return resp_copy

        new_choices: list[dict[str, Any]] = []
        for choice in choices:
            c = dict(choice)
            msg = dict(c.get("message", {}))

            if not msg.get("tool_calls"):
                content = msg.get("content") or ""
                tool_calls, cleaned_content = cls.parse_tool_calls_from_text(content)
                if tool_calls:
                    msg["tool_calls"] = tool_calls
                    msg["content"] = cleaned_content
                    if c.get("finish_reason") == "stop":
                        c["finish_reason"] = "tool_calls"

            c["message"] = msg
            new_choices.append(c)

        resp_copy["choices"] = new_choices
        return resp_copy
