# ADR 0004 – Authentification du frontend : PKCE, jeton en mémoire

- **Statut :** accepté (F-01, N-04)
- **Contexte :** l'API est le contrat unique et attend un jeton `Bearer`. Il faut choisir entre un jeton en mémoire avec PKCE et un cookie via un BFF, ce qui décide de l'exposition CSRF.
- **Décision :** flux OIDC « code » avec PKCE (S256) dans le navigateur, avec `oidc-client-ts`. Le jeton d'accès reste **en mémoire** (aucun `localStorage`, aucun cookie). L'API lit `Authorization: Bearer`.
- **Conséquences :**
  - Pas de cookie d'authentification : l'API n'est pas exposée au CSRF et n'a donc besoin d'aucun jeton anti-CSRF.
  - Un rechargement de page perd le jeton ; l'application relance le flux et la session SSO Keycloak (30 min d'inactivité) évite de ressaisir le mot de passe et le code TOTP tant que le niveau 2 reste valide.
  - Risque résiduel : une faille XSS pourrait lire le jeton en mémoire. Mitigation : CSP stricte posée par Caddy (`default-src 'self'`), aucun contenu externe, durée de vie du jeton de 5 minutes.
  - Un BFF n'est pas retenu : plus de composants à exploiter pour un seul développeur.
