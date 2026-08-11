from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import problem_detail_error
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models import Organization, User
from app.schemas.auth import UserLogin, UserOut, UserRegister


def register_user(db: Session, reg: UserRegister) -> tuple[User, str, str]:
    # Check if email already exists
    stmt = select(User).where(User.email == reg.email.lower())
    if db.execute(stmt).scalar_one_or_none():
        raise problem_detail_error(
            status_code=409,
            title="User already exists",
            detail=f"An account with email {reg.email} already exists.",
            code="USER_ALREADY_EXISTS"
        )

    # Create Organization
    org = Organization(
        name=reg.org_name,
        plan="standard"
    )
    db.add(org)
    db.flush()

    # Create User
    user = User(
        org_id=org.id,
        email=reg.email.lower(),
        password_hash=hash_password(reg.password),
        role=reg.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token_data = {"sub": user.id, "org_id": user.org_id, "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return user, access_token, refresh_token


def authenticate_user(db: Session, login: UserLogin) -> tuple[User, str, str]:
    stmt = select(User).where(User.email == login.email.lower())
    user = db.execute(stmt).scalar_one_or_none()

    if not user or not verify_password(login.password, user.password_hash):
        raise problem_detail_error(
            status_code=401,
            title="Invalid credentials",
            detail="Incorrect email or password.",
            code="INVALID_CREDENTIALS"
        )

    token_data = {"sub": user.id, "org_id": user.org_id, "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return user, access_token, refresh_token
