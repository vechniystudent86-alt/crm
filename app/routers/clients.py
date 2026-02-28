"""
Роутер управления клиентами
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Client
from app.schemas import ClientCreate, ClientUpdate, ClientResponse


router = APIRouter()


@router.get("/", response_model=List[ClientResponse], summary="Список клиентов")
async def get_all_clients(
    search: Optional[str] = Query(None, description="Поиск по имени или телефону"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка всех клиентов с поддержкой поиска.
    
    - **search**: Поиск по имени, фамилии или телефону
    - **skip**: Пропустить N записей
    - **limit**: Количество записей (макс. 500)
    """
    query = select(Client).where(Client.is_active == True)
    
    if search:
        search_filter = or_(
            Client.first_name.ilike(f"%{search}%"),
            Client.last_name.ilike(f"%{search}%"),
            Client.phone.ilike(f"%{search}%"),
            Client.telegram.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
    
    query = query.order_by(Client.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    clients = result.scalars().all()
    
    return clients


@router.get("/{client_id}", response_model=ClientResponse, summary="Клиент по ID")
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение информации о клиенте по ID"""
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    
    return client


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, summary="Добавить клиента")
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавление нового клиента.
    
    - **first_name**: Имя (обязательно)
    - **last_name**: Фамилия
    - **phone**: Телефон (обязательно, уникальный)
    - **telegram**: Telegram
    - **whatsapp**: WhatsApp
    - **email**: Email
    - **comment**: Комментарий
    - **source**: Источник (website, telegram, instagram)
    """
    # Проверка уникальности телефона
    result = await db.execute(
        select(Client).where(Client.phone == client_data.phone)
    )
    existing_client = result.scalar_one_or_none()
    
    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Клиент с таким телефоном уже существует"
        )
    
    # Создание клиента
    client = Client(
        **client_data.model_dump(),
        created_by_id=current_user.id
    )
    
    db.add(client)
    await db.commit()
    await db.refresh(client)
    
    return client


@router.put("/{client_id}", response_model=ClientResponse, summary="Обновить клиента")
async def update_client(
    client_id: int,
    client_update: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновление информации о клиенте"""
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    
    # Проверка уникальности телефона при изменении
    if client_update.phone and client_update.phone != client.phone:
        existing = await db.execute(
            select(Client).where(Client.phone == client_update.phone)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Клиент с таким телефоном уже существует"
            )
    
    # Обновление полей
    update_data = client_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    await db.commit()
    await db.refresh(client)
    
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить клиента")
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удаление клиента (мягкое удаление - установка is_active=False).
    
    Для полного удаления обратитесь к администратору.
    """
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    
    # Мягкое удаление
    client.is_active = False
    await db.commit()
    
    return None


@router.get("/phone/{phone}", response_model=ClientResponse, summary="Поиск по телефону")
async def get_client_by_phone(
    phone: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поиск клиента по номеру телефона"""
    result = await db.execute(
        select(Client).where(Client.phone == phone)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    
    return client
