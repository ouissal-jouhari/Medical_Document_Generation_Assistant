"""Vérification de bout en bout de F-01 sur la pile Docker Compose démarrée (jalon 2).

1. Connexion réelle (PKCE), mot de passe puis TOTP : jeton acr=2, l'API répond 200.
2. Connexion mono-facteur (niveau 1 demandé) : jeton acr=1, l'API répond 403 mfa_required.
3. Jalon 3 : dépôt authentifié de l'Annexe A (état parsed), refus d'un fichier hors limite par
   l'API (413 file_too_large) et par Caddy (413), sans consultation créée.

Variables d'environnement : BASE_URL (défaut https://localhost), KC_TEST_USER_PASSWORD,
KC_TEST_USER_TOTP_SECRET (secret brut, comme dans le realm importé).
"""

import base64
import hashlib
import hmac
import html
import json
import os
import re
import struct
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

BASE = os.environ.get("BASE_URL", "https://localhost")
PASSWORD = os.environ["KC_TEST_USER_PASSWORD"]
RAW_SECRET = os.environ["KC_TEST_USER_TOTP_SECRET"].encode()
CLIENT = "xeleron-web"
FIXTURES = Path(__file__).resolve().parents[1] / "backend" / "tests" / "fixtures" / "superbills"
OIDC = f"{BASE}/auth/realms/xeleron/protocol/openid-connect"


def totp(secret: bytes) -> str:
    digest = hmac.new(secret, struct.pack(">Q", int(time.time()) // 30), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 10**6
    return f"{value:06d}"


def form_action(page: str) -> str:
    match = re.search(r'<form[^>]*action="([^"]+)"', page)
    if not match:
        raise SystemExit("formulaire Keycloak introuvable")
    return html.unescape(match.group(1))


def login(acr_values: str, with_otp: bool) -> dict[str, object]:
    verifier = base64.urlsafe_b64encode(os.urandom(48)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode()
    with httpx.Client(verify=False, timeout=30) as client:  # noqa: S501 - certificat interne Caddy
        page = client.get(
            f"{OIDC}/auth",
            params={
                "client_id": CLIENT,
                "redirect_uri": f"{BASE}/",
                "response_type": "code",
                "scope": "openid profile",
                "code_challenge": challenge.rstrip("="),
                "code_challenge_method": "S256",
                "acr_values": acr_values,
                "state": "check",
            },
            follow_redirects=True,
        )
        response = client.post(
            form_action(page.text), data={"username": "clinicien-test", "password": PASSWORD}
        )
        if with_otp:
            if 'name="otp"' not in response.text:
                raise SystemExit("le second facteur n'a pas été demandé")
            response = client.post(form_action(response.text), data={"otp": totp(RAW_SECRET)})
        if response.status_code != 302:
            raise SystemExit(f"connexion refusée (HTTP {response.status_code})")
        code = parse_qs(urlparse(response.headers["location"]).query)["code"][0]
        token = client.post(
            f"{OIDC}/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT,
                "code": code,
                "redirect_uri": f"{BASE}/",
                "code_verifier": verifier,
            },
        ).json()["access_token"]
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        me = client.get(f"{BASE}/api/me", headers={"Authorization": f"Bearer {token}"})
        return {
            "acr": claims.get("acr"),
            "status": me.status_code,
            "body": me.json(),
            "token": token,
        }


def check(condition: bool, result: object, requirement: str = "F-01") -> None:
    if not condition:
        raise SystemExit(f"ÉCHEC {requirement} : {result}")


def check_superbill_upload(token: str) -> None:
    """Jalon 3 sur la vraie pile : dépôt de l'Annexe A, puis limites de taille (Caddy et API)."""
    sample = FIXTURES / "annex_a_sample.pdf"
    auth = {"Authorization": f"Bearer {token}"}
    # Certificat interne de Caddy : la vérification TLS est volontairement désactivée.
    with httpx.Client(verify=False, timeout=300) as client:  # noqa: S501
        response = client.post(
            f"{BASE}/api/consultations",
            files={"file": ("a.pdf", sample.read_bytes())},
            headers=auth,
        )
        body = response.json()
        patient = (body.get("data") or {}).get("patient") or {}
        check(
            response.status_code == 201
            and body.get("state") == "parsed"
            and patient.get("fullName") == "Marcus Ellery Thorne",
            {"status": response.status_code, "state": body.get("state")},
            "F-04",
        )
        listing = client.get(f"{BASE}/api/consultations", headers=auth)
        check(any(row["id"] == body["id"] for row in listing.json()), listing.status_code, "F-25")
        before = len(listing.json())
        # Entre la limite de l'API (50 Mio) et celle de Caddy (51 Mio) : refus par l'API.
        api_limit = client.post(
            f"{BASE}/api/consultations",
            files={"file": ("big.pdf", b"%PDF-" + b"0" * 52_900_000)},
            headers=auth,
        )
        check(
            api_limit.status_code == 413 and api_limit.json() == {"detail": "file_too_large"},
            api_limit.status_code,
            "F-03 (API)",
        )
        # Au-delà de la limite de Caddy : refus avant même d'atteindre l'API.
        caddy_limit = client.post(
            f"{BASE}/api/consultations",
            files={"file": ("big.pdf", b"%PDF-" + b"0" * 56_000_000)},
            headers=auth,
        )
        check(caddy_limit.status_code == 413, caddy_limit.status_code, "F-03 (Caddy)")
        after = client.get(f"{BASE}/api/consultations", headers=auth).json()
        check(len(after) == before, "une consultation a été créée par un fichier refusé", "F-03")


def main() -> None:
    mfa = login("2", with_otp=True)
    check(mfa["acr"] == "2" and mfa["status"] == 200, mfa)
    single = login("1", with_otp=False)
    check(single["acr"] == "1", single)
    check(single["status"] == 403 and single["body"] == {"detail": "mfa_required"}, single)
    print("F-01 OK : MFA -> 200 (acr=2) ; mono-facteur -> 403 mfa_required (acr=1)")
    check_superbill_upload(str(mfa["token"]))
    print("Jalon 3 OK : Annexe A extraite (parsed), limites de taille refusées (API et Caddy)")


if __name__ == "__main__":
    main()
