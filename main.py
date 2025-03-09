from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from depends import get_db
from api import auth_api
from api import permissions_api
from api import roles_api
from api import users_api
from api import apps_api
from api import payroll_bands_api
from api import companies_api
from api import staff_api
from api import payroll_codes_api
from api import payroll_computations_api
from api import files_api
from api import payslips_api
from api import p9as_api
from api import payroll_report_api


fastapi_config = {
    "title":"Hummingbird Service",
    "debug":True,
    "root_path": "/api",
}

app = FastAPI(**fastapi_config)
app.include_router(auth_api.router,prefix="/auth")
app.include_router(permissions_api.router,prefix="/permissions")
app.include_router(roles_api.router,prefix="/roles")
app.include_router(users_api.router,prefix="/users")
app.include_router(apps_api.router,prefix="/apps")
app.include_router(payroll_bands_api.router,prefix="/bands")
app.include_router(companies_api.router,prefix="/companies")
app.include_router(p9as_api.router,prefix="/companies/{company_id}/p9as")
app.include_router(staff_api.router,prefix="/companies/{company_id}/staff")
app.include_router(payroll_codes_api.router,prefix="/companies/{company_id}/codes")
app.include_router(payroll_computations_api.router,prefix="/companies/{company_id}/computations")
app.include_router(payslips_api.router,prefix="/companies/{company_id}/computations/{computation_id}/payslips")
app.include_router(payroll_report_api.router,prefix="/companies/{company_id}/computations/{computation_id}/report")
app.include_router(files_api.router,prefix="/files")

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