from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.core.logging import logger
from app.core.exceptions import GovernanceException
from app.db.repository import FinancialRepository


from app.services.scope_engine import normalize_customer_id


class FinancialToolService:
    """
    Isolated Protected Financial Tool Service.
    CRITICAL SECURITY INVARIANT:
    This service is NEVER exposed directly as an API endpoint.
    It can ONLY be invoked internally by the Delegation Governor PEP after all policy and token checks pass.
    """

    @classmethod
    async def get_customer_record(cls, customer_id: str) -> Optional[Dict[str, Any]]:
        """Fetch customer financial summary from repository layer."""
        target_id = normalize_customer_id(customer_id)
        return await FinancialRepository.get_customer_financial_summary(target_id)

    @classmethod
    async def execute_operation(
        cls,
        operation: str,
        customer_id: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute requested financial operation against protected customer records.
        """
        op = operation.strip().upper()
        target_id = normalize_customer_id(customer_id)

        record = await cls.get_customer_record(target_id)
        if not record:
            raise GovernanceException(
                message=f"Customer record '{customer_id}' not found.",
                error_code="CUSTOMER_NOT_FOUND",
                status_code=404
            )

        if op == "READ_SUMMARY":
            return {
                "customer_id": record["customer_id"],
                "customer_name": record["customer_name"],
                "tier": record.get("tier", "STANDARD"),
                "industry": record.get("industry", "Professional"),
                "customer_segment": record.get("customer_segment", "SALARIED"),
                "city": record.get("city", "Mumbai"),
                "state": record.get("state", "Maharashtra"),
                "country": record.get("country", "India"),
                "annual_income": record.get("annual_income", 0.0),
                "monthly_income": record.get("monthly_income", 0.0),
                "accounts": record.get("accounts", []),
                "balances": record.get("balances", {}),
                "income_ytd": record.get("income_ytd", 0.0),
                "expenses_ytd": record.get("expenses_ytd", 0.0),
                "metrics": record.get("metrics", {}),
                "financial_health": record.get("financial_health", {}),
                "monthly_aggregations": record.get("monthly_aggregations", []),
                "transactions": record.get("transactions", []),
                "summary": record.get("summary", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        elif op == "READ_METRICS":
            return {
                "customer_id": record["customer_id"],
                "customer_name": record["customer_name"],
                "tier": record.get("tier", "STANDARD"),
                "customer_segment": record.get("customer_segment", "SALARIED"),
                "metrics": record.get("metrics", {}),
                "financial_health": record.get("financial_health", {}),
                "monthly_aggregations": record.get("monthly_aggregations", []),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        elif op == "READ_FINANCIALS":
            result = dict(record)
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            return result

        elif op == "WRITE_RECORD":
            if not payload:
                raise GovernanceException(
                    message="Write operation requires a valid payload dictionary.",
                    error_code="MISSING_WRITE_PAYLOAD",
                    status_code=400
                )

            from app.db.session import DatabaseSession
            db = DatabaseSession.get_db()
            if db is not None:
                try:
                    await db["financial_records"].update_one(
                        {"customer_id": target_id},
                        {"$set": {"summary": payload.get("summary", record.get("summary", "")), "updated_at": datetime.now(timezone.utc)}}
                    )
                except Exception as e:
                    logger.error(f"Error updating customer record in DB: {e}")

            return {
                "customer_id": target_id,
                "status": "RECORD_UPDATED",
                "updated_fields": list(payload.keys()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        else:
            raise GovernanceException(
                message=f"Unsupported tool operation '{operation}'.",
                error_code="UNSUPPORTED_TOOL_OPERATION",
                status_code=400
            )
