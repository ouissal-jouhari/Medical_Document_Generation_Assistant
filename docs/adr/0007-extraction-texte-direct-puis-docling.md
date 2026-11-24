# ADR 0007 – Extraction : texte direct puis Docling, hors de la boucle d'événements

- **Statut :** accepté (F-04, I-01, D-02, R-02)
- **Règle de décision (explicite) pour un PDF :**
  1. extraire la couche texte avec pypdf ;
  2. si elle est **non vide** et que **tous les champs obligatoires** du schéma 9.2 y sont trouvés par le parsing déterministe, ce texte est utilisé (moteur `text-layer`) ;
  3. sinon (scan, couche texte vide ou incomplète), **Docling** sur CPU (moteur `docling`).
  Une image (png, jpg, jpeg) passe toujours par Docling.
- **Exécution :** Docling tourne dans un thread dédié (un seul worker : un seul traitement CPU à la fois), jamais dans la boucle d'événements. Délai maximal de sécurité : 120 s ; au-delà, l'extraction est comptée comme échec. L'objectif de 20 s reste non bloquant et mesuré (jalon 7).
- **Poids des modèles :** embarqués dans l'image Docker au moment du build (variable `DOCLING_ARTIFACTS_PATH`) : aucun téléchargement à l'exécution, compatible on-premise.
- **Paquet optionnel :** `docling` est un extra (`uv sync --extra ocr`). Il est installé dans l'image Docker et dans un job CI dédié ; le job de qualité rapide ne l'installe pas. Le port `OcrProvider` reste l'unique point d'entrée (N-13).
- **Aucun LLM** dans l'extraction (diagrammes) ; le nom du patient ne sort jamais du système (N-19).
- **Limite :** la qualité sur un scan réel n'est pas garantie ; la vérification par le clinicien (F-05) est le filet de sécurité (R-02).
