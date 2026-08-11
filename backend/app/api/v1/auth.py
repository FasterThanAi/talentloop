from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.auth import Token, UserLogin, UserOut, UserRegister
from app.services.auth import authenticate_user, register_user
from app.services.gmail import exchange_code_for_tokens, generate_auth_url

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
        samesite="strict",
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
        samesite="strict",
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
