"""
Secure Migration Script: Local MongoDB -> MongoDB Atlas
Transfers all portal collections and GridFS file uploads (resumes, attachments)
while preserving exact ObjectIds and cryptographic password hashes.
"""

import sys
import os
from pymongo import MongoClient

SOURCE_URI = "mongodb://localhost:27017"
SOURCE_DB_NAME = "placement_system"
TARGET_DB_NAME = "placement_system"

COLLECTIONS_TO_MIGRATE = [
    'users',
    'students',
    'jobs',
    'applications',
    'announcements',
    'notifications',
    'forms',
    'form_responses',
    'settings',
    'password_requests',
    'login_logs',
    'fs.files',
    'fs.chunks'
]

def migrate(target_uri):
    if not target_uri or "mongodb" not in target_uri:
        print("[ERROR] Please provide a valid MongoDB Atlas URI (starts with mongodb+srv://)")
        return False

    print("=" * 60)
    print(" CBS 3i-CELL: SECURE DATA MIGRATION TO CLOUD")
    print("=" * 60)
    print(f"[*] Source Database: {SOURCE_URI} / {SOURCE_DB_NAME}")
    print(f"[*] Target Database: MongoDB Atlas / {TARGET_DB_NAME}")

    try:
        source_client = MongoClient(SOURCE_URI, serverSelectionTimeoutMS=5000)
        source_db = source_client[SOURCE_DB_NAME]
        source_client.admin.command('ping')
        print("[✓] Connected to local MongoDB.")
    except Exception as e:
        print(f"[ERROR] Could not connect to local MongoDB: {e}")
        return False

    try:
        print("[*] Connecting to MongoDB Atlas cluster...")
        target_client = MongoClient(target_uri, serverSelectionTimeoutMS=10000)
        target_db = target_client[TARGET_DB_NAME]
        target_client.admin.command('ping')
        print("[✓] Connected to MongoDB Atlas successfully!")
    except Exception as e:
        print(f"[ERROR] Could not connect to MongoDB Atlas: {e}")
        print("Tip: Make sure Network Access in Atlas allows 0.0.0.0/0 (or your IP) and credentials are correct.")
        return False

    print("\n[*] Starting migration of portal collections...")
    total_migrated = 0

    for col_name in COLLECTIONS_TO_MIGRATE:
        if col_name not in source_db.list_collection_names():
            continue

        src_col = source_db[col_name]
        tgt_col = target_db[col_name]

        doc_count = src_col.count_documents({})
        if doc_count == 0:
            print(f"  - {col_name:20}: 0 documents (skipped)")
            continue

        # Clean destination collection before fresh import
        tgt_col.delete_many({})

        # Read docs from local
        docs = list(src_col.find({}))
        
        # Insert into Atlas in batches
        BATCH_SIZE = 500
        for i in range(0, len(docs), BATCH_SIZE):
            batch = docs[i:i + BATCH_SIZE]
            tgt_col.insert_many(batch)

        verified_count = tgt_col.count_documents({})
        print(f"  [✓] {col_name:20}: Migrated {verified_count}/{doc_count} documents")
        total_migrated += verified_count

    print("\n" + "=" * 60)
    print(f"[✓] MIGRATION COMPLETED SUCCESSFULLY! Total records: {total_migrated}")
    print("=" * 60)
    print("All logins, student profiles, job postings, and resumes are now live in Atlas.")
    return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        target = sys.argv[1].strip()
    else:
        target = input("\nEnter your MongoDB Atlas URI: ").strip()
    
    migrate(target)
