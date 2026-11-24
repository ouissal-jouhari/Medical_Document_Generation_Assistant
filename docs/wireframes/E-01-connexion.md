# Maquette E-01 – Connexion (basse fidélité)

Exigence : F-01 (authentification avec MFA). La saisie du mot de passe et du code TOTP se fait sur la page Keycloak, pas dans l'application.

```
┌──────────────────────────────────────────────────────┐
│  XeleronIA                                           │
├──────────────────────────────────────────────────────┤
│                                                      │
│              Connexion au clinicien                  │
│                                                      │
│   Une authentification à deux facteurs est requise.  │
│                                                      │
│        [ Se connecter ]                              │
│                                                      │
│   (zone de message : redirection en cours,           │
│    ou erreur sûre, par exemple « Service             │
│    d'identification indisponible. Réessayez. »)      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

Page Keycloak (hors application) : 1) identifiant et mot de passe, 2) code TOTP.

États :
1. **Sans session** : l'écran s'affiche, l'application redirige vers Keycloak (F-01 : « une requête sans session est redirigée vers la connexion »).
2. **Retour de Keycloak** : échange du code (PKCE), puis écran d'accueil « Bonjour [nom d'affichage] » et bouton « Se déconnecter ».
3. **Session expirée (401)** : retour à l'état 1.
4. **MFA absent (403)** : message « Authentification à deux facteurs requise », bouton « Se déconnecter ».
5. **Fournisseur indisponible (503)** : message « Service d'identification indisponible », bouton « Réessayer ».

Messages : texte fixe par code d'erreur, jamais de détail technique (N-11).
