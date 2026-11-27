# Maquette E-06 – Revue du document (basse fidélité)

Exigences : F-07, F-11 à F-17, F-19, F-26 ; S-01, S-05, S-06, S-07.

```
┌────────────────────────────────────────────────────────────────────┐
│ XeleronIA                                                          │
├────────────────────────────────────────────────────────────────────┤
│ ▓▓ AI-generated draft – review every section before approval ▓▓    │  ← tant que non approuvé
│ Referral Letter            Under Review · Version 3 (edited)       │
│ ⚠ No consultation text: sections depending on it are Not provided │  ← si pas de texte
│                                                                    │
│ Missing information                                                │
│  • Assessment (required)  • Allergies and adverse reactions (safety)│
│                                                                    │
│ Patient and encounter                       [origin: Superbill]    │
│  Name · DOB · ID · Physician · Date of service                     │
│  Diagnoses (coded) · Procedures (coded)                            │
│                                                                    │
│ Reason for referral   REQUIRED · Provided   [origin: AI]           │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ texte modifiable                                             │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  Sources: [Consultation text] « extrait »  [Superbill] « code »    │
│                                                                    │
│ Allergies and adverse reactions  SAFETY · ⚠ NOT PROVIDED           │  ← mis en évidence
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ (vide)                                                       │ │
│  └──────────────────────────────────────────────────────────────┘ │
│ Assessment   REQUIRED · Provided   [origin: Clinician, auteur, date]│
│                                                                    │
│ [ Save ] [ Mark as reviewed ] [ Approve ] [ Reject ] [ Regenerate ]│
│                                                                    │
│ Version history                                                    │
│  v3 edited      Dr A  2026-01-01 10:12   current  reviewed         │
│  v2 ai_generated Dr A 2026-01-01 10:05   rejected   [View][Restore]│
│  v1 ai_generated Dr A 2026-01-01 10:00              [View][Restore]│
│                                                                    │
│ Message d'approbation impossible :                                │
│ « Approval is not possible: Assessment (Not provided). »          │
└────────────────────────────────────────────────────────────────────┘

Après approbation (document figé) :
┌────────────────────────────────────────────────────────────────────┐
│ Referral Letter            Approved · Version 3                    │
│ Approved by Dr A on 2026-01-01 10:20                               │
│ Clinic: nom, adresse, ville, code postal, téléphone, e-mail, site  │
│ Sections en lecture seule (aucun bandeau brouillon)                │
│ Version history (consultable, sans Restore)                        │
│                                      [ Create new document ]       │
└────────────────────────────────────────────────────────────────────┘
```

Règles :
- Chaque action envoie le numéro de version affiché ; si le document a changé entre-temps, l'action est refusée (« The document changed. Reload it. »).
- « Save » crée une seule version « edited » pour toutes les sections modifiées ; une section « Not provided » remplie devient fournie (origine clinicien).
- Toute nouvelle version (édition, rollback, régénération) annule la marque « relu ».
- « Mark as reviewed » et « Approve » sont impossibles sur une version rejetée ; « Regenerate » n'est proposé qu'après un rejet.
- « Approve » exige la version courante relue et toutes les sections REQUIRED fournies ; sinon la liste des éléments manquants est affichée et le document reste Under Review.
- « Restore » copie l'ancienne version dans une nouvelle version ; indisponible après approbation.
- « Create new document » relance la génération du même type ; le document approuvé reste inchangé.
