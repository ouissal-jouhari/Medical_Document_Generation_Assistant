# Maquette E-07 – Document approuvé (basse fidélité)

Exigences : F-18, F-19, F-23, F-24 ; L-08, N-11. F-27 (FHIR) hors MVP (P2) : aucun bouton.

```
┌────────────────────────────────────────────────────────────────────┐
│ XeleronIA                                                          │
├────────────────────────────────────────────────────────────────────┤
│ Referral Letter            Approved · Version 3                    │  ← aucun bandeau brouillon
│ Approved by Dr A on 2026-01-01 10:20                               │
│ Clinic: nom, adresse, ville, code postal, téléphone, e-mail, site  │  ← instantané figé (H-02)
│                                                                    │
│ [ Export PDF ] [ Provenance report ] [ Create new document ]       │
│                                                                    │
│ Message d'échec de l'export (N-11) :                               │
│ « The PDF could not be produced. The document is unchanged. »      │
│                                                                    │
│ Patient and encounter · sections en lecture seule                  │
│ Version history (consultable, sans Restore)                        │
└────────────────────────────────────────────────────────────────────┘
```

Avant approbation (E-06), seul le bouton « Provenance report » est proposé (F-23).

PDF clinique (F-18, F-24, L-08) :

```
┌──────────────────────── page x ───────────────────────────────┐
│ Nom de la clinique · adresse · ville code postal               │  ← en-tête répété
│────────────────────────────────────────────────────────────────│
│ REFERRAL LETTER                                                │
│ Patient · DOB · ID · Physician · Date of service               │
│ Diagnoses (ICD-10-CM) · Procedures (CPT)                       │
│ Section 1 …  Section n (texte approuvé, « Not provided » sinon)│
│ Approved by Dr A on 2026-01-01                                 │
│────────────────────────────────────────────────────────────────│
│ téléphone · e-mail · site                          page x / y  │  ← pied répété
└────────────────────────────────────────────────────────────────┘
```

Aucune mention de l'IA, des sources, des origines ni de brouillon dans le PDF clinique.
Le rapport de provenance est un PDF séparé : section, statut, origine, sources (type, champ ou
extrait, auteur et date d'une modification).
