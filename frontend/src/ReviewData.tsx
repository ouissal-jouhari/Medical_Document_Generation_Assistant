import { useEffect, useState } from "react";

import { ApiError, type Consultation, type Issue, type Superbill, api } from "./api";
import { ISSUE_MESSAGES, STATE_LABELS, messageFor } from "./messages";

type Props = { token: string; id: string; onBack: () => void; onExpired: () => void };

type TextPath = "patient.fullName" | "patient.dateOfBirth" | "patient.patientId" | "physician.name"
  | "encounter.dateOfService" | "encounter.placeOfService" | "billing.totalCharges";

function readPath(data: Superbill, path: TextPath): string {
  const [group, key] = path.split(".") as [keyof Superbill, string];
  const value = (data[group] as Record<string, string | null>)[key];
  return value ?? "";
}

function writePath(data: Superbill, path: TextPath, value: string): Superbill {
  const [group, key] = path.split(".") as [keyof Superbill, string];
  return { ...data, [group]: { ...(data[group] as object), [key]: value } };
}

// Le serveur reçoit tout sauf la métadonnée technique (nombre de pages, non modifiable).
function payload(data: Superbill) {
  const { extraction: _ignored, ...editable } = data;
  void _ignored;
  return editable;
}

// E-04 : afficher et corriger les champs extraits ; valider explicitement (F-04, F-05).
export function ReviewData({ token, id, onBack, onExpired }: Props) {
  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [data, setData] = useState<Superbill | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);

  const fail = (e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
      onExpired();
      return;
    }
    const code = e instanceof ApiError ? e.code : "error";
    setMessage(messageFor(code));
    if (e instanceof ApiError && e.issues.length > 0) setIssues(e.issues);
  };

  const load = (result: Consultation) => {
    setConsultation(result);
    setData(result.data);
    setIssues(result.issues);
  };

  useEffect(() => {
    api<Consultation>(token, `/consultations/${id}`)
      .then(load)
      .catch(fail);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, id]);

  if (!consultation || !data) {
    return <p role="status">{message ?? "Chargement…"}</p>;
  }

  const readOnly = consultation.state !== "parsed";
  const issueFor = (field: string) => issues.find((i) => i.field === field);

  const note = (field: string) => {
    const issue = issueFor(field);
    if (!issue) return null;
    return (
      <span role="note" className={issue.blocking ? "blocking" : "warning"}>
        {" "}
        ⚠ {ISSUE_MESSAGES[issue.code] ?? "À vérifier"}
      </span>
    );
  };

  const text = (label: string, path: TextPath, required = false) => (
    <div>
      <label>
        {label}
        {required ? "*" : ""}{" "}
        <input
          value={readPath(data, path)}
          disabled={readOnly}
          onChange={(event) => setData(writePath(data, path, event.target.value))}
        />
      </label>
      {note(path)}
    </div>
  );

  async function save(): Promise<Consultation | null> {
    try {
      const result = await api<Consultation>(token, `/consultations/${id}/data`, {
        method: "PUT",
        body: JSON.stringify(payload(data as Superbill)),
      });
      load(result);
      setMessage("Corrections enregistrées.");
      return result;
    } catch (e) {
      fail(e);
      return null;
    }
  }

  async function validate() {
    const saved = await save();
    if (!saved) return;
    try {
      load(await api<Consultation>(token, `/consultations/${id}/validate`, { method: "POST" }));
      setMessage("Données validées.");
    } catch (e) {
      fail(e);
    }
  }

  const last = consultation.corrections[0];

  return (
    <section aria-label="Vérification des données">
      <h2>Vérification des données</h2>
      <p>État : {STATE_LABELS[consultation.state]}</p>
      <fieldset>
        <legend>Patient</legend>
        {text("Nom complet", "patient.fullName", true)}
        {text("Date de naissance", "patient.dateOfBirth", true)}
        {text("Identifiant", "patient.patientId", true)}
      </fieldset>
      {text("Médecin", "physician.name", true)}
      <fieldset>
        <legend>Consultation</legend>
        {text("Date de service", "encounter.dateOfService", true)}
        {text("Lieu de service", "encounter.placeOfService")}
      </fieldset>

      <fieldset>
        <legend>Diagnostics* (ICD-10-CM)</legend>
        {note("diagnoses")}
        {data.diagnoses.map((diagnosis, i) => (
          <div key={i}>
            <input
              aria-label={`Code diagnostic ${i + 1}`}
              value={diagnosis.code}
              disabled={readOnly}
              onChange={(e) =>
                setData({
                  ...data,
                  diagnoses: data.diagnoses.map((d, j) => (j === i ? { ...d, code: e.target.value } : d)),
                })
              }
            />
            <input
              aria-label={`Description diagnostic ${i + 1}`}
              value={diagnosis.description}
              disabled={readOnly}
              onChange={(e) =>
                setData({
                  ...data,
                  diagnoses: data.diagnoses.map((d, j) =>
                    j === i ? { ...d, description: e.target.value } : d,
                  ),
                })
              }
            />
            {note(`diagnoses[${i}].code`)}
            {!readOnly && (
              <button
                type="button"
                onClick={() => setData({ ...data, diagnoses: data.diagnoses.filter((_, j) => j !== i) })}
              >
                Retirer
              </button>
            )}
          </div>
        ))}
        {!readOnly && (
          <button
            type="button"
            onClick={() => setData({ ...data, diagnoses: [...data.diagnoses, { code: "", description: "" }] })}
          >
            + Ajouter un diagnostic
          </button>
        )}
      </fieldset>

      <fieldset>
        <legend>Procédures* (CPT)</legend>
        {note("procedures")}
        {data.procedures.map((procedure, i) => (
          <div key={i}>
            <input
              aria-label={`Code procédure ${i + 1}`}
              value={procedure.code}
              disabled={readOnly}
              onChange={(e) =>
                setData({
                  ...data,
                  procedures: data.procedures.map((p, j) => (j === i ? { ...p, code: e.target.value } : p)),
                })
              }
            />
            <input
              aria-label={`Description procédure ${i + 1}`}
              value={procedure.description}
              disabled={readOnly}
              onChange={(e) =>
                setData({
                  ...data,
                  procedures: data.procedures.map((p, j) =>
                    j === i ? { ...p, description: e.target.value } : p,
                  ),
                })
              }
            />
            <input
              aria-label={`Unités procédure ${i + 1}`}
              type="number"
              value={procedure.units ?? ""}
              disabled={readOnly}
              onChange={(e) =>
                setData({
                  ...data,
                  procedures: data.procedures.map((p, j) =>
                    j === i ? { ...p, units: e.target.value === "" ? null : Number(e.target.value) } : p,
                  ),
                })
              }
            />
            {note(`procedures[${i}].code`)}
            {note(`procedures[${i}].units`)}
            {!readOnly && (
              <button
                type="button"
                onClick={() => setData({ ...data, procedures: data.procedures.filter((_, j) => j !== i) })}
              >
                Retirer
              </button>
            )}
          </div>
        ))}
        {!readOnly && (
          <button
            type="button"
            onClick={() =>
              setData({ ...data, procedures: [...data.procedures, { code: "", description: "", units: null }] })
            }
          >
            + Ajouter une procédure
          </button>
        )}
      </fieldset>

      {text("Montant total", "billing.totalCharges")}
      {note("billing.totalCharges")}
      <p>Pages extraites : {data.extraction.pageCount}</p>
      <p>
        Corrections : {consultation.corrections.length}
        {last ? ` (dernière le ${last.changed_at.slice(0, 19).replace("T", " ")} UTC)` : ""}
      </p>

      {!readOnly && (
        <div>
          <button type="button" onClick={() => void save()}>
            Enregistrer les corrections
          </button>
          <button type="button" onClick={() => void validate()}>
            Valider les données
          </button>
        </div>
      )}
      <button type="button" onClick={onBack}>
        Retour à mes consultations
      </button>
      {message && <p role="status">{message}</p>}
    </section>
  );
}
