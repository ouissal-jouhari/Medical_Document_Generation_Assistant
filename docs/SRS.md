# XeleronIA – SRS du MVP et choix techniques

- **Partie A** : SRS XeleronIA – Spécification des exigences du MVP (Version 1.0)
- **Partie B** : XeleronIA – Proposition de choix techniques (Version 1.1, auteur : Ouissal Jouhari)

---

# Partie A – SRS XeleronIA : Spécification des exigences du MVP

**Version 1.0**

**Conventions.** Priorités : **M** = indispensable au MVP · **S** = souhaitable · **C** = si le temps le permet. Les exigences sont identifiées par F (fonctionnelle), N (non fonctionnelle), S (sécurité médicale), C (contrainte), I (interface), E (écran), R (risque).

## 1. Introduction

### 1.1 Objet

Ce document définit les exigences du MVP de XeleronIA, un assistant qui génère des brouillons de documents médicaux à partir d'une Superbill et d'un texte de consultation complémentaire. Il sert de base à la phase d'architecture et n'impose aucune technologie.

### 1.2 Raison d'être

Gagner du temps pour le clinicien et participer à la digitalisation des hôpitaux. Ce sont des objectifs, pas des cibles mesurables.

### 1.3 Périmètre

**Dans le MVP :** authentification, dépôt et extraction (OCR et parsing) de la Superbill, saisie optionnelle du texte de consultation, génération selon le template choisi, revue et édition, versions et rollback, approbation, export PDF (et FHIR si faisable), audit.

**Hors MVP :** AI Scribe, rôles autres que « Clinician », microservices et infrastructure avancée. Une frontière d'entrée est prévue pour l'AI Scribe, sans le développer.

### 1.4 Définitions

| Terme | Définition |
|---|---|
| Superbill | Document de facturation médicale (invoice) : identités, dates, codes ICD-10 et CPT, facturation. Entrée : PDF ou image scannée. |
| Texte de consultation | Récit clinique brut de la consultation, optionnel et complémentaire, 5 000 caractères au maximum. |
| Consultation | Ensemble Superbill + texte, qui peut produire plusieurs documents. |
| Template | Structure d'un type de document (sections, statuts). |
| Brouillon | Toute sortie produite par l'IA, jamais une vérité médicale validée. |
| Provenance | Origine d'une information : Superbill, texte, IA ou clinicien. |
| Version | État conservé d'un document : IA générée, éditée, approuvée ou rejetée. |
| Approuvé | Version validée par le clinicien, figée, prête à être exportée. |

### 1.5 Références

Cahier des charges initial du stage · C-CDA on FHIR (HL7) · panels LOINC 81218-0, 81219-8 et 81223-0 · standards PRSB (eDischarge, lettre de consultation externe) · HIPAA Security Rule · RGPD. Les standards ont été lus en extraits : aucune conformité n'est revendiquée.

## 2. Description générale

### 2.1 Perspective produit

Application autonome et simple au MVP. Elle est le composant aval d'un futur écosystème : un AI Scribe (voix vers texte) enverra plus tard le texte de consultation par API ; d'autres systèmes de l'hôpital pourront s'intégrer par l'API et, si faisable, par FHIR. Aucune de ces intégrations n'est développée au MVP.

### 2.2 Acteur et accès

Un seul rôle : **Clinician**. Un document n'est visible que par son auteur. Le modèle d'autorisation doit pouvoir accueillir d'autres rôles plus tard, sans être sur-construit.

### 2.3 Contraintes

- **C-01** Un développeur, environ 8 semaines.
- **C-02** Environ 10 utilisateurs simultanés.
- **C-03** Données synthétiques uniquement.
- **C-04** Interface, texte de consultation et documents générés en anglais ; d'autres langues plus tard.
- **C-05** Cloud-first, compatible on-premise.
- **C-06** Conçu pour respecter les exigences techniques de HIPAA et du RGPD, sans déclaration de conformité.
- **C-07** Aucune contrainte matérielle définie au MVP.

### 2.4 Hypothèses

- **H-01** Les informations de la clinique sont constantes ; aucune interface ne permet de les modifier.
- **H-02** Un document approuvé garde les coordonnées de la clinique telles qu'elles étaient à l'approbation.
- **H-03** Le clinicien qui crée la consultation est l'auteur de tous ses documents et le seul à pouvoir les approuver.

### 2.5 Dépendances externes

Un service d'OCR, un service LLM, un fournisseur d'identité OIDC avec MFA. Les produits sont choisis à l'architecture (section 13).

## 3. Workflow et états

**Niveau 1 – la consultation :** Uploaded → Parsed → Validated. Le texte de consultation est saisi à tout moment avant la génération, ou jamais.

**Niveau 2 – chaque document :** version IA générée → Under Review → Approved.

| État ou objet | Action | Résultat | Condition |
|---|---|---|---|
| Consultation | Dépôt de la Superbill | Uploaded | Fichier conforme aux limites |
| Uploaded | Extraction réussie | Parsed | Sortie conforme au schéma |
| Parsed | Vérification et validation par le clinicien | Validated | Le clinicien peut corriger les champs |
| Validated | Génération d'un type de document | Document en Under Review (version IA) | Plusieurs documents possibles par consultation |
| Under Review | Édition | Nouvelle version « éditée » | État inchangé |
| Under Review | Rejet | Version marquée « rejetée » | Régénération possible |
| Under Review | Rollback | Nouvelle version copiée d'une ancienne | Avant approbation seulement |
| Under Review | Marquer comme relu | Événement « relu » sur la version courante | Préalable à l'approbation |
| Under Review | Approbation | Approved (figé) | Version relue ; sections obligatoires remplies |
| Approved | Export | Événement d'audit | Répétable, état inchangé |
| Approved | Correction nécessaire | Nouveau document du même type | L'ancien reste intact |

« Edited » est un type de version, pas un état. « Exported » est un événement, pas un état (journal, section 12).

## 4. Exigences fonctionnelles

Chaque exigence a un critère d'acceptation vérifiable.

### 4.1 Authentification et accès

| ID | Exigence | Critère d'acceptation | P |
|---|---|---|---|
| F-01 | Le clinicien s'authentifie avec MFA. | Sans MFA validé, l'accès est refusé ; une requête sans session est redirigée vers la connexion. | M |
| F-02 | Rôle unique « Clinician », autorisation extensible. | Chaque route vérifie le rôle ; ajouter un rôle ne demande pas de modifier les routes existantes (revue de conception). | M |
| F-25 | Un document n'est visible que par son auteur. | Un autre clinicien ne peut ni lister, ni lire, ni exporter ce document ; la réponse ne révèle pas son existence. | M |

### 4.2 Consultation et Superbill

| ID | Exigence | Critère d'acceptation | P |
|---|---|---|---|
| F-03 | Le clinicien crée une consultation en déposant la Superbill (PDF, png, jpg, jpeg). | PDF de 3 pages au maximum ; une image par fichier ; 50 Mo au maximum ; autre format ou fichier hors limites refusé avec un message clair, sans créer de consultation. Scan de 200 à 300 dpi recommandé. | M |
| F-04 | Le système extrait une Superbill normalisée. | Sur la Superbill synthétique de test, les champs obligatoires du schéma (section 9.2) sont extraits et le résultat respecte le schéma. | M |
| F-05 | Le clinicien vérifie et corrige les données extraites. | Chaque champ est modifiable ; chaque modification conserve auteur et date ; la consultation passe à Validated seulement après une validation explicite. | M |
| F-06 | Un échec d'extraction est géré. | Message clair ; la consultation reste Uploaded ; un nouveau dépôt est possible ; l'échec est compté. | M |

### 4.3 Texte de consultation

| ID | Exigence | Critère d'acceptation | P |
|---|---|---|---|
| F-07 | Texte optionnel et complémentaire, 5 000 caractères au maximum. | 5 001 caractères sont refusés côté serveur ; l'absence de texte est acceptée. Sans texte, l'interface (écrans E-05 et E-06) affiche : « Superbill data alone is not sufficient to generate complete clinical documents. Adding the consultation text is recommended. » Cette remarque n'apparaît jamais dans le document exporté. | M |
| F-08 | Frontière d'entrée pour l'AI Scribe. | L'enregistrement du texte d'une consultation est exposé par l'API indépendamment de l'écran (revue de conception) ; aucun développement de l'AI Scribe. | S |

### 4.4 Génération

| ID | Exigence | Critère d'acceptation | P |
|---|---|---|---|
| F-09 | Le clinicien choisit le type de document (Clinical Note, Referral Letter, Discharge Summary) et peut en créer plusieurs par consultation. | Génération impossible si la consultation n'est pas Validated ; plusieurs documents peuvent coexister pour une consultation. | M |
| F-10 | Génération structurée selon le template, à partir de la Superbill et, si présent, du texte. | Sortie conforme au schéma du template ; chaque section enregistre ses sources ; sans texte, la règle S-03 s'applique. | M |
| F-11 | Information absente = « Not provided ». | Sur un jeu de test où une information manque, la section contient « Not provided » et aucune valeur inventée. | M |
| F-12 | La sortie est contrôlée avant affichage. | Une sortie malformée ou incomplète n'est jamais affichée comme brouillon ; message clair ; nouvelle tentative possible. | M |

### 4.5 Revue et approbation

| ID | Exigence | Critère d'acceptation | P |
|---|---|---|---|
| F-13 | Écran de revue. | Bandeau « AI-generated draft » visible tant que le document n'est pas approuvé ; 4 origines distinguables (Superbill, texte, IA, clinicien) ; statut de chaque section ; liste « Missing information ». | M |
| F-14 | Édition en ligne. | Toute édition crée une version « éditée » avec auteur et date ; la version précédente reste intacte. | M |
| F-15 | Rejeter puis régénérer. | La version rejetée est conservée et marquée ; la régénération crée une nouvelle version IA. | M |
| F-16 | Rollback. | Le contenu d'une ancienne version est restauré dans une nouvelle version ; l'historique reste intact ; impossible sur un document approuvé. | M |
| F-26 | Marquer comme relu. | Un clic « Mark as reviewed » enregistre auteur, version et date ; l'approbation exige que la version courante ait été marquée relue. | M |
| F-17 | Approbation. | Impossible si une section obligatoire est « Not provided » ; après approbation, aucune modification n'est possible ; auteur et date enregistrés. | M |
| F-19 | Correction après approbation. | L'action « Create new document » depuis un document approuvé produit un document du même type ; l'ancien reste inchangé. | M |

### 4.6 Export

| ID | Exigence | Critère d'acceptation | P |
|---|---|---|---|
| F-18 | Export PDF obligatoire, téléchargé sur l'appareil local. | Possible après approbation seulement ; PDF lisible conforme au template ; aucune mention de l'IA, des sources ni de brouillon ; chaque export est tracé. | M |
| F-27 | Export FHIR Composition si faisable. | L'échec de la validation FHIR n'empêche pas l'export PDF ; aucune conformité FHIR n'est affirmée sans validation par un outil officiel. | S |
| F-23 | Rapport de provenance séparé, imprimable et exportable. | Généré à la demande, avant et après approbation ; hors du document clinique ; chaque génération est tracée. | S |

### 4.7 Audit et données

| ID | Exigence | Critère d'acceptation | P |
|---|---|---|---|
| F-20 | Audit simple. | Sont tracés avec acteur, action, date, document et version : généré, relu, approuvé, rejeté, rollback, exporté, rapport de provenance généré. | M |
| F-21 | L'audit n'est pas modifiable. | Aucune route ni aucun écran ne modifie ou ne supprime un événement d'audit. | M |
| F-22 | Suppression manuelle d'une consultation. | Fichiers, texte, documents et versions sont supprimés ; une trace minimale sans donnée patient est conservée dans l'audit. | S |
| F-24 | Informations de la clinique constantes. | Nom, adresse, ville, code postal, téléphone, e-mail et site s'affichent dans l'en-tête et le pied de page des documents exportés ; un document approuvé garde les valeurs de son approbation ; aucune interface ne les modifie. | M |

## 5. Templates

Alignés sur C-CDA on FHIR (États-Unis) et PRSB/NHS (Royaume-Uni), lus en extraits. La mention « (non confirmé) » signale un statut qui n'a pas pu être confirmé dans les extraits lus.

### 5.1 Règles communes

**Bloc commun obligatoire**, issu de la Superbill : patient, date de naissance, identifiant patient, médecin, date de service, diagnostics codés (ICD-10-CM), procédures codées (CPT).

**Statuts de section :**

- **Obligatoire** : bloque l'approbation si « Not provided ».
- **Champ de sécurité** : médicaments, allergies ; jamais déduits, bien visibles s'ils manquent, ne bloquent pas ; « Not provided » ne signifie pas « aucune allergie connue ».
- **Standard** : affiché, « Not provided » si rien ne le soutient, ne bloque pas.

**Document exporté :** une page, en anglais, sans mention de l'IA, des sources ni de brouillon.

- En-tête : nom, adresse, ville, code postal, téléphone, e-mail et site de la clinique.
- Pied de page : nom, téléphone et ville de la clinique, identifiant du document, version, mention de confidentialité, pagination.
- Ligne d'approbation : « Approved by [name] on [date] – version [n] ».

### 5.2 Clinical Note (SOAP)

| Section | Statut | Source | Alignement US / UK |
|---|---|---|---|
| Subjective | Standard | Texte | US : histoire de la maladie (Consultation Note) · UK : History |
| Objective | Standard | Texte | US : examen, résultats (non confirmé) · UK : Investigation results |
| Assessment | Standard | Texte, diagnostics codés | US : Assessment (non confirmé pour la Progress Note) · UK : Diagnoses |
| Plan | Standard | Texte | US : Plan of treatment · UK : Plan and requested actions, Information and advice given |
| Medications | Sécurité | Texte | UK : Medications and medical devices |
| Allergies and adverse reactions | Sécurité | Texte | UK : Allergies and adverse reactions |

Aucune section obligatoire en plus du bloc commun.

### 5.3 Referral Letter

| Section | Statut | Source | Alignement US / UK |
|---|---|---|---|
| Recipient | Standard | Texte | UK : liste de distribution (non confirmé pour une lettre d'orientation) |
| Reason for referral | Obligatoire | Texte | US : guide FHIR 1.2.0 (ballot) 1..1, panel LOINC optionnel |
| Urgency | Standard | Texte | Cahier des charges initial |
| History and clinical summary | Standard | Texte | US : histoire de la maladie, optionnel · UK : History |
| Clinical findings and investigation results | Standard | Texte | US : physical findings, optionnel · UK : Investigation results |
| Assessment | Obligatoire | Texte | US : requis (panel LOINC) |
| Current treatment and medications | Sécurité | Texte | US : optionnel · UK : Medications and medical devices |
| Allergies and adverse reactions | Sécurité | Texte | US : optionnel (panel), requis (FHIR 1.1) · UK : Allergies and adverse reactions |
| Plan and requested actions | Obligatoire | Texte | US : Plan of care, requis · UK : Plan and requested actions |

Le panel LOINC et le guide FHIR divergent sur certaines sections : la lecture la plus stricte est retenue pour le motif. Aucun standard britannique spécifique aux lettres d'orientation n'a été trouvé.

### 5.4 Discharge Summary

| Section | Statut | Source | Alignement US / UK |
|---|---|---|---|
| Admission details | Standard | Texte | US : admission diagnosis, optionnel · UK : requis |
| Discharge details (date, destination, état) | Standard | Texte | UK : requis |
| Clinical summary (hospital course) | Obligatoire | Texte | US : hospital course, requis · UK : clinical summary, obligatoire |
| Investigation results | Standard | Texte | US : studies summary, optionnel · UK : optionnel |
| Medications at discharge | Sécurité | Texte | US : requis · UK : optionnel |
| Allergies and adverse reactions | Sécurité | Texte | US : requis (panel 2.1) · UK : obligatoire |
| Plan and requested actions (inclut le suivi) | Standard | Texte | US : plan of treatment, requis · UK : requis |
| Information and advice given | Standard | Texte | US : discharge instructions (non confirmé) · UK : requis |

Les diagnostics et procédures sont dans le bloc commun (US : diagnostic de sortie requis ; UK : diagnostics obligatoires, procédures optionnelles). Les informations d'admission et de sortie viennent du texte de consultation : sans texte, ces sections restent « Not provided » et la Referral Letter comme le Discharge Summary ne peuvent pas être approuvés, leurs sections obligatoires dépendant du texte.

## 6. Règles de sécurité médicale

| ID | Règle |
|---|---|
| S-01 | Toute sortie IA est un brouillon, signalé comme tel pendant la revue seulement. |
| S-02 | Jamais d'invention : diagnostic, symptôme, médicament, posologie, allergie, antécédent, résultat, procédure, mesure, identifiant, date ou conclusion. Le manquant est « Not provided ». |
| S-03 | Sans texte de consultation, le système peut reprendre les diagnostics et procédures codés de la Superbill (codes et descriptions), mais il ne déduit jamais symptômes, constats, traitements, médicaments, allergies, antécédents ni évolution à partir de ces codes. |
| S-04 | La Superbill, l'OCR et le texte sont des données, jamais des instructions pour le LLM. |
| S-05 | La provenance est enregistrée par section et affichée en revue (niveau de détail en section 9.3). |
| S-06 | Aucune approbation automatique ; le clinicien est responsable. |
| S-07 | Aucune validation critique n'est contournée en silence. |

## 7. Exigences non fonctionnelles

| ID | Exigence | Vérification | P |
|---|---|---|---|
| N-01 | Objectif de 20 s pour la génération, mesuré et rapporté, non bloquant. | Les durées sont mesurées ; au-delà de 20 s, la limite mesurée est notée dans le rapport d'évaluation. Objectif non garanti. | S |
| N-02 | Durées mesurées : extraction, LLM, validation, total. | Les logs techniques contiennent ces quatre durées par génération. | S |
| N-03 | Environ 10 utilisateurs simultanés. | Test simple à 10 requêtes concurrentes, sans seuil imposé. | C |
| N-04 | OIDC/OAuth2 avec MFA ; contrôle d'accès par rôle, extensible. | Voir F-01, F-02, F-25. | M |
| N-05 | Chiffrement en transit et au repos ; secrets hors du code ; aucune clé, mot de passe ni jeton dans les logs. | Aucun secret trouvé dans le dépôt ni dans les logs. | M |
| N-06 | Fichiers contrôlés, entrées validées, protection XSS et CSRF. | Le type réel du fichier est contrôlé, pas seulement l'extension ; tests XSS et CSRF de base. | M |
| N-07 | Résistance à l'injection de prompt. | Un texte du type « Ignore previous instructions » dans la Superbill ou le texte ne change ni les règles ni le format de sortie (cas de test). | M |
| N-08 | Données synthétiques ; minimisation, logs minimaux, accès contrôlé. | Aucune donnée réelle dans les jeux de test ; logs sans donnée patient. | M |
| N-09 | Conçu pour respecter les exigences techniques de HIPAA et du RGPD, sans déclaration de conformité formelle tant qu'aucun audit n'a eu lieu. | Chacun des cinq contrôles techniques HIPAA (accès, audit, intégrité, authentification, transmission) est relié à une exigence ; aucune mention « conforme » dans le produit ni dans la documentation. | M |
| N-10 | Conservation : consultation et ses données 90 jours après la dernière approbation ; audit (sans donnée patient) 1 an ; logs techniques 30 jours. Valeurs du MVP, remplacées au déploiement par celles de l'hôpital et d'un juriste ou DPO. | Test avec dates simulées. | S |
| N-11 | Chaque défaillance a un chemin contrôlé avec un message sûr : fichier invalide, extraction ratée, LLM indisponible ou trop lent, sortie malformée, FHIR ou PDF en échec, accès refusé. | Un test par cas vérifie le message et l'absence de trace technique. | M |
| N-12 | Suivi des durées, des échecs par étape et des changements d'état ; pas de document complet dans les logs. | Les métriques existent ; aucun document complet dans les logs. | S |
| N-13 | OCR, LLM et entrée du texte remplaçables sans toucher au domaine. | Chacun est derrière une interface ; remplacer un fournisseur ne modifie pas le domaine (revue de conception). | M |
| N-14 | Nouveau type de document ou nouvelle langue ajoutable par configuration. | Ajouter un template ou une langue ne modifie pas le moteur de génération. | S |
| N-15 | Compatible cloud et on-premise ; monolithe modulaire (décision D-07). | Démarrage reproductible par conteneur. | S |
| N-16 | Tests unitaires, API et bout en bout ; évaluation IA sur jeu contrôlé : ancrage, hallucination, cohérence, complétude, respect du template, charge de correction. | Les trois niveaux de tests existent ; le jeu d'évaluation est rejouable après chaque changement de modèle. | M |
| N-17 | Seuil fixé : zéro allergie ou médicament inventé. Aucun autre seuil avant la première évaluation. | Zéro sur le jeu d'évaluation. | M |
| N-18 | Intégration future : autonome au MVP, intégrable plus tard à d'autres systèmes de l'hôpital par l'API et FHIR si faisable. | Les fonctions du MVP sont accessibles par l'API sans dépendre d'un écran. | S |
| N-19 | Minimisation vers le LLM : nom, date de naissance et identifiant du patient ne sont pas envoyés au LLM ; ils sont réinjectés après la génération. | Test automatique sur les prompts envoyés. | M |

## 8. Interfaces externes

Les produits ne sont pas choisis ici : ils le sont à l'architecture (section 13).

| ID | Interface | Entrée | Sortie | Statut |
|---|---|---|---|---|
| I-01 | Service d'extraction (OCR) | PDF ou image | Texte structuré | MVP |
| I-02 | Service LLM | Instructions de confiance et données non fiables, sans identifiants directs du patient | Sortie structurée conforme au template | MVP |
| I-03 | Fournisseur d'identité | Connexion OIDC avec MFA | Identité du clinicien | MVP |
| I-04 | AI Scribe | Texte de consultation envoyé par API | Texte enregistré dans la consultation | Futur |
| I-05 | Systèmes de l'hôpital | Appels API, FHIR si faisable | Documents exportés | Futur |
| I-06 | Export local | Document approuvé | PDF, puis FHIR si faisable | MVP |

## 9. Données

### 9.1 Entités conceptuelles

| Entité | Rôle | Relations |
|---|---|---|
| User | Identité du clinicien, issue de l'OIDC | Possède des consultations |
| ClinicProfile | Coordonnées de la clinique, constantes (configuration) | Utilisé par les exports |
| Consultation | Fichier Superbill, données extraites et corrigées, texte optionnel, état (Uploaded, Parsed, Validated) | 1 vers n Document |
| Document | Type, état (Under Review, Approved), auteur | 1 vers n Version, 1 vers n Export |
| DocumentVersion | Contenu par section, type (IA générée, éditée, rejetée, approuvée), auteur, date, sources | Appartient à un Document |
| Export | Format (PDF, FHIR), date, acteur | Appartient à un Document |
| AuditEvent | Acteur, action, date, document, version ; non modifiable | Référence un Document |

### 9.2 Schéma de la Superbill normalisée

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| patient.fullName | texte | Oui | |
| patient.dateOfBirth | date | Oui | |
| patient.patientId | texte | Oui | |
| physician.name | texte | Oui | |
| encounter.dateOfService | date | Oui | |
| encounter.placeOfService | texte | Non | |
| diagnoses[] : code, description | texte | Oui, au moins un | Code ICD-10-CM |
| procedures[] : code, description, unités | texte, nombre | Oui, au moins un | Code CPT |
| billing.totalCharges | nombre | Non | Extrait, non utilisé dans les documents cliniques |
| insurance, coordonnées de la clinique | texte | Non | Non utilisés : la clinique vient de la configuration |
| extraction.pageCount | nombre | Oui | Métadonnée technique |

Validation déterministe : format de date ISO ; format des codes ICD-10-CM et CPT. C'est un contrôle de format, pas une validation clinique : il repère une erreur d'OCR, mais ne prouve pas qu'un code est le bon.

### 9.3 Provenance

Enregistrée par section : liste des sources, avec leur type (Superbill, texte, IA, clinicien).

- Pour la Superbill : le nom du champ, et la page seulement si l'extraction la fournit de façon fiable.
- Pour le texte : l'extrait (positions des caractères).
- Pour une affirmation de l'IA : les sources qui la soutiennent.
- Pour une modification : l'auteur et la date.
- Sans texte, les sources sont uniquement la Superbill.

## 10. Écrans

| ID | Écran | Contenu et actions | Exigences |
|---|---|---|---|
| E-01 | Connexion | Authentification avec MFA | F-01 |
| E-02 | Mes consultations | Liste des consultations de l'auteur ; créer ; supprimer | F-25, F-22 |
| E-03 | Nouvelle consultation | Dépôt de la Superbill ; messages d'erreur | F-03, F-06 |
| E-04 | Vérification des données | Afficher et corriger les champs extraits ; valider | F-04, F-05 |
| E-05 | Texte et type de document | Saisie optionnelle avec compteur et remarque d'avertissement ; choix du type ; générer | F-07, F-09, F-10 |
| E-06 | Revue du document | Bandeau brouillon ; 4 origines ; sections modifiables ; versions et rollback ; rejeter et régénérer ; marquer relu ; approuver ; remarque d'avertissement si pas de texte | F-07, F-11 à F-17, F-26 |
| E-07 | Document approuvé | Export PDF et FHIR ; rapport de provenance ; créer un nouveau document | F-18, F-19, F-23, F-27 |

## 11. Risques

| ID | Risque | Réponse prévue |
|---|---|---|
| R-01 | Information médicale inventée par l'IA | S-02, S-03, contrôle de sortie, évaluation (N-16, N-17) |
| R-02 | Erreur d'OCR sur un code | Vérification par le clinicien (F-05), contrôle de format |
| R-03 | Génération plus lente que 20 s | Mesure (N-02), modèle plus léger, réduction de la résolution des images (décision d'architecture) |
| R-04 | Données patient envoyées à un LLM externe | N-19, données synthétiques, choix du LLM à l'architecture |
| R-05 | Export FHIR non valide | FHIR « si faisable », validation par un outil officiel |
| R-06 | Un seul développeur en environ 8 semaines | Priorités M, S, C ; périmètre minimal |
| R-07 | Schéma de Superbill validé sur un exemple synthétique | Revalidation sur une Superbill réelle avant tout déploiement (section 14) |

## 12. Journal des décisions

| Réf. | Décision | Raison |
|---|---|---|
| D3-1 | Rejet : version marquée « rejetée », puis régénération | Choix du clinicien ; historique conservé |
| D3-2 | Document approuvé figé ; export répétable et tracé | Un document final ne doit plus bouger |
| D3-3 | Correction après approbation : nouveau document | Sinon le clinicien est bloqué |
| D3-4 | Le clinicien corrige les données extraites ; corrections tracées | L'OCR peut se tromper sur des codes |
| É-1 | « Edited » devient un type de version, pas un état | Évite de dupliquer le versioning |
| É-2 | « Exported » devient un événement d'audit | Plusieurs exports possibles, formats multiples |
| D4-1 | Texte de consultation optionnel et complémentaire, avec une remarque d'avertissement dans l'interface (écart avec le cahier des charges initial) | La Superbill seule est une entrée valide, mais ses données ne suffisent pas pour des documents cliniques complets |
| D4-2 | Templates alignés US/UK, sections obligatoires définies | Alignement C-CDA on FHIR et PRSB |
| D4-3 | Document exporté propre | L'export n'a lieu qu'après approbation |
| D4-4 | Provenance stockée, affichée en revue, rapport séparé après approbation | Traçabilité sans polluer le document final |
| D6-1 | Objectif de 20 s non bloquant | MVP, optimisation au mieux |
| D6-2 | Ce SRS prime sur le cahier des charges initial | Le cahier des charges initial n'était pas stable |
| D6-3 | Respect de HIPAA et du RGPD dès le MVP, sans déclaration de conformité | Éviter une promesse juridique non établie |
| D6-4 | Accès limité à l'auteur | Minimum nécessaire ; protéger les données patient |
| D6-5 | Suppression manuelle ajoutée | RGPD : limitation de la conservation et effacement |
| D6-6 | PDF obligatoire, FHIR « si faisable » | Contrainte du stage |
| D6-7 | Minimisation vers le LLM (N-19) | Protection des données ; facilite un modèle externe plus tard |
| D6-8 | Limites d'upload : 3 pages, 50 Mo | Sécurité des uploads et temps de traitement |
| D6-9 | Informations de la clinique constantes, sans modification prévue | Stable, évite les erreurs d'OCR |
| D6-10 | Aucun seuil IA fixé avant la première évaluation | Mesurer d'abord (sauf zéro allergie ou médicament inventé) |
| D7-1 | S-03 reformulée : reprise des diagnostics et procédures codés autorisée, aucune déduction clinique | Respect de la règle « jamais d'invention » tout en acceptant la Superbill seule |
| D7-2 | « Relu » = clic « Mark as reviewed », exigé avant l'approbation | Trace claire dans l'audit |
| D7-3 | Interface, texte de consultation et documents en anglais | Cible américaine ; limite le risque de traduction de termes médicaux |
| D7-4 | Aucune contrainte matérielle au MVP | Choix du porteur du projet |

## 13. Décisions reportées à la phase d'architecture

Ces décisions ne sont pas des manques du SRS : elles relèvent de l'architecture, et chacune est approuvée par le porteur du projet. Le SRS reste neutre sur les technologies.

| ID | Décision | Critères de choix |
|---|---|---|
| D-01 | Modèle LLM | Données hors de l'hôpital ou non, latence, sortie structurée fiable, coût ; interface unique et jeu d'évaluation rejouable pour pouvoir changer de modèle |
| D-02 | Service OCR | Qualité sur les codes, formats PDF et image, exécution locale ou non ; test sur des pages réelles ou synthétiques |
| D-03 | Fournisseur d'identité | OIDC avec MFA ; contrainte on-premise possible |
| D-04 | Portée FHIR | Version, profil (C-CDA on FHIR est le candidat), ressources de support ; FHIR reste « si faisable » |
| D-05 | Stratégie anti-hallucination | S-02, S-03, contrôle de sortie, évaluation |
| D-06 | Contrat de l'API et schéma de sortie structurée | Doit permettre validation, provenance, édition, versioning, PDF et FHIR |
| D-07 | Style d'architecture | Recommandation : monolithe modulaire (un développeur, environ 10 utilisateurs) |

## 14. Limites connues et suites prévues

- **L-01** Le schéma de la Superbill (section 9.2) est validé sur un exemple synthétique ; il sera revalidé sur une Superbill réelle anonymisée avant tout déploiement.
- **L-02** Les durées de conservation (N-10) sont celles du MVP ; elles sont remplacées au déploiement par celles de l'hôpital et d'un juriste ou DPO.
- **L-03** Les seuils d'acceptation de l'IA, hors « zéro allergie ou médicament inventé », sont fixés après la première évaluation sur le jeu contrôlé, défini à l'architecture.
- **L-04** Écarts connus avec HIPAA : l'audit simple n'enregistre pas la consultation d'un document ; une procédure d'accès d'urgence est à documenter et n'est pas développée au MVP.
- **L-05** Aucune conformité FHIR n'est revendiquée sans validation par un outil officiel.
- **L-06** L'alignement avec les standards repose sur des extraits ; les statuts « non confirmé » seront vérifiés lors de la conception détaillée.
- **L-07** Le texte de consultation peut contenir un identifiant direct (par exemple un nom) que le système ne retire pas automatiquement.
- **L-08** La provenance n'est pas imprimée dans le document exporté ; elle est disponible en revue et dans le rapport séparé.
- **L-09** Les repères HIPAA et RGPD de ce document sont généraux, pas un avis juridique ; ils seront validés par un juriste ou un DPO avant tout déploiement réel.

## 15. Annexes

### Annexe A – Fichiers joints

- `XeleronIA_Superbill_Form_Sample.docx` : exemple fictif de Superbill (une page, données synthétiques).
- `XeleronIA_Template_Clinical_Note.docx`, `XeleronIA_Template_Referral_Letter.docx`, `XeleronIA_Template_Discharge_Summary.docx` : documents exportés, une page chacun.

### Annexe B – Pistes pour l'architecture (sans engagement)

Sources secondaires, rien n'a été testé sur les documents du projet.

- **LLM :** candidats libres auto-hébergeables Qwen3.8-27B, Gemma 4, gpt-oss-20b. L'API Gemini gratuite pourrait servir de modèle de comparaison, uniquement avec des données synthétiques (les conditions lues indiquaient l'usage des données pour améliorer les produits et une interdiction d'usage clinique ; à revérifier).
- **OCR :** PaddleOCR-VL-1.6, GLM-OCR, Docling ; Tesseract avec OCRmyPDF sans GPU. Privilégier un OCR dédié et une validation de format des codes plutôt qu'un LLM pour lire les codes.
- **Dépôts proches** (code et licences non vérifiés) : consult-to-note, clinical-scribe, open-medical-scribe, OpenScribe, AI-Medical-Scribe, recon, clinical-note-to-fhir. Aucun ne traite la fusion Superbill + texte ni les trois types de documents avec versioning.

---

# Partie B – XeleronIA : Proposition de choix techniques

**Technical Stack Proposal** · Auteur : Ouissal Jouhari · Version 1.1

## 1. Principes d'architecture

- **Ports et adaptateurs.** OCR, LLM, identité et export sont derrière des interfaces. Changer de fournisseur ne modifie pas le domaine.
- **Templates en configuration.** Chaque type de document est un fichier YAML (sections, statuts, langue). Ajouter un type ou une langue ne demande pas de code.
- **API comme contrat unique.** L'entrée du texte de consultation passe par l'API, ce qui prépare l'arrivée de l'AI Scribe (hors MVP – version future).
- **Historique immuable.** Chaque modification crée une nouvelle version ; l'audit ne peut qu'être complété.

## 3. Choix technologiques

| Domaine | Choix | Raison |
|---|---|---|
| Architecture | Monolithe modulaire | Un développeur, environ 10 utilisateurs ; pas de microservices. |
| Backend | Python 3.12, FastAPI, Pydantic v2 | Un schéma unique valide l'API et la sortie du LLM. |
| Base de données | PostgreSQL, SQLAlchemy, Alembic | Versions et audit sont relationnels ; audit en ajout seul. |
| Frontend | React, Vite, TypeScript | Interface qui consomme l'API comme n'importe quel client. |
| Identité | Keycloak (auto-hébergé) | OIDC, MFA, compatible on-premise, gratuit. |
| OCR | Extraction directe du texte, puis Docling sur CPU | Local, gratuit ; le scan n'est utilisé que si nécessaire. |
| LLM | Gemini (quota gratuit) en démonstration ; gpt-oss-20b via Ollama en local | Interchangeables par configuration ; données fictives uniquement. |
| Codes médicaux | ICD-10-CM (table CDC) ; CPT : format seulement | Les descriptions CPT sont sous licence. |
| PDF | Jinja2, WeasyPrint | Reproduit les trois modèles d'une page. |
| FHIR | Hors MVP, port prévu | Ajout futur sans toucher au domaine. |
| Déploiement | Docker Compose, Caddy, GitHub Actions | Même image en cloud et en on-premise. |
| Suivi et tests | structlog, Prometheus, Grafana ; pytest, Playwright | Durées mesurées ; jeu d'évaluation IA rejouable. |

## 4. Risques et limites connus

- **Délai de 20 s.** Docling et un LLM local sur CPU peuvent le dépasser. L'objectif est non bloquant ; les durées sont mesurées et rapportées.
- **Gemini gratuit.** Réservé aux données fictives. Ce n'est pas une solution de production.
- **Conformité.** Conçu en tenant compte de HIPAA et du RGPD, sans déclaration de conformité.
