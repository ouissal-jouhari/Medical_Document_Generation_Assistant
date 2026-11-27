export type Issue = { field: string; code: string; blocking: boolean };

export type Diagnosis = { code: string; description: string };
export type Procedure = { code: string; description: string; units: number | null };

export type Superbill = {
  patient: { fullName: string | null; dateOfBirth: string | null; patientId: string | null };
  physician: { name: string | null };
  encounter: { dateOfService: string | null; placeOfService: string | null };
  diagnoses: Diagnosis[];
  procedures: Procedure[];
  billing: { totalCharges: string | null };
  extraction: { pageCount: number };
};

export type Correction = { field: string; author_id: string; changed_at: string };

export type Consultation = {
  id: string;
  state: "uploaded" | "parsed" | "validated";
  created_at: string;
  extraction_failures: number;
  extraction: "parsed" | "failed" | null;
  data: Superbill | null;
  issues: Issue[];
  corrections: Correction[];
};

export type Summary = {
  id: string;
  state: Consultation["state"];
  created_at: string;
  patient_name: string | null;
  extraction_failures: number;
};

export type CommonBlock = {
  patient_name: string | null;
  date_of_birth: string | null;
  patient_id: string | null;
  physician: string | null;
  date_of_service: string | null;
  diagnoses: { code: string; description: string }[];
  procedures: { code: string; description: string }[];
};

export type DocumentSource = {
  kind: "consultation_text" | "superbill" | "clinician";
  citation?: string;
  start?: number;
  end?: number;
  author_id?: string;
  at?: string;
};

export type DocumentSection = {
  name: string;
  status: "PROVIDED" | "NOT_PROVIDED";
  content: string | null;
  level: "REQUIRED" | "SAFETY" | "STANDARD";
  origin: "ai" | "clinician";
  sources: DocumentSource[];
};

export type DocumentContent = {
  template: string;
  common_block: CommonBlock;
  sections: DocumentSection[];
};

export type Mark = { actor_id: string; occurred_at: string };

export type Clinic = {
  name: string;
  address: string;
  city: string;
  postal_code: string;
  phone: string;
  email: string;
  website: string;
};

export type GeneratedDocument = {
  id: string;
  consultation_id: string;
  document_type: "clinical_note" | "referral_letter" | "discharge_summary";
  state: "under_review" | "approved";
  draft: boolean;
  version: number;
  version_kind: "ai_generated" | "edited";
  restored_from: number | null;
  version_author_id: string;
  version_created_at: string;
  reviewed: Mark | null;
  rejected: Mark | null;
  text_snapshot: string | null;
  sections: DocumentContent;
  missing_information: { name: string; level: string }[];
  created_at: string;
  approved_at: string | null;
  approver_name: string | null;
  approved_version: number | null;
  clinic: Clinic | null;
};

export type DocumentVersion = {
  number: number;
  kind: GeneratedDocument["version_kind"];
  restored_from: number | null;
  author_id: string;
  created_at: string;
  reviewed: Mark | null;
  rejected: Mark | null;
  approved: boolean;
  text_snapshot: string | null;
  sections: DocumentContent;
};

/** Erreur d'API : seul le code stable est exposé, jamais de détail technique (N-11). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly issues: Issue[] = [],
    readonly missing: string[] = [],
  ) {
    super(code);
  }
}

export async function api<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (typeof init.body === "string") headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error");
  }
  if (response.status === 204) return undefined as T;
  if (response.ok) return (await response.json()) as T;
  let code = "error";
  let issues: Issue[] = [];
  let missing: string[] = [];
  try {
    const body = (await response.json()) as {
      detail?: unknown;
      issues?: Issue[];
      missing?: string[];
    };
    if (typeof body.detail === "string") code = body.detail;
    if (Array.isArray(body.issues)) issues = body.issues;
    if (Array.isArray(body.missing)) missing = body.missing;
  } catch {
    // corps absent ou illisible : code générique
  }
  throw new ApiError(response.status, code, issues, missing);
}

export function upload(token: string, path: string, file: File): Promise<Consultation> {
  const form = new FormData();
  form.append("file", file);
  return api<Consultation>(token, path, { method: "POST", body: form });
}
