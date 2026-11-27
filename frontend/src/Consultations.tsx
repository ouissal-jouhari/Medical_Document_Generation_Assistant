import { useEffect, useState } from "react";

import { ApiError, api, type Summary } from "./api";
import { STATE_LABELS, messageFor } from "./messages";

type Props = {
  token: string;
  onNew: () => void;
  onOpen: (id: string, state: Summary["state"]) => void;
  onExpired: () => void;
};

// E-02 : liste des consultations de l'auteur ; suppression définitive après confirmation (F-22).
export function Consultations({ token, onNew, onOpen, onExpired }: Props) {
  const [rows, setRows] = useState<Summary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Summary[]>(token, "/consultations")
      .then(setRows)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) onExpired();
        else setError(messageFor(e instanceof ApiError ? e.code : "error"));
      });
  }, [token, onExpired]);

  const remove = async (id: string) => {
    const confirmed = window.confirm(
      "Supprimer définitivement cette consultation, son texte, ses documents et ses versions ?",
    );
    if (!confirmed) return;
    try {
      await api<void>(token, `/consultations/${id}`, { method: "DELETE" });
      setRows((current) => (current ?? []).filter((row) => row.id !== id));
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 401) onExpired();
      else setError(messageFor(e instanceof ApiError ? e.code : "error"));
    }
  };

  const action = (state: Summary["state"]) =>
    state === "uploaded" ? "Reprendre" : state === "parsed" ? "Vérifier" : "Ouvrir";

  return (
    <section aria-label="Mes consultations">
      <h2>Mes consultations</h2>
      <button type="button" onClick={onNew}>
        + Nouvelle consultation
      </button>
      {error && <p role="alert">{error}</p>}
      {rows !== null && rows.length === 0 && <p>Aucune consultation. Créez-en une.</p>}
      {rows !== null && rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Créée le</th>
              <th>Patient</th>
              <th>État</th>
              <th>Action</th>
              <th>Suppression</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.created_at.slice(0, 10)}</td>
                <td>{row.patient_name ?? "(non extrait)"}</td>
                <td>{STATE_LABELS[row.state]}</td>
                <td>
                  <button type="button" onClick={() => onOpen(row.id, row.state)}>
                    {action(row.state)}
                  </button>
                </td>
                <td>
                  <button type="button" onClick={() => void remove(row.id)}>
                    Supprimer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
