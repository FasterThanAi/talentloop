from collections.abc import Callable
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import current_org_id_ctx, get_db
from app.core.security import decode_token
from app.models import User

security_scheme = HTTPBearer(auto_error=False)


def problem_detail_error(
    status_code: int,
    title: str,
    detail: str,
    code: str
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "type": "about:blank",
            "title": title,
            "status": status_code,
            "detail": detail,
            "code": code
        }
    )


async def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not auth or not auth.credentials:
        raise problem_detail_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Authentication required",
            detail="Missing or invalid Authorization header",
            code="UNAUTHORIZED"
        )
    try:
        payload = decode_token(auth.credentials)
        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            raise ValueError("Token missing subject identifier")
    except Exception as e:
        raise problem_detail_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Invalid token",
            detail=str(e),
            code="INVALID_TOKEN"
        )

    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()
    if not user:
        raise problem_detail_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="User not found",
            detail="The authenticated user no longer exists",
            code="USER_NOT_FOUND"
        )

    # Set context variable for tenancy
    current_org_id_ctx.set(user.org_id)
    return user


def require_scope(required_role: str) -> Callable:
    async def scope_checker(current_user: User = Depends(get_current_user)) -> User:
        # Admin can access all recruiter paths
        if required_role == "recruiter" and current_user.role in ("recruiter", "admin"):
            return current_user
        if required_role == "admin" and current_user.role == "admin":
            return current_user
        if required_role == "candidate" and current_user.role in ("candidate", "recruiter", "admin"):
            return current_user

        if current_user.role != required_role:
            raise problem_detail_error(
                status_code=status.HTTP_403_FORBIDDEN,
                title="Insufficient permissions",
                detail=f"Action requires role '{required_role}', current role is '{current_user.role}'",
                code="FORBIDDEN_SCOPE"
            )
        return current_user
    return scope_checker
