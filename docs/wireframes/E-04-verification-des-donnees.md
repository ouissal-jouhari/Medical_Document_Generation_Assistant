# Maquette E-04 – Vérification des données (basse fidélité)

Exigences : F-04 (champs extraits), F-05 (correction tracée, validation explicite), R-02 (erreur d'OCR sur un code), S-07.

```
┌────────────────────────────────────────────────────────────────────┐
│ XeleronIA                                                          │
├────────────────────────────────────────────────────────────────────┤
│ Vérification des données                       État : Parsed       │
│                                                                    │
│ Patient                                                            │
│  Nom complet*      [ Jane Doe            ]                         │
│  Date de naissance*[ 1980-04-12          ]  ⚠ format AAAA-MM-JJ    │
│  Identifiant*      [ P-000123            ]                         │
│ Médecin*           [ Dr Alice Martin     ]                         │
│ Consultation                                                       │
│  Date de service*  [ 2026-11-20          ]                         │
│  Lieu de service   [ Office               ]                        │
│                                                                    │
│ Diagnostics* (ICD-10-CM)                  [ + ajouter ] [ ⌫ ligne ]│
│  [ E11.9  ] [ Type 2 diabetes mellitus without complications ]     │
│  [ I1O.9  ] [ Hypertension ]        ⚠ format invalide (bloquant)   │
│  [ Z99.99 ] [ ...            ]      ⚠ code absent de la table CDC  │
│                                                (avertissement)     │
│ Procédures* (CPT)                         [ + ajouter ] [ ⌫ ligne ]│
│  [ 99213  ] [ Office visit ] unités [ 1 ]                          │
│ Montant total      [ 150.00 ]  (non utilisé dans les documents)    │
│ Pages extraites : 1 (technique, non modifiable)                    │
│                                                                    │
│ * obligatoire.   Dernières corrections : 2 (auteur et date)        │
│                                                                    │
│   [ Enregistrer les corrections ]     [ Valider les données ]      │
│                                                                    │
│ (message : « Corrigez les champs signalés avant de valider. »)     │
└────────────────────────────────────────────────────────────────────┘
```

Règles :
- Chaque champ est modifiable tant que l'état est Parsed ; chaque modification enregistre auteur et date.
- Les problèmes bloquants (champ obligatoire manquant, date ou format de code invalide) empêchent « Valider ». Un code ICD-10-CM absent de la table CDC est un avertissement, non bloquant.
- « Valider les données » est une action explicite : la consultation passe à Validated. En Validated, l'écran est en lecture seule.
- Les messages ne reprennent jamais les valeurs saisies (N-11).
