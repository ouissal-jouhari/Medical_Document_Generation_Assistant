# ADR 0017 – Versions immuables, marques de revue et concurrence (jalon 5)

## Contexte

- F-14 à F-17, F-26 : toute édition crée une version, l'ancienne reste intacte ; rejet, rollback,
  « relu » et approbation portent sur une version ; le document approuvé est figé.
- JALONS tâche 1 : une version par « Save » explicite, numéro de version attendu dans chaque requête,
  contrainte d'unicité (document, numéro). Le gel doit être imposé par le domaine, pas par l'interface.
- SRS 9.1 cite les types de version « IA générée, éditée, rejetée, approuvée ».
- Au jalon 4, une ligne `document` portait directement le contenu et un numéro séquentiel par consultation.

## Décision

1. **Table `document_version`** (migration 0006) : numéro, type, auteur, date, instantané du texte (P12),
   contenu (bloc commun, sections, sources). Contrainte `uq_document_version (document_id, number)`.
   Le rôle applicatif n'a que SELECT, INSERT (et DELETE pour F-22) : une version n'est jamais modifiée.
   Les documents existants deviennent leur version 1 (`ai_generated`).
2. **Types stockés : `ai_generated` et `edited`.** « Rejetée » et « approuvée » sont des marques :
   le rejet et le « relu » sont des lignes de `document_version_event` (ajout seul) ; l'approbation est
   `document.approved_version`. L'API expose ces marques par version. Un rollback crée une version
   `edited` avec `restored_from` (numéro restauré).
3. **`document.version` = version courante**, utilisée comme verrou optimiste (`version_id_col` de
   SQLAlchemy) : chaque UPDATE porte `WHERE version = <lue>`. Toute requête de revue envoie
   `expectedVersion` ; écart, course perdue ou numéro déjà pris → 409 `version_conflict`.
4. **Règles dans `app/domain/document.py`** (sans dépendance externe) : document approuvé → 409
   `document_approved` pour toute action ; « relu » et approbation impossibles sur une version rejetée ;
   régénération seulement après rejet ; approbation exige la version courante relue, les sections
   REQUIRED et le bloc commun fournis (409 `approval_blocked` + liste `missing`, document inchangé).
   Une nouvelle version n'a pas de marque : elle annule donc « relu ».
5. **Édition** : un enregistrement = une version pour toutes les sections modifiées ; sans changement,
   aucune version. Une section éditée prend l'origine `clinician` et une source « clinicien » (auteur,
   date, SRS 9.3) qui remplace les citations IA, qui ne justifient plus le nouveau contenu. Vidée, elle
   redevient « Not provided ». Le bloc commun (Superbill validée) n'est pas éditable.
6. **Audit** (F-20) via `SqlAuditLog` et l'énumération `AuditAction` : `generated` (création et
   régénération), `reviewed`, `rejected`, `rollback`, `approved`, avec document et version. L'action
   du jalon 4 `document_generated` devient `generated` (valeur de l'énumération).
7. **Routes** sous `/documents/{id}` (lecture, `versions`, `sections`, `reject`, `regenerate`, `rollback`,
   `review`, `approve`, `new-document`) ; la lecture `/consultations/documents/{id}` du jalon 4 y est
   déplacée. Accès par le dépôt filtré par auteur (F-25, H-03).
8. **« Create new document »** (F-19, P14) : relance la génération du même type depuis la consultation ;
   nouveau document en revue ; l'ancien reste figé.

## Conséquences

- Historique complet consultable ; l'approbation porte toujours sur une version relue et identifiée.
- SAFETY (médicaments, allergies) ne bloque pas l'approbation (SRS : seules les sections obligatoires
  bloquent) mais est mis en évidence dans la liste « Missing information » et à l'écran.
- Le rendu de l'écran E-06 est vérifié par l'API (champs `draft`, `origin`, `sources`,
  `missing_information`) ; le test navigateur bout en bout est prévu au jalon 7 (Playwright).
