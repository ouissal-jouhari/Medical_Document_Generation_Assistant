from typing import Any, Protocol


class LlmProvider(Protocol):
    """Génération d'une sortie structurée validée par un schéma JSON."""

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]: ...
