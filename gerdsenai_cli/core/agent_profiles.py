"""Agent profiles: named personas bound to a provider + model.

A profile pairs a persona (system prompt) with a specific provider/model so a
user can switch the agent's "brain" and behaviour together — e.g. a local
``reviewer`` on Ollama and a cloud ``architect`` on Claude. Profiles are
persisted in settings; activating one updates ``current_model`` so the existing
model path picks it up.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..config.manager import ConfigManager


@dataclass
class AgentProfile:
    """A named persona bound to a provider/model."""

    name: str
    model: str
    provider: str = ""  # informational label: ollama | anthropic | vllm | ...
    system_prompt: str = ""
    description: str = ""
    temperature: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> AgentProfile:
        return cls(
            name=name,
            model=str(data.get("model", "")),
            provider=str(data.get("provider", "")),
            system_prompt=str(data.get("system_prompt", "")),
            description=str(data.get("description", "")),
            temperature=data.get("temperature"),
        )


class AgentProfileManager:
    """Load, persist, and activate agent profiles via the config manager."""

    def __init__(self, config: ConfigManager | None = None) -> None:
        self.config = config or ConfigManager()

    def _profiles_dict(self) -> dict[str, dict[str, Any]]:
        return dict(self.config.get_settings().agent_profiles)

    def list(self) -> list[AgentProfile]:
        return [
            AgentProfile.from_dict(name, data)
            for name, data in self._profiles_dict().items()
        ]

    def get(self, name: str) -> AgentProfile | None:
        data = self._profiles_dict().get(name)
        return AgentProfile.from_dict(name, data) if data is not None else None

    def add(self, profile: AgentProfile) -> bool:
        profiles = self._profiles_dict()
        stored = profile.to_dict()
        stored.pop("name", None)  # name is the key
        profiles[profile.name] = stored
        return self.config.update_setting("agent_profiles", profiles)

    def remove(self, name: str) -> bool:
        profiles = self._profiles_dict()
        if name not in profiles:
            return False
        del profiles[name]
        ok = self.config.update_setting("agent_profiles", profiles)
        # Clear active pointer if it referenced the removed profile.
        if ok and self.config.get_settings().active_agent_profile == name:
            self.config.update_setting("active_agent_profile", "")
        return ok

    def get_active(self) -> AgentProfile | None:
        name = self.config.get_settings().active_agent_profile
        return self.get(name) if name else None

    def set_active(self, name: str) -> AgentProfile | None:
        """Activate a profile: set the pointer and switch ``current_model``."""
        profile = self.get(name)
        if profile is None:
            return None
        self.config.update_setting("active_agent_profile", name)
        if profile.model:
            self.config.update_setting("current_model", profile.model)
        return profile

    def clear_active(self) -> bool:
        return self.config.update_setting("active_agent_profile", "")
