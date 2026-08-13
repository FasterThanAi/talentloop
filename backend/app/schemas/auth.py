from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class OrganizationOut(BaseModel):
    id: str
    name: str
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserRegister(BaseModel):
    # Optional: only employers belong to an organisation. A candidate registers as a person,
    # and the backend gives them a private workspace so tenancy stays uniform.
    org_name: str | None = None
    email: EmailStr
    password: str
    role: str = "recruiter"  # admin | recruiter | candidate


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    org_id: str
    email: str
    role: str
    gmail_email: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenData(BaseModel):
    user_id: str
    org_id: str
    role: str
    email: str
