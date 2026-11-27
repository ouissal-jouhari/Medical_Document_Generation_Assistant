# ADR 0019 – Export PDF : Jinja2 autoéchappé, WeasyPrint sans accès externe

## Contexte

- F-18 : export après approbation seulement, PDF conforme au modèle, sans mention de l'IA, des
  sources ni de brouillon ; chaque export est tracé. F-24 : clinique en en-tête et pied de page.
- P15 : le PDF peut dépasser une page ; en-tête, pied de page et pagination « x / y » sur chaque page.
- N-06 : le contenu (saisi ou généré) ne doit ni injecter de HTML ni déclencher de requête.
- Stack figée : Jinja2 + WeasyPrint, derrière le port `DocumentExporter`.

## Décision

1. Port `DocumentExporter` : `export(ExportableDocument)` et `export_provenance(ProvenanceReport)`.
   `ExportableDocument` ne contient que le contenu clinique (bloc commun, sections, approbateur,
   date, instantané de la clinique) : origines, sources et marques sont exclues dès le domaine
   (`app/domain/export.py`).
2. Adaptateur `WeasyPrintExporter` : environnement Jinja2 avec autoéchappement forcé ; WeasyPrint
   reçoit un `URLFetcher` qui refuse toute URL (fichier, réseau, données) ; journaux WeasyPrint
   coupés (une URL peut venir du contenu, N-08).
3. En-tête et pied de page = éléments courants CSS (`position: running()`) répétés sur chaque page,
   avec toutes les coordonnées de la clinique ; pagination par `counter(page) / counter(pages)`.
4. Rendu en mémoire ; le fichier est téléchargé (`Content-Disposition: attachment`,
   `Cache-Control: no-store`) et jamais stocké. Entité `Export` (migration 0007, ajout seul,
   DELETE pour F-22/N-10) et événement d'audit `exported` dans la même transaction.
5. Échec de rendu : `ExportFailed` (500, code `export_failed`), rien n'est tracé, le document reste
   Approved inchangé (N-11).
6. Modèles de l'Annexe A (.docx) non joints au dépôt : la mise en page reprend leur structure
   (clinique, titre, bloc patient et codes, sections, ligne « Approved by »).
7. Pango n'est pas installable sur le poste de développement (réseau limité) : WeasyPrint est
   importé au premier rendu ; les tests de rendu réel sont obligatoires en CI (`require_weasyprint`).

## Conséquences

Image backend et job CI installent `libpango` et une police (DejaVu). Un export FHIR futur
implémentera le même port sans toucher au domaine (P2).
