from sqlalchemy.orm import sessionmaker, declarative_base
from models.rds_models import engine
from sqlalchemy.orm import Session

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()