# backend/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from backend.core.config import SECRET_KEY, ALGORITHM

from backend.db.session import get_db
from backend.crud import user_crud
from backend.models.user_model import User

# Контекст для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    if SECRET_KEY is None:
        raise ValueError("The SECRET_KEY environment variable is not set. Please set it before running the application.")
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Graph ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if SECRET_KEY is None:
            raise ValueError("The SECRET_KEY environment variable is not set. Please set it before running the application.")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username_from_payload = payload.get("sub")
        if username_from_payload is None or not isinstance(username_from_payload, str):
            raise credentials_exception
        
        username: str = username_from_payload 
        
    except JWTError:
        raise credentials_exception
    
    user = await user_crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user