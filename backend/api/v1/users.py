# backend/api/v1/users.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.crud import user_crud
from backend.schemas import user_schema
from backend.core import security
from backend.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from backend.db.session import get_db
from backend.core.security import get_current_user
from backend.models.user_model import User

router = APIRouter()

@router.post("/register", response_model=user_schema.UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: user_schema.UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await user_crud.get_user_by_username(db, username=user_in.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    user = await user_crud.create_user(db=db, user=user_in)
    return user

@router.post("/login/token")
async def login_for_access_token(db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = await user_crud.get_user_by_username(db, username=form_data.username)
    
    # 1. Сначала проверяем, найден ли пользователь
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 2. Теперь, когда Pylance знает, что 'user' не None, проверяем пароль
    if not security.verify_password(form_data.password, str(user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me/profile", response_model=user_schema.UserProfile)
async def read_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получает профиль текущего аутентифицированного пользователя."""
    owned_graphs = await user_crud.get_owned_graphs(db, user_id=current_user.id) # type: ignore
    learning_graphs = await user_crud.get_learning_graphs(db, user_id=current_user.id) # type: ignore
    
    total_ratings = await user_crud.get_user_total_ratings(db, user_id=current_user.id) # type: ignore
    
    profile_data = {
        "id": current_user.id,
        "username": current_user.username,
        "total_likes": total_ratings["total_likes"],
        "total_dislikes": total_ratings["total_dislikes"],
        "owned_graphs": owned_graphs,
        "learning_graphs": learning_graphs
    }
    
    return profile_data