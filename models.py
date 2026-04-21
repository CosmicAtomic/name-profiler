from sqlalchemy import Column, Integer, String, Float,DateTime
from database import Base

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
    country_name = Column(String)
    country_probability = Column(Float)
    created_at = Column(DateTime)
