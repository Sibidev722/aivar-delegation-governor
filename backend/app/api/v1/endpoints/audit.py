from typing import List
from fastapi import APIRouter, HTTPException, status
from app.models.audit import AuditLogEntry, ChainVerificationResult
from app.services.audit_service import AuditService

router = APIRouter()


@router.get(
    "/chain/{chain_id}",
    response_model=List[AuditLogEntry],
    summary="Get Audit Ledger Chain",
    description="Returns the complete chronological list of tamper-evident audit events for a correlation chain."
)
async def get_audit_chain(chain_id: str) -> List[AuditLogEntry]:
    events = await AuditService.get_chain(chain_id)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit records found for chain_id '{chain_id}'"
        )
    return events


@router.get(
    "/verify/{chain_id}",
    response_model=ChainVerificationResult,
    summary="Verify Audit Ledger Integrity",
    description=(
        "Cryptographically verifies the Tamper-Evident Hash-Chained Audit Ledger for a chain. "
        "Validates sequence continuity, backward hash pointers, and recomputes canonical event hashes."
    )
)
async def verify_audit_chain(chain_id: str) -> ChainVerificationResult:
    result = await AuditService.verify_chain(chain_id)
    return result
