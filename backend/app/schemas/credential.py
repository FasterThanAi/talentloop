from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CredentialVerifyResponse(BaseModel):
    verified: bool
    payload_hash: str
    tx_hash: Optional[str] = None
    network: str = "polygon-amoy"
    issued_at: Optional[datetime] = None
    revoked: bool = False
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
