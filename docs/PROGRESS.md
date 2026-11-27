# Progression XeleronIA
## Fait
- Jalon 2 : TERMINÉ (validé). Jalon 3 : TERMINÉ (validé le 2026-11-26). Jalon 4 : TERMINÉ (validé le 2026-11-27, PR #2).
- Jalon 4 : porte vérifiée par tests (backend 159 passés avec PostgreSQL, 5 ignorés : Docling, évaluation live) ; Gemini réel : 4/4 cas du jeu d'évaluation passent (ADR 0015, 0016 ; `docs/mesures/jalon-4-gemini.md`).
- Jalon 4 : sortie LLM validée par Pydantic (F-12) ; budget de délai 90 s par appel / 150 s total ; proxy aligné (330 s) ; double déclenchement refusé ; durées N-02 journalisées.
- F-22 (suppression d'une consultation) livré en avance (jalon 6), ADR 0014.
## En cours
- Jalon 5 : EN COURS (branche jalon-5-revue-approbation).
## Reste ouvert (écarts notés)
- Jalon 4 : objectif 20 s (N-01) non tenu sur Gemini (11–119 s mesurés), non bloquant. gpt-oss-20b non mesuré (démon Ollama arrêté). Conditions d'usage Gemini à relire par l'équipe (ADR 0010). Durée d'extraction non rattachée à la génération (N-02).
- Jalon 1 : hôte DEV (P13), déploiement/chiffrement au repos ; « jalon validé » non donné.
- Jalon 2 : test automatique de la redirection navigateur (Playwright) reporté au jalon 7.
- Jalon 3 : extraction froide 43 s en CI / 90–110 s poste (objectif non atteint) ; placeholder .env à remplacer avant déploiement.
