from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from bson import ObjectId
from enum import Enum
from utils.helpers import strip_string



#- User

class UserRegister(BaseModel):
    name: str = Field(min_length=3, max_length=20)
    email: EmailStr
    mobile: str
    password: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "mobile", "password", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return strip_string(v)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v):
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def strong_password(cls, v:str):

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        has_upper = False
        has_lower = False
        has_num = False
        has_special_char = False

        special_chars = set("!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~")

        for char in v:
            if char.islower():
                has_lower=True
            if char.isupper():
                has_upper=True
            if char.isnumeric():
                has_num=True
            if char in special_chars:
                has_special_char = True
        
        if not all([has_upper, has_lower, has_num, has_special_char]):
            raise ValueError(
            "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character."
        )
        return v

    
    @field_validator('mobile')
    @classmethod
    def validate_mobile(cls, v):

        v = str(v)

        if not v.isdigit() or len(v) != 10:
            raise ValueError("Mobile number must be exactly 10 digits.")

        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v):
        return v.lower().strip()

    @field_validator("password", mode="before")
    @classmethod
    def strip_password(cls, v):
        return strip_string(v)
















