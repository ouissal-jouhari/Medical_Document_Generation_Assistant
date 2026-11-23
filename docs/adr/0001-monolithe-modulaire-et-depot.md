# ADR 0001 – Monolithe modulaire, ports et adaptateurs, organisation du dépôt

- **Statut :** accepté (D-07, N-13, N-15)
- **Contexte :** un développeur, environ 10 utilisateurs, déploiement cloud ou on-premise avec la même image.
- **Décision :**
  - Monolithe modulaire : `backend/` (FastAPI) et `frontend/` (React/Vite/TS), l'API est le contrat unique.
  - Le backend suit ports et adaptateurs : `app/domain` (aucune dépendance externe), `app/ports` (interfaces), `app/adapters` (implémentations), `app/api` (routes), `app/core` (configuration, logs, erreurs).
  - Les templates de documents sont des fichiers YAML dans `backend/app/templates/`.
  - Le dépôt GitHub est `Medical_Document_Generation_Assistant`. `CLAUDE.md` et `docs/` sont versionnés à sa racine (copiés depuis le dossier parent de travail).
- **Conséquences :** remplacer OCR, LLM, identité, entrée du texte ou export ne touche pas le domaine.
