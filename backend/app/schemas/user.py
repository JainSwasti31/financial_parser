from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import Role

# Shared properties
class UserBase(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[Role] = Role.Analyst

# Properties to receive via API on creation
class UserCreate(UserBase):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: Role = Role.Analyst

# Properties to receive via API on login (JSON)
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserInDBBase(UserBase):
    id: int
    name: str
    email: str
    role: Role
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Additional properties to return via API
class UserResponse(UserInDBBase):
    pass
