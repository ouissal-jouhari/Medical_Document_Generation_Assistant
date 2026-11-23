# Progression XeleronIA
## Fait
(aucun jalon terminé)
## En cours
Jalon 1 : tâches 1 à 5 faites. Local : ruff, mypy, bandit, 13 tests backend, eslint + build frontend verts. Reste : CI verte sur GitHub (job smoke = preuve N-15), gitleaks/Trivy, hôte DEV.
## Bloqué / réseau
- Build Docker local impossible (ghcr.io et PyPI instables depuis le poste) : N-15 prouvé par le job CI `smoke`.
- P13 ouvert : pas d'hôte DEV. Déploiement DEV désactivé tant que la variable DEV_DEPLOY_ENABLED n'est pas à true ; la porte « DEV déployé » reste non cochée.
## Notes
- Test canari : a révélé que les URL réelles étaient journalisées (corrigé : gabarit de route, httpx en WARNING).
