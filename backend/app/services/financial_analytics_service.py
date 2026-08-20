"""
Financial Analytics & Aggregation Service.
Performs deterministic, explainable financial health and metrics calculations
from customer transaction streams. (Zero LLM numerical hallucination).
"""
from typing import Any, Dict, List, Tuple
from collections import defaultdict


class FinancialAnalyticsService:
    """
    Service for calculating deterministic financial KPIs and monthly aggregations.
    """

    @classmethod
    def calculate_monthly_aggregations(cls, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group transactions by YYYY-MM and calculate income, expenses, savings, and count.
        """
        monthly_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "income": 0.0,
            "expenses": 0.0,
            "savings": 0.0,
            "transaction_count": 0
        })

        for tx in transactions:
            tx_date = str(tx.get("transaction_date", ""))
            month_key = tx_date[:7] if len(tx_date) >= 7 else "2026-01"
            amount = float(tx.get("amount", 0.0))
            tx_type = tx.get("transaction_type", "EXPENSE")

            entry = monthly_map[month_key]
            entry["transaction_count"] += 1

            if tx_type == "INCOME":
                entry["income"] += amount
            elif tx_type == "EXPENSE":
                entry["expenses"] += amount
            elif tx_type == "INVESTMENT":
                entry["savings"] += amount

        results = []
        for month in sorted(monthly_map.keys()):
            data = monthly_map[month]
            inc = round(data["income"], 2)
            exp = round(data["expenses"], 2)
            sav = round(inc - exp, 2)
            results.append({
                "month": month,
                "income": inc,
                "expenses": exp,
                "savings": sav,
                "transaction_count": data["transaction_count"]
            })

        return results

    @classmethod
    def calculate_summary_metrics(
        cls,
        customer: Dict[str, Any],
        accounts: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate key financial KPIs across customer accounts and transactions.
        """
        total_assets = 0.0
        total_liabilities = 0.0
        credit_limit_total = 0.0
        credit_card_balance = 0.0
        loan_balance = 0.0
        investment_value = 0.0

        for acc in accounts:
            acc_type = acc.get("account_type", "")
            curr_bal = float(acc.get("current_balance", 0.0))

            if acc_type in ["CHECKING", "SAVINGS"]:
                total_assets += curr_bal
            elif acc_type == "INVESTMENT":
                total_assets += curr_bal
                investment_value += curr_bal
            elif acc_type == "CREDIT_CARD":
                total_liabilities += curr_bal
                credit_card_balance += curr_bal
                credit_limit_total += float(acc.get("credit_limit", 0.0))
            elif acc_type == "LOAN":
                total_liabilities += curr_bal
                loan_balance += curr_bal

        net_worth = round(total_assets - total_liabilities, 2)

        # Transaction Aggregations
        income_txs = [t for t in transactions if t.get("transaction_type") == "INCOME"]
        expense_txs = [t for t in transactions if t.get("transaction_type") == "EXPENSE"]

        total_income = sum(float(t.get("amount", 0.0)) for t in income_txs)
        total_expenses = sum(float(t.get("amount", 0.0)) for t in expense_txs)

        num_months = max(1, len(set(str(t.get("transaction_date", ""))[:7] for t in transactions)))
        avg_monthly_income = round(total_income / num_months, 2) if total_income > 0 else float(customer.get("monthly_income", 50000.0))
        avg_monthly_expenses = round(total_expenses / num_months, 2) if total_expenses > 0 else 30000.0
        monthly_savings = round(avg_monthly_income - avg_monthly_expenses, 2)

        savings_rate = round((monthly_savings / avg_monthly_income) * 100.0, 1) if avg_monthly_income > 0 else 0.0
        monthly_burn_rate = avg_monthly_expenses
        runway_months = round(total_assets / monthly_burn_rate, 1) if monthly_burn_rate > 0 else 24.0

        largest_income = max((float(t.get("amount", 0.0)) for t in income_txs), default=0.0)
        largest_expense = max((float(t.get("amount", 0.0)) for t in expense_txs), default=0.0)
        avg_tx_amount = round(sum(float(t.get("amount", 0.0)) for t in transactions) / max(1, len(transactions)), 2)

        credit_utilization = round((credit_card_balance / credit_limit_total) * 100.0, 1) if credit_limit_total > 0 else 0.0

        # Category spending breakdown
        category_counts: Dict[str, float] = defaultdict(float)
        for t in expense_txs:
            category_counts[t.get("category", "OTHER")] += float(t.get("amount", 0.0))

        top_categories = sorted(
            [{"category": cat, "total_amount": round(amt, 2)} for cat, amt in category_counts.items()],
            key=lambda x: x["total_amount"],
            reverse=True
        )[:5]

        return {
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "net_worth": net_worth,
            "monthly_income": avg_monthly_income,
            "monthly_expenses": avg_monthly_expenses,
            "monthly_savings": monthly_savings,
            "savings_rate_pct": savings_rate,
            "monthly_burn_rate": monthly_burn_rate,
            "runway_months": runway_months,
            "credit_utilization_pct": credit_utilization,
            "loan_balance": round(loan_balance, 2),
            "investment_value": round(investment_value, 2),
            "transaction_count": len(transactions),
            "average_transaction_amount": avg_tx_amount,
            "largest_income": round(largest_income, 2),
            "largest_expense": round(largest_expense, 2),
            "top_spending_categories": top_categories,
            "credit_score": customer.get("credit_score", 750)
        }

    @classmethod
    def calculate_financial_health(
        cls,
        summary_metrics: Dict[str, Any],
        customer_segment: str
    ) -> Dict[str, Any]:
        """
        Compute explainable financial health scores (0-100) across 4 pillars.
        """
        # 1. Savings Score (0-100)
        sav_rate = summary_metrics.get("savings_rate_pct", 0.0)
        if sav_rate >= 30.0:
            savings_score = 95
        elif sav_rate >= 20.0:
            savings_score = 80
        elif sav_rate >= 10.0:
            savings_score = 65
        elif sav_rate >= 0.0:
            savings_score = 50
        else:
            savings_score = 30

        # 2. Debt / Leverage Score (0-100)
        cred_util = summary_metrics.get("credit_utilization_pct", 0.0)
        if cred_util <= 15.0:
            debt_score = 95
        elif cred_util <= 30.0:
            debt_score = 85
        elif cred_util <= 50.0:
            debt_score = 65
        elif cred_util <= 75.0:
            debt_score = 45
        else:
            debt_score = 25

        # 3. Liquidity Score (0-100)
        runway = summary_metrics.get("runway_months", 1.0)
        if runway >= 12.0:
            liquidity_score = 95
        elif runway >= 6.0:
            liquidity_score = 80
        elif runway >= 3.0:
            liquidity_score = 60
        else:
            liquidity_score = 35

        # 4. Spending Stability Score (0-100)
        if summary_metrics.get("monthly_savings", 0.0) > 0:
            spending_score = 85
        else:
            spending_score = 40

        # Composite Overall Score (Weighted)
        overall_score = round(
            (savings_score * 0.30) +
            (debt_score * 0.25) +
            (liquidity_score * 0.25) +
            (spending_score * 0.20)
        )

        grade = (
            "EXCELLENT" if overall_score >= 85 else
            "HEALTHY" if overall_score >= 70 else
            "FAIR" if overall_score >= 50 else
            "NEEDS_ATTENTION"
        )

        return {
            "financial_health_score": overall_score,
            "grade": grade,
            "savings_score": savings_score,
            "debt_score": debt_score,
            "liquidity_score": liquidity_score,
            "spending_score": spending_score
        }
