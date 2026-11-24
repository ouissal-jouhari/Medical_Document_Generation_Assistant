# Maquette E-02 – Mes consultations (basse fidélité)

Exigences : F-25 (seules les consultations de l'auteur), F-22 (suppression, livrée au jalon 6 ; emplacement prévu ici).

```
┌────────────────────────────────────────────────────────────────────┐
│ XeleronIA                         Bonjour Dr Test   [Se déconnecter]│
├────────────────────────────────────────────────────────────────────┤
│ Mes consultations                          [ + Nouvelle consultation]│
│                                                                    │
│ ┌────────────┬─────────────────┬──────────────┬─────────┬─────────┐│
│ │ Créée le   │ Patient         │ État         │ Action  │ Suppr.  ││
│ ├────────────┼─────────────────┼──────────────┼─────────┼─────────┤│
│ │ 2026-11-24 │ (non extrait)   │ Uploaded     │ Reprendre│  [ ⌫ ]  ││
│ │ 2026-11-23 │ Jane Doe        │ Parsed       │ Vérifier │  [ ⌫ ]  ││
│ │ 2026-11-22 │ John Roe        │ Validated    │ Ouvrir   │  [ ⌫ ]  ││
│ └────────────┴─────────────────┴──────────────┴─────────┴─────────┘│
│ (liste vide : « Aucune consultation. Créez-en une. »)               │
└────────────────────────────────────────────────────────────────────┘
```

Règles :
- La liste ne montre que les consultations de l'utilisateur connecté.
- « Reprendre » (Uploaded) ouvre E-03 pour un nouveau dépôt ; « Vérifier » (Parsed) ouvre E-04 ; « Ouvrir » (Validated) affiche E-04 en lecture seule.
- Le bouton de suppression est présent mais désactivé jusqu'au jalon 6.
