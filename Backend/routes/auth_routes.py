from fastapi import APIRouter
from database import users_collection
from models.user_model import User
from fastapi import Query

router = APIRouter(prefix="/auth", tags=["Auth"])


# ✅ Signup
@router.post("/users")
def signup(user: User):
    existing = users_collection.find_one({"username": user.username})
    if existing:
        return {"error": "User exists"}

    users_collection.insert_one(user.dict())
    return {"message": "User created"}


# ✅ Login
@router.get("/users")
def login(username: str = Query(...), password: str = Query(...)):
    db_user = users_collection.find_one({
        "username": username,
        "password": password
    })

    if not db_user:
        return {"error": "Invalid credentials"}

   
    if username == "munci" and password == "1234":
        return {
            "username": "munci",
            "role": "municipality"
        }
    else:
        return {
            "username": db_user["username"],
            "role": "user"
        }
