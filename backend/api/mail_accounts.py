"""
API endpoints for managing user mail accounts (IMAP connections).
Each user can connect multiple email accounts for monitoring.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, EmailStr, Field
import imaplib
import ssl
import logging

from database import get_db, MailAccount
from auth.dependencies import get_current_user, CurrentUser
from utils.crypto import encrypt_password, decrypt_password

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/mail-accounts",
    tags=["📬 Почтовые аккаунты"]
)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class MailProviderPreset(BaseModel):
    """Предустановленные настройки для популярных провайдеров"""
    provider: str
    imap_server: str
    imap_port: int = 993
    imap_use_ssl: bool = True
    notes: str = ""


# Provider presets
MAIL_PROVIDERS = {
    "gmail": MailProviderPreset(
        provider="gmail",
        imap_server="imap.gmail.com",
        imap_port=993,
        notes="Требуется App Password: https://myaccount.google.com/apppasswords"
    ),
    "outlook": MailProviderPreset(
        provider="outlook",
        imap_server="outlook.office365.com",
        imap_port=993,
        notes="Используйте пароль приложения если включена 2FA"
    ),
    "yandex": MailProviderPreset(
        provider="yandex",
        imap_server="imap.yandex.ru",
        imap_port=993,
        notes="Создайте пароль приложения в настройках Яндекс.Почты"
    ),
    "mailru": MailProviderPreset(
        provider="mailru",
        imap_server="imap.mail.ru",
        imap_port=993,
        notes="Включите IMAP в настройках Mail.ru"
    ),
}


class MailAccountCreate(BaseModel):
    """Схема для создания почтового аккаунта"""
    name: str = Field(..., min_length=1, max_length=255, description="Название аккаунта (напр. 'Рабочая почта')")
    email: EmailStr = Field(..., description="Email адрес")
    provider: str = Field(default="custom", description="Провайдер: gmail, outlook, yandex, mailru, custom")
    
    # IMAP settings (required for custom, optional for preset providers)
    imap_server: Optional[str] = Field(None, description="IMAP сервер (авто для известных провайдеров)")
    imap_port: int = Field(default=993, ge=1, le=65535)
    imap_use_ssl: bool = Field(default=True)
    
    username: Optional[str] = Field(None, description="Логин (если отличается от email)")
    password: str = Field(..., min_length=1, description="Пароль или App Password")
    
    folder: str = Field(default="INBOX", description="Папка для мониторинга")
    sync_interval_minutes: int = Field(default=5, ge=1, le=60)


class MailAccountUpdate(BaseModel):
    """Схема для обновления почтового аккаунта"""
    name: Optional[str] = None
    folder: Optional[str] = None
    sync_interval_minutes: Optional[int] = Field(None, ge=1, le=60)
    is_active: Optional[bool] = None


class MailAccountResponse(BaseModel):
    """Ответ с данными почтового аккаунта (без пароля!)"""
    id: int
    name: str
    email: str
    provider: str
    imap_server: str
    imap_port: int
    username: str
    folder: str
    sync_interval_minutes: int
    is_active: bool
    status: str
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    total_emails_synced: int
    created_at: datetime

    class Config:
        from_attributes = True


class MailAccountTestResult(BaseModel):
    """Результат тестирования подключения"""
    success: bool
    message: str
    folders: Optional[List[str]] = None


class ProviderInfo(BaseModel):
    """Информация о провайдере"""
    provider: str
    imap_server: str
    imap_port: int
    notes: str


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def test_imap_connection(
    server: str,
    port: int,
    username: str,
    password: str,
    use_ssl: bool = True
) -> tuple[bool, str, list[str] | None]:
    """
    Тестирует IMAP подключение и возвращает список папок.
    
    Returns:
        (success, message, folders)
    """
    try:
        if use_ssl:
            context = ssl.create_default_context()
            imap = imaplib.IMAP4_SSL(server, port, ssl_context=context, timeout=10)
        else:
            imap = imaplib.IMAP4(server, port, timeout=10)
        
        # Try to login
        imap.login(username, password)
        
        # Get folder list
        status, folder_data = imap.list()
        folders = []
        if status == "OK":
            for item in folder_data:
                if item:
                    # Parse folder name from IMAP response
                    parts = item.decode().split(' "/" ')
                    if len(parts) > 1:
                        folders.append(parts[1].strip('"'))
        
        imap.logout()
        return True, "Подключение успешно!", folders
        
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        if "AUTHENTICATIONFAILED" in error_msg.upper():
            return False, "Ошибка аутентификации. Проверьте логин и пароль.", None
        return False, f"IMAP ошибка: {error_msg}", None
    except ssl.SSLError as e:
        return False, f"SSL ошибка: {str(e)}", None
    except Exception as e:
        return False, f"Ошибка подключения: {str(e)}", None


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/providers", response_model=List[ProviderInfo])
async def get_providers():
    """
    📋 Получить список поддерживаемых почтовых провайдеров с настройками.
    """
    return [
        ProviderInfo(
            provider=p.provider,
            imap_server=p.imap_server,
            imap_port=p.imap_port,
            notes=p.notes
        )
        for p in MAIL_PROVIDERS.values()
    ]


@router.get("/", response_model=List[MailAccountResponse])
async def list_mail_accounts(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    📬 Получить список своих подключенных почтовых аккаунтов.
    """
    result = await db.execute(
        select(MailAccount)
        .where(MailAccount.user_id == current_user.id)
        .order_by(MailAccount.created_at.desc())
    )
    accounts = result.scalars().all()
    return accounts


@router.post("/", response_model=MailAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_mail_account(
    account_data: MailAccountCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    ➕ Подключить новый почтовый аккаунт.
    
    Для Gmail, Outlook, Yandex, Mail.ru настройки IMAP подставляются автоматически.
    Для других провайдеров укажите imap_server вручную.
    """
    # Check for duplicate email
    existing = await db.execute(
        select(MailAccount).where(
            and_(
                MailAccount.user_id == current_user.id,
                MailAccount.email == account_data.email
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Аккаунт {account_data.email} уже подключен"
        )
    
    # Get IMAP settings from preset or use provided
    imap_server = account_data.imap_server
    imap_port = account_data.imap_port
    use_ssl = account_data.imap_use_ssl
    
    if account_data.provider in MAIL_PROVIDERS:
        preset = MAIL_PROVIDERS[account_data.provider]
        imap_server = preset.imap_server
        imap_port = preset.imap_port
        use_ssl = preset.imap_use_ssl
    elif not imap_server:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для кастомного провайдера необходимо указать imap_server"
        )
    
    username = account_data.username or account_data.email
    
    # Test connection first
    success, message, folders = test_imap_connection(
        server=imap_server,
        port=imap_port,
        username=username,
        password=account_data.password,
        use_ssl=use_ssl
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Не удалось подключиться: {message}"
        )
    
    # Encrypt password
    encrypted_pwd = encrypt_password(account_data.password)
    
    # Create account
    new_account = MailAccount(
        user_id=current_user.id,
        name=account_data.name,
        email=account_data.email,
        provider=account_data.provider,
        imap_server=imap_server,
        imap_port=imap_port,
        imap_use_ssl=use_ssl,
        username=username,
        encrypted_password=encrypted_pwd,
        folder=account_data.folder,
        sync_interval_minutes=account_data.sync_interval_minutes,
        status="connected"
    )
    
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    
    logger.info(f"User {current_user.id} connected mail account: {account_data.email}")
    
    return new_account


@router.post("/test", response_model=MailAccountTestResult)
async def test_connection(
    account_data: MailAccountCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    🔌 Проверить подключение к почтовому аккаунту без сохранения.
    
    Возвращает список доступных папок при успешном подключении.
    """
    # Get IMAP settings
    imap_server = account_data.imap_server
    imap_port = account_data.imap_port
    use_ssl = account_data.imap_use_ssl
    
    if account_data.provider in MAIL_PROVIDERS:
        preset = MAIL_PROVIDERS[account_data.provider]
        imap_server = preset.imap_server
        imap_port = preset.imap_port
        use_ssl = preset.imap_use_ssl
    elif not imap_server:
        return MailAccountTestResult(
            success=False,
            message="Для кастомного провайдера нужно указать imap_server"
        )
    
    username = account_data.username or account_data.email
    
    success, message, folders = test_imap_connection(
        server=imap_server,
        port=imap_port,
        username=username,
        password=account_data.password,
        use_ssl=use_ssl
    )
    
    return MailAccountTestResult(
        success=success,
        message=message,
        folders=folders
    )


@router.get("/{account_id}", response_model=MailAccountResponse)
async def get_mail_account(
    account_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    📧 Получить информацию о почтовом аккаунте.
    """
    result = await db.execute(
        select(MailAccount).where(
            and_(
                MailAccount.id == account_id,
                MailAccount.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аккаунт не найден"
        )
    
    return account


@router.patch("/{account_id}", response_model=MailAccountResponse)
async def update_mail_account(
    account_id: int,
    update_data: MailAccountUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    ✏️ Обновить настройки почтового аккаунта.
    """
    result = await db.execute(
        select(MailAccount).where(
            and_(
                MailAccount.id == account_id,
                MailAccount.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аккаунт не найден"
        )
    
    # Update fields
    if update_data.name is not None:
        account.name = update_data.name
    if update_data.folder is not None:
        account.folder = update_data.folder
    if update_data.sync_interval_minutes is not None:
        account.sync_interval_minutes = update_data.sync_interval_minutes
    if update_data.is_active is not None:
        account.is_active = update_data.is_active
    
    account.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(account)
    
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mail_account(
    account_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    🗑️ Отключить и удалить почтовый аккаунт.
    
    Это также удалит связанные результаты анализа писем.
    """
    result = await db.execute(
        select(MailAccount).where(
            and_(
                MailAccount.id == account_id,
                MailAccount.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аккаунт не найден"
        )
    
    await db.delete(account)
    await db.commit()
    
    logger.info(f"User {current_user.id} deleted mail account: {account.email}")


@router.post("/{account_id}/sync", response_model=dict)
async def trigger_sync(
    account_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    🔄 Запустить принудительную синхронизацию почтового ящика.
    """
    result = await db.execute(
        select(MailAccount).where(
            and_(
                MailAccount.id == account_id,
                MailAccount.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аккаунт не найден"
        )
    
    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Аккаунт неактивен"
        )
    
    # Reset status if it looks stuck (older than 10 min) or just force it
    # We set it to pending first so the task can pick it up and set to syncing
    account.status = "pending"
    # Reset last_sync_at to ensure it's picked up by monitor if direct task fails
    # account.last_sync_at = None 
    
    await db.commit()
    
    # Queue Celery task
    from tasks.mail_sync import sync_user_mailbox
    sync_user_mailbox.delay(account_id)
    
    return {
        "message": f"Синхронизация аккаунта {account.email} запущена",
        "account_id": account_id
    }
