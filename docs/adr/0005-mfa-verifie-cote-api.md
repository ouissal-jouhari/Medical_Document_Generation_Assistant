# ADR 0005 – MFA vérifié côté API par la claim `acr`

- **Statut :** accepté, **à valider contre la version de Keycloak retenue** (JALONS, tâche 1)
- **Décision :** le flux de connexion du realm (`browser-mfa`) impose un second facteur TOTP. Il utilise les niveaux d'authentification de Keycloak : niveau 1 = mot de passe, niveau 2 = TOTP. Le client `xeleron-web` demande `acr_values=2` par défaut. Le jeton émis porte alors `acr = "2"`. L'API (`OidcIdentityProvider`) vérifie la signature, l'émetteur, l'expiration, le client (`azp`) **et** `acr == OIDC_REQUIRED_ACR` (« 2 »). Sans cela, la réponse est `403 mfa_required`, même si le jeton est valide.
- **Pourquoi côté API :** ne pas faire confiance au frontend ; un jeton mono-facteur (`acr = "1"`) ou sans `acr` est refusé (tests `test_F01_*`).
- **Réglages du realm :** niveau 1 valable 10 h, niveau 2 valable 30 min (`deploy/keycloak/xeleron-realm.json`). Le rôle `clinician` est un rôle de realm ; l'API lit `realm_access.roles`.
- **Validation restante :** l'obtention réelle de `acr = "2"` après saisie du TOTP sera confirmée par le test de bout en bout (Playwright, jalon 7) avec l'utilisateur de test du realm. La valeur attendue est un paramètre (`OIDC_REQUIRED_ACR`) : si la version de Keycloak émet une autre valeur, un changement de configuration suffit, sans toucher au code.
- **Secrets :** le mot de passe et le secret TOTP de l'utilisateur de test viennent de l'environnement (`KC_TEST_USER_*`), jamais du dépôt. Ils doivent être changés ou l'utilisateur supprimé hors test.
