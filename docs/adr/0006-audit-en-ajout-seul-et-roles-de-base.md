# ADR 0006 – Audit en ajout seul garanti par la base, rôles de base distincts

- **Statut :** accepté (F-20, F-21, N-10, F-25, L-04)
- **Décision :**
  - Trois rôles PostgreSQL : le **propriétaire** (migrations seulement), `xeleron_app` (application : `SELECT`/`INSERT` sur `audit_event`, aucun `UPDATE`, `DELETE` ni `TRUNCATE`) et `xeleron_purge` (purge à 1 an : `SELECT` et `DELETE` seulement, sans `UPDATE`). La migration 0002 crée les rôles et les droits ; les mots de passe viennent de l'environnement.
  - L'événement d'audit est ajouté dans **la session de l'action** (même transaction) : action et trace réussissent ou échouent ensemble.
  - `audit_event` n'a **aucune clé étrangère** (ni vers un document, ni vers un utilisateur) : l'audit survit à la suppression d'un document (F-22) et ne contient aucune donnée patient.
  - Aucune route ne lit, modifie ou supprime l'audit (testé).
  - Accès aux données : `AuthorScopedRepository` exige toujours `author_id`. Une ressource inexistante et une ressource d'un autre auteur renvoient la même réponse `404 not_found` (F-25).
  - Au démarrage, le conteneur exécute les migrations avec le propriétaire, puis retire ses identifiants de l'environnement avant de lancer le serveur.
- **Écart connu (L-04) :** la consultation d'un document n'est pas tracée au MVP. La procédure d'accès d'urgence reste à documenter.
- **Conséquence :** le service applicatif ne peut pas modifier le schéma ni réécrire l'historique, même s'il est compromis.
