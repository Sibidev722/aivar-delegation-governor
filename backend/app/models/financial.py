from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AccountInfo(BaseModel):
    account_id: str
    name: str
    balance: float
    currency: str = "USD"


class TransactionRecord(BaseModel):
    transaction_id: str
    date: str
    amount: float
    currency: str = "USD"
    type: str  # CREDIT | DEBIT
    category: str
    description: str


class CustomerFinancialRecord(BaseModel):
    customer_id: str = Field(json_schema_extra={"example": "CUST-101"})
    customer_name: str
    tier: str  # Enterprise | Mid-Market | Commercial
    industry: str
    accounts: List[AccountInfo]
    balances: Dict[str, float]
    transactions: List[TransactionRecord]
    income_ytd: float
    expenses_ytd: float
    summary: str
    metrics: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
