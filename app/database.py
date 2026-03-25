import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

def get_database_url() -> str:
    env = os.environ.get("ENV", "production")
    if env == "development":
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv("DATABASE_URL")
    else:
        from app.secrets import get_secret
        return get_secret("DATABASE_URL")

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
