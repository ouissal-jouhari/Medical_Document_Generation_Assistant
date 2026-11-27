# ADR 0021 – Conservation : purge planifiée, repère et acteur système

## Contexte

- N-10 : consultation et données 90 jours après la dernière approbation ; audit sans donnée patient
  1 an ; logs techniques 30 jours. P16 : consultation jamais approuvée = dernière activité.
- F-22 : suppression complète, y compris fichiers temporaires et caches ; trace minimale.
- ADR 0006 : seul le rôle `xeleron_purge` peut supprimer l'audit.

## Décision

1. `erase_consultation` (partagé par la suppression manuelle et la purge) efface fichier déposé,
   texte, données, corrections, documents, versions, marques et exports. Aucun fichier temporaire
   ni cache n'est persisté (extraction en mémoire, PDF rendus en mémoire), il n'y a donc rien
   d'autre à effacer.
2. Repère : date maximale d'approbation des documents de la consultation ; à défaut, dernière
   activité (consultation, texte, documents, versions, marques). Lecture stricte du SRS : une
   activité postérieure à une approbation ne prolonge pas la conservation.
3. `RetentionService` (horloge injectable) ; ordonnanceur dans le cycle de vie de l'application
   (`RETENTION_ENABLED`, une passe au démarrage puis toutes les 24 h). Consultations effacées avec
   le rôle applicatif ; audit de plus d'un an supprimé via `PURGE_DATABASE_URL` (rôle de purge).
4. Acteur des purges : identifiant nul réservé (`00000000-0000-0000-0000-000000000000`), action
   `consultation_purged`, sans identifiant de consultation ni donnée patient.
5. Logs : rotation quotidienne existante, 30 fichiers conservés (`LOG_RETENTION_DAYS`).
6. Durées en configuration (`RETENTION_CONSULTATION_DAYS`, `RETENTION_AUDIT_DAYS`) : valeurs du MVP
   remplacées au déploiement (L-02).

## Conséquences

Avec plusieurs instances, chaque instance purgerait : sans effet nuisible (opérations idempotentes),
le MVP n'en déploie qu'une.
