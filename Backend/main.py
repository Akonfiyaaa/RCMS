from fastapi import FastAPI
from routes.complaint_routes import router as complaint_router
from routes.auth_routes import router as auth_router



app = FastAPI()

app.include_router(complaint_router)
app.include_router(auth_router)
