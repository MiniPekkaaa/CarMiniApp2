#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pymongo import MongoClient
import json
from bson import json_util
from config import Config

try:
    # MongoDB connection используя настройки из config.py
    client = MongoClient(Config.MONGO_URI)
    
    # Switch to Auto database
    db = client.Auto

    # Check collections
    collections = db.list_collection_names()
    print("Collections in Auto database:")
    print(collections)

    if Config.COLLECTION_CURRENT_AUTO in collections:
        # Check documents in CurrentAuto collection
        print(f"\nFirst 3 documents from {Config.COLLECTION_CURRENT_AUTO} collection:")
        cursor = db[Config.COLLECTION_CURRENT_AUTO].find().limit(3)
        for doc in cursor:
            print(json.loads(json_util.dumps(doc)))

        # Count documents
        count = db[Config.COLLECTION_CURRENT_AUTO].count_documents({})
        print(f"\nTotal documents in collection: {count}")

        # Check document structure
        print("\nAll unique fields in collection:")
        all_fields = set()
        for doc in db[Config.COLLECTION_CURRENT_AUTO].find():
            all_fields.update(doc.keys())
        print(sorted(list(all_fields)))
    else:
        print(f"Collection '{Config.COLLECTION_CURRENT_AUTO}' not found!")

except Exception as e:
    print(f"MongoDB Error: {str(e)}")
finally:
    if 'client' in locals():
        client.close()
