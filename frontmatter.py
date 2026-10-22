"""Utilities for parsing and serializing YAML frontmatter."""

from __future__ import annotations

import yaml


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split text into a frontmatter dict and stripped body.

    Raises ValueError if opening or closing delimiters are missing or YAML is invalid.
    """
    clean_text = text.lstrip("\ufeff")
    lines = clean_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing opening frontmatter delimiter ('---')")

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            frontmatter_raw = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1:]).lstrip("\r\n")
            try:
                data = yaml.safe_load(frontmatter_raw)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid YAML in frontmatter: {exc}") from exc

            if data is None:
                data = {}
            elif not isinstance(data, dict):
                raise ValueError("Frontmatter must be a YAML mapping")

            return data, body

    raise ValueError("Missing closing frontmatter delimiter ('---')")


def parse_frontmatter(text: str) -> dict:
    """Parse and return only the frontmatter dictionary."""
    data, _ = split_frontmatter(text)
    return data


def format_frontmatter(data: dict, body: str) -> str:
    """Format frontmatter mapping and body into markdown with delimiters."""
    yaml_lines = []
    for key, val in data.items():
        if isinstance(val, str):
            escaped = val.replace('\\', '\\\\').replace('"', '\\"')
            yaml_lines.append(f'{key}: "{escaped}"')
        else:
            yaml_lines.append(f"{key}: {val}")
    fm_text = "\n".join(yaml_lines)
    stripped_body = body.strip("\r\n")
    if stripped_body:
        return f"---\n{fm_text}\n---\n\n{stripped_body}\n"
    return f"---\n{fm_text}\n---\n"
