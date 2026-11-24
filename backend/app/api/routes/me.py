from fastapi import APIRouter

from app.api.deps import ClinicianUser

router = APIRouter(tags=["identity"])


@router.get("/me")
def me(user: ClinicianUser) -> dict[str, str]:
    """Identité du clinicien connecté (affichage après connexion, E-01)."""
    return {"id": str(user.id), "display_name": user.display_name}
