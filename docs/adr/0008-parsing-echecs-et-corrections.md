# ADR 0008 – Parsing déterministe, politique d'échec et corrections

- **Statut :** accepté (F-04, F-05, F-06, S-07, L-01, R-07)
- **Parsing :** déterministe, sans LLM. Un seul gabarit de Superbill est géré (L-01) : champs repérés par leur libellé (deux-points, tabulation ou cellule de tableau), codes ICD-10-CM et CPT repérés dans leurs sections « Diagnoses » et « Procedures ». Les libellés connus mais inutilisés (assurance, téléphone, adresse…) servent de séparateurs. Les dates US (MM/DD/YYYY) et « Month DD, YYYY » sont converties en ISO ; une date illisible est conservée telle quelle et signalée.
- **Unités des procédures :** lues seulement si le tableau a une colonne « Units » ; sinon `null` (jamais inventées, S-02).
- **Politique d'échec (F-06) :**
  - *Extraction ratée* = texte vide, erreur technique, délai dépassé, ou **aucun** champ obligatoire trouvé. La consultation est créée (ou reste) à l'état **Uploaded**, l'échec est compté, un nouveau dépôt est possible sur la même consultation.
  - *Données incomplètes ou invalides* (au moins un champ trouvé, d'autres manquants ou mal formés) : la consultation passe à **Parsed** pour que le clinicien complète et corrige (E-04). Les problèmes sont listés (champ et code, jamais la valeur). La validation est refusée tant qu'un problème **bloquant** subsiste (S-07).
- **Problèmes bloquants :** champ obligatoire manquant, date non ISO, format ICD-10-CM ou CPT invalide, unités < 1. **Non bloquants :** code ICD-10-CM absent de la table CDC (P9), unités absentes, montant total illisible.
- **Corrections (F-05) :** chaque champ modifié produit une ligne en ajout seul (champ, ancienne et nouvelle valeur, auteur, date) ; l'extraction d'origine est conservée à côté des données corrigées. Les corrections ne sont possibles qu'à l'état Parsed ; une consultation **Validated est verrouillée** (le SRS ne prévoit pas de retour en arrière).
- **Données :** le nom du fichier d'origine n'est jamais conservé ni journalisé (il peut contenir un nom de patient).
- **Écart avec la Superbill d'exemple :** le fichier `XeleronIA_Superbill_Form_Sample.docx` (Annexe A) n'était pas disponible. Les Superbills de test sont synthétiques et suivent le schéma 9.2 ; la revalidation sur l'exemple réel et sur une Superbill réelle anonymisée reste à faire (R-07, L-01).
