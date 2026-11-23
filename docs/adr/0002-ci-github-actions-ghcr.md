# ADR 0002 – CI/CD : GitHub Actions et GHCR (P1, P4, P5)

- **Statut :** accepté
- **Contexte :** le Technical Stack indique GitHub Actions, Architectures indique GitLab CI. Les relecteurs requis des environnements GitHub ne sont pas disponibles pour un dépôt privé hors Enterprise.
- **Décision :** GitHub Actions + GHCR. Qualité : ruff, mypy, eslint. Sécurité : bandit, gitleaks, Trivy. Déploiement DEV automatique sur `main` ; déploiement PROD-démo manuel sur tag de version. SonarQube et Dependency-Track/SBOM sont hors MVP (Trivy couvre les dépendances).
- **Conséquences :** le schéma CI/CD d'Architectures est à corriger (JALONS section 6).
