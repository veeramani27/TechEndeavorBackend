from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List
from fastapi.middleware.cors import CORSMiddleware

from . import crud, models, schemas, auth
from .database import engine, get_db

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TechEndeavor API",
    description="Backend for TechEndeavor blog platform",
    version="1.0.0"
)

# CORS Middleware
origins = [
    "http://localhost",
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:5173",
    "https://tech-endeavor.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.get("/blogs/", response_model=schemas.PaginatedBlog)
def read_blogs(page: int = 1, limit: int = 25, db: Session = Depends(get_db)):
    skip = (page - 1) * limit
    blogs = crud.get_blogs(db, skip=skip, limit=limit)
    total_count = crud.get_blogs_count(db)
    total_pages = (total_count + limit - 1) // limit
    return {
        "items": blogs,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

@app.get("/blogs/{blog_id}", response_model=schemas.Blog)
def read_blog(blog_id: int, db: Session = Depends(get_db)):
    db_blog = crud.get_blog(db, blog_id=blog_id)
    if db_blog is None:
        raise HTTPException(status_code=404, detail="Blog not found")
    return db_blog

@app.post("/blogs/", response_model=schemas.Blog)
def create_blog(blog: schemas.BlogCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return crud.create_blog(db=db, blog=blog, user_id=current_user.id)

@app.get("/")
def read_root():
    return {"message": "Welcome to TechEndeavor API"}
