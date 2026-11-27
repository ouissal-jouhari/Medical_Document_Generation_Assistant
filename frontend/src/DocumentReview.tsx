import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  api,
  type DocumentContent,
  type DocumentSection,
  type DocumentSource,
  type DocumentVersion,
  type GeneratedDocument,
} from "./api";
import { BLOCKER_LABELS, messageFor } from "./messages";

type Props = {
  token: string;
  id: string;
  onExpired: () => void;
  onBack: () => void;
  onOpen: (documentId: string) => void;
};

const ORIGIN_LABELS: Record<string, string> = {
  superbill: "Superbill",
  consultation_text: "Consultation text",
  ai: "AI",
  clinician: "Clinician",
};

const KIND_LABELS: Record<string, string> = { ai_generated: "AI-generated", edited: "edited" };

const BANNER = { background: "#fff3cd", border: "2px solid #b58100", padding: "0.5rem" };
const SAFETY_MISSING = { border: "2px solid #b00020", padding: "0.5rem" };

function formatDate(value: string): string {
  return new Date(value).toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

function sourceLabel(source: DocumentSource): string {
  const origin = ORIGIN_LABELS[source.kind] ?? source.kind;
  if (source.kind === "clinician") return `${origin} edit, ${source.at ? formatDate(source.at) : ""}`;
  return `${origin}: “${source.citation ?? ""}”`;
}

/** E-06 : revue d'un document. Chaque action envoie la version affichée (F-14). */
export function DocumentReview({ token, id, onExpired, onBack, onOpen }: Props) {
  const [document, setDocument] = useState<GeneratedDocument | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [history, setHistory] = useState<DocumentVersion[]>([]);
  const [viewed, setViewed] = useState<DocumentVersion | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blockers, setBlockers] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  // Garde synchrone contre le double clic (l'état React est asynchrone).
  const inFlight = useRef(false);

  const show = useCallback((result: GeneratedDocument) => {
    setDocument(result);
    setDrafts(
      Object.fromEntries(result.sections.sections.map((s) => [s.name, s.content ?? ""])),
    );
  }, []);

  const fail = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.status === 401) {
        onExpired();
        return;
      }
      const code = e instanceof ApiError ? e.code : "error";
      setError(messageFor(code));
      setBlockers(e instanceof ApiError && code === "approval_blocked" ? e.missing : []);
    },
    [onExpired],
  );

  const load = useCallback(async () => {
    const [current, versions] = await Promise.all([
      api<GeneratedDocument>(token, `/documents/${id}`),
      api<DocumentVersion[]>(token, `/documents/${id}/versions`),
    ]);
    show(current);
    setHistory(versions);
  }, [token, id, show]);

  useEffect(() => {
    load().catch(fail);
  }, [load, fail]);

  const run = async (action: () => Promise<GeneratedDocument | null>, done?: string) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    setBlockers([]);
    setNotice(null);
    try {
      const result = await action();
      if (result) {
        show(result);
        setHistory(await api<DocumentVersion[]>(token, `/documents/${id}/versions`));
        setViewed(null);
        if (done) setNotice(done);
      }
    } catch (e: unknown) {
      fail(e);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  const post = (path: string, extra: Record<string, unknown> = {}) =>
    api<GeneratedDocument>(token, `/documents/${id}/${path}`, {
      method: "POST",
      body: JSON.stringify({ expectedVersion: document?.version, ...extra }),
    });

  if (!document) {
    return (
      <section aria-label="Revue du document">
        {error ? <p role="alert">{error}</p> : <p>Chargement…</p>}
        <button type="button" onClick={onBack}>
          Back
        </button>
      </section>
    );
  }

  const approved = document.state === "approved";
  const changed = document.sections.sections.filter(
    (s) => (drafts[s.name] ?? "") !== (s.content ?? ""),
  );
  const save = () =>
    run(
      () =>
        api<GeneratedDocument>(token, `/documents/${id}/sections`, {
          method: "PUT",
          body: JSON.stringify({
            expectedVersion: document.version,
            sections: changed.map((s) => ({ name: s.name, content: drafts[s.name] })),
          }),
        }),
      "Saved as a new version.",
    );
  const createNew = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      const created = await api<GeneratedDocument>(token, `/documents/${id}/new-document`, {
        method: "POST",
      });
      onOpen(created.id);
    } catch (e: unknown) {
      fail(e);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  return (
    <section aria-label="Revue du document">
      {document.draft && (
        <p role="note" style={BANNER}>
          <strong>AI-generated draft</strong> – review every section before approval.
        </p>
      )}
      <h2>{document.sections.template}</h2>
      <p>
        {approved ? "Approved" : "Under Review"} · Version {document.version} (
        {KIND_LABELS[document.version_kind]}
        {document.restored_from ? `, restored from version ${document.restored_from}` : ""}
        {document.rejected ? ", rejected" : ""}
        {document.reviewed ? ", reviewed" : ""})
      </p>
      {!approved && !document.text_snapshot && (
        <p role="status">
          No consultation text was provided: sections that depend on it are Not provided.
        </p>
      )}
      {approved && document.approved_at && (
        <section aria-label="Approbation">
          <p>
            Approved by {document.approver_name} on {formatDate(document.approved_at)}
          </p>
          {document.clinic && (
            <p>
              {document.clinic.name} · {document.clinic.address} · {document.clinic.city}{" "}
              {document.clinic.postal_code} · {document.clinic.phone} · {document.clinic.email} ·{" "}
              {document.clinic.website}
            </p>
          )}
        </section>
      )}

      {document.missing_information.length > 0 && (
        <section aria-label="Missing information">
          <h3>Missing information</h3>
          <ul>
            {document.missing_information.map((item) => (
              <li key={item.name}>
                {BLOCKER_LABELS[item.name] ?? item.name} ({item.level.toLowerCase()})
              </li>
            ))}
          </ul>
        </section>
      )}

      <Content
        content={document.sections}
        editable={!approved}
        drafts={drafts}
        busy={busy}
        onChange={(name, value) => setDrafts({ ...drafts, [name]: value })}
      />

      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert">{error}</p>}
      {blockers.length > 0 && (
        <ul aria-label="Approval blockers">
          {blockers.map((b) => (
            <li key={b}>{BLOCKER_LABELS[b] ?? `${b} (Not provided)`}</li>
          ))}
        </ul>
      )}

      <p>
        <button type="button" onClick={onBack} disabled={busy}>
          Back
        </button>{" "}
        {!approved && (
          <>
            <button
              type="button"
              onClick={() => void save()}
              disabled={busy || changed.length === 0}
            >
              Save
            </button>{" "}
            <button
              type="button"
              onClick={() => void run(() => post("review"), "Marked as reviewed.")}
              disabled={busy || !!document.rejected || !!document.reviewed || changed.length > 0}
            >
              Mark as reviewed
            </button>{" "}
            <button
              type="button"
              onClick={() => void run(() => post("approve"), "Document approved.")}
              disabled={busy || changed.length > 0}
            >
              Approve
            </button>{" "}
            <button
              type="button"
              onClick={() => void run(() => post("reject"), "Version rejected.")}
              disabled={busy || !!document.rejected}
            >
              Reject
            </button>{" "}
            {document.rejected && (
              <button
                type="button"
                onClick={() => void run(() => post("regenerate"), "New AI version generated.")}
                disabled={busy}
              >
                {busy ? "Generating…" : "Regenerate"}
              </button>
            )}
          </>
        )}
        {approved && (
          <button type="button" onClick={() => void createNew()} disabled={busy}>
            {busy ? "Generating…" : "Create new document"}
          </button>
        )}
      </p>

      <section aria-label="Version history">
        <h3>Version history</h3>
        <ul>
          {history.map((v) => (
            <li key={v.number}>
              v{v.number} {KIND_LABELS[v.kind]}
              {v.restored_from ? ` (restored from v${v.restored_from})` : ""} ·{" "}
              {formatDate(v.created_at)}
              {v.number === document.version ? " · current" : ""}
              {v.rejected ? " · rejected" : ""}
              {v.reviewed ? " · reviewed" : ""}
              {v.approved ? " · approved" : ""}{" "}
              <button type="button" onClick={() => setViewed(v)} disabled={busy}>
                View
              </button>{" "}
              {!approved && v.number !== document.version && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    void run(
                      () => post("rollback", { toVersion: v.number }),
                      `Version ${v.number} restored as a new version.`,
                    )
                  }
                >
                  Restore
                </button>
              )}
            </li>
          ))}
        </ul>
        {viewed && (
          <section aria-label={`Version ${viewed.number}`}>
            <h4>
              Version {viewed.number} (read only){" "}
              <button type="button" onClick={() => setViewed(null)}>
                Close
              </button>
            </h4>
            <Content content={viewed.sections} editable={false} drafts={{}} busy={busy} />
          </section>
        )}
      </section>
    </section>
  );
}

type ContentProps = {
  content: DocumentContent;
  editable: boolean;
  drafts: Record<string, string>;
  busy: boolean;
  onChange?: (name: string, value: string) => void;
};

function Content({ content, editable, drafts, busy, onChange }: ContentProps) {
  const block = content.common_block;
  return (
    <>
      <article aria-label="Common block">
        <h4>
          Patient and encounter <small>[origin: {ORIGIN_LABELS.superbill}]</small>
        </h4>
        <p>
          {block.patient_name} · {block.date_of_birth} · {block.patient_id}
        </p>
        <p>
          {block.physician} · {block.date_of_service}
        </p>
        <h4>Diagnoses (coded)</h4>
        <ul>
          {block.diagnoses.map((item, index) => (
            <li key={`${index}-${item.code}`}>
              {item.code}: {item.description}
            </li>
          ))}
        </ul>
        <h4>Procedures (coded)</h4>
        <ul>
          {block.procedures.map((item, index) => (
            <li key={`${index}-${item.code}`}>
              {item.code}: {item.description}
            </li>
          ))}
        </ul>
      </article>
      {content.sections.map((section) => (
        <Section
          key={section.name}
          section={section}
          editable={editable}
          value={drafts[section.name] ?? section.content ?? ""}
          busy={busy}
          onChange={onChange}
        />
      ))}
    </>
  );
}

type SectionProps = {
  section: DocumentSection;
  editable: boolean;
  value: string;
  busy: boolean;
  onChange?: (name: string, value: string) => void;
};

function Section({ section, editable, value, busy, onChange }: SectionProps) {
  const missing = section.status !== "PROVIDED";
  const safetyMissing = missing && section.level === "SAFETY";
  return (
    <article aria-label={section.name} style={safetyMissing ? SAFETY_MISSING : undefined}>
      <h4>
        {section.name} <small>{section.level}</small> ·{" "}
        {safetyMissing ? <strong>⚠ NOT PROVIDED</strong> : missing ? "Not provided" : "Provided"}{" "}
        {!missing && <small>[origin: {ORIGIN_LABELS[section.origin] ?? section.origin}]</small>}
      </h4>
      {editable ? (
        <textarea
          aria-label={`${section.name} content`}
          maxLength={10000}
          value={value}
          placeholder="Not provided"
          disabled={busy}
          onChange={(event) => onChange?.(section.name, event.target.value)}
        />
      ) : (
        <p>{missing ? "Not provided" : section.content}</p>
      )}
      {section.sources.length > 0 && (
        <ul aria-label={`${section.name} sources`}>
          {section.sources.map((source, index) => (
            <li key={index}>{sourceLabel(source)}</li>
          ))}
        </ul>
      )}
    </article>
  );
}
