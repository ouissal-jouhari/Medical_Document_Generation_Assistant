# ADR 0020 – Rapport de provenance séparé, tracé dans l'audit

## Contexte

- F-23 : rapport séparé, imprimable et exportable, à la demande, avant et après approbation ;
  chaque génération est tracée. L-08 : la provenance n'est jamais imprimée dans le PDF clinique.
- SRS 9.3 : sources par section (Superbill, texte avec positions, IA et ses sources, auteur et date
  d'une modification).

## Décision

1. Route `POST /documents/{id}/provenance-report` (authentifiée, filtrée par auteur, F-25) ;
   PDF distinct produit par `export_provenance`, pied de page « not part of the clinical document ».
2. Contenu : bloc commun (origine Superbill, noms des champs), puis une ligne par section :
   statut, origine (AI ou Clinician), sources lisibles (extrait du texte avec positions des
   caractères, extrait Superbill, ou « Clinician edit by <nom> on <date> »).
3. Version courante du document ; aucune table dédiée : l'audit `provenance_report_generated`
   (acteur, document, version, date) est la trace.

## Conséquences

Le PDF clinique et le rapport sont produits par deux modèles distincts ; un test vérifie que le
texte du PDF clinique ne contient ni « provenance », ni sources, ni mention de l'IA.
