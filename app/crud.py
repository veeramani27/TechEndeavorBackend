from sqlalchemy.orm import Session

from . import models, schemas


def _get_pwd_context():
    from passlib.context import CryptContext

    return CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return _get_pwd_context().verify(plain_password, hashed_password)


def get_password_hash(password):
    return _get_pwd_context().hash(password)


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email, username=user.username, hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_blogs(db: Session, skip: int = 0, limit: int = 25):
    return (
        db.query(models.Blog)
        .order_by(models.Blog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_blogs_count(db: Session):
    return db.query(models.Blog).count()


def get_blog(db: Session, blog_id: int):
    return db.query(models.Blog).filter(models.Blog.id == blog_id).first()


def create_blog(db: Session, blog: schemas.BlogCreate, user_id: int):
    db_blog = models.Blog(**blog.dict(), author_id=user_id)
    db.add(db_blog)
    db.commit()
    db.refresh(db_blog)
    return db_blog


def update_blog(db: Session, db_blog: models.Blog, blog: schemas.BlogUpdate):
    blog_data = blog.dict(exclude_unset=True)
    for key, value in blog_data.items():
        setattr(db_blog, key, value)
    db.commit()
    db.refresh(db_blog)
    return db_blog


def get_blog_titles(db: Session):
    return [title[0] for title in db.query(models.Blog.title).order_by(models.Blog.created_at).all()]
