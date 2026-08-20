import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.db.session import DatabaseSession
from app.db.indexes import create_database_indexes
from app.db.seed import seed_financial_data


async def verify_mongo_connection():
    print("=" * 60)
    print("TESTING LIVE MONGODB ATLAS CONNECTION")
    print("=" * 60)
    print(f"Target URI: {settings.MONGODB_URI[:30]}...[REDACTED]...")
    print(f"Target DB Name: {settings.MONGODB_DB_NAME}")

    try:
        # 1. Connect
        print("\n[Step 1] Initializing Motor Async client...")
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )

        # 2. Ping
        print("[Step 2] Sending ping command to MongoDB Atlas...")
        ping_result = await client.admin.command('ping')
        print(f" Ping successful! Server response: {ping_result}")

        # 3. Test Database Session Connection
        print("\n[Step 3] Initializing Application DatabaseSession...")
        await DatabaseSession.connect()
        db = DatabaseSession.get_db()
        assert db is not None, "DatabaseSession.get_db() returned None"
        print(" Application DatabaseSession connected successfully.")

        # 4. Create Indexes
        print("\n[Step 4] Creating database indexes (tokens, audit_logs, financial_records)...")
        await create_database_indexes()
        print(" Database indexes established successfully.")

        # 5. Seed Financial Data
        print("\n[Step 5] Seeding mock financial data (CUST-101 to CUST-105)...")
        await seed_financial_data()
        
        # Verify collection contents
        count_customers = await db["financial_records"].count_documents({})
        print(f" 'financial_records' collection document count: {count_customers}")

        # Fetch sample document
        sample_doc = await db["financial_records"].find_one({"customer_id": "CUST-101"}, {"_id": 0, "customer_name": 1, "tier": 1, "balances": 1})
        print(f" Sample record retrieved: {sample_doc}")

        # 6. Test Write / Read in audit_logs
        print("\n[Step 6] Testing write and read in 'audit_logs' collection...")
        test_event = {
            "event_id": "test_ping_event_01",
            "chain_id": "urn:uuid:test-ping-chain",
            "sequence": 0,
            "event_type": "MONGODB_HEALTH_CHECK",
            "actor": "system",
            "target": "mongodb_atlas",
            "decision": "ALLOW",
            "reason": "Live connectivity test verification",
            "previous_event_hash": "0" * 64,
            "event_hash": "test_hash_12345"
        }
        await db["audit_logs"].replace_one({"event_id": "test_ping_event_01"}, test_event, upsert=True)
        read_back = await db["audit_logs"].find_one({"event_id": "test_ping_event_01"})
        assert read_back is not None
        print(f" Write and read verification passed! Found event: {read_back['event_type']}")

        # Clean up test event
        await db["audit_logs"].delete_one({"event_id": "test_ping_event_01"})
        print(" Cleaned up test probe.")

        print("\n" + "=" * 60)
        print(" RESULT: MongoDB Atlas is CONNECTED and WORKING PERFECTLY!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "!" * 60)
        print(f" ERROR: Failed to connect to MongoDB Atlas: {e}")
        print("!" * 60)
        sys.exit(1)
    finally:
        await DatabaseSession.disconnect()


if __name__ == "__main__":
    asyncio.run(verify_mongo_connection())
