# Maquette E-03 – Nouvelle consultation (basse fidélité)

Exigences : F-03 (dépôt et limites), F-06 (échec d'extraction), N-11 (messages sûrs).

```
┌────────────────────────────────────────────────────────────────────┐
│ XeleronIA                                                          │
├────────────────────────────────────────────────────────────────────┤
│ Nouvelle consultation                                              │
│                                                                    │
│ Déposez la Superbill (PDF de 3 pages maximum, ou une image         │
│ png/jpg/jpeg), 50 Mo maximum.                                      │
│                                                                    │
│   [ Choisir un fichier… ]   superbill.pdf                          │
│                                                                    │
│   [ Envoyer ]   [ Annuler ]                                        │
│                                                                    │
│ ┌ Message (zone d'état) ──────────────────────────────────────────┐│
│ │ Extraction en cours…   |   ou erreur sûre, une des suivantes :   ││
│ │ • Format non accepté (PDF, png, jpg, jpeg).                      ││
│ │ • Fichier trop volumineux (50 Mo maximum).                       ││
│ │ • Le PDF dépasse 3 pages.                                        ││
│ │ • PDF protégé : déposez une version non chiffrée.                ││
│ │ • Fichier illisible ou corrompu.                                 ││
│ │ • Extraction impossible. La consultation reste « Uploaded » ;    ││
│ │   déposez de nouveau la Superbill.                               ││
│ └──────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────┘
```

Règles :
- Un fichier refusé ne crée aucune consultation.
- Un échec d'extraction conserve la consultation à l'état Uploaded et le bouton « Envoyer » reste disponible (nouveau dépôt sur la même consultation).
- Succès : passage à E-04.
