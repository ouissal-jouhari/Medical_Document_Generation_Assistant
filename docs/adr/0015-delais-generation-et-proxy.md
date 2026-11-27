# ADR 0015 – Délais de génération et alignement du proxy

## Contexte

Mesures réelles sur Gemini le 2026-11-27 (données synthétiques, voir `docs/mesures/jalon-4-gemini.md`) :

- générations réussies entre 16 s et 110 s ;
- réponses `503 UNAVAILABLE` après 3 s à 85 s d'attente, `429 RESOURCE_EXHAUSTED`, et délais de 78 s à 90 s
  sur le modèle principal ; le modèle de repli répond en 14 s à 17 s.

Le budget initial (20 s par appel, sans borne globale) ne permettait pas de terminer une génération,
et une chaîne de repli pouvait dépasser 4 minutes sans limite globale (tâche 6 : délai maximal).

## Décision

- **Délai par appel LLM** : 90 s (`LLM_TIMEOUT_SECONDS`).
- **Délai total d'une génération**, tous modèles et tentatives confondus : 150 s (`LLM_TOTAL_TIMEOUT_SECONDS`).
  Au-delà, l'API répond `504 llm_timeout` ; aucun brouillon n'est créé et la consultation reste Validated.
- Un appel ne reçoit jamais plus que le temps restant du budget total.
- Repli : un délai passe immédiatement au modèle suivant ; `400/401/403` ne basculent pas (requête ou clé
  invalide, identique pour tous les modèles) ; `429` et `5xx` font deux tentatives par modèle.
- **Proxy Caddy** (`deploy/Caddyfile`) : `response_header_timeout` et `read_timeout` à 330 s, soit le plus long
  traitement serveur (extraction Superbill 300 s) plus une marge de 30 s. Le test
  `test_F12_proxy_response_timeout_covers_server_budgets` garde cet alignement.

## Contraintes

- Les durées et la disponibilité dépendent du fournisseur : les valeurs sont paramétrables par environnement.
- Les messages affichés restent fixes et sûrs (N-11) : « Document generation took too long. You can retry. »

## Conséquence

- Un fournisseur surchargé se traduit par un message « réessayer », jamais par un brouillon partiel.
- L'objectif de 20 s (N-01) n'est **pas tenu** sur Gemini aux dates mesurées. L'objectif est non bloquant ;
  l'écart est noté dans `docs/PROGRESS.md` et dans le rapport de mesures.
- Le choix de 90 s et 150 s est une valeur de départ, à réviser après une mesure sur une période de charge normale.
- Décision liée : ADR 0010 (la limite de 20 s y est remplacée).
