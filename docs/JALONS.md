# XeleronIA – Plan de jalons du MVP (v2)

**Sources :** SRS MVP v1.0 (prime, D6-2) > Technical Stack v1.1 > Architectures (architecture + CI/CD) > diagrammes (Four Views, Class, Lifecycle, Sequence, Use Case, Error Paths).
**Contraintes (C-01) :** 1 développeur, environ 8 semaines = 40 jours ouvrés.
**Hors MVP :** AI Scribe, autres rôles, microservices, FHIR (non planifié, voir P2), SonarQube et Dependency-Track/SBOM (voir P4, P5).
**Durées :** ce sont des estimations du chef de projet (les sources n'en donnent pas).

**Changements de la v2 (revue du plan v1) :** décisions P1 (GitHub Actions), P12 (instantané du texte), P13 (Gemini pour la démo hébergée), P14 (régénération), P15 (PDF multi-pages) ; mécanismes précisés (chiffrement au repos, audit au niveau base, MFA vérifié côté API, parsing déterministe, validateur d'ancrage, concurrence des versions) ; dépendances entre jalons rendues explicites (champ « Préparation pour les jalons suivants ») ; tests déplacés dans chaque jalon (définition de « terminé »).

---

## 0. PROTOCOLE D'EXÉCUTION (à lire en premier, à chaque jalon)

### 0.1 Règle de passage (porte de sortie)
1. On ne démarre le jalon N+1 que si le jalon N est **terminé avec succès**.
2. Un jalon est terminé avec succès si **toutes** les conditions suivantes sont vraies :
   - Toutes les tâches du jalon sont faites.
   - Chaque critère d'acceptation du jalon est vérifié (résultat noté dans la section « Porte de sortie » du jalon).
   - **Définition de « vérifié » :** chaque critère est couvert par un **test automatique** (unitaire, API ou bout en bout), ou, pour les critères de type « revue de conception », par une revue consignée dans un ADR ou une note de conception.
   - Le pipeline CI est vert (à partir du jalon 1).
   - Les livrables existent.
   - Les ADR des décisions prises pendant le jalon sont écrits (15 min chacun, au fil de l'eau).
   - L'utilisateur a confirmé « jalon validé ».
3. Si un critère échoue : on corrige dans le même jalon. On ne passe pas au suivant. Si cela retarde le calendrier, on le **signale** (R10), on ne réduit pas le périmètre en silence. L'ordre de coupe est fixé à l'avance (section 4).

### 0.2 Règle de lecture (ne lire que ce qui concerne le jalon en cours)
Au début de chaque jalon, relire **uniquement** :
- la section 0 (ce protocole) ;
- la section du jalon en cours (`## JALON n`), y compris son champ « Préparation reçue des jalons précédents » ;
- les lignes de la section 3 (« Points à confirmer ») listées dans le champ « Points à confirmer liés » du jalon ;
- le tableau de suivi (section 1), pour vérifier que le jalon précédent est « TERMINÉ ».

Ne pas relire les autres jalons, ni la matrice, ni le calendrier, ni l'auto-contrôle (sections 2 à 5), sauf demande explicite. Les dépendances entre jalons sont écrites dans les champs « Préparation reçue » et « Préparation pour les jalons suivants » : ils remplacent la relecture croisée.

### 0.3 Comment démarrer
Dire : « Démarre le jalon N ». Le contenu du jalon N est alors lu, puis exécuté tâche par tâche. Au début de chaque jalon comportant des écrans, l'assistant fournit les wireframes basse fidélité listés dans « Maquettes requises ».

### 0.4 Règles transverses (valables pour tous les jalons)
- **Autorisation par construction :** tout accès aux données passe par une couche qui filtre par auteur ; toute nouvelle route doit déclarer la dépendance d'authentification (test automatique, jalon 2).
- **Aucune donnée patient dans les logs, les messages d'erreur ni les prompts d'identification :** vérifié par la valeur-canari (jalon 1) rejouée à chaque jalon.
- **Dates en UTC**, horloge injectable (nécessaire aux tests de conservation).
- **Données synthétiques uniquement** (C-03), y compris dans les jeux de test et d'évaluation.

---

## 1. TABLEAU DE SUIVI

| Jalon | Nom | Semaines | Jours | Statut |
|---|---|---|---|---|
| 1 | Socle technique et CI/CD | S1 | j1–j4 | EN COURS (DEV et validation reportés) |
| 2 | Authentification, contrôle d'accès et audit | S1–S2 | j5–j8 | TERMINÉ |
| 3 | Superbill : dépôt, extraction, vérification | S2–S3 | j9–j15 | TERMINÉ (validé par l'utilisateur) |
| 4 | Texte de consultation et génération | S4–S5 | j16–j23 | EN COURS |
| 5 | Revue, versions et approbation | S5–S6 | j24–j30 | À FAIRE |
| 6 | Export, provenance, suppression et conservation | S7 | j31–j35 | À FAIRE |
| 7 | Évaluation IA, tests, observabilité, démonstration | S8 | j36–j40 | À FAIRE |

Statuts possibles : À FAIRE · EN COURS · TERMINÉ (validé par l'utilisateur).

---

## JALON 1 – Socle technique et CI/CD

- **Semaine(s) :** S1 (j1–j4)
- **Objectif :** Disposer d'un monolithe modulaire conteneurisé, sécurisé de base et déployé automatiquement en DEV par GitHub Actions.
- **Dépendances :** aucune. **Prérequis avant j1 :** machine d'hébergement de DEV et de la démo fixée (P13).
- **Points à confirmer liés :** P1, P4, P5, P13
- **Préparation reçue des jalons précédents :** aucune.

### Tâches
1. Dépôt GitHub et structure du monolithe modulaire (backend, frontend) ; API comme contrat unique ; templates en configuration ; ADR du style d'architecture (0,5 j)
2. Docker Compose (Ollama dans un profil local seulement, absent du déploiement hébergé), Caddy (TLS, limite de taille des requêtes, en-têtes de sécurité de base), PostgreSQL / SQLAlchemy / Alembic. **Chiffrement au repos :** chiffrement de volume côté hôte, qui couvre PostgreSQL et les Superbills déposées, clé hors du code (1 j)
3. Définir les interfaces OcrProvider, LlmProvider, IdentityProvider, TranscriptIngestion, **DocumentExporter** (port prévu pour un futur export FHIR) (0,5 j)
4. Secrets hors du code et des logs ; structlog sans donnée patient, **rotation des logs à 30 jours (N-10)** ; **gestionnaire d'erreurs global** (les erreurs de validation Pydantic / FastAPI ne renvoient ni ne journalisent les valeurs saisies) ; **test « valeur-canari »** (un faux nom unique cherché dans tous les logs et réponses d'erreur) (0,75 j)
5. Pipeline GitHub Actions : qualité (ruff, mypy, eslint), sécurité (bandit, gitleaks, Trivy), build Docker, publication dans GHCR, déploiement DEV automatique sur la branche principale (1,25 j)

### Exigences couvertes
N-05 (M), N-08 (M), N-13 (M), N-15 (S), N-18 (S, partiel), C-05, D-06, D-07.
Architecture : Python 3.12 / FastAPI / Pydantic v2, React / Vite / TypeScript, Docker Compose, Caddy, PostgreSQL, structlog, pipeline CI/CD.

### Critères d'acceptation (repris du SRS)
- N-05 : « Chiffrement en transit et au repos ; secrets hors du code ; aucune clé, mot de passe ni jeton dans les logs. Vérification : aucun secret trouvé dans le dépôt ni dans les logs. »
- N-13 : « Chacun est derrière une interface ; remplacer un fournisseur ne modifie pas le domaine (revue de conception). »
- N-15 : « Démarrage reproductible par conteneur. »
- N-08 : « logs sans donnée patient ».

### Livrables
Dépôt, Docker Compose, pipeline CI vert, interfaces des ports, environnement DEV, test canari.

### Maquettes requises
aucune

### Risques liés
R-06

### Préparation pour les jalons suivants
- Les poids des modèles (Docling) sont embarqués dans l'image au jalon 3 : prévoir la taille d'image et le cache de build dans la CI.
- L'ordonnanceur de purge (jalon 6) s'appuie sur l'horloge injectable décidée ici.

### Porte de sortie du jalon 1
- [x] Tâches 1 à 5 faites
- [ ] N-05 : fait = gitleaks vert en CI, canari absent des logs (test_N08_*, test_N05_*), TLS Caddy démontré par le job smoke ; **reste = chiffrement au repos à démontrer sur l'hôte (ADR 0003, hôte DEV P13)**
- [x] N-13 vérifié (test_N13_* : domaine et ports sans dépendance externe, un faux fournisseur par port)
- [x] N-15 vérifié (job CI smoke : pile complète démarrée, /api/health via Caddy)
- [x] N-08 vérifié (canari : logs et erreurs sans donnée patient, 5 tests)
- [ ] Pipeline CI vert (fait : run 45293186964 vert, images publiées sur GHCR) ; **DEV déployé : en attente de l'hôte (P13)**
- [x] Utilisateur : « jalon validé »

---

## JALON 2 – Authentification, contrôle d'accès et audit

- **Semaine(s) :** S1 (j5) à S2 (j8)
- **Objectif :** Qu'aucune route ne soit accessible sans MFA, que chaque document n'appartienne qu'à son auteur, et que l'audit soit en ajout seul, garanti par la base.
- **Dépendances :** Jalon 1 (TERMINÉ)
- **Points à confirmer liés :** aucun
- **Préparation reçue des jalons précédents :** gestionnaire d'erreurs global et test canari (jalon 1).

### Tâches
1. Keycloak auto-hébergé : OIDC + MFA ; **realm exporté en fichier de configuration** ; **vérification côté API que le jeton atteste bien un MFA** (claim `acr` / niveaux d'authentification Keycloak, à valider dans la documentation de la version retenue) ; utilisateur de test avec TOTP pré-enregistré pour les tests automatiques ; ADR sur l'authentification du front (jeton en mémoire avec PKCE, ou cookie via BFF, ce qui décide de l'exposition CSRF) (1,75 j)
2. Rôle unique « Clinician », vérifié sur chaque route, extensible ; table `User` avec nom d'affichage issu de l'OIDC ; **test qui parcourt toutes les routes FastAPI et vérifie la dépendance d'authentification** (0,5 j)
3. Visibilité limitée à l'auteur **par filtre dans la couche d'accès aux données** ; réponse identique si la ressource n'existe pas ou n'est pas autorisée (0,5 j)
4. AuditEvent en ajout seul **garanti au niveau base** (UPDATE et DELETE retirés au rôle applicatif), écrit dans **la même transaction** que l'action, **sans clé étrangère** vers Document (pour survivre à la suppression, F-22) ; la purge à 1 an (N-10) passe par un rôle distinct ; aucune route de modification ou suppression ; la consultation d'un document n'est pas tracée au MVP (L-04, écart connu) (1 j)
5. Chemins d'erreur : authentification impossible (session absente ou expirée, MFA échoué, fournisseur OIDC indisponible) et ressource introuvable ou non autorisée, avec message sûr (0,25 j)

### Exigences couvertes
F-01 (M), F-02 (M), F-25 (M), F-20 (M, socle), F-21 (M), N-04 (M), N-11 (M, cas authentification et accès refusé), I-03 (MVP), E-01, D-03, L-04 (écart connu).
Architecture : Keycloak.

### Critères d'acceptation (repris du SRS)
- F-01 : « Sans MFA validé, l'accès est refusé ; une requête sans session est redirigée vers la connexion. »
- F-02 : « Chaque route vérifie le rôle ; ajouter un rôle ne demande pas de modifier les routes existantes (revue de conception). »
- F-25 : « Un autre clinicien ne peut ni lister, ni lire, ni exporter ce document ; la réponse ne révèle pas son existence. »
- F-21 : « Aucune route ni aucun écran ne modifie ou ne supprime un événement d'audit. »
- N-04 : voir F-01, F-02, F-25.
- N-11 (cas concernés) : « Un test par cas vérifie le message et l'absence de trace technique. »

### Livrables
Authentification MFA opérationnelle, realm Keycloak versionné, contrôle d'accès par rôle, journal d'audit en ajout seul, écran de connexion.

### Maquettes requises
Maquette requise : E-01

### Risques liés
aucun

### Préparation pour les jalons suivants
- F-25 doit être **rejoué** aux jalons 5 et 6 pour chaque nouvelle route (versions, approbation, export, rapport de provenance) : « exporter » n'existe pas encore ici.
- La table `User` (nom d'affichage) alimente la ligne « Approved by [name] » (jalon 5).
- L'audit sans clé étrangère et la séparation des rôles de base servent F-22 et N-10 (jalon 6).

### Porte de sortie du jalon 2
- [x] Tâches 1 à 5 faites
- [x] F-01 : jeton mono-facteur rejeté par l'API (test_F01_*, et scripts/mfa_login_check.py rejoué en CI : MFA réel -> 200 avec acr=2, mono-facteur -> 403 mfa_required) ; sans session -> 401 ; connexion navigateur vérifiée à la main par l'utilisateur. **Écart connu : le test automatique de la redirection navigateur (Playwright) est reporté au jalon 7.**
- [x] F-02 vérifié (revue de conception ADR 0001/0005 + test_F02_* : toutes les routes dépendent de l'authentification, ajout d'un rôle sans modifier les routes)
- [x] F-25 vérifié (test_F25_* : un autre clinicien reçoit la même réponse qu'une ressource inexistante, y compris pour l'export ; à rejouer aux jalons 5 et 6)
- [x] F-21 vérifié (test_F21_* : aucune route d'audit ; UPDATE, DELETE et TRUNCATE refusés au rôle applicatif par PostgreSQL, testé en CI sur une base migrée par Alembic)
- [x] N-11 : message sûr, sans trace technique, pour authentification (absente, expirée, MFA manquant, fournisseur indisponible) et accès refusé / introuvable
- [x] Canari absent des logs (test_N08_*, y compris nom d'affichage et jeton)
- [x] Pipeline CI vert (run 45305466333)
- [x] Utilisateur : « jalon validé » (2 : validé par l'utilisateur)

---

## JALON 3 – Superbill : dépôt, extraction, vérification

- **Semaine(s) :** S2 (j9) à S3 (j15)
- **Objectif :** Obtenir, à partir d'une Superbill déposée, des données normalisées vérifiées et validées par le clinicien.
- **Dépendances :** Jalon 2 (TERMINÉ)
- **Points à confirmer liés :** P9 (tranché), P13
- **Préparation reçue des jalons précédents :** authentification, filtre par auteur, audit (jalon 2) ; interface OcrProvider (jalon 1).

### Tâches
1. Dépôt de la Superbill avec contrôles : **type réel du fichier (magic bytes)**, 3 pages maximum, 50 Mo maximum **(limite de taille de Caddy et vérification dans l'API)**, formats PDF, png, jpg, jpeg ; protection contre les images piégées (taille décompressée) ; PDF chiffrés refusés (1 j)
2. Extraction derrière OcrProvider : **règle de décision explicite** (texte direct si la couche texte est non vide et que les champs obligatoires sont trouvés, sinon Docling sur CPU) ; Docling exécuté **hors de la boucle d'événements** (thread ou processus) ; **poids des modèles embarqués dans l'image** (compatibilité on-premise) (1,5 j)
3. **Parsing déterministe** (sans LLM : aucun LLM dans l'extraction d'après les diagrammes, et N-19 interdit d'envoyer le nom du patient) de la sortie structurée de Docling vers `SuperbillData` selon le schéma de la section 9.2 du SRS ; validation déterministe (dates ISO, formats ICD-10-CM et CPT) ; **avertissement non bloquant** si un code ICD-10-CM est absent de la table CDC versionnée ; limite assumée : un seul gabarit de Superbill (L-01) (2 j)
4. Gestion des échecs : fichier invalide, extraction ratée, données incomplètes ou invalides ; message clair, état conservé, échec compté (0,5 j)
5. Vérification et correction des champs, validation explicite → état Validated, corrections tracées avec auteur et date (1 j)
6. Intégration des écrans (0,75 j)
7. **Amorce du jeu d'évaluation :** au moins 3 Superbills synthétiques (propre, scan dégradé, invalide) ajoutées aux jeux de test, dont la Superbill d'exemple de l'Annexe A du SRS (en PDF) comme cas propre (0,25 j)

### Exigences couvertes
F-03 (M), F-04 (M), F-05 (M), F-06 (M), N-06 (M, contrôle de fichier), N-11 (M, fichier invalide et extraction ratée), I-01 (MVP), E-02 (liste et création), E-03, E-04, R-02, R-07, D-02, C-03.
Architecture : Docling (CPU, local).

### Critères d'acceptation (repris du SRS)
- F-03 : « PDF de 3 pages au maximum ; une image par fichier ; 50 Mo au maximum ; autre format ou fichier hors limites refusé avec un message clair, sans créer de consultation. »
- F-04 : « Sur la Superbill synthétique de test, les champs obligatoires du schéma (section 9.2) sont extraits et le résultat respecte le schéma. »
- F-05 : « Chaque champ est modifiable ; chaque modification conserve auteur et date ; la consultation passe à Validated seulement après une validation explicite. »
- F-06 : « Message clair ; la consultation reste Uploaded ; un nouveau dépôt est possible ; l'échec est compté. »
- N-06 : « Le type réel du fichier est contrôlé, pas seulement l'extension. »
- N-11 (cas concernés) : « Un test par cas vérifie le message et l'absence de trace technique. »

### Livrables
Flux Uploaded → Parsed → Validated fonctionnel, adaptateur OCR, parseur déterministe, écrans de dépôt et de vérification, 3 Superbills synthétiques de test.

### Maquettes requises
Maquette requise : E-02, E-03, E-04

### Risques liés
R-02, R-07

### Préparation pour les jalons suivants
- Les Superbills synthétiques et leurs `SuperbillData` attendus sont la base du jeu d'évaluation (jalons 4 et 7).
- `SuperbillData` validée alimente le **bloc commun injecté de façon déterministe** (jalon 4).
- L'action « supprimer » de E-02 est livrée au jalon 6 ; son emplacement dans l'écran est prévu ici.

### Porte de sortie du jalon 3
- [x] Tâches 1 à 7 faites (jeu d'évaluation amorcé : Annexe A en PDF, PDF synthétique propre, scan dégradé, fichier invalide renommé, dans backend/tests/fixtures/superbills/)
- [x] F-03 vérifié (test_F03_*, test_N06_* : format, 3 pages, 50 Mo, PDF chiffré, fichier corrompu, image piégée refusés sans créer de consultation ; limite appliquée par Caddy et vérifiée dans l'API : scripts/mfa_login_check.py rejoué en CI sur la vraie pile, 413 de l'API puis de Caddy)
- [x] F-04 vérifié sur la Superbill de l'Annexe A (test_F04_annex_a_sample_* : champs obligatoires extraits, conformes au schéma ; dépôt réel sur la pile en CI : état parsed) ; scan dégradé lu par Docling réel (job CI « ocr »)
- [x] F-05 vérifié (test_F05_* sur SQLite et PostgreSQL : modification tracée avec auteur et date, extraction d'origine conservée, Validated seulement après validation explicite, validation bloquée par les problèmes bloquants)
- [x] F-06 vérifié (test_F06_* : état Uploaded conservé, nouveau dépôt possible sur la même consultation, échec compté)
- [x] N-06 vérifié (test_N06_* : fichier renommé refusé, type réel doit correspondre à l'extension)
- [x] N-11 : message sûr, sans trace technique, pour fichier invalide et extraction ratée (test_N11_*)
- [x] Canari absent des logs ; F-25 rejoué sur toutes les routes de consultation (test_F25_*, test_N08_original_file_name_*)
- [x] Pipeline CI vert (run 45321481250 : qualité 105 tests dont PostgreSQL, sécurité, ocr, smoke, publication des images avec modèles Docling)
- [ ] Utilisateur : « jalon validé »

---

## JALON 4 – Texte de consultation et génération

- **Semaine(s) :** S4 (j16) à S5 (j23)
- **Objectif :** Générer un brouillon structuré, sans invention et sans identifiants envoyés au LLM, à partir de la Superbill et du texte optionnel.
- **Dépendances :** Jalon 3 (TERMINÉ)
- **Points à confirmer liés :** P10 (tranché), P11 (tranché), P12 (tranché), P13
- **Préparation reçue des jalons précédents :** `SuperbillData` validée, Superbills synthétiques de test (jalon 3) ; interface LlmProvider (jalon 1) ; audit (jalon 2).

### Tâches
1. Saisie du texte de consultation (5 000 caractères maximum, contrôle côté serveur), remarque d'avertissement, enregistrement du texte exposé par l'API indépendamment de l'écran ; **le texte reste modifiable après une première génération (P12) : un instantané du texte est stocké avec chaque Document à la génération** ; intégration de l'écran (1,5 j)
2. Les trois templates (Clinical Note, Referral Letter, Discharge Summary) en fichiers de configuration, avec statuts de section, **validés par schéma au démarrage** (1,25 j)
3. Adaptateurs LLM derrière LlmProvider : Gemini (démonstration hébergée) et gpt-oss-20b via Ollama (profil local), interchangeables par configuration ; normalisation des différences de sortie structurée ; délai maximal ; ADR sur Gemini (données synthétiques uniquement, conditions d'usage relues avant le premier appel) (1 j)
4. Minimisation : nom, date de naissance et identifiant du patient non envoyés au LLM, réinjectés après la génération ; **bloc commun (patient, médecin, date, diagnostics et procédures codés) injecté de façon déterministe depuis `SuperbillData` : le LLM ne rédige que les sections narratives** ; Superbill, OCR et texte traités comme des données, jamais comme des instructions (1 j)
5. Génération structurée selon le template : statut `PROVIDED / NOT_PROVIDED` dans le schéma de sortie (affiché « Not provided ») ; règles S-02 et S-03 ; **provenance par section fondée sur des citations littérales renvoyées par le LLM, positions calculées côté serveur** (1,25 j)
6. **Validateur d'ancrage et contrôle de sortie avant affichage :** une citation introuvable dans le texte, ou un médicament ou une allergie sans citation, repasse la section à « Not provided » ; codes de sortie ⊆ codes de la Superbill ; une nouvelle tentative maximum ; chemins d'erreur LLM indisponible ou lent, sortie malformée ; génération protégée contre le double déclenchement ; délais Caddy / serveur alignés ; indicateur de chargement (2 j)

### Exigences couvertes
F-07 (M), F-08 (S), F-09 (M), F-10 (M), F-11 (M), F-12 (M), S-02 (M), S-03 (M), S-04 (M), S-05 (M, enregistrement), N-07 (M), N-11 (M, LLM et sortie malformée), N-14 (S), N-18 (S), N-19 (M), I-02 (MVP), I-04 (frontière seulement), I-05 (futur, via API), C-04, R-01, R-03, R-04, E-05, D-01, D-05.
Architecture : Pydantic v2 (validation de la sortie LLM), Gemini, gpt-oss-20b / Ollama, templates YAML.

### Critères d'acceptation (repris du SRS)
- F-07 : « 5 001 caractères sont refusés côté serveur ; l'absence de texte est acceptée. Sans texte, l'interface (écrans E-05 et E-06) affiche : "Superbill data alone is not sufficient to generate complete clinical documents. Adding the consultation text is recommended." Cette remarque n'apparaît jamais dans le document exporté. »
- F-08 : « L'enregistrement du texte d'une consultation est exposé par l'API indépendamment de l'écran (revue de conception) ; aucun développement de l'AI Scribe. »
- F-09 : « Génération impossible si la consultation n'est pas Validated ; plusieurs documents peuvent coexister pour une consultation. »
- F-10 : « Sortie conforme au schéma du template ; chaque section enregistre ses sources ; sans texte, la règle S-03 s'applique. »
- F-11 : « Sur un jeu de test où une information manque, la section contient "Not provided" et aucune valeur inventée. »
- F-12 : « Une sortie malformée ou incomplète n'est jamais affichée comme brouillon ; message clair ; nouvelle tentative possible. »
- N-07 : « Un texte du type "Ignore previous instructions" dans la Superbill ou le texte ne change ni les règles ni le format de sortie (cas de test). »
- N-19 : « Test automatique sur les prompts envoyés. »
- N-14 : « Ajouter un template ou une langue ne modifie pas le moteur de génération. »
- N-11 (cas concernés) : « Un test par cas vérifie le message et l'absence de trace technique. »

### Livrables
Génération de bout en bout (Document en Under Review avec version IA), adaptateurs LLM, trois templates, validateur d'ancrage, écran texte et choix du type, cas de test d'évaluation (information manquante, injection, négation).

### Maquettes requises
Maquette requise : E-05

### Risques liés
R-01, R-03, R-04

### Préparation pour les jalons suivants
- Le jeu d'évaluation est **alimenté ici** (information manquante pour F-11, injection pour N-07, **négation** : « no known allergies » n'est pas équivalent à « allergies non mentionnées »).
- Chaque Document porte son instantané de texte : les positions de provenance restent valides (jalons 5 et 6).
- Le statut `PROVIDED / NOT_PROVIDED` pilote le blocage d'approbation (jalon 5).
- La régénération (rejet, jalon 5) et « Create new document » (jalon 5) réutilisent ce flux.

### Porte de sortie du jalon 4
- [ ] Tâches 1 à 6 faites
- [ ] F-07 vérifié (5 001 caractères refusés ; absence de texte acceptée ; remarque affichée, jamais exportée ; texte modifiable après génération, instantané conservé)
- [ ] F-08 vérifié (revue de conception)
- [ ] F-09 vérifié (impossible si non Validated ; plusieurs documents possibles)
- [ ] F-10 vérifié (sortie conforme au schéma, sources enregistrées)
- [ ] F-11 vérifié sur le jeu de test avec information manquante
- [ ] F-12 vérifié (sortie malformée jamais affichée)
- [ ] Si la première génération échoue, la consultation reste Validated et aucun Document n'est créé
- [ ] S-02 / S-03 : cas de négation et section sans citation repassée à « Not provided »
- [ ] N-07 vérifié (cas « Ignore previous instructions »)
- [ ] N-19 vérifié (test automatique sur les prompts : aucun identifiant, canari absent)
- [ ] N-14 vérifié (ajout d'un template sans modifier le moteur)
- [ ] N-11 : message sûr, sans trace technique, pour LLM indisponible ou lent et sortie malformée
- [ ] Durées mesurées pour Gemini ; durées gpt-oss-20b mesurées en local si disponible (N-02 préparé)
- [ ] Pipeline CI vert ; F-25 rejoué sur les routes de génération
- [ ] Utilisateur : « jalon validé »

---

## JALON 5 – Revue, versions et approbation

- **Semaine(s) :** S5 (j24) à S6 (j30)
- **Objectif :** Permettre au clinicien de réviser, corriger, restaurer et approuver un document, qui devient alors figé, avec les coordonnées de la clinique conservées à l'approbation.
- **Dépendances :** Jalon 4 (TERMINÉ)
- **Points à confirmer liés :** P11 (tranché), P12 (tranché), P14 (tranché)
- **Préparation reçue des jalons précédents :** génération, instantané du texte, statuts de section (jalon 4) ; table `User` et audit (jalon 2).

### Tâches
1. Versioning immuable ; édition en ligne → version « éditée » avec auteur et date ; **une version par « Save » explicite** ; **concurrence : numéro de version attendu dans chaque requête d'édition et contrainte d'unicité (document, numéro)** (1,5 j)
2. Rejet puis régénération ; rollback avant approbation (1,25 j)
3. « Mark as reviewed » (auteur, version, date) (0,5 j)
4. Approbation (version relue, sections obligatoires fournies, document figé) ; **configuration des coordonnées de la clinique (H-01) et instantané figé à l'approbation (H-02), avec le nom d'affichage de l'approbateur** ; « Create new document » : relance de la génération du même type (P14), l'ancien reste figé (1,75 j)
5. Intégration de l'écran de revue : bandeau, 4 origines, statut de chaque section, liste « Missing information », champs de sécurité (médicaments, allergies) bien visibles s'ils manquent, historique des versions consultable (2 j)

**Règles de revue à implémenter et tester :**
- Éditer une section « Not provided » avec un contenu non vide la rend fournie (origine clinicien).
- Toute nouvelle version (édition, rollback) annule la marque « relu » : l'approbation exige que la **version courante** soit relue.
- Impossible de marquer comme relue ou d'approuver une version courante REJECTED.
- Le gel d'un document approuvé est imposé par le domaine, pas par l'interface.

### Exigences couvertes
F-13 (M), F-14 (M), F-15 (M), F-16 (M), F-17 (M), F-19 (M), F-26 (M), F-20 (M : généré, relu, approuvé, rejeté, rollback), F-24 (M, configuration et instantané), H-01, H-02, H-03, S-01 (M), S-05 (M, affichage), S-06 (M), S-07 (M), N-11 (M, approbation impossible et régénération), E-06.

### Critères d'acceptation (repris du SRS)
- F-13 : « Bandeau "AI-generated draft" visible tant que le document n'est pas approuvé ; 4 origines distinguables (Superbill, texte, IA, clinicien) ; statut de chaque section ; liste "Missing information". »
- F-14 : « Toute édition crée une version "éditée" avec auteur et date ; la version précédente reste intacte. »
- F-15 : « La version rejetée est conservée et marquée ; la régénération crée une nouvelle version IA. »
- F-16 : « Le contenu d'une ancienne version est restauré dans une nouvelle version ; l'historique reste intact ; impossible sur un document approuvé. »
- F-26 : « Un clic "Mark as reviewed" enregistre auteur, version et date ; l'approbation exige que la version courante ait été marquée relue. »
- F-17 : « Impossible si une section obligatoire est "Not provided" ; après approbation, aucune modification n'est possible ; auteur et date enregistrés. »
- F-19 : « L'action "Create new document" depuis un document approuvé produit un document du même type ; l'ancien reste inchangé. »
- F-20 : « Sont tracés avec acteur, action, date, document et version : généré, relu, approuvé, rejeté, rollback, exporté, rapport de provenance généré. » (ici : généré, relu, approuvé, rejeté, rollback)
- F-24 (part. jalon 5) : « un document approuvé garde les valeurs de son approbation ; aucune interface ne les modifie. »
- N-11 (cas concernés) : « Un test par cas vérifie le message et l'absence de trace technique. »

### Livrables
Cycle de vie complet du document (Under Review → Approved), écran de revue, audit des actions de revue, configuration et instantané de la clinique.

### Maquettes requises
Maquette requise : E-06

### Risques liés
R-01

### Préparation pour les jalons suivants
- Le document approuvé contient l'instantané des coordonnées de la clinique et le nom de l'approbateur : l'export (jalon 6) les lit sans les recalculer.
- Les sources par section et les positions de provenance alimentent le rapport de provenance (jalon 6).
- F-25 doit être rejoué sur toutes les routes créées ici (versions, rollback, relu, approbation).

### Porte de sortie du jalon 5
- [ ] Tâches 1 à 5 faites
- [ ] F-13 vérifié (bandeau, 4 origines, statuts, « Missing information », champs de sécurité visibles s'ils manquent)
- [ ] F-14 vérifié (version précédente intacte ; édition concurrente refusée)
- [ ] F-15 vérifié (version rejetée conservée et marquée)
- [ ] F-16 vérifié (historique intact ; impossible après approbation)
- [ ] Historique des versions consultable (cas d'usage « View the version history »)
- [ ] F-26 vérifié (approbation exige une version relue ; une nouvelle version annule « relu »)
- [ ] F-17 vérifié (bloquée si section obligatoire « Not provided » ; figé après approbation ; édition d'une section la rend fournie)
- [ ] Referral Letter et Discharge Summary sans texte de consultation : approbation impossible
- [ ] F-19 vérifié (nouveau document du même type par régénération ; ancien inchangé)
- [ ] F-20 vérifié pour : généré, relu, approuvé, rejeté, rollback
- [ ] H-02 vérifié (coordonnées de la clinique figées à l'approbation)
- [ ] N-11 : approbation impossible = liste des éléments manquants, document reste Under Review ; régénération échouée = version courante intacte
- [ ] Pipeline CI vert ; F-25 rejoué sur toutes les routes du jalon
- [ ] Utilisateur : « jalon validé »

---

## JALON 6 – Export, provenance, suppression et conservation

- **Semaine(s) :** S7 (j31–j35)
- **Objectif :** Exporter un PDF propre d'un document approuvé, et gérer la provenance, la suppression et la conservation.
- **Dépendances :** Jalon 5 (TERMINÉ)
- **Points à confirmer liés :** P2 (tranché), P11 (tranché), P15 (tranché), P16
- **Préparation reçue des jalons précédents :** instantané de la clinique et approbateur, sources et provenance, audit sans clé étrangère, horloge injectable.

### Tâches
1. Export PDF des trois modèles (référence de rendu : les modèles de l'Annexe A du SRS), après approbation seulement, chaque export tracé (entité `Export`) ; Jinja2 avec **autoéchappement activé** et WeasyPrint avec **chargeur d'URL bloquant** (pas de lecture de fichier ni de requête réseau depuis le contenu) ; **en-tête et pied de page répétés sur chaque page, pagination « x / y »** ; export via l'interface DocumentExporter (2 j)
2. Rapport de provenance séparé, imprimable et exportable, à la demande, avant et après approbation, tracé ; la provenance n'est jamais imprimée dans le PDF clinique (L-08) (1 j)
3. Intégration de l'écran « Document approuvé » (0,5 j)
4. Suppression manuelle d'une consultation (fichiers, texte, documents, versions, **fichiers temporaires et caches** ; trace minimale sans donnée patient) ; durées de conservation avec ordonnanceur de purge et horloge injectable ; consultations jamais approuvées : repère = dernière activité (P16) (1,5 j)

### Exigences couvertes
F-18 (M), F-24 (M, affichage), F-23 (S), F-22 (S), F-20 (M : exporté, rapport de provenance généré), N-10 (S), N-11 (M, PDF en échec), N-06 (échappement des contenus), I-06 (MVP), H-01, H-02, C-04, E-07, L-08, R-05 (FHIR non planifié, voir P2).
Architecture : Jinja2 + WeasyPrint.

### Critères d'acceptation (repris du SRS)
- F-18 : « Possible après approbation seulement ; PDF lisible conforme au template ; aucune mention de l'IA, des sources ni de brouillon ; chaque export est tracé. »
- F-24 : « Nom, adresse, ville, code postal, téléphone, e-mail et site s'affichent dans l'en-tête et le pied de page des documents exportés ; un document approuvé garde les valeurs de son approbation ; aucune interface ne les modifie. »
- F-23 : « Généré à la demande, avant et après approbation ; hors du document clinique ; chaque génération est tracée. »
- F-22 : « Fichiers, texte, documents et versions sont supprimés ; une trace minimale sans donnée patient est conservée dans l'audit. »
- N-10 : « Test avec dates simulées. » (valeurs du MVP : consultation et données 90 jours après la dernière approbation ; audit sans donnée patient 1 an ; logs techniques 30 jours)
- F-20 : exporté et rapport de provenance généré tracés.
- N-11 (cas concerné) : « Un test par cas vérifie le message et l'absence de trace technique. »
- Pagination (SRS, pied de page) : en-tête et pied de page présents sur chaque page d'un document de plusieurs pages (le PDF peut dépasser une page, P15).

### Livrables
PDF exportables (trois modèles), rapport de provenance, suppression manuelle, durées de conservation, écran du document approuvé.

### Maquettes requises
Maquette requise : E-07 (l'action « supprimer » de E-02 a déjà été prévue au jalon 3)

### Risques liés
R-05

### Préparation pour les jalons suivants
- Les durées d'export et de rendu sont mesurées pour le rapport du jalon 7.
- Tous les cas d'échec (PDF) ont un test : ils sont comptés dans N-11 au jalon 7.

### Porte de sortie du jalon 6
- [ ] Tâches 1 à 4 faites
- [ ] F-18 vérifié (après approbation seulement ; **le texte du PDF ne contient aucune mention d'IA, de sources ou de brouillon** (test automatique) ; export tracé)
- [ ] F-24 vérifié (en-tête et pied de page sur chaque page ; valeurs figées à l'approbation)
- [ ] Pagination vérifiée sur un document de plusieurs pages
- [ ] Contenu HTML injecté dans une section : échappé, aucune requête sortante du rendu PDF
- [ ] F-23 vérifié (avant et après approbation ; hors du document clinique ; tracé ; provenance absente du PDF clinique, L-08)
- [ ] F-22 vérifié (suppression complète ; trace minimale sans donnée patient ; audit intact)
- [ ] N-10 vérifié avec dates simulées (y compris consultation jamais approuvée) ; rotation des logs à 30 jours en place
- [ ] N-11 : échec PDF = message sûr, document reste Approved inchangé
- [ ] Pipeline CI vert ; F-25 rejoué sur export, rapport de provenance et suppression
- [ ] Utilisateur : « jalon validé »

---

## JALON 7 – Évaluation IA, tests, observabilité et démonstration

- **Semaine(s) :** S8 (j36–j40)
- **Objectif :** Prouver la qualité du MVP (évaluation IA, tests, durées) et le déployer en démonstration.
- **Dépendances :** Jalons 1 à 6 (TOUS TERMINÉS)
- **Points à confirmer liés :** P5 (tranché), P6 (tranché), P7 (tranché), P8 (tranché), P13
- **Préparation reçue des jalons précédents :** jeu d'évaluation amorcé (jalons 3 et 4), tests de chaque jalon, durées mesurées, test canari.

### Tâches
1. Compléter et rejouer le jeu d'évaluation IA (ancrage, hallucination, cohérence, complétude, respect du template, charge de correction) ; seuil « zéro allergie ou médicament inventé » ; durées et limite mesurée vs 20 s dans le rapport (1,5 j)
2. Compléter les tests : bout en bout (Playwright, avec l'utilisateur TOTP de test), XSS et CSRF de base ; vérifier qu'il existe un test par chemin d'erreur (1 j)
3. Prometheus (durées extraction / LLM / validation / total, échecs par étape, changements d'état) et **un seul tableau de bord Grafana** provisionné par configuration (0,5 j)
4. Test simple à 10 requêtes concurrentes (0,25 j)
5. Pipeline final : job d'évaluation IA unique avec deux déclencheurs (manuel bloquant avant PROD, planifié la nuit sans blocage) ; environnements **DEV (automatique sur la branche principale) et PROD-démo (manuel sur tag, après approbation et évaluation)** ; quota Gemini budgété (0,5 j)
6. Relier chacun des cinq contrôles techniques HIPAA à une exigence ; vérifier l'absence de mention « conforme » ; documenter l'écart L-04 (la consultation d'un document n'est pas tracée) et la procédure d'accès d'urgence, non développée (0,5 j)
7. Documentation finale (README, guide de déploiement, runbook, index des ADR, section « limites connues » reprenant L-04, L-08, L-07 et L-01) et préparation de la démonstration (0,75 j)

### Exigences couvertes
N-16 (M), N-17 (M), N-09 (M), N-01 (S), N-02 (S), N-12 (S), N-03 (C), N-18 (S, vérification), L-04, L-08, N-11 (M, vérification de tous les cas), vérifications de N-05, N-06, N-07, N-08, N-15, C-01, C-02, C-03, C-06, C-07, R-01, R-03, R-06, D-05.
Architecture : pytest, Playwright, structlog, Prometheus, Grafana, jeu d'évaluation rejouable, environnements du pipeline.

### Critères d'acceptation (repris du SRS)
- N-16 : « Les trois niveaux de tests existent ; le jeu d'évaluation est rejouable après chaque changement de modèle. »
- N-17 : « Zéro sur le jeu d'évaluation. »
- N-09 : « Chacun des cinq contrôles techniques HIPAA (accès, audit, intégrité, authentification, transmission) est relié à une exigence ; aucune mention "conforme" dans le produit ni dans la documentation. »
- N-01 : « Les durées sont mesurées ; au-delà de 20 s, la limite mesurée est notée dans le rapport d'évaluation. Objectif non garanti. »
- N-02 : « Les logs techniques contiennent ces quatre durées par génération. »
- N-12 : « Les métriques existent ; aucun document complet dans les logs. »
- N-03 : « Test simple à 10 requêtes concurrentes, sans seuil imposé. »
- N-18 : « Les fonctions du MVP sont accessibles par l'API sans dépendre d'un écran. »
- N-11 : « Un test par cas vérifie le message et l'absence de trace technique. »

### Livrables
Rapport d'évaluation IA, suite de tests (trois niveaux), tableau de bord, pipeline complet, démonstration en PROD, documentation finale.

### Maquettes requises
aucune

### Risques liés
R-01, R-03, R-06

### Porte de sortie du jalon 7
- [ ] Tâches 1 à 7 faites
- [ ] N-16 vérifié (trois niveaux de tests ; jeu d'évaluation rejouable)
- [ ] N-17 vérifié (zéro allergie ou médicament inventé, négation incluse)
- [ ] N-09 vérifié (cinq contrôles reliés ; aucune mention « conforme » ; L-04 et L-08 documentées comme limites connues)
- [ ] N-01 et N-02 vérifiés (quatre durées dans les logs ; dépassement de 20 s noté, mesures Gemini et gpt-oss-20b local)
- [ ] N-12 vérifié
- [ ] N-03 vérifié
- [ ] N-18 vérifié (fonctions du MVP accessibles par l'API sans écran : revue de conception)
- [ ] N-11 : un test par cas de défaillance (fichier invalide, extraction ratée, LLM indisponible ou lent, sortie malformée, PDF en échec, accès refusé)
- [ ] N-05, N-06, N-07, N-08, N-15 revérifiés (canari, XSS, CSRF, injection de prompt)
- [ ] Pipeline CI vert, job d'évaluation IA passé, PROD (démonstration) déployé
- [ ] Utilisateur : « jalon validé »

---

# SECTIONS DE RÉFÉRENCE (ne pas lire pendant un jalon, sauf demande)

## 2. MATRICE DE TRAÇABILITÉ (exigence SRS → jalon)

| Exigence | Jalon(s) | Priorité |
|---|---|---|
| F-01 | 2 | M |
| F-02 | 2 | M |
| F-03 | 3 | M |
| F-04 | 3 | M |
| F-05 | 3 | M |
| F-06 | 3 | M |
| F-07 | 4 | M |
| F-08 | 4 | S |
| F-09 | 4 | M |
| F-10 | 4 | M |
| F-11 | 4 | M |
| F-12 | 4 | M |
| F-13 | 5 | M |
| F-14 | 5 | M |
| F-15 | 5 | M |
| F-16 | 5 | M |
| F-17 | 5 | M |
| F-18 | 6 | M |
| F-19 | 5 | M |
| F-20 | 2, 5, 6 | M |
| F-21 | 2 | M |
| F-22 | 6 | S |
| F-23 | 6 | S |
| F-24 | 5 (configuration, instantané), 6 (affichage) | M |
| F-25 | 2 (rejoué 3 à 6) | M |
| F-26 | 5 | M |
| F-27 | Non planifié (P2) | S |
| N-01 | 7 | S |
| N-02 | 4 (préparé), 7 | S |
| N-03 | 7 | C |
| N-04 | 2 | M |
| N-05 | 1 (vérifié 7) | M |
| N-06 | 3, 6 (échappement), 7 (XSS, CSRF) | M |
| N-07 | 4 (vérifié 7) | M |
| N-08 | 1 (vérifié 7) | M |
| N-09 | 7 | M |
| N-10 | 6 | S |
| N-11 | 2, 3, 4, 5, 6 (vérifié 7) | M |
| N-12 | 7 | S |
| N-13 | 1 | M |
| N-14 | 4 | S |
| N-15 | 1, 7 | S |
| N-16 | 7 | M |
| N-17 | 7 | M |
| N-18 | 1, 4, 7 | S |
| N-19 | 4 | M |
| S-01 | 5 | M |
| S-02 | 4 | M |
| S-03 | 4 | M |
| S-04 | 4 | M |
| S-05 | 4 (enregistrement), 5 (affichage) | M |
| S-06 | 5 | M |
| S-07 | 5 | M |
| C-01 | 1 à 7 (calendrier) | contrainte |
| C-02 | 7 | contrainte |
| C-03 | 3, 7 | contrainte |
| C-04 | 4, 6 | contrainte |
| C-05 | 1 | contrainte |
| C-06 | 7 | contrainte |
| C-07 | 7 (voir P13) | contrainte |
| I-01 | 3 | MVP |
| I-02 | 4 | MVP |
| I-03 | 2 | MVP |
| I-04 | 4 (frontière seulement) | futur |
| I-05 | 4 (via API) | futur |
| I-06 | 6 | MVP |
| E-01 | 2 | |
| E-02 | 3 (suppression en 6) | |
| E-03 | 3 | |
| E-04 | 3 | |
| E-05 | 4 | |
| E-06 | 5 | |
| E-07 | 6 | |
| R-01 | 4, 5, 7 | |
| R-02 | 3 | |
| R-03 | 4, 7 | |
| R-04 | 4 | |
| R-05 | 6 (FHIR non planifié, P2) | |
| R-06 | 1, 7 | |
| R-07 | 3 | |
| H-01 | 5 | hypothèse |
| H-02 | 5 (instantané), 6 (export) | hypothèse |
| H-03 | 5 | hypothèse |
| D-01 | 4 | décision d'architecture |
| D-02 | 3 | décision d'architecture |
| D-03 | 2 | décision d'architecture |
| D-04 | Non planifié (P2) | décision d'architecture |
| D-05 | 4, 7 | décision d'architecture |
| D-06 | 1 | décision d'architecture |
| D-07 | 1 | décision d'architecture |
| L-04 | 2 (écart connu), 7 (documenté) | limite |
| L-08 | 6, 7 (documenté) | limite |
| Architecture : Docker Compose, Caddy, PostgreSQL | 1 | |
| Architecture : CI/CD qualité et sécurité (GitHub Actions) | 1 | |
| Architecture : Keycloak | 2 | |
| Architecture : Docling | 3 | |
| Architecture : LLM, templates YAML | 4 | |
| Architecture : Jinja2 + WeasyPrint | 6 | |
| Architecture : observabilité, tests, job d'évaluation, environnements | 7 | |

## 3. POINTS À CONFIRMER (R8) ET DÉCISIONS

| ID | Point | Statut / décision | Jalon |
|---|---|---|---|
| P1 | Le Technical Stack indique GitHub Actions, Architectures indique GitLab CI/CD. | **TRANCHÉ : GitHub Actions + GHCR.** Corriger le schéma CI/CD. **Vérifié : les relecteurs requis des environnements GitHub ne sont pas disponibles pour un dépôt privé hors GitHub Enterprise (Free, Pro et Team : dépôts publics seulement). Décision sans fonctionnalité payante : le déploiement PROD-démo est déclenché à la main sur un tag de version.** | 1 |
| P2 | Le SRS prévoit le FHIR « si faisable » (F-27, D-04, E-07) ; la consigne et Architectures le placent hors MVP. | **TRANCHÉ : non planifié.** Décision à ajouter au SRS ; port DocumentExporter prévu. | 6 |
| P3 | Le Technical Stack saute la section 2 et sa dernière puce de risques est vide. | **À corriger dans le document** (10 min), hors jalon. | aucun |
| P4 | SonarQube « actif dès que le serveur existe » : aucun serveur défini. | **TRANCHÉ : hors MVP** (bandit, ruff, mypy, Trivy). | 1 |
| P5 | Dependency-Track et SBOM notés « 2e itération ». | **TRANCHÉ : hors MVP** (Trivy couvre les dépendances). | 1, 7 |
| P6 | Trois environnements dans Architectures, absents du SRS. | **TRANCHÉ : DEV + PROD-démo ;** « Validation » = approbation manuelle sur tag, pas une infrastructure. | 7 |
| P7 | Évaluation « manuelle et bloquante avant PROD » et « planifiée la nuit ». | **TRANCHÉ : un job, deux déclencheurs** (manuel bloquant, nocturne informatif). | 7 |
| P8 | Contenu du jeu d'évaluation non défini. | **TRANCHÉ : construit progressivement** dès le jalon 3 (Superbills), jalon 4 (manquant, injection, négation), complété au jalon 7. | 3, 4, 7 |
| P9 | Table ICD-10-CM du CDC (Technical Stack) vs contrôle de format seul (SRS F-04). | **TRANCHÉ :** avertissement non bloquant si code absent de la table versionnée ; CPT : format seulement. | 3 |
| P10 | Conditions d'usage de Gemini « à revérifier ». | **TRANCHÉ :** Gemini pour dev et démo, données synthétiques uniquement ; ADR ; relire les conditions avant le premier appel. | 4 |
| P11 | GENERATING (Lifecycle) ; Export et ClinicProfile absents du Class Diagram. | **TRANCHÉ :** GENERATING transitoire non persisté ; `Export` entité ; ClinicProfile en configuration avec instantané à l'approbation. | 4, 5, 6 |
| P12 | Texte saisi « avant la génération » (SRS) vs modifiable en tout état (Lifecycle). | **TRANCHÉ : modifiable ; instantané du texte stocké avec chaque Document.** Écart au SRS à acter. | 4, 5 |
| P13 | C-07 « aucune contrainte matérielle » ; Docling et gpt-oss-20b sur CPU menacent les 20 s. | **PARTIEL : démo hébergée avec Gemini ; gpt-oss-20b mesuré en local seulement.** **RESTE OUVERT :** machine d'hébergement (RAM, CPU) à fixer avant j1 ; ordre de grandeur visé : au moins 8 Go de RAM et 4 vCPU pour Keycloak, PostgreSQL, Docling et l'application. | 1, 3, 4, 7 |
| P14 | « Create new document » : copie du contenu ou régénération ? | **TRANCHÉ : régénération** (Use Case : relancer « Generate a document » ; Lifecycle : nouveau Document du même type). L'ancien reste figé. | 5 |
| P15 | Le PDF est-il limité à une page ? | **TRANCHÉ : « une page » est une cible, le PDF peut dépasser ;** en-tête, pied de page et pagination sur chaque page. Écart au SRS à acter. | 6 |
| P16 | Conservation de 90 jours « après la dernière approbation » : que faire d'une consultation jamais approuvée ? | **PAR DÉFAUT (sauf objection) :** le repère est la dernière activité de la consultation. | 6 |

## 4. CALENDRIER GLOBAL

| Jalon | Jours | Semaines |
|---|---|---|
| 1 Socle et CI/CD | j1–j4 (4 j) | S1 |
| 2 Authentification, accès, audit | j5–j8 (4 j) | S1–S2 |
| 3 Superbill | j9–j15 (7 j) | S2–S3 |
| 4 Texte et génération | j16–j23 (8 j) | S4–S5 |
| 5 Revue et approbation | j24–j30 (7 j) | S5–S6 |
| 6 Export, suppression, conservation | j31–j35 (5 j) | S7 |
| 7 Évaluation, tests, démonstration | j36–j40 (5 j) | S8 |

**Signalement (R10) :** le périmètre M tient en 40 jours **sans aucune marge**. Les ajouts de la v2 (parsing déterministe, validateur d'ancrage, audit au niveau base, MFA vérifié côté API, concurrence des versions) ont été compensés par : PDF non limité à une page (P15), SonarQube et Dependency-Track hors MVP, un seul tableau de bord Grafana, tests écrits au fil des jalons et non concentrés au jalon 7. Les estimations restent serrées pour un seul développeur.

**Ordre de coupe convenu à l'avance (sans décision sous pression) :**
1. N-03 (test de charge) : réduit à son minimum.
2. N-12 : Prometheus sans tableau de bord Grafana.
3. N-10 : politique documentée et purge simple, sans automatisation complète.
4. F-23 (rapport de provenance, 1 j) : en dernier recours parmi les exigences S.

Ne sont jamais coupées : les exigences M et les règles de sécurité médicale (S-01 à S-07). Toute coupe est décidée par l'utilisateur et consignée, jamais appliquée en silence.

## 5. AUTO-CONTRÔLE (R1 à R10)

- **R1 (zéro ajout) :** respectée. Les durées sont des estimations ; les mécanismes ajoutés par la v2 viennent de la revue du plan v1 et sont rattachés à une exigence ou à un risque du SRS (S-02, N-19, N-05, F-21, F-01, H-02).
- **R2 (zéro manque) :** respectée. **Écart :** F-27 et D-04 (FHIR) non planifiés (P2) ; I-04 et I-05 ne sont que des frontières futures.
- **R3 (pas de détail inventé) :** respectée.
- **R4 (4 à 7 tâches) :** respectée (5, 5, 7, 6, 5, 4, 7).
- **R5 :** absente de la liste de règles fournie (elle passe de R4 à R6) ; à confirmer.
- **R6 (critères du SRS) :** respectée, critères repris du SRS.
- **R7 (maquettes) :** respectée, uniquement « Maquette requise : E-xx ».
- **R8 (points à confirmer) :** respectée (P1 à P16) ; restent ouverts : machine d'hébergement (P13) et repère de conservation (P16, par défaut).
- **R9 (dépendances) :** respectée et rendue explicite par les champs « Préparation reçue » et « Préparation pour les jalons suivants ».
- **R10 (8 semaines) :** répartition explicite ; **écart :** aucune marge, signalée en section 4, avec ordre de coupe.

## 6. MISES À JOUR DES DOCUMENTS SOURCES À FAIRE

| Document | Modification |
|---|---|
| Architectures (CI/CD) | GitLab CI/CD et GitLab Container Registry deviennent GitHub Actions et GHCR ; SonarQube et Dependency-Track marqués hors MVP ; environnements DEV et PROD-démo. |
| Technical Stack | Corriger la numérotation (section 2) et la puce vide (P3) ; ajouter le port DocumentExporter ; préciser que Ollama est un profil local. |
| SRS | Ajouter des décisions pour : FHIR non planifié (P2), instantané du texte (P12), « une page » devenant une page cible (P15), repère de conservation (P16). |
| Lifecycle / Class Diagram | Ajouter Export et ClinicProfile (P11) ; préciser que le texte est modifiable avec instantané par Document (P12). |
