import { useEffect, useState } from "react";

type Status = "checking" | "ok" | "down";

export function App() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => setStatus(r.ok ? "ok" : "down"))
      .catch(() => setStatus("down"));
  }, []);

  return (
    <main>
      <h1>XeleronIA</h1>
      <p>API : {status === "checking" ? "vérification…" : status === "ok" ? "disponible" : "indisponible"}</p>
    </main>
  );
}
