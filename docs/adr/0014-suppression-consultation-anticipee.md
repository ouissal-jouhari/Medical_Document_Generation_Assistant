# ADR 0014 – Suppression d'une consultation (F-22) livrée avant le jalon 6

## Contexte
Le bouton « Supprimer » de l'écran E-02 était inactif (prévu au jalon 6). Le clinicien en a besoin pour retirer ses données de test et ses consultations.

## Décision
- `DELETE /consultations/{id}` (clinicien authentifié, filtre par auteur, 404 identique si absente ou étrangère) supprime le fichier, le texte, les documents, leurs versions et les corrections de champs.
- Une seule trace d'audit reste : acteur, action `consultation_deleted`, date. Aucun identifiant de consultation, de document ni donnée patient.
- Migration 0005 : le rôle applicatif reçoit DELETE sur `consultation`, `consultation_correction` et `document`. Les corrections restent sans UPDATE ; l'audit reste en ajout seul (aucun DELETE pour le rôle applicatif).
- L'écran demande une confirmation avant la suppression.

## Conséquences
Les tests PostgreSQL qui interdisaient la suppression avant le jalon 6 sont remplacés par un test qui vérifie le droit de suppression et l'interdiction de supprimer l'audit.
