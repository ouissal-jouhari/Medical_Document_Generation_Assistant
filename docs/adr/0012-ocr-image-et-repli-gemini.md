# ADR 0012 – OCR des images et repli Gemini

## Contexte
Deux défauts constatés au jalon 4 : (1) la génération échouait (« Document generation is unavailable ») car `gemini-3.8-flash` répond 503 en cas de forte demande, sans nouvelle tentative ; (2) l'extraction d'une image laissait la plupart des champs vides : la mise en page de Docling mélangeait l'ordre des champs du formulaire.

## Décision
- `GeminiLlmProvider` : 2 tentatives par modèle, puis modèles de repli (`LLM_FALLBACK_MODELS`). La clé passe dans l'en-tête `x-goog-api-key`, plus dans l'URL. Les erreurs restent normalisées (`LlmUnavailable`, `LlmTimeout`).
- Images : nettoyage (gris, contraste, médian, Otsu, agrandissement) puis Tesseract direct (psm 6, ordre ligne par ligne). Docling reste utilisé pour les PDF scannés. Aucune donnée ne quitte le système (N-19), pas de LLM dans l'extraction.
- Parseur : « 110 » lu pour « I10 » corrigé dans les diagnostics ; libellé « Insurance Provider. » ignoré.

## Conséquences
Scan de test : 8 champs sur 8 corrects en 5–8 s (contre 35 s et 1 champ). Le clinicien vérifie toujours le résultat (R-02).
