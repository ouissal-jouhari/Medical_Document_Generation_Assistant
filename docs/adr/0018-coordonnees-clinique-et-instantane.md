# ADR 0018 – Coordonnées de la clinique en configuration, instantané à l'approbation

## Contexte

- H-01 : les informations de la clinique sont constantes ; aucune interface ne les modifie.
- H-02, F-24 : un document approuvé garde les valeurs de son approbation.
- P11 (tranché) : ClinicProfile en configuration avec instantané à l'approbation.

## Décision

1. `ClinicProfile` (domaine, valeur immuable) lu des variables `CLINIC_NAME`, `CLINIC_ADDRESS`,
   `CLINIC_CITY`, `CLINIC_POSTAL_CODE`, `CLINIC_PHONE`, `CLINIC_EMAIL`, `CLINIC_WEBSITE`
   (valeurs fictives par défaut, `.env.example`, `docker-compose.yml`). Aucune route ne les lit ni
   ne les modifie (test `test_H01_*`).
2. À l'approbation, `document.clinic_snapshot` reçoit une copie de ces valeurs et
   `document.approver_name` le nom d'affichage de l'approbateur ; ces champs ne sont plus jamais écrits
   (le domaine refuse toute action sur un document approuvé).
3. L'export (jalon 6) lit l'instantané sans recalculer.

## Conséquences

Changer la configuration n'affecte que les approbations futures (test `test_H02_*`).
