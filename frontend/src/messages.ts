// Textes fixes par code d'erreur ou de validation : jamais de détail technique ni de valeur saisie (N-11).
export const ERROR_MESSAGES: Record<string, string> = {
  unsupported_format: "Format non accepté (PDF, png, jpg, jpeg).",
  file_too_large: "Fichier trop volumineux (50 Mo maximum).",
  too_many_pages: "Le PDF dépasse 3 pages.",
  encrypted_pdf: "PDF protégé : déposez une version non chiffrée.",
  corrupt_file: "Fichier illisible ou corrompu.",
  image_too_large: "Image trop grande (dimensions excessives).",
  wrong_state: "Action impossible dans l'état actuel de la consultation.",
  validation_failed: "Corrigez les champs signalés avant de valider.",
  not_found: "Consultation introuvable.",
  network_error: "Service indisponible. Réessayez.",
  identity_provider_unavailable: "Service d'identification indisponible. Réessayez.",
  forbidden: "Accès refusé.",
  llm_unavailable: "Document generation is unavailable. You can retry.",
  llm_timeout: "Document generation took too long. You can retry.",
  malformed_generation: "Document generation failed safely. You can retry.",
  version_conflict: "The document changed in the meantime. Reload it before trying again.",
  document_approved: "This document is approved and can no longer be modified.",
  approval_blocked: "Approval is not possible yet.",
  document_not_approved: "Export is possible after approval only.",
  export_failed: "The PDF could not be produced. The document is unchanged. You can retry.",
};

// Éléments bloquant l'approbation (N-11) : libellés fixes, les noms de section sont affichés tels quels.
export const BLOCKER_LABELS: Record<string, string> = {
  not_reviewed: "The current version has not been marked as reviewed",
  version_rejected: "The current version is rejected",
  patient_name: "Patient name",
  date_of_birth: "Date of birth",
  patient_id: "Patient ID",
  physician: "Physician",
  date_of_service: "Date of service",
  diagnoses: "Coded diagnoses",
  procedures: "Coded procedures",
};

export const EXTRACTION_FAILED_MESSAGE =
  "Extraction impossible. La consultation reste « Uploaded » ; déposez de nouveau la Superbill.";

export const GENERIC_ERROR = "Une erreur est survenue. Réessayez.";

export const ISSUE_MESSAGES: Record<string, string> = {
  required_missing: "Champ obligatoire",
  invalid_date: "Format AAAA-MM-JJ attendu",
  invalid_icd10cm_format: "Format ICD-10-CM invalide",
  invalid_cpt_format: "Format CPT invalide",
  invalid_units: "Unités invalides",
  icd10cm_unknown: "Code absent de la table CDC (avertissement)",
  units_missing: "Unités non renseignées (avertissement)",
  invalid_amount: "Montant illisible (avertissement)",
};

export const STATE_LABELS = { uploaded: "Uploaded", parsed: "Parsed", validated: "Validated" };

export function messageFor(code: string): string {
  return ERROR_MESSAGES[code] ?? GENERIC_ERROR;
}
