"""
Sign in with Google — AUTHENTICATION.

This is deliberately separate from `services/gmail.py`, which does AUTHORISATION: getting a
recruiter's permission to send mail on their behalf. They use the same Google OAuth client
but different scopes and different consequences:

    services/google_auth.py   openid, email, profile        "who are you?"      → issues our JWT
    services/gmail.py         gmail.send, gmail.readonly    "may we act as you?" → stores a refresh token

Keeping them apart matters: a candidate signing in should never be asked for mailbox access,
and a recruiter granting mailbox access should not have it conflated with logging in.
"""
from __future__ import annotations

import logging
import secrets
from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import problem_detail_error
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models import Organization, User

logger = logging.getLogger("talentloop.google_auth")

# Identity only. No mailbox scopes here — that consent is asked for separately, and only
# from recruiters, at the point they actually try to send something.
GOOGLE_SIGNIN_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def google_signin_configured() -> bool:
    return bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET)


def _client_config() -> dict[str, Any]:
    return {
        "web": {
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def build_signin_url(role: str = "candidate") -> tuple[str, str]:
    """
    Returns (authorization_url, state). The chosen account type rides along in `state`
    so the callback knows whether to provision a recruiter or a candidate.
    """
    if not google_signin_configured():
        raise problem_detail_error(
            status_code=503,
            title="Google sign-in not configured",
            detail="GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set to enable Google sign-in.",
            code="GOOGLE_SIGNIN_NOT_CONFIGURED",
        )

    role = role if role in ("recruiter", "candidate") else "candidate"
    nonce = secrets.token_urlsafe(16)
    state = f"{role}:{nonce}"

    flow = Flow.from_client_config(
        _client_config(),
        scopes=GOOGLE_SIGNIN_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        autogenerate_code_verifier=False,
    )
    auth_url, _ = flow.authorization_url(
        access_type="online",          # identity only — we are not storing a refresh token here
        include_granted_scopes="true",
        prompt="select_account",
        state=state,
    )
    return auth_url, state


def _verify_id_token(raw_id_token: str) -> dict[str, Any]:
    """Verify signature, issuer and audience. Never trust an unverified ID token."""
    try:
        claims = google_id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            settings.GMAIL_CLIENT_ID,
        )
    except Exception as e:
        raise problem_detail_error(
            status_code=401,
            title="Invalid Google token",
            detail=f"Could not verify the Google identity token: {e}",
            code="GOOGLE_TOKEN_INVALID",
        ) from e

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise problem_detail_error(
            status_code=401, title="Invalid issuer",
            detail="Identity token was not issued by Google.", code="GOOGLE_TOKEN_INVALID",
        )
    if not claims.get("email_verified"):
        raise problem_detail_error(
            status_code=403, title="Email not verified",
            detail="Your Google account email is not verified.", code="GOOGLE_EMAIL_UNVERIFIED",
        )
    return claims


def complete_signin(db: Session, code: str, state: str | None) -> tuple[User, str, str]:
    """
    Exchange the authorization code, verify the ID token, then find-or-create the user.
    Returns (user, access_token, refresh_token).
    """
    role = "candidate"
    if state and ":" in state:
        candidate_role = state.split(":", 1)[0]
        if candidate_role in ("recruiter", "candidate"):
            role = candidate_role

    flow = Flow.from_client_config(
        _client_config(),
        scopes=GOOGLE_SIGNIN_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        autogenerate_code_verifier=False,
    )
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.error(f"Google OAuth token exchange failed: {e}")
        raise problem_detail_error(
            status_code=400,
            title="Google token exchange failed",
            detail=f"Could not exchange authorization code with Google: {e}",
            code="GOOGLE_TOKEN_EXCHANGE_FAILED",
        ) from e

    raw_id_token = getattr(flow.credentials, "id_token", None)
    if not raw_id_token:
        raise problem_detail_error(
            status_code=401, title="No identity token",
            detail="Google did not return an identity token.", code="GOOGLE_TOKEN_MISSING",
        )

    claims = _verify_id_token(raw_id_token)
    email = claims["email"].lower()
    display_name = claims.get("name") or email.split("@")[0]

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None:
        # First sign-in: provision. Candidates get a private workspace rather than being
        # asked for a company they do not have.
        org_name = (
            f"Candidate workspace — {email}" if role == "candidate" else f"{display_name}'s organization"
        )
        org = Organization(name=org_name, plan="candidate" if role == "candidate" else "standard")
        db.add(org)
        db.flush()

        user = User(
            org_id=org.id,
            email=email,
            # No usable password: this account authenticates via Google only. A random
            # unguessable hash means the password login path can never match it.
            password_hash=hash_password(secrets.token_urlsafe(48)),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Provisioned %s account via Google sign-in: %s", role, email)
    else:
        logger.info("Google sign-in for existing user: %s", email)

    token_data = {"sub": user.id, "org_id": user.org_id, "role": user.role, "email": user.email}
    return user, create_access_token(token_data), create_refresh_token(token_data)
