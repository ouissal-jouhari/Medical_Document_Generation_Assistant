"""Coordonnées de la clinique (SRS 9.1 ClinicProfile, F-24, H-01).

Constantes : lues de la configuration, aucune interface ne les modifie. Un document approuvé
en garde un instantané figé (H-02).
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ClinicProfile:
    name: str
    address: str
    city: str
    postal_code: str
    phone: str
    email: str
    website: str

    def snapshot(self) -> dict[str, str]:
        return asdict(self)
