"""Versioned prompts on disk: ``<root>/<name>/v<N>/system.txt`` and ``user.txt``.

Prompts live next to the code that uses them, are reviewed like code, and a new version is
a new folder, so an eval can compare v1 and v2 side by side. ``user.txt`` is a
``str.format`` template; ``system.txt`` is optional.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ai_app_chassis.llm import Message

VERSION = re.compile(r"^v(\d+)$")


class PromptNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    system: str | None
    user_template: str

    @property
    def id(self) -> str:
        """Stable identifier for ledgers and eval reports, e.g. ``summarize/v2``."""
        return f"{self.name}/{self.version}"

    def render(self, **variables: object) -> list[Message]:
        messages = [Message("system", self.system)] if self.system else []
        return [*messages, Message("user", self.user_template.format(**variables))]


class PromptStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def versions(self, name: str) -> list[str]:
        folder = self.root / name
        if not folder.is_dir():
            return []
        found = [p.name for p in folder.iterdir() if p.is_dir() and VERSION.match(p.name)]
        return sorted(found, key=lambda v: int(v[1:]))

    def load(self, name: str, version: str = "latest") -> Prompt:
        versions = self.versions(name)
        if not versions:
            raise PromptNotFoundError(f"no versions of prompt {name!r} under {self.root}")
        chosen = versions[-1] if version == "latest" else version
        folder = self.root / name / chosen
        user = folder / "user.txt"
        if not user.is_file():
            raise PromptNotFoundError(f"prompt {name}/{chosen} has no user.txt")
        system = folder / "system.txt"
        return Prompt(
            name=name,
            version=chosen,
            system=system.read_text(encoding="utf-8").strip() if system.is_file() else None,
            user_template=user.read_text(encoding="utf-8").strip(),
        )
