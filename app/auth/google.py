from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import urlopen

from app.config.env import load_dotenv_file

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo?id_token={token}"
GOOGLE_CLIENT_IDS_ENV_VAR = "GOOGLE_OAUTH_CLIENT_IDS"


class GoogleIdentityTokenError(ValueError):
    pass


class GoogleAuthConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    display_name: str | None
    audience: str


def verify_google_identity_token(identity_token: str) -> GoogleIdentity:
    token = identity_token.strip()
    if not token:
        raise GoogleIdentityTokenError("identity_token is required")

    try:
        with urlopen(
            GOOGLE_TOKENINFO_URL.format(token=quote_plus(token)),
            timeout=10,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise GoogleIdentityTokenError("google identity token is invalid") from error
    except URLError as error:
        raise GoogleIdentityTokenError(
            "google identity token verification is unavailable"
        ) from error

    return _validate_tokeninfo_payload(payload)


def configured_google_client_ids() -> tuple[str, ...]:
    load_dotenv_file()
    raw = os.getenv(GOOGLE_CLIENT_IDS_ENV_VAR, "")
    values = tuple(value.strip() for value in raw.split(",") if value.strip())
    if not values:
        raise GoogleAuthConfigurationError(
            f"{GOOGLE_CLIENT_IDS_ENV_VAR} must list at least one allowed client id"
        )
    return values


def _validate_tokeninfo_payload(payload: dict[str, Any]) -> GoogleIdentity:
    audience = str(payload.get("aud", "")).strip()
    if not audience:
        raise GoogleIdentityTokenError("google identity token is missing aud")
    if audience not in configured_google_client_ids():
        raise GoogleIdentityTokenError("google identity token has unexpected aud")

    subject = str(payload.get("sub", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    if not subject or not email:
        raise GoogleIdentityTokenError(
            "google identity token is missing subject or email"
        )

    if str(payload.get("email_verified", "")).lower() != "true":
        raise GoogleIdentityTokenError("google identity token email is not verified")

    return GoogleIdentity(
        subject=subject,
        email=email,
        display_name=str(payload.get("name")).strip() or None
        if payload.get("name") is not None
        else None,
        audience=audience,
    )
