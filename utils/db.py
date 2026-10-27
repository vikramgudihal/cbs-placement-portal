import os
from pymongo import MongoClient
import gridfs

# Production MongoDB Connection Pool Singleton
_client = None
_fs = None

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'placement_system')

def get_client():
    global _client
    if _client is None:
        _client = MongoClient(
            MONGO_URI,
            maxPoolSize=50,
            minPoolSize=5,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            retryWrites=True
        )
    return _client

def get_db():
    client = get_client()
    return client[DB_NAME]

def get_fs():
    global _fs
    if _fs is None:
        db = get_db()
        _fs = gridfs.GridFS(db)
    return _fs

def check_db_health():
    """Returns True if MongoDB responds to ping within timeout."""
    try:
        client = get_client()
        client.admin.command('ping')
        return True, "Connected"
    except Exception as e:
        return False, str(e)
