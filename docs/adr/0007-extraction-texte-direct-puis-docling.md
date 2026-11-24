# ADR 0007 – Extraction : texte direct puis Docling, hors de la boucle d'événements

- **Statut :** accepté (F-04, I-01, D-02, R-02)
- **Règle de décision (explicite) pour un PDF :**
  1. extraire la couche texte avec pypdf ;
  2. si elle est **non vide** et que **tous les champs obligatoires** du schéma 9.2 y sont trouvés par le parsing déterministe, ce texte est utilisé (moteur `text-layer`) ;
  3. sinon (scan, couche texte vide ou incomplète), **Docling** sur CPU (moteur `docling`).
  Une image (png, jpg, jpeg) passe toujours par Docling.
- **Exécution :** Docling tourne dans un thread dédié (un seul worker : un seul traitement CPU à la fois), jamais dans la boucle d'événements. Délai maximal de sécurité : 300 s ; au-delà, l'extraction est comptée comme échec. L'objectif de 20 s reste non bloquant et mesuré (jalon 7). Mesures du jalon 3 pour un scan de 1700 × 2200 px, premier appel avec chargement des modèles : environ 90 à 110 s sur le poste de développement, environ 43 s sur un runner GitHub (CI). L'objectif de 20 s n'est donc pas atteint à froid. Pistes (jalon 7) : préchargement des modèles au démarrage, mesure à chaud.
- **Poids des modèles :** embarqués dans l'image Docker au moment du build (conversion à vide, `python -m app.adapters.docling_warmup`, puis `HF_HUB_OFFLINE=1`) : aucun téléchargement à l'exécution, compatible on-premise. `DOCLING_ARTIFACTS_PATH` reste disponible pour un dossier de modèles externe.
- **Paquet optionnel :** `docling` est un extra (`uv sync --extra ocr`). Il est installé dans l'image Docker et dans un job CI dédié ; le job de qualité rapide ne l'installe pas. Le port `OcrProvider` reste l'unique point d'entrée (N-13).
- **Aucun LLM** dans l'extraction (diagrammes) ; le nom du patient ne sort jamais du système (N-19).
- **Limite :** la qualité sur un scan réel n'est pas garantie ; la vérification par le clinicien (F-05) est le filet de sécurité (R-02).
- **Variabilité :** la mise en forme du Markdown de Docling varie selon l'environnement (tableaux éclatés ou brouillés sur certains PDF). C'est pourquoi un PDF avec couche texte complète n'est jamais envoyé à Docling, et pourquoi le parseur tolère plusieurs formes (tableau Markdown, ligne par cellule). Les tests d'intégration vérifient le contenu lu, pas la mise en forme.
