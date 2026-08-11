from app.schemas.credential import CredentialVerifyResponse
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.credential import verify_credential

router = APIRouter(prefix="/credentials", tags=["Credentials"])


@router.get("/{hash}/verify", response_model=CredentialVerifyResponse)
def verify_credential_endpoint(
    hash: str,
    db: Session = Depends(get_db)
):
    """
    Public unauthenticated endpoint to verify authenticity of a feedback report credential hash.
    """
    result = verify_credential(db=db, payload_hash=hash)
    return CredentialVerifyResponse(**result)
