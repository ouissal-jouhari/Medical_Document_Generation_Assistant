# ADR 0010 – Gemini pour la démonstration et Ollama local

## Décision

XeleronIA utilise Gemini derrière `LlmProvider` pour les environnements hébergés de
développement et de démonstration. Ollama avec `gpt-oss-20b` reste disponible dans le
profil Docker Compose `local`. Les données envoyées sont synthétiques.

## Contraintes

- Aucun nom, date de naissance ou identifiant patient direct n'est envoyé au LLM.
- Les Superbills, l'OCR et le texte de consultation sont des données non fiables.
- La sortie est validée par Pydantic (ADR 0016) puis par un validateur d'ancrage.
- Les délais sont bornés par appel et par génération : voir ADR 0015 (remplace la limite
  de 20 secondes de la première version).
- Conditions d'usage Gemini : à relire par l'équipe avant tout usage hors données synthétiques.

## Conséquence

Le moteur de génération reste indépendant du fournisseur grâce au port `LlmProvider`.
Mesures réelles Gemini : `docs/mesures/jalon-4-gemini.md`.
