"""Stockage local des Superbills déposées. Le chiffrement au repos est assuré par le volume hôte
(ADR 0003). Les fichiers sont nommés par un identifiant aléatoire, jamais par le nom d'origine."""

from pathlib import Path
from uuid import uuid4


class LocalFileStore:
    def __init__(self, root: str) -> None:
        self._root = Path(root) / "superbills"

    def save(self, content: bytes) -> str:
        self._root.mkdir(parents=True, exist_ok=True)
        key = uuid4().hex
        (self._root / key).write_bytes(content)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def _path(self, key: str) -> Path:
        if not key.isalnum():  # clé produite par save() : défense contre toute traversée de chemin
            raise ValueError("clé de stockage invalide")
        return self._root / key
