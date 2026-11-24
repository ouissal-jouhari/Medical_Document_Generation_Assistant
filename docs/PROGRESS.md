# Progression XeleronIA
## En cours
Jalon 2 : tâches 1 à 5 faites, CI verte (40 tests dont droits PostgreSQL, bandit, gitleaks, Trivy, smoke Keycloak + MFA réel de bout en bout).
## Reste pour clore le jalon 2
- Test navigateur de la redirection sans session (F-01) : Playwright, jalon 7 (écart noté, pas de coupe silencieuse).
- Votre « jalon validé ».
## Reporté du jalon 1 (décision utilisateur)
- Hôte DEV (P13) : déploiement DEV et preuve du chiffrement au repos ; « jalon validé » du jalon 1.
## Acquis et notes
- ADR 0004 (front PKCE, jeton en mémoire), 0005 (MFA via acr, validé sur Keycloak 26.0.8 : acr=2 après TOTP), 0006 (audit, rôles de base).
- Défauts trouvés au démarrage réel : sonde Keycloak sous /auth, alembic sans sys.path (corrigés).
- Docs OpenAPI désactivées (aucune route publique hors /health).
