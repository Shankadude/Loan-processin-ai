import asyncio
import os
from dotenv import load_dotenv
import motor.motor_asyncio
from datetime import datetime, timezone

load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_DETAILS", "mongodb://localhost:27017/loan_db")

async def check_mongo():
    print(f"🔍 Testing connection to MongoDB...")
    print(f"📌 Target URI: {MONGO_DETAILS.split('@')[-1] if '@' in MONGO_DETAILS else MONGO_DETAILS}")

    # Determine if SSL/TLS is needed based on URI (Atlas / srv requires TLS, local does not)
    is_atlas = "mongodb+srv" in MONGO_DETAILS or "ssl=true" in MONGO_DETAILS.lower()
    
    # Build client kwargs conditionally
    client_kwargs = {"serverSelectionTimeoutMS": 5000}
    if is_atlas:
        client_kwargs["tls"] = True
        client_kwargs["tlsAllowInvalidCertificates"] = True

    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGO_DETAILS,
            **client_kwargs
        )
        
        # Test ping
        await client.admin.command('ping')
        print("✅ MongoDB Ping Successful: Server is responding!")

        # Test insert/read on loan_processing DB
        db = client.loan_processing
        test_col = db.get_collection("connection_test")
        
        test_doc = {"test_run": True, "timestamp": datetime.now(timezone.utc)}
        result = await test_col.insert_one(test_doc)
        print(f"✅ Write Check Passed! Inserted Test ID: {result.inserted_id}")

        read_back = await test_col.find_one({"_id": result.inserted_id})
        print(f"✅ Read Check Passed! Retrieved document successfully.")

        # Cleanup
        await test_col.delete_one({"_id": result.inserted_id})
        print("🧹 Cleaned up test record. MongoDB is fully operational!\n")

    except Exception as e:
        print(f"\n❌ MongoDB Connection Failed: {e}\n")
        print("Troubleshooting tips:")
        print("1. If using MongoDB Atlas: Check if your current IP is whitelisted under 'Network Access'.")
        print("2. If using Local MongoDB: Verify the Windows service is running (services.msc -> MongoDB Server).")

if __name__ == "__main__":
    asyncio.run(check_mongo())