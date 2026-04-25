from pydantic import BaseModel
from typing import Optional

class ComplaintCreate(BaseModel):
    latitude: float
    longitude: float

class ComplaintResponse(BaseModel):
    username: str
    id: str
    latitude: float
    longitude: float
    severity: float
    potholes: int
    status: str
    image_url: Optional[str] = None