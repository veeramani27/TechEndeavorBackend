from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    blogs: List["Blog"] = []

    class Config:
        from_attributes = True


# Blog Schemas
class BlogBase(BaseModel):
    title: str
    content: str


class BlogCreate(BlogBase):
    pass


class BlogUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class Blog(BlogBase):
    id: int
    created_at: datetime
    author_id: int
    author: Optional[UserBase] = None

    class Config:
        from_attributes = True


class PaginatedBlog(BaseModel):
    items: List[Blog]
    total_count: int
    page: int
    limit: int
    total_pages: int


# AI Enhancement Schemas
class BlogEnhanceRequest(BaseModel):
    title: str
    content: str


class BlogEnhanceResponse(BaseModel):
    title: str
    content: str


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
