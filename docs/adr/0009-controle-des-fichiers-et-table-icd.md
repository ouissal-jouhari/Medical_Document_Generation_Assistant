# ADR 0009 – Contrôle des fichiers déposés et table ICD-10-CM

- **Statut :** accepté (F-03, N-06, P9)
- **Contrôle du fichier (dans l'API, avant toute création) :**
  - taille ≤ 50 Mo (50 × 1024 × 1024 octets), lue par blocs limités (au plus limite + 1 octet) ; Caddy plafonne aussi la requête (51 Mo, marge pour l'enveloppe multipart) ;
  - **type réel** par les premiers octets (`%PDF-`, signature PNG, signature JPEG), jamais l'extension seule ; l'extension doit en plus correspondre au type réel (un fichier renommé est refusé) ;
  - PDF : 3 pages au maximum, PDF chiffré refusé (même avec mot de passe vide), structure illisible refusée ; image : une par fichier, 25 millions de pixels au maximum (protection contre les images piégées, vérifiée avant décodage complet).
  Codes d'erreur stables : `unsupported_format`, `file_too_large`, `too_many_pages`, `encrypted_pdf`, `corrupt_file`, `image_too_large`.
- **Table ICD-10-CM :** liste des codes de l'exercice FY2026 du CDC/NCHS (domaine public), sans les descriptions, dans `backend/app/data/icd10cm_fy2026_codes.txt` (74 719 codes). Un code absent donne un avertissement non bloquant. CPT : format seulement (descriptions sous licence).
- **Mise à jour :** remplacer le fichier chaque année (nouvel exercice) et ajuster le nom ; le format de la ligne d'en-tête documente la source.
