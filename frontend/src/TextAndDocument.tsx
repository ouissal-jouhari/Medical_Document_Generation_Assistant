import { useEffect, useRef, useState } from "react";

import { ApiError, api, type GeneratedDocument } from "./api";
import { messageFor } from "./messages";

type Props = {
  token: string;
  id: string;
  onExpired: () => void;
  onBack: () => void;
  onOpenDocument: (documentId: string) => void;
};

const TYPE_LABELS: Record<string, string> = {
  clinical_note: "Clinical Note",
  referral_letter: "Referral Letter",
  discharge_summary: "Discharge Summary",
};

export function TextAndDocument({ token, id, onExpired, onBack, onOpenDocument }: Props) {
  const [text, setText] = useState("");
  const [documentType, setDocumentType] = useState("clinical_note");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  // Garde synchrone : un double clic ne lance jamais deux générations (l'état React est asynchrone).
  const inFlight = useRef(false);

  useEffect(() => {
    api<{ consultation_text: string | null }>(token, `/consultations/${id}`)
      .then((consultation) => setText(consultation.consultation_text ?? ""))
      .then(() => api<GeneratedDocument[]>(token, `/consultations/${id}/documents`))
      .then(setDocuments)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) onExpired();
        else setError(messageFor(e instanceof ApiError ? e.code : "error"));
      });
  }, [token, id, onExpired]);

  const saveText = async () => {
    await api(token, `/consultations/${id}/text`, {
      method: "PUT",
      body: JSON.stringify({ text }),
    });
  };

  const save = async () => {
    setError(null);
    setSaved(false);
    try {
      await saveText();
      setSaved(true);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 401) onExpired();
      else setError(messageFor(e instanceof ApiError ? e.code : "error"));
    }
  };

  const generate = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      await saveText();
      const result = await api<GeneratedDocument>(token, `/consultations/${id}/documents`, {
        method: "POST",
        body: JSON.stringify({ documentType }),
      });
      onOpenDocument(result.id);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 401) onExpired();
      else setError(messageFor(e instanceof ApiError ? e.code : "error"));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  return (
    <section aria-label="Texte et type de document">
      <h2>Text and document type</h2>
      <label>
        Document type
        <select value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
          <option value="clinical_note">Clinical Note</option>
          <option value="referral_letter">Referral Letter</option>
          <option value="discharge_summary">Discharge Summary</option>
        </select>
      </label>
      <label>
        Consultation text (optional)
        <textarea
          maxLength={5000}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setSaved(false);
          }}
        />
      </label>
      <p>{text.length} / 5000 characters</p>
      {text.length === 0 && (
        <p role="status">
          Superbill data alone is not sufficient to generate complete clinical documents.
          Adding the consultation text is recommended.
        </p>
      )}
      {saved && <p role="status">Text saved.</p>}
      {error && <p role="alert">{error}</p>}
      <button type="button" onClick={onBack} disabled={busy}>
        Cancel
      </button>
      <button type="button" onClick={() => void save()} disabled={busy}>
        Save text
      </button>
      <button type="button" onClick={() => void generate()} disabled={busy}>
        {busy ? "Generating…" : "Generate draft"}
      </button>
      {documents.length > 0 && (
        <section aria-label="Documents">
          <h3>Documents</h3>
          <ul>
            {documents.map((d) => (
              <li key={d.id}>
                {TYPE_LABELS[d.document_type]} · {d.state === "approved" ? "Approved" : "Under Review"}{" "}
                · version {d.version}{" "}
                <button type="button" onClick={() => onOpenDocument(d.id)} disabled={busy}>
                  Open
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
