import { InMemoryWebStorage, UserManager, WebStorageStateStore } from "oidc-client-ts";

const origin = window.location.origin;

// PKCE (flux « code »). Le jeton d'accès reste en mémoire : jamais de localStorage ni de cookie,
// donc pas d'exposition CSRF (ADR 0004). Seul l'état transitoire du flux utilise sessionStorage.
export const userManager = new UserManager({
  authority: `${origin}/auth/realms/xeleron`,
  client_id: "xeleron-web",
  redirect_uri: `${origin}/`,
  post_logout_redirect_uri: `${origin}/`,
  response_type: "code",
  scope: "openid profile",
  acr_values: "2",
  automaticSilentRenew: false,
  userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
});

export function isCallback(): boolean {
  const params = new URLSearchParams(window.location.search);
  return params.has("code") && params.has("state");
}
