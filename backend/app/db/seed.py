"""
Large-Scale Realistic Synthetic Financial Dataset Generator.
Generates 500 relational customers, ~1,250 accounts, and ~50,000+ transactions
in an Indian financial context with strictly deterministic calculations (seed 42).
"""
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
from pymongo import ReplaceOne

from app.core.logging import logger
from app.db.session import DatabaseSession
from app.services.financial_analytics_service import FinancialAnalyticsService

# Configuration
SEED_CUSTOMERS = int(os.environ.get("SEED_CUSTOMERS", 500))
SEED_MIN_TRANSACTIONS = int(os.environ.get("SEED_MIN_TRANSACTIONS", 50))
SEED_MAX_TRANSACTIONS = int(os.environ.get("SEED_MAX_TRANSACTIONS", 150))

# Synthetic Name Components
FIRST_NAMES = [
    "Aarav", "Aditi", "Ajay", "Akash", "Ananya", "Anil", "Anjali", "Arjun", "Deepak", "Divya",
    "Gaurav", "Harish", "Ishaan", "Kavya", "Karthik", "Madhav", "Manish", "Meera", "Neha", "Nikhil",
    "Pooja", "Pranav", "Priya", "Rahul", "Rajesh", "Ravi", "Riya", "Rohan", "Sanjay", "Shreya",
    "Siddharth", "Sneha", "Sunil", "Suresh", "Tanvi", "Varun", "Vikas", "Vikram", "Yash", "Zoya",
    "Aditya", "Bhavna", "Chirag", "Deepika", "Esha", "Farhan", "Gayatri", "Hemant", "Indira", "Jatin"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Rao", "Gupta", "Deshmukh", "Joshi",
    "Kulkarni", "Mehta", "Singh", "Kumar", "Chatterjee", "Banerjee", "Bose", "Menon", "Pillai", "Chopra",
    "Kapoor", "Bhat", "Hegde", "Shetty", "Agarwal", "Mishra", "Pandey", "Saxena", "Malhotra", "Dewan",
    "Sengupta", "Mukherjee", "Das", "Dutta", "Goswami", "Choudhury", "Bhattacharya", "Sinha", "Ghosh", "Patil"
]

CITIES_STATE_MAP = [
    ("Bengaluru", "Karnataka"),
    ("Chennai", "Tamil Nadu"),
    ("Mumbai", "Maharashtra"),
    ("Hyderabad", "Telangana"),
    ("Pune", "Maharashtra"),
    ("Delhi", "Delhi"),
    ("Kolkata", "West Bengal"),
    ("Coimbatore", "Tamil Nadu"),
    ("Kochi", "Kerala"),
    ("Ahmedabad", "Gujarat")
]

SEGMENT_PROFILES = {
    "SALARIED": {
        "weight": 0.40,
        "income_range": (350000, 2400000),
        "occupations": ["Software Engineer", "Systems Architect", "Financial Analyst", "Operations Manager", "Product Specialist"],
        "credit_score_range": (720, 840),
        "employment": "Full-Time Salaried"
    },
    "PROFESSIONAL": {
        "weight": 0.20,
        "income_range": (800000, 4500000),
        "occupations": ["Physician", "Chartered Accountant", "Corporate Legal Counsel", "Management Consultant", "Architect"],
        "credit_score_range": (750, 870),
        "employment": "Licensed Professional"
    },
    "BUSINESS_OWNER": {
        "weight": 0.15,
        "income_range": (1200000, 9500000),
        "occupations": ["Enterprise Proprietor", "Export Logistics Director", "Manufacturing Founder", "Retail Franchisee"],
        "credit_score_range": (700, 860),
        "employment": "Business Owner"
    },
    "SELF_EMPLOYED": {
        "weight": 0.12,
        "income_range": (300000, 1800000),
        "occupations": ["Independent Tech Contractor", "Digital Media Producer", "Commercial Designer", "Consultant"],
        "credit_score_range": (670, 790),
        "employment": "Self-Employed"
    },
    "RETIRED": {
        "weight": 0.08,
        "income_range": (250000, 900000),
        "occupations": ["Former Public Sector Officer", "Retired Professor", "Retired Bank Executive"],
        "credit_score_range": (760, 850),
        "employment": "Retired"
    },
    "STUDENT": {
        "weight": 0.05,
        "income_range": (60000, 240000),
        "occupations": ["Graduate Research Scholar", "University Student", "Technical Intern"],
        "credit_score_range": (640, 730),
        "employment": "Student / Scholar"
    }
}

MERCHANTS_BY_CATEGORY = {
    "GROCERIES": ["Reliance Fresh", "BigBasket India", "Zepto Supermarket", "Nature's Basket", "Blinkit Retail", "D-Mart Hypermarket"],
    "DINING": ["Zomato Food Delivery", "Swiggy Gourmet", "Saravana Bhavan", "Mainland China Restaurant", "Barbeque Nation", "Haldiram's Sweets"],
    "UTILITIES": ["BESCOM Electricity", "Tata Power Energy", "Mahanagar Gas Limited", "Airtel Broadband Fiber", "Jio Infocomm Telecom", "Delhi Jal Board"],
    "FUEL": ["Indian Oil Corporation", "Bharat Petroleum Fuel", "Hindustan Petroleum Corporation", "Shell Fuel Station"],
    "SHOPPING": ["Flipkart India", "Amazon India Marketplace", "Myntra Fashion", "Tata CLiQ Luxury", "Croma Electronics", "Titan World"],
    "HEALTHCARE": ["Apollo Pharmacy", "MedPlus Diagnostics", "Manipal Hospital Network", "Max Healthcare Clinic", "Fortis Healthcare Care"],
    "EDUCATION": ["Coursera Global Learning", "Unacademy Learning Platform", "School Tuition Fee", "University Semester Fee", "Simplilearn Upskilling"],
    "ENTERTAINMENT": ["BookMyShow Cinema", "PVR Cinemas Multiplex", "Netflix India Stream", "Hotstar Premium OTT", "Spotify India Music"],
    "TRAVEL": ["MakeMyTrip Aviation", "IRCTC Indian Railways", "IndiGo Airlines Flight", "Uber India Mobility", "Ola Cabs Urban"],
    "INSURANCE": ["HDFC Life Insurance", "ICICI Lombard Health", "Star Health Allied Insurance", "SBI Life Shield"],
    "SUBSCRIPTION": ["Amazon Prime India", "Google One Storage", "Apple One Subscription", "Microsoft 365 Personal"],
    "SALARY": ["Corporate Direct Payroll", "Enterprise Salary Disbursement", "Tech Systems Monthly Wage"],
    "DIVIDEND": ["TCS Equity Dividend", "Infosys Limited Dividend", "Reliance Industries Dividend", "HDFC Bank Share Dividend"],
    "MUTUAL_FUND": ["SBI Bluechip Mutual Fund", "HDFC Flexi Cap Fund", "Mirae Asset Large Cap", "Zerodha AMC Equity Fund"],
    "FD_DEPOSIT": ["HDFC Bank Fixed Deposit", "ICICI Bank Term Deposit", "SBI Term Certificate Deposit"]
}


def generate_synthetic_dataset(
    num_customers: int = SEED_CUSTOMERS,
    min_tx: int = SEED_MIN_TRANSACTIONS,
    max_tx: int = SEED_MAX_TRANSACTIONS
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generate deterministic, relational synthetic financial dataset (seed 42).
    Returns: (customers, accounts, transactions, metrics, denormalized_records)
    """
    random.seed(42)

    customers_list: List[Dict[str, Any]] = []
    accounts_list: List[Dict[str, Any]] = []
    transactions_list: List[Dict[str, Any]] = []
    metrics_list: List[Dict[str, Any]] = []
    denormalized_records: List[Dict[str, Any]] = []

    # Historical date window: 2025-08-01 to 2026-08-15
    start_date = datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(2026, 8, 15, 0, 0, 0, tzinfo=timezone.utc)
    total_days = (end_date - start_date).days

    segments = list(SEGMENT_PROFILES.keys())
    segment_weights = [SEGMENT_PROFILES[s]["weight"] for s in segments]

    for i in range(1, num_customers + 1):
        cust_id = f"CUST-{i:04d}"
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"

        segment = random.choices(segments, weights=segment_weights, k=1)[0]
        profile = SEGMENT_PROFILES[segment]

        city, state = random.choice(CITIES_STATE_MAP)
        occupation = random.choice(profile["occupations"])
        employment_status = profile["employment"]

        annual_income = round(random.uniform(*profile["income_range"]), -3)
        monthly_income = round(annual_income / 12.0, 2)
        credit_score = random.randint(*profile["credit_score_range"])

        # Determine Customer Tier based on income & score
        if annual_income >= 3500000 and credit_score >= 800:
            tier = "PLATINUM"
        elif annual_income >= 1800000 and credit_score >= 750:
            tier = "GOLD"
        elif annual_income >= 800000 or credit_score >= 720:
            tier = "PREMIUM"
        else:
            tier = "STANDARD"

        risk_profile = (
            "AGGRESSIVE" if segment in ["BUSINESS_OWNER", "SELF_EMPLOYED"] and tier in ["GOLD", "PLATINUM"] else
            "CONSERVATIVE" if segment in ["RETIRED", "STUDENT"] else
            "MODERATE"
        )

        customer_since_year = random.randint(2018, 2024)
        customer_since_month = random.randint(1, 12)
        customer_since_day = random.randint(1, 28)
        customer_since = datetime(customer_since_year, customer_since_month, customer_since_day, tzinfo=timezone.utc)

        age = random.randint(20, 26) if segment == "STUDENT" else random.randint(62, 78) if segment == "RETIRED" else random.randint(25, 58)

        customer_doc = {
            "customer_id": cust_id,
            "customer_name": full_name,
            "customer_tier": tier,
            "customer_segment": segment,
            "age": age,
            "city": city,
            "state": state,
            "country": "India",
            "occupation": occupation,
            "employment_status": employment_status,
            "annual_income": annual_income,
            "monthly_income": monthly_income,
            "credit_score": credit_score,
            "risk_profile": risk_profile,
            "customer_since": customer_since.strftime("%Y-%m-%d"),
            "created_at": customer_since,
            "updated_at": datetime(2026, 8, 15, tzinfo=timezone.utc)
        }
        customers_list.append(customer_doc)

        # -------------------------------------------------------------
        # Generate 1–4 Accounts for Customer
        # -------------------------------------------------------------
        customer_accounts = []

        # Account 1: Always Primary Savings / Checking
        acc1_type = "SAVINGS" if segment in ["STUDENT", "RETIRED", "SALARIED"] else "CHECKING"
        acc1_num = f"XXXX-XXXX-{random.randint(1000, 9999)}"
        acc1_opening = round(random.uniform(25000, max(50000, monthly_income * 2)), 2)
        acc1_id = f"ACC-{i:04d}-01"
        account1 = {
            "account_id": acc1_id,
            "customer_id": cust_id,
            "account_type": acc1_type,
            "account_number_masked": acc1_num,
            "currency": "INR",
            "opening_balance": acc1_opening,
            "current_balance": acc1_opening,
            "available_balance": acc1_opening,
            "credit_limit": 0.0,
            "interest_rate": 3.5 if acc1_type == "SAVINGS" else 0.0,
            "status": "ACTIVE",
            "opened_date": customer_since.strftime("%Y-%m-%d"),
            "last_updated": datetime(2026, 8, 15, tzinfo=timezone.utc)
        }
        customer_accounts.append(account1)

        # Account 2: Credit Card (for eligible tiers)
        if tier in ["PREMIUM", "GOLD", "PLATINUM"] or (segment == "SALARIED" and random.random() < 0.8):
            acc2_id = f"ACC-{i:04d}-02"
            credit_lim = round(min(1500000.0, max(50000.0, monthly_income * 2.5)), -3)
            account2 = {
                "account_id": acc2_id,
                "customer_id": cust_id,
                "account_type": "CREDIT_CARD",
                "account_number_masked": f"XXXX-XXXX-{random.randint(1000, 9999)}",
                "currency": "INR",
                "opening_balance": 0.0,
                "current_balance": 0.0,
                "available_balance": credit_lim,
                "credit_limit": credit_lim,
                "interest_rate": 28.5,
                "status": "ACTIVE",
                "opened_date": (customer_since + timedelta(days=90)).strftime("%Y-%m-%d"),
                "last_updated": datetime(2026, 8, 15, tzinfo=timezone.utc)
            }
            customer_accounts.append(account2)

        # Account 3: Investment Account (for Gold/Platinum or High Earners)
        if tier in ["GOLD", "PLATINUM"] or random.random() < 0.4:
            acc3_id = f"ACC-{i:04d}-03"
            inv_opening = round(random.uniform(100000, max(200000, annual_income * 0.4)), -3)
            account3 = {
                "account_id": acc3_id,
                "customer_id": cust_id,
                "account_type": "INVESTMENT",
                "account_number_masked": f"XXXX-XXXX-{random.randint(1000, 9999)}",
                "currency": "INR",
                "opening_balance": inv_opening,
                "current_balance": inv_opening,
                "available_balance": inv_opening,
                "credit_limit": 0.0,
                "interest_rate": 11.2,
                "status": "ACTIVE",
                "opened_date": (customer_since + timedelta(days=180)).strftime("%Y-%m-%d"),
                "last_updated": datetime(2026, 8, 15, tzinfo=timezone.utc)
            }
            customer_accounts.append(account3)

        # Account 4: Loan Account (Home/Auto/Education for selected customers)
        if random.random() < 0.25 and segment != "STUDENT":
            acc4_id = f"ACC-{i:04d}-04"
            loan_principal = round(random.uniform(500000, 4500000), -4)
            account4 = {
                "account_id": acc4_id,
                "customer_id": cust_id,
                "account_type": "LOAN",
                "account_number_masked": f"XXXX-XXXX-{random.randint(1000, 9999)}",
                "currency": "INR",
                "opening_balance": loan_principal,
                "current_balance": loan_principal,
                "available_balance": 0.0,
                "credit_limit": 0.0,
                "interest_rate": 8.65,
                "status": "ACTIVE",
                "opened_date": (customer_since + timedelta(days=120)).strftime("%Y-%m-%d"),
                "last_updated": datetime(2026, 8, 15, tzinfo=timezone.utc)
            }
            customer_accounts.append(account4)

        # -------------------------------------------------------------
        # Generate 50–150 Transactions per Customer with Temporal Regularity
        # -------------------------------------------------------------
        num_transactions = random.randint(min_tx, max_tx)
        customer_transactions: List[Dict[str, Any]] = []

        # Account balance running accumulators
        account_balances = {acc["account_id"]: acc["opening_balance"] for acc in customer_accounts}

        # 1. Salary / Recurring Monthly Inflows (12 monthly dates)
        for m in range(12):
            tx_day = min(total_days, m * 30 + random.randint(1, 4))
            tx_date = start_date + timedelta(days=tx_day)
            salary_amt = round(monthly_income * random.uniform(0.95, 1.05), 2)
            primary_acc = customer_accounts[0]["account_id"]
            tx_id = f"TX-{i:04d}-{len(customer_transactions) + 1:04d}"

            tx_doc = {
                "transaction_id": tx_id,
                "customer_id": cust_id,
                "account_id": primary_acc,
                "transaction_date": tx_date.strftime("%Y-%m-%d"),
                "transaction_type": "INCOME",
                "category": "SALARY" if segment == "SALARIED" else "CONSULTING_FEE" if segment == "PROFESSIONAL" else "BUSINESS_REVENUE",
                "merchant": random.choice(MERCHANTS_BY_CATEGORY["SALARY"]),
                "description": f"Monthly Direct Payroll Settlement - {tx_date.strftime('%B %Y')}",
                "amount": salary_amt,
                "currency": "INR",
                "status": "COMPLETED",
                "reference_id": f"NEFT-IN-{random.randint(10000000, 99999999)}",
                "created_at": tx_date
            }
            customer_transactions.append(tx_doc)
            account_balances[primary_acc] += salary_amt

        # 2. Monthly Fixed Expenses (Rent, Utilities, Subscriptions)
        for m in range(12):
            # Rent / Mortgage
            if segment != "STUDENT":
                rent_day = min(total_days, m * 30 + 5)
                rent_date = start_date + timedelta(days=rent_day)
                rent_amt = round(monthly_income * random.uniform(0.20, 0.35), 2)
                primary_acc = customer_accounts[0]["account_id"]
                tx_id = f"TX-{i:04d}-{len(customer_transactions) + 1:04d}"
                customer_transactions.append({
                    "transaction_id": tx_id,
                    "customer_id": cust_id,
                    "account_id": primary_acc,
                    "transaction_date": rent_date.strftime("%Y-%m-%d"),
                    "transaction_type": "EXPENSE",
                    "category": "RENT",
                    "merchant": "Residential Society Lease Escrow",
                    "description": f"Monthly Lease Rental Remittance - {rent_date.strftime('%B %Y')}",
                    "amount": rent_amt,
                    "currency": "INR",
                    "status": "COMPLETED",
                    "reference_id": f"UPI-RENT-{random.randint(10000000, 99999999)}",
                    "created_at": rent_date
                })
                account_balances[primary_acc] -= rent_amt

            # Utilities
            util_day = min(total_days, m * 30 + 10)
            util_date = start_date + timedelta(days=util_day)
            util_amt = round(random.uniform(1500, 6500), 2)
            primary_acc = customer_accounts[0]["account_id"]
            tx_id = f"TX-{i:04d}-{len(customer_transactions) + 1:04d}"
            customer_transactions.append({
                "transaction_id": tx_id,
                "customer_id": cust_id,
                "account_id": primary_acc,
                "transaction_date": util_date.strftime("%Y-%m-%d"),
                "transaction_type": "EXPENSE",
                "category": "UTILITIES",
                "merchant": random.choice(MERCHANTS_BY_CATEGORY["UTILITIES"]),
                "description": f"Utility Energy & Broadband Bill - {util_date.strftime('%B %Y')}",
                "amount": util_amt,
                "currency": "INR",
                "status": "COMPLETED",
                "reference_id": f"BBPS-{random.randint(10000000, 99999999)}",
                "created_at": util_date
            })
            account_balances[primary_acc] -= util_amt

        # 3. Discretionary Daily Transactions to reach total count
        expense_categories = [
            ("GROCERIES", 0.30, (400, 4500)),
            ("DINING", 0.22, (250, 2800)),
            ("SHOPPING", 0.16, (600, 12000)),
            ("TRANSPORT", 0.14, (120, 1400)),
            ("FUEL", 0.08, (500, 3500)),
            ("ENTERTAINMENT", 0.05, (300, 2200)),
            ("HEALTHCARE", 0.05, (300, 5000))
        ]

        exp_cats = [c[0] for c in expense_categories]
        exp_weights = [c[1] for c in expense_categories]

        # Available spend accounts (Savings or Credit Card)
        spend_accounts = [acc["account_id"] for acc in customer_accounts if acc["account_type"] in ["SAVINGS", "CHECKING", "CREDIT_CARD"]]

        while len(customer_transactions) < num_transactions:
            target_acc = random.choice(spend_accounts)
            cat = random.choices(exp_cats, weights=exp_weights, k=1)[0]
            cat_info = next(c for c in expense_categories if c[0] == cat)
            amt = round(random.uniform(*cat_info[2]), 2)

            rand_day = random.randint(0, total_days)
            tx_date = start_date + timedelta(days=rand_day)
            merchant = random.choice(MERCHANTS_BY_CATEGORY.get(cat, ["General Store"]))
            tx_id = f"TX-{i:04d}-{len(customer_transactions) + 1:04d}"

            tx_doc = {
                "transaction_id": tx_id,
                "customer_id": cust_id,
                "account_id": target_acc,
                "transaction_date": tx_date.strftime("%Y-%m-%d"),
                "transaction_type": "EXPENSE",
                "category": cat,
                "merchant": merchant,
                "description": f"{merchant} payment for {cat.lower()}",
                "amount": amt,
                "currency": "INR",
                "status": "COMPLETED",
                "reference_id": f"UPI-TX-{random.randint(10000000, 99999999)}",
                "created_at": tx_date
            }
            customer_transactions.append(tx_doc)

            # Update balance
            acc_obj = next(a for a in customer_accounts if a["account_id"] == target_acc)
            if acc_obj["account_type"] == "CREDIT_CARD":
                account_balances[target_acc] += amt  # Credit card balance increases with spend
            else:
                account_balances[target_acc] -= amt

        # Sort transactions chronologically
        customer_transactions.sort(key=lambda t: t["transaction_date"])

        # Update final current_balance and available_balance for each account
        for acc in customer_accounts:
            aid = acc["account_id"]
            final_bal = round(account_balances[aid], 2)
            acc["current_balance"] = final_bal
            if acc["account_type"] == "CREDIT_CARD":
                acc["available_balance"] = round(max(0.0, acc["credit_limit"] - final_bal), 2)
            else:
                acc["available_balance"] = final_bal

        accounts_list.extend(customer_accounts)
        transactions_list.extend(customer_transactions)

        # -------------------------------------------------------------
        # Compute Deterministic Financial Metrics & Monthly Aggregations
        # -------------------------------------------------------------
        monthly_aggs = FinancialAnalyticsService.calculate_monthly_aggregations(customer_transactions)
        summary_kpis = FinancialAnalyticsService.calculate_summary_metrics(customer_doc, customer_accounts, customer_transactions)
        health_scores = FinancialAnalyticsService.calculate_financial_health(summary_kpis, segment)

        income_ytd = sum(m["income"] for m in monthly_aggs)
        expenses_ytd = sum(m["expenses"] for m in monthly_aggs)

        metrics_doc = {
            "customer_id": cust_id,
            "income_ytd": income_ytd,
            "expenses_ytd": expenses_ytd,
            "summary_metrics": summary_kpis,
            "financial_health": health_scores,
            "monthly_aggregations": monthly_aggs,
            "updated_at": datetime(2026, 8, 15, tzinfo=timezone.utc)
        }
        metrics_list.append(metrics_doc)

        # -------------------------------------------------------------
        # Denormalized Consolidated Document for Ultra-Fast Single-Doc Reads
        # -------------------------------------------------------------
        bal_dict = {}
        for acc in customer_accounts:
            acc_type_key = acc["account_type"].lower()
            bal_dict[acc_type_key] = acc["current_balance"]
        bal_dict["total_cash"] = summary_kpis["total_assets"]

        denorm_record = {
            "customer_id": cust_id,
            "customer_name": full_name,
            "tier": tier,
            "industry": occupation,
            "customer_segment": segment,
            "city": city,
            "state": state,
            "country": "India",
            "annual_income": annual_income,
            "monthly_income": monthly_income,
            "accounts": customer_accounts,
            "balances": bal_dict,
            "income_ytd": income_ytd,
            "expenses_ytd": expenses_ytd,
            "metrics": summary_kpis,
            "financial_health": health_scores,
            "monthly_aggregations": monthly_aggs,
            "transactions": customer_transactions[-15:],  # Most recent 15 transactions
            "summary": (
                f"{full_name} ({tier} {segment} in {city}) holds {len(customer_accounts)} accounts with total assets of INR {summary_kpis['total_assets']:,.2f}. "
                f"Monthly income is INR {monthly_income:,.2f} with {summary_kpis['savings_rate_pct']}% savings rate and {summary_kpis['runway_months']} months cash runway. "
                f"Financial health is rated {health_scores['grade']} (Score: {health_scores['financial_health_score']}/100)."
            ),
            "updated_at": datetime.now(timezone.utc)
        }
        denormalized_records.append(denorm_record)

    return customers_list, accounts_list, transactions_list, metrics_list, denormalized_records


async def seed_financial_data(
    num_customers: int = SEED_CUSTOMERS,
    force_reseed: bool = False
) -> Dict[str, Any]:
    """
    Idempotent bulk seeder for MongoDB.
    Inserts 500 customers, ~1250 accounts, ~50,000+ transactions with chunked bulk writes.
    """
    db = DatabaseSession.get_db()
    if db is None:
        logger.warning("MongoDB DatabaseSession not initialized; skipping seed.")
        return {"status": "skipped", "reason": "database_unavailable"}

    customers_col = db["customers"]
    existing_count = await customers_col.count_documents({})

    if existing_count >= num_customers and not force_reseed:
        logger.info(f"Financial database already seeded with {existing_count} customers. Idempotent skip.")
        return {
            "status": "already_seeded",
            "customers_count": existing_count,
            "accounts_count": await db["accounts"].count_documents({}),
            "transactions_count": await db["transactions"].count_documents({})
        }

    logger.info(f"Generating synthetic relational financial dataset ({num_customers} customers)...")
    customers, accounts, transactions, metrics, denorm = generate_synthetic_dataset(num_customers=num_customers)

    logger.info(f"Generated {len(customers)} customers, {len(accounts)} accounts, {len(transactions)} transactions.")

    # 1. Bulk Write Customers
    logger.info("Bulk writing 'customers' collection...")
    await db["customers"].drop()
    await db["customers"].insert_many(customers, ordered=False)

    # 2. Bulk Write Accounts
    logger.info("Bulk writing 'accounts' collection...")
    await db["accounts"].drop()
    await db["accounts"].insert_many(accounts, ordered=False)

    # 3. Bulk Write Transactions (in chunks of 10,000 for high throughput)
    logger.info(f"Bulk writing {len(transactions)} 'transactions' in chunks...")
    await db["transactions"].drop()
    chunk_size = 10000
    for chunk_start in range(0, len(transactions), chunk_size):
        chunk = transactions[chunk_start:chunk_start + chunk_size]
        await db["transactions"].insert_many(chunk, ordered=False)

    # 4. Bulk Write Financial Metrics
    logger.info("Bulk writing 'financial_metrics' collection...")
    await db["financial_metrics"].drop()
    await db["financial_metrics"].insert_many(metrics, ordered=False)

    # 5. Bulk Write Consolidated Financial Records
    logger.info("Bulk writing 'financial_records' collection...")
    await db["financial_records"].drop()
    await db["financial_records"].insert_many(denorm, ordered=False)

    logger.info("Successfully completed idempotent database seeding.")

    return {
        "status": "success",
        "customers_count": len(customers),
        "accounts_count": len(accounts),
        "transactions_count": len(transactions),
        "metrics_count": len(metrics)
    }


if __name__ == "__main__":
    import asyncio
    async def main():
        await DatabaseSession.connect()
        res = await seed_financial_data(force_reseed=True)
        print("SEED RESULT:", res)
        await DatabaseSession.disconnect()
    asyncio.run(main())
