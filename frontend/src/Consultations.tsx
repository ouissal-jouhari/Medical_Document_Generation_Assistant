import { useEffect, useState } from "react";

import { ApiError, api, type Summary } from "./api";
import { STATE_LABELS, messageFor } from "./messages";

type Props = {
  token: string;
  onNew: () => void;
  onOpen: (id: string, state: Summary["state"]) => void;
  onExpired: () => void;
};

// E-02 : liste des consultations de l'auteur. La suppression arrive au jalon 6 (bouton inactif).
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
                  <button type="button" disabled title="Disponible au jalon 6">
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
