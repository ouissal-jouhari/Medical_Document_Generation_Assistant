import { useState } from "react";

import { ApiError, type Consultation, upload } from "./api";
import { EXTRACTION_FAILED_MESSAGE, messageFor } from "./messages";

type Props = {
  token: string;
  /** Consultation à l'état Uploaded dont on redépose la Superbill (F-06). */
  existingId?: string;
  onParsed: (id: string) => void;
  onCancel: () => void;
  onExpired: () => void;
};

// E-03 : dépôt de la Superbill. Un fichier refusé ne crée aucune consultation (F-03).
export function NewConsultation({ token, existingId, onParsed, onCancel, onExpired }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [currentId, setCurrentId] = useState<string | undefined>(existingId);

  async function submit() {
    if (!file) {
      setMessage("Choisissez un fichier.");
      return;
    }
    setBusy(true);
    setMessage("Extraction en cours…");
    try {
      const path = currentId ? `/consultations/${currentId}/superbill` : "/consultations";
      const result: Consultation = await upload(token, path, file);
      if (result.extraction === "failed" || result.state === "uploaded") {
        setCurrentId(result.id); // le prochain dépôt reprend la même consultation
        setMessage(EXTRACTION_FAILED_MESSAGE);
      } else {
        onParsed(result.id);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) onExpired();
      else setMessage(messageFor(e instanceof ApiError ? e.code : "error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Nouvelle consultation">
      <h2>Nouvelle consultation</h2>
      <p>
        Déposez la Superbill (PDF de 3 pages maximum, ou une image png/jpg/jpeg), 50 Mo maximum.
      </p>
      <input
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        aria-label="Fichier Superbill"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
      <div>
        <button type="button" onClick={() => void submit()} disabled={busy}>
          Envoyer
        </button>
        <button type="button" onClick={onCancel} disabled={busy}>
          Annuler
        </button>
      </div>
      {message && <p role="status">{message}</p>}
    </section>
  );
}
