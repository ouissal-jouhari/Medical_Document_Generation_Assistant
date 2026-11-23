# ADR 0003 – Chiffrement au repos par volume hôte (N-05, P13)

- **Statut :** accepté
- **Décision :** le chiffrement au repos est assuré par le chiffrement de volume côté hôte (LUKS/BitLocker/chiffrement du disque du fournisseur). Il couvre PostgreSQL (`pgdata`), les Superbills déposées (`storage`) et les logs. La clé est gérée par l'hôte, hors du code et hors du dépôt.
- **Transit :** TLS terminé par Caddy (certificat automatique ; certificat interne en `localhost`).
- **Preuve :** procédure de vérification dans le README (section « Chiffrement au repos ») ; l'application ne contient aucune clé.
- **Conséquence :** la machine d'hébergement (P13, au moins 8 Go de RAM et 4 vCPU) doit fournir un disque chiffré avant le déploiement DEV.
