from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    """Route publique volontaire (sonde de démarrage conteneur) : ne renvoie aucune donnée."""
    return {"status": "ok"}
