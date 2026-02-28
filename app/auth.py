"""
Модуль аутентификации и авторизации
JWT-токены, хеширование паролей, управление пользователями
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.schemas import TokenData


# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT-токена"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def authenticate_user(
    username: str,
    password: str,
    db: AsyncSession
) -> Optional[User]:
    """Аутентификация пользователя по логину и паролю"""
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return False
    
    if not verify_password(password, user.hashed_password):
        return False
    
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Получение текущего пользователя из JWT-токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username)
        
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(
        select(User).where(User.username == token_data.username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Получение текущего активного пользователя"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Пользователь деактивирован")
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Получение текущего пользователя с ролью администратора"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )
    return current_user


async def create_user_with_role(
    username: str,
    password: str,
    role: UserRole = UserRole.TRAINER,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> User:
    """
    Создание пользователя с указанной ролью.
    Если db не передан, создаётся новая сессия.
    """
    from app.database import async_session_maker
    
    async def _create_user(session: AsyncSession) -> User:
        # Проверка существования пользователя
        result = await session.execute(
            select(User).where(User.username == username)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ValueError(f"Пользователь {username} уже существует")
        
        # Создание нового пользователя
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            hashed_password=hashed_password,
            role=role,
            full_name=full_name,
            phone=phone,
            is_active=True
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        return user
    
    if db:
        return await _create_user(db)
    else:
        async with async_session_maker() as session:
            return await _create_user(session)
