# XeleronIA – Medical Document Generation Assistant

MVP d'assistant de génération de documents médicaux (projet de stage 2026). Données synthétiques uniquement.
Spécifications : [docs/SRS.md](docs/SRS.md) · Plan : [docs/JALONS.md](docs/JALONS.md) · Avancement : [docs/PROGRESS.md](docs/PROGRESS.md) · Décisions : [docs/adr/](docs/adr/)

## Architecture
Monolithe modulaire conteneurisé (ADR 0001) :
- `backend/` – Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, Alembic, structlog.
  - `app/domain` : règles métier, aucune dépendance externe ; horloge injectable en UTC.
  - `app/ports` : `OcrProvider`, `LlmProvider`, `IdentityProvider`, `TranscriptIngestion`, `DocumentExporter`.
  - `app/adapters` : implémentations (base de données, fournisseurs).
  - `app/api` : routes HTTP (l'API est le contrat unique) ; `app/core` : configuration, logs, erreurs.
  - `app/templates` : templates de documents en YAML.
- `frontend/` – React, Vite, TypeScript ; image servie par Caddy.
- `deploy/Caddyfile` – TLS, limite de taille des requêtes, en-têtes de sécurité, proxy `/api` vers le backend.
- `docker-compose.yml` – `db` (PostgreSQL), `keycloak` (OIDC + MFA, realm dans `deploy/keycloak/`), `backend`, `web` (Caddy + frontend), `ollama` (profil `local` seulement).
- Documents : versions immuables, revue (relu, rejet, régénération, rollback) et approbation figée avec instantané des coordonnées de la clinique (`CLINIC_*`, ADR 0017, 0018).
- Identité : connexion OIDC (PKCE) avec TOTP obligatoire ; l'API vérifie la signature du jeton et le niveau `acr` (ADR 0004, 0005). Audit en ajout seul garanti par les droits PostgreSQL (ADR 0006).

## Installation (développement)
Prérequis : Python 3.12 et [uv](https://docs.astral.sh/uv/), Node 22, Docker.
```bash
cp .env.example .env            # puis remplacer les valeurs d'exemple
cd backend && uv sync           # dépendances backend
cd ../frontend && npm ci        # dépendances frontend
```

## Lancement
```bash
docker compose up -d --build                 # déploiement hébergé (sans Ollama)
docker compose --profile local up -d --build # poste local avec Ollama
```
Application : https://localhost (certificat interne de Caddy). Hors conteneur : `uv run uvicorn app.api.main:app --reload` (backend) et `npm run dev` (frontend).

## Tests et qualité
```bash
cd backend && uv run pytest && uv run ruff check . && uv run mypy && uv run bandit -r app -c pyproject.toml
cd frontend && npm run lint && npm run build
```
Superbills : PDF de 3 pages au maximum ou une image png/jpg/jpeg, 50 Mo au maximum (ADR 0009). L'extraction lit la couche texte du PDF, puis Docling sur CPU pour les scans (ADR 0007) ; Docling est un extra : `uv sync --extra ocr`, puis `RUN_DOCLING_TESTS=1 uv run pytest tests/test_docling_integration.py -s`. Les jeux de test synthétiques se régénèrent avec `uv run python ../scripts/make_superbill_fixtures.py`.
Les tests de droits de base (F-21) ont besoin de PostgreSQL : définir `TEST_DATABASE_URL` (ex. `postgresql+psycopg://postgres:motdepasse@localhost:5432/postgres`, un compte pouvant créer des bases). Sans cette variable ils sont ignorés en local et échouent en CI.
Utilisateur de test Keycloak : `clinicien-test`, mot de passe `KC_TEST_USER_PASSWORD`. Le secret TOTP brut est `KC_TEST_USER_TOTP_SECRET` ; à saisir dans une application TOTP en base32 (`python -c "import base64;print(base64.b32encode(b'<secret>').decode())"`).
Les tests portent l'ID de l'exigence couverte (ex. `test_N08_...`). Le test canari (`tests/test_n08_canary.py`) vérifie qu'aucune donnée patient n'apparaît dans les logs ni dans les erreurs.

## CI/CD (ADR 0002)
GitHub Actions : qualité (ruff, mypy, pytest, eslint), sécurité (bandit, gitleaks, Trivy), build et publication des images dans GHCR, déploiement DEV automatique sur `main`. PROD-démo : workflow `deploy-prod-demo` lancé à la main sur un tag `v*`.
Le job `smoke` démarre la pile complète et sonde `/api/health` (N-15).
Déploiement DEV : dès que l'hôte existe, définir les secrets `DEV_HOST`, `DEV_USER`, `DEV_SSH_KEY` et la variable de dépôt `DEV_DEPLOY_ENABLED=true` (`PROD_*` pour la démo).

## Chiffrement au repos (ADR 0003)
Les volumes Docker (`pgdata`, `storage`, `logs`) doivent résider sur un disque chiffré par l'hôte. Vérification sur l'hôte Linux : `lsblk -o NAME,TYPE,MOUNTPOINT` doit montrer le point de montage de `/var/lib/docker` sous un périphérique de type `crypt`.
