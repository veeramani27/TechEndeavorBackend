import os
from datetime import timedelta
from typing import List

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, crud, models, schemas
from app.database import engine, get_db

# Load environment variables
load_dotenv()

# Create tables -- Only first time
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TechEndeavor API",
    description="Backend for TechEndeavor blog platform",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm=None

def get_llm_instance(openai_api_key=os.getenv("OPENAI_API_KEY")):
    global llm
    if(llm):
        return llm
    
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        api_key=openai_api_key,
        openai_api_base=os.getenv("BASE_URL"),
        model=os.getenv("MODEL"),
        temperature=0.7,
    )
    return llm


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
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
        "total_pages": total_pages,
    }


@app.get("/blogs/titles", response_model=List[str])
def read_blog_titles(db: Session = Depends(get_db)):
    return crud.get_blog_titles(db)


@app.get("/blogs/{blog_id}", response_model=schemas.Blog)
def read_blog(blog_id: int, db: Session = Depends(get_db)):
    db_blog = crud.get_blog(db, blog_id=blog_id)
    if db_blog is None:
        raise HTTPException(status_code=404, detail="Blog not found")
    return db_blog


@app.post("/blogs/", response_model=schemas.Blog)
def create_blog(
    blog: schemas.BlogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return crud.create_blog(db=db, blog=blog, user_id=current_user.id)


@app.post("/blogs/enhance", response_model=schemas.BlogEnhanceResponse)
async def enhance_blog(
    request: schemas.BlogEnhanceRequest,
    current_user: models.User = Depends(auth.get_current_user),
):
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=500, detail="OPENAI_API_KEY not set in environment"
            )

        llm = get_llm_instance(openai_api_key)

        # Enhance Title
        title_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a professional blog editor. Your task is to enhance the title of a blog post to make it more engaging and catchy, without changing its original meaning. Title should be just Text and no markdown syntax should be introduced.",
                ),
                ("user", "{title}"),
            ]
        )
        title_chain = title_prompt | llm | StrOutputParser()
        enhanced_title = await title_chain.ainvoke({"title": request.title})

        # Enhance Content
        content_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a professional blog editor. Your task is to enhance the content of a blog post to make it more professional, readable, and engaging. DO NOT change the original meaning or intent of the content. Ensure the flow of the content is more smooth. Resturcture it and rephrase it to make it more effective. Keep the markdown formatting if present.",
                ),
                ("user", "{content}"),
            ]
        )
        content_chain = content_prompt | llm | StrOutputParser()
        enhanced_content = await content_chain.ainvoke({"content": request.content})

        return schemas.BlogEnhanceResponse(
            title=enhanced_title.strip().strip('"'), content=enhanced_content.strip()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Enhancement failed: {str(e)}")


@app.put("/blogs/{blog_id}", response_model=schemas.Blog)
def update_blog(
    blog_id: int,
    blog: schemas.BlogUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_blog = crud.get_blog(db, blog_id=blog_id)
    if db_blog is None:
        raise HTTPException(status_code=404, detail="Blog not found")
    if db_blog.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this blog")
    return crud.update_blog(db=db, db_blog=db_blog, blog=blog)


@app.delete("/blogs/{blog_id}")
def delete_blog(
    blog_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_blog = crud.get_blog(db, blog_id=blog_id)
    if db_blog is None:
        raise HTTPException(status_code=404, detail="Blog not found")
    if db_blog.author_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this blog"
        )
    crud.delete_blog(db=db, db_blog=db_blog)
    return {"detail": "Blog deleted successfully"}


@app.get("/")
def read_root():
    return {"message": "Welcome to TechEndeavor API"}
