from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db, problem_detail_error
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models import User
from app.schemas.auth import Token, UserLogin, UserOut, UserRegister
from app.services.auth import authenticate_user, register_user
from app.services.gmail import exchange_code_for_tokens, generate_auth_url
from app.services.google_auth import build_signin_url, complete_signin, google_signin_configured

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(
    reg_data: UserRegister,
    response: Response,
    db: Session = Depends(get_db)
):
    user, access_token, refresh_token = register_user(db, reg_data)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=7 * 24 * 3600
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )


@router.post("/login", response_model=Token)
def login(
    login_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    user, access_token, refresh_token = authenticate_user(db, login_data)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=7 * 24 * 3600
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/refresh", response_model=Token)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Exchange the httpOnly refresh cookie for a new access token.

    Access tokens live 15 minutes. Without this endpoint the session simply died at the
    15-minute mark — /auth/me started returning 401 and the UI had no way to recover, which
    is exactly the failure you see mid-demo. The refresh token itself is rotated on every
    use so a stolen one has a short useful life.
    """
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise problem_detail_error(
            status_code=401, title="Not authenticated",
            detail="No refresh token cookie present. Sign in again.",
            code="REFRESH_TOKEN_MISSING",
        )

    try:
        claims = decode_token(raw)
    except ValueError as e:
        raise problem_detail_error(
            status_code=401, title="Invalid refresh token",
            detail=str(e), code="REFRESH_TOKEN_INVALID",
        ) from e

    if claims.get("type") != "refresh":
        # An access token must never be usable as a refresh token.
        raise problem_detail_error(
            status_code=401, title="Wrong token type",
            detail="That token is not a refresh token.", code="REFRESH_TOKEN_INVALID",
        )

    user = db.execute(select(User).where(User.id == claims.get("sub"))).scalar_one_or_none()
    if not user:
        raise problem_detail_error(
            status_code=401, title="User not found",
            detail="The account for this token no longer exists.",
            code="REFRESH_USER_NOT_FOUND",
        )

    token_data = {"sub": user.id, "org_id": user.org_id, "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=7 * 24 * 3600,
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
    )
    return {"ok": True}


# ─────────────────────────────────────────────────────────── Sign in with Google
# Identity, not mailbox access. See services/google_auth.py for why these are separate.

@router.get("/google/status")
def google_status():
    """Lets the frontend show or hide the Google button without guessing."""
    return {"enabled": google_signin_configured()}


@router.get("/google/login")
def google_login(role: str = Query("candidate", pattern="^(recruiter|candidate)$")):
    """Start the Google sign-in flow. The chosen account type rides along in `state`."""
    auth_url, state = build_signin_url(role=role)
    return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback")
def google_callback(
    response: Response,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    Google redirects here. We exchange the code, verify the ID token, find-or-create the
    user, then bounce back to the SPA with a short-lived access token in the URL fragment
    (fragments are not sent to servers or written to server logs). The refresh token goes
    into an httpOnly cookie, exactly as with password login.
    """
    if error:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={error}")
    if not code:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=missing_code")

    try:
        user, access_token, refresh_token = complete_signin(db=db, code=code, state=state)
    except HTTPException as e:
        detail_msg = e.detail.get("detail", str(e.detail)) if isinstance(e.detail, dict) else str(e.detail)
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={detail_msg}")
    except Exception as e:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={str(e)}")

    landing = "/portal" if user.role == "candidate" else "/requisitions"
    redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback#access_token={access_token}&next={landing}"
    )
    redirect.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        # Cross-site in production (Vercel SPA <- Render API), so samesite=none + secure.
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=7 * 24 * 3600,
    )
    return redirect


@router.get("/gmail/connect")
def connect_gmail(current_user: User = Depends(get_current_user)):
    auth_url = generate_auth_url(state=current_user.id)
    return {"auth_url": auth_url}


@router.get("/gmail/callback")
def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    from sqlalchemy import select
    user = db.execute(select(User).where(User.id == state)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User state not found")

    success = exchange_code_for_tokens(code=code, db=db, user=user)
    return {"connected": success, "email": user.gmail_email}
