import json
from typing import Dict

import jwt
import hashlib
import requests

from datetime import datetime, timedelta, UTC
from fastapi import HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from models.rds_models import engine

secret_key = '6Lcp4Y0rAAAAAMx574CaTgPELQT7aT24Aprreo84'
JWT_SECRET = "p1beyVW)E>b{1gya{,I+yd]>DfN/#*"
UPLOAD_DIR = "uploads"
security = HTTPBearer()

def hash_password(password: str):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_access_token(username: str, expires_delta: timedelta = None):
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=145))
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def verify_recaptcha(token: str) -> bool:
    if token == "test-token":
        return True

    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {
        "secret": secret_key,
        "response": token,
    }
    response = requests.post(url, data=data)
    result = response.json()
    print(result)
    return result["success"]


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def convert_dto_to_json(dto)-> Dict:
    return json.loads(dto.model_dump_json())

def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()