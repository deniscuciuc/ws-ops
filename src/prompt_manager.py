"""Prompt management — loads YAML prompts and renders them with Jinja2.

Prompts live in YAML files under prompts/. Never hardcode prompt strings in code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import Template


@dataclass
class Prompt:
    name: str
    version: str
    system: str
    user_template: str
    output_schema: dict


class PromptManager:
    """Loads and caches YAML prompts, renders user templates with Jinja2."""

    def __init__(self, prompts_dir: str) -> None:
        self._dir = Path(prompts_dir).expanduser()
        self._cache: dict[str, Prompt] = {}

    def get(self, name: str) -> Prompt:
        """Load a prompt by name from YAML file (cached after first load)."""
        if name not in self._cache:
            path = self._dir / f"{name}.yaml"
            if not path.exists():
                raise FileNotFoundError(
                    f"Prompt '{name}' not found at {path}"
                )
            data = yaml.safe_load(path.read_text())
            if not isinstance(data, dict):
                raise ValueError(f"Invalid prompt file: {path}")
            self._cache[name] = Prompt(
                name=data["name"],
                version=data["version"],
                system=data["system"],
                user_template=data["user"],
                output_schema=data.get("output_schema", {}),
            )
        return self._cache[name]

    def render_user(self, prompt_name: str, **kwargs: object) -> str:
        """Load a prompt and render its user template with the given variables."""
        prompt = self.get(prompt_name)
        return Template(prompt.user_template).render(**kwargs)
