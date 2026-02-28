"""
Роутер аутентификации
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_admin_user,
    create_user_with_role,
)
from app.models import User, UserRole
from app.schemas import Token, UserCreate, UserResponse


router = APIRouter()


@router.post("/login", response_model=Token, summary="Вход в систему")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Аутентификация пользователя и получение JWT-токена.
    
    - **username**: Имя пользователя
    - **password**: Пароль
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Регистрация")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Регистрация нового пользователя (только для администратора).
    
    - **username**: Имя пользователя (3-50 символов)
    - **password**: Пароль (минимум 6 символов)
    - **full_name**: Полное имя
    - **phone**: Телефон
    - **role**: Роль (admin или trainer)
    """
    try:
        new_user = await create_user_with_role(
            username=user_data.username,
            password=user_data.password,
            role=UserRole(user_data.role.value),
            full_name=user_data.full_name,
            phone=user_data.phone,
            db=db
        )
        return new_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
