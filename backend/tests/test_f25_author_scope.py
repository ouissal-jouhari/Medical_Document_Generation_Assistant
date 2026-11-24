"""F-25 : un document n'est visible que par son auteur ; la réponse ne révèle pas son existence.

Ressource de test déclarée ici seulement : le modèle réel arrive avec le jalon 3. Ce test sera
rejoué sur chaque nouvelle route (jalons 5 et 6).
"""

from collections.abc import Iterator
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.adapters.author_scoped import AuthorScopedRepository
from app.api.deps import ClinicianUser, get_session
from app.domain.errors import NotFound
from tests.conftest import Api


class TestBase(DeclarativeBase):
    __test__ = False


class Note(TestBase):
    __tablename__ = "test_note"
    __test__ = False

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(Uuid)
    body: Mapped[str] = mapped_column(String(100))


def _mount(api: Api) -> None:
    TestBase.metadata.create_all(api.engine)
    router = APIRouter()

    def repo(session: Session = Depends(get_session)) -> Iterator[AuthorScopedRepository[Note]]:
        yield AuthorScopedRepository(session, Note)

    @router.post("/_t/notes")
    def create(
        user: ClinicianUser, r: AuthorScopedRepository[Note] = Depends(repo)
    ) -> dict[str, str]:
        note = r.add(Note(author_id=user.id, body="secret"))
        return {"id": str(note.id)}

    @router.get("/_t/notes")
    def list_notes(
        user: ClinicianUser, r: AuthorScopedRepository[Note] = Depends(repo)
    ) -> list[str]:
        return [str(n.id) for n in r.list(user.id)]

    @router.get("/_t/notes/{note_id}")
    def read(
        note_id: UUID, user: ClinicianUser, r: AuthorScopedRepository[Note] = Depends(repo)
    ) -> dict[str, str]:
        note = r.get(note_id, user.id)
        if note is None:
            raise NotFound
        return {"body": note.body}

    @router.get("/_t/notes/{note_id}/export")
    def export(
        note_id: UUID, user: ClinicianUser, r: AuthorScopedRepository[Note] = Depends(repo)
    ) -> dict[str, str]:
        if r.get(note_id, user.id) is None:
            raise NotFound
        return {"export": "ok"}

    api.app.include_router(router)


def test_F25_author_reads_own_resource_and_other_clinician_cannot(api: Api) -> None:
    _mount(api)
    a = api.headers(subject="clin-a")
    b = api.headers(subject="clin-b")
    note_id = api.client.post("/_t/notes", headers=a).json()["id"]
    assert api.client.get(f"/_t/notes/{note_id}", headers=a).status_code == 200
    assert api.client.get("/_t/notes", headers=a).json() == [note_id]
    assert api.client.get("/_t/notes", headers=b).json() == []
    assert api.client.get(f"/_t/notes/{note_id}", headers=b).status_code == 404
    assert api.client.get(f"/_t/notes/{note_id}/export", headers=b).status_code == 404


def test_F25_response_for_foreign_resource_equals_response_for_missing_one(api: Api) -> None:
    _mount(api)
    note_id = api.client.post("/_t/notes", headers=api.headers(subject="clin-a")).json()["id"]
    b = api.headers(subject="clin-b")
    foreign = api.client.get(f"/_t/notes/{note_id}", headers=b)
    missing = api.client.get(f"/_t/notes/{uuid4()}", headers=b)
    assert (foreign.status_code, foreign.json()) == (missing.status_code, missing.json())
    foreign_export = api.client.get(f"/_t/notes/{note_id}/export", headers=b)
    missing_export = api.client.get(f"/_t/notes/{uuid4()}/export", headers=b)
    assert foreign_export.json() == missing_export.json()


def test_F25_repository_never_reads_without_author(api: Api) -> None:
    TestBase.metadata.create_all(api.engine)
    author, other = uuid4(), uuid4()
    with api.session() as session:
        repo = AuthorScopedRepository(session, Note)
        note = repo.add(Note(author_id=author, body="x"))
        assert repo.get(note.id, author) is not None
        assert repo.get(note.id, other) is None
        assert repo.get(uuid4(), author) is None
        assert list(repo.list(other)) == []
