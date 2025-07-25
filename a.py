from pymongo import MongoClient
import certifi

uri = "mongodb+srv://vandyamayya02:pantrypilot3@cluster3.me22ety.mongodb.net/?retryWrites=true&w=majority"

try:
    client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    print("✅ Connection successful!")
    print("Databases:", client.list_database_names())
except Exception as e:
    print("❌ Connection error:", e)
