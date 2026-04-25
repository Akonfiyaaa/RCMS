from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["pothole_db"]
users_collection = db["users"]

user = {
    "username": "munci",
    "password": "1234",
}

users_collection.insert_one(user)

print("User inserted successfully")