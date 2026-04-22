import uuid6
from typing import Optional
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from schemas import ProfileRequest
from models import Profile
from database import get_db
from utils import format_full_profile
from services import get_agify_data, get_genderize_data, get_nationalize_data, choose_country, classify_age, get_country_name

router = APIRouter(prefix="/api/profiles")

@router.post('')
async def create_profile(profile_request: ProfileRequest, db: Session= Depends(get_db)):
    name = profile_request.name
    existing_profile = db.query(Profile).filter(Profile.name == name).first()
    if existing_profile:
        return JSONResponse(content={
            "status": "success",
            "message": "Profile already exists",
            "data": format_full_profile(existing_profile)
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
    country_id = choice_country["country_id"]
    country_name = get_country_name(country_id)

    new_profile = Profile(
        id=str(uuid6.uuid7()),            
        name=name,
        gender = genderize["gender"],
        gender_probability = genderize["probability"],
        age = agify["age"],
        age_group = age_class,
        country_id = country_id,
        country_name = country_name,
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
            "data": format_full_profile(new_profile)
        }
    )

@router.get('')
def get_profiles(gender: Optional[str] = None, country_id: Optional[str] = None, age_group: Optional[str] = None, min_age: Optional[int] = None, max_age: Optional[int] = None, min_gender_probability: Optional[float] = None, min_country_probability: Optional[float] = None, db: Session= Depends(get_db)):
    query = db.query(Profile)
    if gender:
        query = query.filter(Profile.gender == gender.lower())
    if country_id:
        query = query.filter(Profile.country_id == country_id.upper())
    if age_group:
        query = query.filter(Profile.age_group == age_group.lower())
    if min_age is not None:
        query = query.filter(Profile.age >= min_age)
    if max_age is not None:
        query = query.filter(Profile.age <= max_age)
    if min_gender_probability is not None:
        query = query.filter(Profile.gender_probability >= min_gender_probability)
    if min_country_probability is not None:
        query = query.filter(Profile.country_probability >= min_country_probability)
    profiles = query.all()

    
    output = []
    count = 0
    for profile in profiles:
        count += 1
        data = {
            "id": profile.id,
            "name": profile.name,
            "gender": profile.gender,
            "gender_probability": profile.gender_probability,
            "age": profile.age,
            "age_group": profile.age_group,
            "country_id": profile.country_id,
            "country_name": profile.country_name,
            "country_probability": profile.country_probability,
            "created_at": profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        output.append(data)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "total": count,
            "data": output,
        }
    )


@router.get("/{id}")
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
            "data": format_full_profile(profile)
        }
    )

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == id).first()
    if not profile:
        return JSONResponse(
            status_code=404,
            content={ "status": "error", "message": f"Profile not found" }
        )
    db.delete(profile)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
