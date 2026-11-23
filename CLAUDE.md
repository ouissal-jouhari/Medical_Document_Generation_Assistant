# CLAUDE.md – XeleronIA

## Mission
Construire le MVP XeleronIA de bout en bout, en suivant STRICTEMENT docs/SRS.md (Partie A = SRS, Partie B = choix techniques) et docs/JALONS.md (7 jalons).
Tout est déjà décidé et validé : exigences, architecture, stack, ordre des jalons. Tu ne conçois pas, tu construis et tu testes.
Livre une application de qualité : code propre, structuré, testé, documenté, versionné sur GitHub.

## Règles absolues
- La stack et l'architecture sont FIGÉES. Aucun changement de technologie, de bibliothèque majeure ou d'architecture.
- N'ajoute aucune fonctionnalité absente du SRS. N'omets aucune exigence du jalon en cours.
- Hors MVP, ne pas construire : AI Scribe, FHIR, SonarQube, Dependency-Track/SBOM, autres rôles, microservices.
- CI/CD : GitHub Actions + GHCR. Ollama : profil local seulement ; démo hébergée = Gemini. Données synthétiques uniquement.
- Si deux documents se contredisent : applique l'ordre SRS > JALONS > Technical Stack > diagrammes, note la décision dans docs/adr/ et continue.
- Pour tout détail non décrit (noms, découpage interne, organisation des tests) : choisis la solution la plus simple et conforme au SRS, sans demander.
- Règles de sécurité médicale S-01 à S-07 et N-19 : applique-les de la façon la plus stricte, sans exception.

## Exécution (docs/JALONS.md, section 0)
1. Lis docs/PROGRESS.md pour savoir où tu en es. Reprends au premier jalon non TERMINÉ.
2. Lis UNIQUEMENT : section 0, `## JALON n`, les lignes P citées, le tableau de suivi. Dans le SRS, cherche par ID (grep) et lis seulement la section utile.
3. Pour les écrans : produis les wireframes basse fidélité listés dans « Maquettes requises » (docs/wireframes/), puis implémente.
4. Exécute les tâches dans l'ordre, sans demander de confirmation. Boucle : code → tests → ruff/mypy/bandit/eslint → corrige.
5. Un test automatique par critère d'acceptation, nommé avec l'ID de l'exigence (ex. test_F17_...).
6. Jalon terminé quand : toutes les tâches sont faites, la « Porte de sortie » est cochée avec preuves (tests verts), la CI est verte, les livrables existent, les ADR sont écrits.
7. Alors : coche la porte dans docs/JALONS.md, passe le jalon en TERMINÉ dans le tableau de suivi, mets à jour docs/PROGRESS.md (10 lignes max), commit, tag `jalon-N`, push, et enchaîne sur le jalon suivant.
8. Ne réduis jamais le périmètre en silence. Retard : note-le dans PROGRESS.md et continue. Ordre de coupe : voir JALONS section 4, mais ne coupe rien sans l'écrire dans PROGRESS.md.

## Quand t'arrêter (cas très rare)
Arrête-toi et explique SEULEMENT si : une erreur fatale bloque l'application après 3 tentatives de correction différentes, un secret ou une clé manque et ne peut pas être simulé, ou une action serait destructrice ou irréversible hors du dépôt. Sinon, n'interromps jamais le travail.
Ne contourne jamais un test, un linter ou une validation pour passer au vert.

## Qualité et structure du dépôt
- README.md (installation, lancement, tests, architecture), docs/adr/ (un ADR par décision), docs/PROGRESS.md, .env.example, .gitignore (.env, secrets, caches).
- Architecture modulaire : domaine sans dépendance externe ; ports et adaptateurs (OcrProvider, LlmProvider, IdentityProvider, TranscriptIngestion, DocumentExporter).
- Typage complet (mypy), lint propre, pas de code mort, pas de TODO laissé.
- Commits petits et clairs (Conventional Commits : feat:, fix:, test:, docs:, ci:), un par tâche. Branche principale protégée par la CI verte.
- Aucun secret ni donnée patient dans le code, les logs, les erreurs ou les prompts : test canari rejoué à chaque jalon.
- Accès aux données uniquement via la couche qui filtre par auteur ; toute nouvelle route déclare l'authentification ; rejoue F-25.
- Dates en UTC, horloge injectable.

## Économie de tokens
- Réponses courtes, pas de récapitulatif du diff.
- Modifie seulement les lignes concernées, jamais de réécriture complète.
- Tests ciblés d'abord, suite complète en fin de tâche.
- Ne relis pas un fichier déjà lu dans la session.
- Recherches volumineuses : sous-agent (Haiku).
- Après un compactage ou une nouvelle session : relis docs/PROGRESS.md et reprends.