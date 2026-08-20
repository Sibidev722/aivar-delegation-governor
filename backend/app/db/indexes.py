from pymongo import ASCENDING, DESCENDING, IndexModel
from app.core.logging import logger
from app.db.session import DatabaseSession


async def create_database_indexes() -> None:
    """
    Ensure all unique, compound, and TTL indexes exist across all relational and governance collections.
    Distinct index names are used for each collection to prevent index conflicts.
    """
    db = DatabaseSession.get_db()
    if db is None:
        logger.warning("Database unavailable, skipping index creation.")
        return

    try:
        logger.info("Configuring MongoDB collection indexes...")

        # 1. customers collection indexes
        cust_col = db["customers"]
        await cust_col.create_indexes([
            IndexModel([("customer_id", ASCENDING)], unique=True, name="idx_cust_customer_id_unique"),
            IndexModel([("customer_tier", ASCENDING)], name="idx_cust_tier"),
            IndexModel([("customer_segment", ASCENDING)], name="idx_cust_segment")
        ])

        # 2. accounts collection indexes
        acc_col = db["accounts"]
        await acc_col.create_indexes([
            IndexModel([("account_id", ASCENDING)], unique=True, name="idx_acc_account_id_unique"),
            IndexModel([("customer_id", ASCENDING)], name="idx_acc_customer_id"),
            IndexModel([("account_type", ASCENDING)], name="idx_acc_type")
        ])

        # 3. transactions collection indexes
        tx_col = db["transactions"]
        await tx_col.create_indexes([
            IndexModel([("transaction_id", ASCENDING)], unique=True, name="idx_tx_transaction_id_unique"),
            IndexModel([("customer_id", ASCENDING), ("transaction_date", DESCENDING)], name="idx_tx_cust_date_compound"),
            IndexModel([("account_id", ASCENDING)], name="idx_tx_account_id"),
            IndexModel([("category", ASCENDING)], name="idx_tx_category")
        ])

        # 4. financial_metrics collection indexes
        met_col = db["financial_metrics"]
        await met_col.create_indexes([
            IndexModel([("customer_id", ASCENDING)], unique=True, name="idx_met_customer_id_unique")
        ])

        # 5. financial_records collection indexes (denormalized summary cache)
        fin_col = db["financial_records"]
        await fin_col.create_indexes([
            IndexModel([("customer_id", ASCENDING)], unique=True, name="idx_fin_rec_customer_id_unique"),
            IndexModel([("tier", ASCENDING)], name="idx_fin_rec_tier")
        ])

        # 6. delegation_tokens collection indexes
        tokens_col = db["delegation_tokens"]
        await tokens_col.create_indexes([
            IndexModel([("token_id", ASCENDING)], unique=True, name="idx_unique_token_id"),
            IndexModel([("chain_id", ASCENDING), ("depth", ASCENDING)], name="idx_chain_depth"),
            IndexModel([("parent_token_id", ASCENDING)], name="idx_parent_token_id"),
            IndexModel([("expires_at", ASCENDING)], name="idx_token_expires_at"),
            IndexModel([("status", ASCENDING)], name="idx_token_status")
        ])

        # 7. audit_logs collection indexes
        audit_col = db["audit_logs"]
        await audit_col.create_indexes([
            IndexModel([("chain_id", ASCENDING), ("sequence", ASCENDING)], unique=True, name="idx_chain_sequence"),
            IndexModel([("timestamp", DESCENDING)], name="idx_audit_timestamp"),
            IndexModel([("event_type", ASCENDING)], name="idx_audit_event_type"),
            IndexModel([("decision", ASCENDING)], name="idx_audit_decision")
        ])

        logger.info("Successfully established all database indexes across 7 collections.")
    except Exception as e:
        logger.error(f"Failed to create database indexes: {e}")
