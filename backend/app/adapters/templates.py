"""Chargement et validation des templates YAML au démarrage."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class TemplateSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    status: str = Field(pattern=r"^(PROVIDED|NOT_PROVIDED)$")
    citation_required: bool = False


class DocumentTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    sections: list[TemplateSection] = Field(min_length=1)


def load_templates(directory: str | Path) -> dict[str, DocumentTemplate]:
    root = Path(directory)
    templates: dict[str, DocumentTemplate] = {}
    for path in sorted(root.glob("*.yaml")):
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        template = DocumentTemplate.model_validate(raw)
        templates[template.id] = template
    if not templates:
        raise RuntimeError("no_document_templates")
    return templates
