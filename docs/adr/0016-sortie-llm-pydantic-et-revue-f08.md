# ADR 0016 – Sortie LLM validée par Pydantic et revue de conception du texte (F-08)

## Contexte

- F-12 interdit qu'une sortie malformée ou incomplète soit affichée comme brouillon.
- Le contrôle initial lisait la sortie avec `dict.get`. Une section mal formée (statut en minuscules,
  clé `citations` absente, clé inconnue) était transformée en « Not provided » sans erreur : une génération
  incomplète passait pour un brouillon valide.
- F-08 demande une revue de conception : le texte de consultation doit être accessible par l'API,
  indépendamment de l'écran.

## Décision

1. **Sortie validée par Pydantic** avant le contrôle d'ancrage : `_GenerationOutput` et `_SectionOutput`,
   `extra="forbid"`, statut `Literal["PROVIDED", "NOT_PROVIDED"]`, `content` obligatoire (`str | None`),
   `citations` obligatoire. Toute dérive du schéma lève `MalformedGeneration` (HTTP 502, « malformed_generation »).
2. **Une seule nouvelle tentative** pour une sortie illisible ou malformée (`_ask` / `_call_llm`).
   Un délai ou une indisponibilité ne sont jamais réessayés ici : le fournisseur gère ses propres
   repli et délais (ADR 0015).
3. **Durées journalisées par génération** (N-02) : événement `generation_timed` avec `llm_ms`,
   `validation_ms`, `total_ms`. La durée d'extraction de la Superbill est mesurée au dépôt (jalon 3) et
   n'est pas rattachée à la génération : écart noté.
4. **Revue F-08 (conception)** : le texte est enregistré par `PUT /consultations/{id}/text` et relu par
   `GET /consultations/{id}`, sans passer par l'écran. Cette frontière d'API est le point d'entrée d'un futur
   AI Scribe (I-05) ; aucun développement de l'AI Scribe n'est fait (hors MVP).
5. **Instantané** : chaque document garde le texte utilisé (`text_snapshot`), pour que les positions de
   provenance restent valides après une modification du texte (F-07, jalons 5 et 6).
6. **Templates validés au démarrage** : `create_app` charge les gabarits ; un fichier invalide empêche
   l'application de démarrer (N-14). Ajouter un gabarit ne modifie pas le moteur.

## Contraintes

- Le contrôle reste déterministe et ne journalise aucun texte de consultation ni de section (N-19).
- Aucune section n'est inventée : une section sans citation valide reste « Not provided » (F-11, S-02, S-03).

## Conséquence

- Une sortie hors schéma est refusée au lieu d'être affichée comme « Not provided ». Test :
  `test_F12_schema_drift_is_malformed_not_silently_not_provided`.
- Le double déclenchement est refusé (409) pendant une génération : `test_F09_double_trigger_is_refused_while_generating`.
- Les contrôles d'ancrage restent dans `services/generation.py`, sans dépendance vers le fournisseur.
