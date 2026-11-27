# ADR 0013 – Templates alignés sur le SRS 5.2–5.4 et contrôle d'ancrage

## Contexte
Un Discharge Summary de 3 179 caractères revenait avec toutes les sections « Not provided ». Gemini avait pourtant rempli les sections ; le validateur les rejetait :
- règle de négation : tout contenu contenant « no / without / negative… » était vidé, même sourcé (« No intensive care transfer ») ;
- règle des codes : « x10^9/L » était lu comme le code ICD X10 (regex insensible à la casse) ;
- sources : les lignes de la Superbill n'étaient comparables qu'au format « description », alors que le prompt les présente en « code: description ».
Les templates YAML ne suivaient pas le SRS (noms, statuts) et le moteur citait en dur « Discharge Diagnosis » (contraire à N-14).

## Décision
- Templates : noms et niveaux du SRS (`level` : REQUIRED / SAFETY / STANDARD, plus une `description` qui guide le LLM). Les champs `status` et `citation_required` sont supprimés. Le moteur ne contient plus aucun nom de section.
- Bloc commun (SRS 5.1) : stocké dans `sections.common_block`, issu de la Superbill sans déduction (S-03). Les identifiants patient n'y sont ajoutés qu'après la génération et ne sont jamais envoyés au LLM (N-19).
- Contrôle d'ancrage (par section, raison journalisée sans texte) : une section reste « Not provided » sans citation littérale trouvée ; une négation n'est acceptée que si une citation la contient ; un code n'est accepté que s'il figure dans la Superbill ou dans le texte du clinicien.

## Conséquences
Ajouter un template = ajouter un fichier YAML (N-14). Le contrôle anti-invention reste strict : aucune affirmation sans source valide. Le bandeau « AI-generated draft », les 4 origines, les statuts et « Missing information » (F-13) restent au jalon 5.
