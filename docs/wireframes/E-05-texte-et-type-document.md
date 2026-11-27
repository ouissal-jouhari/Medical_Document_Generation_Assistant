# Maquette E-05 – Texte et type de document (basse fidélité)

Exigences : F-07, F-09, F-10.

```
┌────────────────────────────────────────────────────────────────────┐
│ XeleronIA                                                          │
├────────────────────────────────────────────────────────────────────┤
│ Texte et type de document                       État : Validated   │
│                                                                    │
│ Document type                                                      │
│  ( ) Clinical Note                                                 │
│  ( ) Referral Letter                                               │
│  ( ) Discharge Summary                                             │
│                                                                    │
│ Consultation text (optional)                    0 / 5000 characters│
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                                                              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  The consultation text remains editable after generation.         │
│                                                                    │
│ ⚠ Superbill data alone is not sufficient to generate complete    │
│ clinical documents. Adding the consultation text is recommended.   │
│                                                                    │
│                                     [ Cancel ] [ Generate draft ]  │
│                                                                    │
│ Message sûr lors d'une erreur :                                   │
│ « Document generation failed. You can retry. »                     │
└────────────────────────────────────────────────────────────────────┘
```

Règles :
- Le texte est limité à 5 000 caractères côté serveur.
- Le bouton Generate est désactivé pendant la génération pour éviter les doubles déclenchements.
- Sans texte, la remarque d'avertissement reste à l'écran uniquement.
- Le texte modifié après une première génération est enregistré dans l'instantané du prochain Document.
- La génération exige une consultation Validated.
