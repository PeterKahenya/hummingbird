from fastapi import Depends, FastAPI
from mongoengine import connect
import auth_api, payroll_api
from config import DB_URL
from fastapi.middleware.cors import CORSMiddleware
from depends import get_db
import report_api


fastapi_config = {
    "title":"Hummingbird Service",
    "debug":True,
    "root_path": "/api",
}

app = FastAPI(**fastapi_config)
app.include_router(auth_api.router,prefix="/auth")
app.include_router(payroll_api.router,prefix="/payroll")
app.include_router(report_api.router,prefix="/reports")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow only your Next.js app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root(db = Depends(get_db)):
    return {"message": "Welcome to Hummingbird API"}