import { useEffect, useRef, useState } from "react";

import { isCallback, userManager } from "./auth";

type View =
  | { name: "loading" }
  | { name: "login"; message: string; retry: boolean }
  | { name: "home"; displayName: string }
  | { name: "mfa" };

// Textes fixes par code d'erreur de l'API : jamais de détail technique (N-11).
const MESSAGES: Record<string, string> = {
  session_invalid: "Votre session a expiré. Reconnectez-vous.",
  authentication_required: "Connexion requise.",
  identity_provider_unavailable: "Service d'identification indisponible. Réessayez.",
  forbidden: "Accès refusé.",
};

async function errorCode(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      return String((body as { detail: unknown }).detail);
    }
  } catch {
    // corps absent ou illisible : code générique
  }
  return "error";
}

export function App() {
  const [view, setView] = useState<View>({ name: "loading" });
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const toLogin = (message: string, retry: boolean) => setView({ name: "login", message, retry });
    const redirect = () => {
      toLogin("Redirection vers la connexion…", false);
      userManager.signinRedirect().catch(() => {
        toLogin("Service d'identification indisponible. Réessayez.", true);
      });
    };

    async function start() {
      let user = null;
      if (isCallback()) {
        try {
          user = await userManager.signinRedirectCallback();
        } catch {
          window.history.replaceState({}, "", "/");
          toLogin("La connexion a échoué. Réessayez.", true);
          return;
        }
        window.history.replaceState({}, "", "/");
      } else {
        user = await userManager.getUser();
      }
      if (!user || user.expired) {
        redirect();
        return;
      }
      let response: Response;
      try {
        response = await fetch("/api/me", {
          headers: { Authorization: `Bearer ${user.access_token}` },
        });
      } catch {
        toLogin("Service indisponible. Réessayez.", true);
        return;
      }
      if (response.ok) {
        const body = (await response.json()) as { display_name: string };
        setView({ name: "home", displayName: body.display_name });
        return;
      }
      const code = await errorCode(response);
      if (response.status === 401) {
        await userManager.removeUser();
        redirect();
      } else if (code === "mfa_required") {
        setView({ name: "mfa" });
      } else {
        toLogin(MESSAGES[code] ?? "Une erreur est survenue. Réessayez.", true);
      }
    }

    void start();
  }, []);

  const logout = () => {
    void userManager.signoutRedirect();
  };

  return (
    <main>
      <h1>XeleronIA</h1>
      {view.name === "loading" && <p>Chargement…</p>}
      {view.name === "login" && (
        <section aria-label="Connexion">
          <h2>Connexion au clinicien</h2>
          <p>Une authentification à deux facteurs est requise.</p>
          <p role="status">{view.message}</p>
          {view.retry && (
            <button type="button" onClick={() => window.location.assign("/")}>
              Se connecter
            </button>
          )}
        </section>
      )}
      {view.name === "mfa" && (
        <section aria-label="Authentification à deux facteurs requise">
          <p role="alert">Authentification à deux facteurs requise.</p>
          <button type="button" onClick={logout}>
            Se déconnecter
          </button>
        </section>
      )}
      {view.name === "home" && (
        <section aria-label="Accueil">
          <p>Bonjour {view.displayName}</p>
          <button type="button" onClick={logout}>
            Se déconnecter
          </button>
        </section>
      )}
    </main>
  );
}
