# Progression XeleronIA
## Fait
(aucun jalon terminé)
## En cours
Jalon 1 : tâches 1 à 5 faites. CI verte (qualité, sécurité, smoke N-15, publication GHCR). Local : 13 tests backend, ruff, mypy, bandit, eslint OK.
## Reste pour clore le jalon 1
- Hôte DEV (P13) : créer secrets DEV_HOST/DEV_USER/DEV_SSH_KEY + variable DEV_DEPLOY_ENABLED=true ; puis déploiement DEV et preuve du chiffrement au repos (disque chiffré, ADR 0003).
- Votre « jalon validé » ; ensuite tag jalon-1 et jalon 2.
## Notes
- Le test canari a révélé des fuites d'URL dans les logs (corrigé : gabarit de route, httpx en WARNING).
- Trivy-action épinglée par SHA (v0.36.0) après échec de résolution du tag.
