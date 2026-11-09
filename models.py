from sqlalchemy import  Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__="users"

    id=Column(Integer, primary_key=True, index=True)
    full_name=Column(String, nullable=False)
    email=Column(String, unique=True, index=True, nullable=False)
    password_hash=Column(String, nullable=False)
    study_level=Column(String,nullable=False)
    is_verified=Column(Boolean,default=False)
    otp_code=Column(String(6), nullable=True)
    created_at=Column(DateTime(timezone=True), server_default=func.now())

class Epreuves(Base):
    __tablename__="epreuves"

    id=Column(Integer, primary_key=True, index=True)
    title=Column(String, nullable=False)
    subject=Column(String, nullable=False)
    school=Column(String, nullable=False)
    study_level=Column(String, nullable=False)
    date=Column(String, nullable=False)
    downloads=Column(Integer, default=0)
    file_size=Column(String, default="1.0 MB")
    file_uri=Column(Text, nullable=True)

    user_id= Column(Integer, ForeignKey("users.id"), nullable=True)