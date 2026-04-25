from pydantic import BaseModel

class Complaint(BaseModel):
    username: str
    latitude: float
    longitude: float
    severity: float
    status: str = "to-do"
    