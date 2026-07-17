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

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)

class UserAdminUpdate(BaseModel):
    role: Optional[Role] = None
    is_active: Optional[bool] = None

class UserInDBBase(UserBase):
    id: int
    name: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Additional properties to return via API
class UserResponse(UserInDBBase):
    pass

class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UserResponse]
