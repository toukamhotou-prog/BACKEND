from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegister(BaseModel):
    full_name:str
    email:EmailStr
    password:str
    study_level:str

class VerifyOTP(BaseModel):
    email:EmailStr
    otp_code:str

class UserResponse(BaseModel):
    id:int
    full_name:str
    email:EmailStr
    study_level:str
    is_verified:bool

    class Config:
        from_attributes=True

class UserLogin(BaseModel):
    email: EmailStr
    password:str

class VerifyOTP(BaseModel):
    email: EmailStr
    otp_code:str

class EpreuveCreate(BaseModel):
    title:str
    subject:str
    school:str
    date:str
    file_uri:Optional[str]=None

class EpreuvesResponse(BaseModel):
    id:int
    title:str
    subject:str
    school:str
    study_level:str
    date:str
    downloads:int
    file_size:str
    file_uri:Optional[str]=None

    class Config:
        from_attributes=True

class UserUpdate(BaseModel):
    email: str
    full_name: Optional[str] = None
    password: Optional[str] = None
