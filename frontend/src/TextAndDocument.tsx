import { useEffect, useState } from "react";

import { ApiError, api, type GeneratedDocument } from "./api";
import { messageFor } from "./messages";

type Props = {
  token: string;
  id: string;
  onExpired: () => void;
  onBack: () => void;
};

export function TextAndDocument({ token, id, onExpired, onBack }: Props) {
  const [text, setText] = useState("");
  const [documentType, setDocumentType] = useState("clinical_note");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [document, setDocument] = useState<GeneratedDocument | null>(null);

  useEffect(() => {
    api<{ consultation_text: string | null }>(token, `/consultations/${id}`)
      .then((consultation) => setText(consultation.consultation_text ?? ""))
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

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      await saveText();
      const result = await api<GeneratedDocument>(token, `/consultations/${id}/documents`, {
        method: "POST",
        body: JSON.stringify({ documentType }),
      });
      setDocument(result);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 401) onExpired();
      else setError(messageFor(e instanceof ApiError ? e.code : "error"));
    } finally {
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
          onChange={(event) => setText(event.target.value)}
        />
      </label>
      <p>{text.length} / 5000 characters</p>
      {text.length === 0 && (
        <p role="status">
          Superbill data alone is not sufficient to generate complete clinical documents.
          Adding the consultation text is recommended.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      <button type="button" onClick={onBack} disabled={busy}>
        Cancel
      </button>
      <button type="button" onClick={() => void generate()} disabled={busy}>
        {busy ? "Generating…" : "Generate draft"}
      </button>
      {document && (
        <section aria-label="Document brouillon">
          <h3>{document.sections.template}</h3>
          {document.sections.sections.map((section) => (
            <article key={section.name}>
              <h4>{section.name}</h4>
              <p>{section.status === "PROVIDED" ? section.content : "Not provided"}</p>
            </article>
          ))}
        </section>
      )}
    </section>
  );
}
