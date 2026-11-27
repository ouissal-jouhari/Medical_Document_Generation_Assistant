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

export type DocumentSection = {
  name: string;
  status: "PROVIDED" | "NOT_PROVIDED";
  content: string | null;
  sources: { citation: string; start: number; end: number; kind: string }[];
};

export type GeneratedDocument = {
  id: string;
  consultation_id: string;
  document_type: "clinical_note" | "referral_letter" | "discharge_summary";
  state: "under_review";
  version: number;
  text_snapshot: string | null;
  sections: { template: string; sections: DocumentSection[] };
  created_at: string;
};

/** Erreur d'API : seul le code stable est exposé, jamais de détail technique (N-11). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly issues: Issue[] = [],
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
  if (response.ok) return (await response.json()) as T;
  let code = "error";
  let issues: Issue[] = [];
  try {
    const body = (await response.json()) as { detail?: unknown; issues?: Issue[] };
    if (typeof body.detail === "string") code = body.detail;
    if (Array.isArray(body.issues)) issues = body.issues;
  } catch {
    // corps absent ou illisible : code générique
  }
  throw new ApiError(response.status, code, issues);
}

export function upload(token: string, path: string, file: File): Promise<Consultation> {
  const form = new FormData();
  form.append("file", file);
  return api<Consultation>(token, path, { method: "POST", body: form });
}
