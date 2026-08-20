"""
Financial Data Repository.
Provides clean async data access routines for customers, accounts,
transactions, and financial metrics stored in MongoDB with BSON sanitization.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from pymongo import DESCENDING
from app.db.session import DatabaseSession
from app.core.logging import logger
from app.services.scope_engine import normalize_customer_id


def sanitize_bson(obj: Any) -> Any:
    """Recursively strip MongoDB _id fields and convert BSON ObjectIds to strings."""
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if k == "_id":
                continue
            res[k] = sanitize_bson(v)
        return res
    elif isinstance(obj, list):
        return [sanitize_bson(x) for x in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj


class FinancialRepository:
    """
    Data access layer for financial collections.
    Encapsulates all direct MongoDB queries with automatic customer_id normalization and BSON sanitization.
    """

    @classmethod
    async def get_customer_by_id(cls, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve core customer profile document by customer_id."""
        db = DatabaseSession.get_db()
        if db is None:
            return None
        target_id = normalize_customer_id(customer_id)
        doc = await db["customers"].find_one(
            {"$or": [{"customer_id": target_id}, {"customer_id": customer_id.strip().upper()}]},
            {"_id": 0}
        )
        return sanitize_bson(doc) if doc else None

    @classmethod
    async def get_customer_accounts(cls, customer_id: str) -> List[Dict[str, Any]]:
        """Retrieve all active financial accounts belonging to a customer."""
        db = DatabaseSession.get_db()
        if db is None:
            return []
        target_id = normalize_customer_id(customer_id)
        cursor = db["accounts"].find(
            {"$or": [{"customer_id": target_id}, {"customer_id": customer_id.strip().upper()}]},
            {"_id": 0}
        )
        raw_list = await cursor.to_list(length=20)
        return sanitize_bson(raw_list)

    @classmethod
    async def get_customer_transactions(
        cls,
        customer_id: str,
        limit: int = 150,
        account_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve customer transactions ordered chronologically descending."""
        db = DatabaseSession.get_db()
        if db is None:
            return []
        target_id = normalize_customer_id(customer_id)
        query: Dict[str, Any] = {
            "$or": [{"customer_id": target_id}, {"customer_id": customer_id.strip().upper()}]
        }
        if account_id:
            query["account_id"] = account_id.strip()

        cursor = db["transactions"].find(query, {"_id": 0}).sort("transaction_date", DESCENDING).limit(limit)
        raw_list = await cursor.to_list(length=limit)
        return sanitize_bson(raw_list)

    @classmethod
    async def get_customer_financial_metrics(cls, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve pre-aggregated deterministic financial metrics and health scores."""
        db = DatabaseSession.get_db()
        if db is None:
            return None
        target_id = normalize_customer_id(customer_id)
        doc = await db["financial_metrics"].find_one(
            {"$or": [{"customer_id": target_id}, {"customer_id": customer_id.strip().upper()}]},
            {"_id": 0}
        )
        return sanitize_bson(doc) if doc else None

    @classmethod
    async def get_customer_financial_summary(cls, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve unified customer financial record combining customer profile,
        accounts, recent transactions, and computed metrics.
        """
        db = DatabaseSession.get_db()
        target_id = normalize_customer_id(customer_id)

        # 1. First check dedicated denormalized cache if present
        if db is not None:
            cached = await db["financial_records"].find_one(
                {"$or": [{"customer_id": target_id}, {"customer_id": customer_id.strip().upper()}]},
                {"_id": 0}
            )
            if cached:
                return sanitize_bson(cached)

        # 2. Reconstruct from relational collections
        customer = await cls.get_customer_by_id(target_id)
        if not customer:
            return None

        accounts = await cls.get_customer_accounts(target_id)
        transactions = await cls.get_customer_transactions(target_id, limit=50)
        metrics = await cls.get_customer_financial_metrics(target_id)

        balances = {}
        for acc in accounts:
            acc_type_key = acc.get("account_type", "other").lower()
            balances[acc_type_key] = acc.get("current_balance", 0.0)

        total_cash = sum(
            acc.get("current_balance", 0.0)
            for acc in accounts
            if acc.get("account_type") in ["CHECKING", "SAVINGS", "INVESTMENT"]
        )
        balances["total_cash"] = round(total_cash, 2)

        res = {
            "customer_id": customer["customer_id"],
            "customer_name": customer["customer_name"],
            "tier": customer.get("customer_tier", "STANDARD"),
            "industry": customer.get("occupation", "Professional"),
            "customer_segment": customer.get("customer_segment", "SALARIED"),
            "city": customer.get("city", "Mumbai"),
            "state": customer.get("state", "Maharashtra"),
            "country": customer.get("country", "India"),
            "annual_income": customer.get("annual_income", 0.0),
            "monthly_income": customer.get("monthly_income", 0.0),
            "accounts": accounts,
            "balances": balances,
            "income_ytd": metrics.get("income_ytd", 0.0) if metrics else 0.0,
            "expenses_ytd": metrics.get("expenses_ytd", 0.0) if metrics else 0.0,
            "metrics": metrics.get("summary_metrics", {}) if metrics else {},
            "financial_health": metrics.get("financial_health", {}) if metrics else {},
            "monthly_aggregations": metrics.get("monthly_aggregations", []) if metrics else [],
            "transactions": transactions[:10],
            "summary": (
                f"{customer['customer_name']} ({customer.get('customer_segment', 'SALARIED')}, {customer.get('city', 'India')}) "
                f"holds {len(accounts)} accounts with total assets of INR {total_cash:,.2f}. "
                f"Annual income is INR {customer.get('annual_income', 0):,.2f} with {metrics.get('summary_metrics', {}).get('runway_months', 6.0) if metrics else 6.0} months runway."
            ),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return sanitize_bson(res)
