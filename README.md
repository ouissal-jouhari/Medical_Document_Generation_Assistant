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
- `docker-compose.yml` – `db` (PostgreSQL), `backend`, `web` (Caddy + frontend), `ollama` (profil `local` seulement).

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
Les tests portent l'ID de l'exigence couverte (ex. `test_N08_...`). Le test canari (`tests/test_n08_canary.py`) vérifie qu'aucune donnée patient n'apparaît dans les logs ni dans les erreurs.

## CI/CD (ADR 0002)
GitHub Actions : qualité (ruff, mypy, pytest, eslint), sécurité (bandit, gitleaks, Trivy), build et publication des images dans GHCR, déploiement DEV automatique sur `main`. PROD-démo : workflow `deploy-prod-demo` lancé à la main sur un tag `v*`.
Secrets GitHub requis : `DEV_HOST`, `DEV_USER`, `DEV_SSH_KEY` (et `PROD_*` pour la démo).

## Chiffrement au repos (ADR 0003)
Les volumes Docker (`pgdata`, `storage`, `logs`) doivent résider sur un disque chiffré par l'hôte. Vérification sur l'hôte Linux : `lsblk -o NAME,TYPE,MOUNTPOINT` doit montrer le point de montage de `/var/lib/docker` sous un périphérique de type `crypt`.
