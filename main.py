from sqlalchemy import Column, Integer, String, Float,DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi import FastAPI, Depends, status, Response, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from services import get_agify_data, get_genderize_data, get_nationalize_data, choose_country, classify_age
from datetime import datetime, timezone
import uuid6
from typing import Optional
import os
from dotenv import load_dotenv
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./sql_app.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(String, primary_key=True)
    name = Column(String, unique= True)
    gender = Column(String)
    gender_probability = Column(Float)
    sample_size = Column(Integer)
    age = Column(Integer)
    age_group = Column(String)
    country_id = Column(String)
    country_probability = Column(Float)
    created_at = Column(DateTime)

class ProfileRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip().lower()
        if not v:
            raise ValueError("name must not be empty")
        return v

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    for error in exc.errors():
        if error["type"] in ("missing", "value_error") and "name" in error.get("loc", []):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Missing or empty name"}
            )
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Invalid type"}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=True,     
    allow_methods=["*"],         
    allow_headers=["*"],         
)

Base.metadata.create_all(bind=engine)

@app.get('/')
def test():
    return JSONResponse(content={"message": "API is running"})

@app.post('/api/profiles')
async def create_profile(profile_request: ProfileRequest, db: Session= Depends(get_db)):
    name = profile_request.name
    existing_profile = db.query(Profile).filter(Profile.name == name).first()
    if existing_profile:
        return JSONResponse(content={
            "status": "success",
            "message": "Profile already exists",
            "data": {
                "id": existing_profile.id,
                "name": existing_profile.name,
                "gender": existing_profile.gender,
                "gender_probability": existing_profile.gender_probability,
                "sample_size": existing_profile.sample_size,
                "age": existing_profile.age,
                "age_group": existing_profile.age_group,
                "country_id": existing_profile.country_id,
                "country_probability": existing_profile.country_probability,
                "created_at": existing_profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
    )
    
    genderize = await get_genderize_data(name)
    if genderize["count"] == 0 or genderize["gender"] is None:
        return JSONResponse(
            status_code=502,
            content={ "status": "502", "message": "Genderize returned an invalid response" }
        )

    agify = await get_agify_data(name)
    if agify["age"] is None:
        return JSONResponse(
            status_code=502,
            content={ "status": "502", "message": "Agify returned an invalid response" }
        )

    nationalize = await get_nationalize_data(name)
    if not nationalize["country"]:
        return JSONResponse(
            status_code=502,
            content={ "status": "502", "message": "Nationalize returned an invalid response" }
        )
    
    age_class = classify_age(agify["age"])
    choice_country = choose_country(nationalize["country"])

    new_profile = Profile(
        id=str(uuid6.uuid7()),            
        name=name,
        gender = genderize["gender"],
        gender_probability = genderize["probability"],
        sample_size = genderize["count"],
        age = agify["age"],
        age_group = age_class,
        country_id = choice_country["country_id"],
        country_probability = choice_country["probability"],
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_profile)
    db.commit()     
    db.refresh(new_profile) 

    return JSONResponse(
        status_code=201,
        content= {
            "status": "success",
            "data": {
                "id": new_profile.id,
                "name": new_profile.name,
                "gender": new_profile.gender,
                "gender_probability": new_profile.gender_probability,
                "sample_size": new_profile.sample_size, 
                "age": new_profile.age,
                "age_group": new_profile.age_group,
                "country_id": new_profile.country_id,
                "country_probability": new_profile.country_probability,
                "created_at": new_profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
    )

@app.get('/api/profiles')
def get_profiles(gender: Optional[str] = None, country_id: Optional[str] = None, age_group: Optional[str] = None, db: Session= Depends(get_db)):
    query = db.query(Profile)
    if gender:
        query = query.filter(Profile.gender == gender.lower())
    if country_id:
        query = query.filter(Profile.country_id == country_id.upper())
    if age_group:
        query = query.filter(Profile.age_group == age_group.lower())
    profiles = query.all()

    
    output = []
    count = 0
    for profile in profiles:
        count += 1
        data = {
            "id": profile.id,
            "name": profile.name,
            "gender": profile.gender,
            "age": profile.age,
            "age_group": profile.age_group,
            "country_id": profile.country_id
        }
        output.append(data)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "count": count,
            "data": output,
        }
    )



@app.get("/api/profiles/{id}")
def get_profile(id: str, db: Session= Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == id).first()
    
    if not profile:
        return JSONResponse(
            status_code=404,
            content={ "status": "error", "message": "Profile not found" }
        )
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "data": {
                "id": profile.id,
                "name": profile.name,
                "gender": profile.gender,
                "gender_probability": profile.gender_probability,
                "sample_size": profile.sample_size,
                "age": profile.age,
                "age_group": profile.age_group,
                "country_id": profile.country_id,
                "country_probability": profile.country_probability,
                "created_at": profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
    )


@app.delete("/api/profiles/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == id).first()
    if not profile:
        return JSONResponse(
            status_code=404,
            content={ "status": "error", "message": f"Profile with id {id} not found" }
        )
    db.delete(profile)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)



