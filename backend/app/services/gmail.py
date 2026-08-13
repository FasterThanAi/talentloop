import base64
import logging
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_token, encrypt_token
from app.models import User

logger = logging.getLogger("talentloop.gmail")

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly"
]


def get_oauth_flow() -> Flow | None:
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET:
        return None

    client_config = {
        "web": {
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GMAIL_REDIRECT_URI]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.GMAIL_REDIRECT_URI,
        autogenerate_code_verifier=False
    )
    return flow


def generate_auth_url(state: str) -> str:
    flow = get_oauth_flow()
    if not flow:
        # Fallback mock auth URL for local dev without GCP credentials
        return f"http://127.0.0.1:8000/api/v1/auth/gmail/callback?code=mock_code&state={state}"

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state
    )
    return auth_url


def exchange_code_for_tokens(code: str, db: Session, user: User) -> bool:
    if code == "mock_code" or not settings.GMAIL_CLIENT_ID:
        user.gmail_refresh_token_encrypted = encrypt_token("mock_refresh_token_12345")
        user.gmail_email = user.email
        db.commit()
        return True

    flow = get_oauth_flow()
    if not flow:
        return False

    flow.fetch_token(code=code)
    credentials = flow.credentials

    if credentials.refresh_token:
        user.gmail_refresh_token_encrypted = encrypt_token(credentials.refresh_token)

    try:
        service = build("gmail", "v1", credentials=credentials)
        profile = service.users().getProfile(userId="me").execute()
        user.gmail_email = profile.get("emailAddress", user.email)
    except Exception as e:
        logger.warning(f"Could not fetch Gmail profile: {e}")
        user.gmail_email = user.email

    db.commit()
    return True


def get_gmail_service(user: User):
    if not user.gmail_refresh_token_encrypted:
        return None

    refresh_token = decrypt_token(user.gmail_refresh_token_encrypted)
    if refresh_token == "mock_refresh_token_12345" or not settings.GMAIL_CLIENT_ID:
        return None

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        scopes=GMAIL_SCOPES
    )
    return build("gmail", "v1", credentials=credentials)


def send_gmail_message(
    user: User,
    to_email: str,
    subject: str,
    body: str
) -> dict[str, Any]:
    """
    Sends an email via Gmail API using the recruiter's connected OAuth account.
    Falls back gracefully to simulated delivery in development/mock mode.
    """
    service = get_gmail_service(user)

    if not service:
        # Mock delivery for local demo / testing
        import uuid
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        logger.info(f"[SIMULATED GMAIL SEND] To: {to_email} | Subject: {subject} | ID: {msg_id}")
        return {"id": msg_id, "status": "sent", "simulated": True}

    message = MIMEText(body)
    message["to"] = to_email
    message["from"] = user.gmail_email or user.email
    message["subject"] = subject

    raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw_msg}).execute()
    return {"id": sent.get("id"), "status": "sent", "simulated": False}
