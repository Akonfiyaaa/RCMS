from fastapi import APIRouter, UploadFile, File, Form, Query
from bson import ObjectId

from database import complaints_collection
from services.severity_service import process_image
from services.map_service import get_traffic_density
from utils.helpers import image_to_base64
from datetime import datetime, timezone
from services.gnn_service import run_gnn


router = APIRouter(prefix="/api", tags=["Complaints"])


# =========================
# ✅ CREATE COMPLAINT
# =========================
@router.post("/complaint")
async def create_complaint(
    username: str = Query(...),
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    file_bytes = await file.read()

    result = process_image(file_bytes)
    traffic = get_traffic_density(latitude, longitude)

    image_base64 = image_to_base64(result["image_bytes"])

    # 1️⃣ insert complaint FIRST (without priority yet)
    complaint_data = {
        "username": username,
        "latitude": latitude,
        "longitude": longitude,
        "severity": result["score"],
        "potholes": result["potholes"],
        "traffic": traffic,
        "priority": 0,  # placeholder
        "status": "to-do",
        "image": image_base64,
        "timestamp": datetime.now(timezone.utc)
    }

    inserted = complaints_collection.insert_one(complaint_data)

    # 2️⃣ fetch ALL complaints (including new one)
    all_complaints = list(complaints_collection.find())

    for c in all_complaints:
        c["id"] = str(c["_id"])
        del c["_id"]

    # 3️⃣ run GNN on full graph
    gnn_output = run_gnn(all_complaints)

    # 4️⃣ update ALL priorities in DB
    for i, c in enumerate(gnn_output):
        complaints_collection.update_one(
            {"_id": ObjectId(c["id"])},
            {
                "$set": {
                    "priority": round(c["gnn_score"], 2),
                    "zone": c["zone"]
                }
            }
        )

    # 5️⃣ return newly inserted complaint with updated priority
    new_doc = complaints_collection.find_one({"_id": inserted.inserted_id})
    new_doc["id"] = str(new_doc["_id"])
    del new_doc["_id"]

    return new_doc
# =========================
# 📥 GET COMPLAINTS
# =========================
from Backend.services.gnn_service import run_gnn

from Backend.services.gnn_service import run_gnn_and_cluster

@router.get("/complaint")
def get_complaints(username: str = Query(None)):

    from Backend.services.gnn_service import run_gnn_and_cluster

    complaints = list(complaints_collection.find())

    for c in complaints:
        c["id"] = str(c["_id"])
        del c["_id"]

    # 👇 USER VIEW
    if username and username != "munci":
        return [c for c in complaints if c.get("username") == username]

    # 👇 MUNICIPALITY VIEW
    return run_gnn_and_cluster(complaints)


# =========================
# 🧩 CONFIG VALUES
# =========================
@router.get("/config")
def get_config():
    from Backend.config import GOOGLE_MAPS_API_KEY

    return {
        "google_maps_api_key": GOOGLE_MAPS_API_KEY,
    }


# =========================
# 🔄 UPDATE STATUS (FIXED)
# =========================
@router.put("/complaint/{complaint_id}")
def update_status(
    complaint_id: str,
    status: str = Query(...)
):
    valid_status = ["to-do", "in progress", "done"]

    status = status.lower()

    if status not in valid_status:
        return {"error": "Invalid status"}

    result = complaints_collection.update_one(
        {"_id": ObjectId(complaint_id)},
        {"$set": {"status": status}}
    )

    if result.modified_count == 0:
        return {"error": "Complaint not found or no change"}

    updated_doc = complaints_collection.find_one(
        {"_id": ObjectId(complaint_id)}
    )

    updated_doc["id"] = str(updated_doc["_id"])
    del updated_doc["_id"]

    return updated_doc
