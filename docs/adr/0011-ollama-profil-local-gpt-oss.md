# ADR 0011 – Ollama avec gpt-oss-20b en profil local

## Statut
Accepté (jalon 4).

## Contexte
Le SRS et le CLAUDE.md imposent : Ollama uniquement en profil local, démonstration hébergée = Gemini, données synthétiques seulement. Le jalon 4 exige que les deux fournisseurs LLM soient interchangeables par configuration.

## Décision
- `OllamaLlmProvider` (gpt-oss-20b) est un adaptateur derrière le port `LlmProvider`, activé par `LLM_PROVIDER=ollama`.
- Il n'est pas inclus dans le profil hébergé (`deploy-prod-demo.yml`) ; le profil local le lance via Docker Compose.
- Même contrat que Gemini : sortie JSON validée par Pydantic, délai maximal `LLM_TIMEOUT_SECONDS`, mêmes erreurs normalisées (`LlmTimeout`, `LlmUnavailable`, `MalformedGeneration`).
- Mesure de durée : à faire en local sur poste disposant du modèle ; non mesurée dans l'environnement de CI.

## Conséquences
- Aucune donnée n'est envoyée hors du poste en profil local.
- Les différences de sortie structurée entre fournisseurs sont absorbées par l'adaptateur, pas par le moteur de génération.
