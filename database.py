from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./chat_app.db"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "lokesh123"
POSTGRES_SERVER = "chatroom-fastapi.c6tu2uok2zjc.us-east-1.rds.amazonaws.com"
POSTGRES_PORT = "5432"
POSTGRES_DB = "postgres"

POSTGRES_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()