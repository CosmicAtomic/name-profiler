from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from profile_routes import profile_router
from database import Base, engine
from auth_routes import auth_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=True,     
    allow_methods=["*"],         
    allow_headers=["*"],         
)

Base.metadata.create_all(bind=engine)


app.include_router(profile_router)
app.include_router(auth_router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    for error in exc.errors():
        if error["type"] in ("missing", "value_error") and "name" in error.get("loc", []):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Missing or empty name"}
            )
        if error["type"] in ("int_parsing", "float_parsing"):
            return JSONResponse(
                status_code=422,
                content={"status": "error", "message": "Invalid query parameters"}
            )
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Invalid type"}
    )


@app.get('/')
def test():
    return JSONResponse(content={"message": "API is running"})
