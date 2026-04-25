from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["pothole_db"]

complaints_collection = db["complaints"]
users_collection = db["users"]