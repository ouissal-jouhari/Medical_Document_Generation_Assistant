# ADR 0010 – Gemini pour la démonstration et Ollama local

## Décision

XeleronIA utilise Gemini derrière `LlmProvider` pour les environnements hébergés de
développement et de démonstration. Ollama avec `gpt-oss-20b` reste disponible dans le
profil Docker Compose `local`. Les données envoyées sont synthétiques.

## Contraintes

- Aucun nom, date de naissance ou identifiant patient direct n'est envoyé au LLM.
- Les Superbills, l'OCR et le texte de consultation sont des données non fiables.
- La sortie est validée par Pydantic côté domaine et par un validateur d'ancrage.
- Le délai d'appel est limité à 20 secondes.

## Conséquence

Le moteur de génération reste indépendant du fournisseur grâce au port `LlmProvider`.
