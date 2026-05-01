"""
🛡️ Email Check API
REST API для проверки входящих писем через реестр доверенных отправителей
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging
from datetime import datetime

from database import get_db
from schemas.check import (
    EmailCheckRequest,
    EmailCheckResponse,
    BulkCheckRequest,
    BulkCheckResponse
)
from services.analysis_service import AnalysisService

from auth.permissions import get_current_user, CurrentUser

router = APIRouter(
    prefix="/api/v1/check",
    tags=["🔍 Проверка писем"]
)
logger = logging.getLogger(__name__)


@router.post(
    "/registry",
    response_model=EmailCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="📧 Проверить входящее письмо",
    description="""
    **Комплексная проверка входящего письма** через реестр доверенных отправителей.

    ## 🚀 Типы проверки

    ### ⚡ Fast Track (Level 1-2)
    - Для **высокодоверенных отправителей** из реестра
    - Минимальная проверка: SPF, DKIM, IP
    - Скорость: **~50ms**
    - Используется для государственных организаций

    ### 🔬 Full Check (Level 3-4 или неизвестные)
    - Для остальных и неизвестных отправителей
    - Полная проверка всех параметров
    - Скорость: **~200ms**
    - Включает поведенческий анализ

    ## 📊 Действия системы

    | Действие | Описание |
    |----------|----------|
    | `allow` | ✅ Письмо безопасно, доставить получателю |
    | `quarantine` | ⚠️ Подозрительное, поместить в карантин |
    | `block` | ❌ Опасное, заблокировать полностью |

    ## 🎯 Уровни риска

    | Уровень | Score | Действие | Цвет |
    |---------|-------|----------|------|
    | **safe** | 0-30 | allow | 🟢 Зеленый |
    | **caution** | 30-50 | allow | 🟡 Желтый |
    | **warning** | 50-70 | quarantine | 🟠 Оранжевый |
    | **danger** | 70-100 | block | 🔴 Красный |

    ## 💾 Кэширование

    - Результаты кэшируются в **Redis** на **15 минут**
    - Формат ключа: `registry_check:{email}:{ip}`
    - Блокированные письма: **5 минут** TTL

    ## 🔍 Проверяемые параметры

    - ✉️ SPF проверка (30% веса)
    - 🔐 DKIM подпись (30% веса)
    - 🌐 IP reputation (25% веса)
    - 📋 Email заголовки (15% веса)
    - 📝 Контекст письма (тема, время)
    - 📈 Поведенческий анализ (история)
    """,
    responses={
        200: {
            "description": "✅ Проверка выполнена успешно",
            "content": {
                "application/json": {
                    "example": {
                        "action": "allow",
                        "status": "safe",
                        "risk_score": 15.5,
                        "confidence": 95.0,
                        "in_registry": True,
                        "trust_level": 1,
                        "check_type": "fast_track",
                        "processing_time_ms": 50.0
                    }
                }
            }
        },
        401: {"description": "🔒 Требуется аутентификация"},
        500: {"description": "❌ Ошибка сервера"}
    }
)
async def check_email(
    request: EmailCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    **Проверить одно входящее письмо**

    Выполняет комплексный анализ безопасности:
    - 🔍 Поиск отправителя в реестре
    - ✉️ Валидация SPF/DKIM
    - 🌐 Проверка IP репутации
    - 📋 Анализ заголовков
    - 📝 Контекстная проверка
    - 📈 Поведенческий анализ
    """
    try:
        logger.info(
            f"Email check requested by user {current_user.id}: "
            f"{request.from_address} -> {request.to_address}"
        )

        checker = AnalysisService(db)

        result = await checker.check_incoming_email(
            from_address=request.from_address,
            to_address=request.to_address,
            subject=request.subject,
            ip_address=request.ip_address,
            headers=request.headers,
            body_preview=request.body_preview,
            spf_result=request.spf_result,
            dkim_result=request.dkim_result,
            dkim_signature=request.dkim_signature,
            use_cache=request.use_cache
        )

        logger.info(
            f"Check completed for {request.from_address}: "
            f"action={result['action']}, risk={result['risk_score']}"
        )

        return result

    except Exception as e:
        logger.error(f"Error checking email: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка проверки письма: {str(e)}"
        )


@router.post(
    "/registry/bulk",
    response_model=BulkCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="📬 Массовая проверка писем",
    description="""
    **Проверка нескольких писем одновременно** (до 100 штук).

    ## 📦 Возможности

    - ⚡ Параллельная обработка
    - 📊 Индивидуальные результаты для каждого письма
    - 📈 Агрегированная статистика
    - 🔄 Интеграция с почтовыми серверами

    ## 💡 Применение

    - Batch обработка очереди писем
    - Интеграция с Postfix/Exim policy daemon
    - Массовый анализ архива писем
    - Ночная проверка накопленных писем

    ## ⚙️ Ограничения

    - **Максимум 100 писем** за один запрос
    - Рекомендуемый размер батча: **10-50 писем**
    - Общее время: ~200ms × количество писем
    """,
    responses={
        200: {
            "description": "✅ Массовая проверка выполнена",
            "content": {
                "application/json": {
                    "example": {
                        "total": 2,
                        "successful": 2,
                        "failed": 0,
                        "processing_time_ms": 150.5,
                        "results": [
                            {"action": "allow", "risk_score": 10.0},
                            {"action": "quarantine", "risk_score": 65.0}
                        ]
                    }
                }
            }
        },
        400: {"description": "❌ Превышен лимит (100 писем)"},
        401: {"description": "🔒 Требуется аутентификация"}
    }
)
async def check_emails_bulk(
    request: BulkCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    **Проверить несколько писем одновременно**

    Возвращает:
    - Результаты для каждого письма
    - Статистику: всего/успешно/провалено
    - Общее время обработки

    Лимиты: Максимум **100 писем** за запрос
    """
    try:
        if len(request.emails) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Максимум 100 писем за один запрос"
            )

        logger.info(
            f"Bulk check requested by user {current_user.id}: "
            f"{len(request.emails)} emails"
        )

        start_time = datetime.utcnow()
        checker = AnalysisService(db)

        results = []
        successful = 0
        failed = 0

        for email_request in request.emails:
            try:
                result = await checker.check_incoming_email(
                    from_address=email_request.from_address,
                    to_address=email_request.to_address,
                    subject=email_request.subject,
                    ip_address=email_request.ip_address,
                    headers=email_request.headers,
                    body_preview=email_request.body_preview,
                    spf_result=email_request.spf_result,
                    dkim_result=email_request.dkim_result,
                    dkim_signature=email_request.dkim_signature,
                    use_cache=email_request.use_cache
                )
                results.append(result)
                successful += 1

            except Exception as e:
                logger.error(
                    f"Error checking email {email_request.from_address}: {e}"
                )
                results.append({
                    "action": "block",
                    "status": "danger",
                    "risk_score": 100.0,
                    "confidence": 0.0,
                    "in_registry": False,
                    "trust_level": None,
                    "check_type": "error",
                    "checks": {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "processing_time_ms": 0,
                    "cached": False,
                    "reason": "check_error",
                    "details": str(e)
                })
                failed += 1

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            f"Bulk check completed: {successful} successful, "
            f"{failed} failed, {processing_time:.2f}ms"
        )

        return {
            "results": results,
            "total": len(request.emails),
            "successful": successful,
            "failed": failed,
            "processing_time_ms": round(processing_time, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk check: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка массовой проверки: {str(e)}"
        )


@router.get(
    "/test/trusted",
    response_model=EmailCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="✅ Тест: доверенный отправитель",
    description="""
    **Тестовый endpoint** с примером высокодоверенного отправителя.

    ## 🧪 Параметры теста

    - **Отправитель:** director@ministry.gov.ru
    - **Trust Level:** 1 (MAX_TRUST)
    - **Тип проверки:** Fast Track
    - **Ожидаемый результат:** ✅ allow, safe, ~50ms

    ## 📊 Что проверяется

    - ✅ Наличие в реестре
    - ✅ SPF: pass
    - ✅ DKIM: pass
    - ✅ IP: whitelisted (10.0.1.15)
    - ⚡ Быстрая обработка (~50ms)

    Используется для демонстрации и тестирования работы Fast Track режима.
    """,
    responses={
        200: {
            "description": "✅ Тест выполнен успешно",
            "content": {
                "application/json": {
                    "example": {
                        "action": "allow",
                        "status": "safe",
                        "risk_score": 1.5,
                        "in_registry": True,
                        "trust_level": 1,
                        "check_type": "fast_track"
                    }
                }
            }
        }
    }
)
async def test_trusted_sender(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    **Тест с доверенным отправителем**

    Проверяет письмо от director@ministry.gov.ru (Level 1).

    Ожидается: ✅ allow, 🟢 safe, ⚡ fast_track
    """
    checker = AnalysisService(db)

    result = await checker.check_incoming_email(
        from_address="director@ministry.gov.ru",
        to_address="security@fsb.gov.ru",
        subject="Monthly Security Report",
        ip_address="10.0.1.15",
        headers={
            "From": "Director <director@ministry.gov.ru>",
            "To": "Security <security@fsb.gov.ru>",
            "Date": "Mon, 13 Oct 2025 10:30:00 +0300",
            "Message-ID": "<test123@ministry.gov.ru>",
            "Return-Path": "<director@ministry.gov.ru>",
            "Received": "from mail.ministry.gov.ru by mail.fsb.gov.ru"
        },
        body_preview="Dear colleagues, Please find attached the monthly security report.",
        spf_result="pass",
        dkim_result="pass",
        use_cache=False
    )

    return result


@router.get(
    "/test/untrusted",
    response_model=EmailCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="⚠️ Тест: недоверенный отправитель",
    description="""
    **Тестовый endpoint** с примером недоверенного отправителя.

    ## 🧪 Параметры теста

    - **Отправитель:** ceo@mega-bank.com (не в реестре)
    - **Тема:** "URGENT: Verify your account NOW!!!"
    - **Тип проверки:** Full Check
    - **Ожидаемый результат:** ⚠️ quarantine, 🟠 warning

    ## 🚩 Красные флаги

    - ❌ **Не в реестре** доверенных отправителей
    - ⚠️ **SPF:** softfail
    - ❌ **DKIM:** none
    - 🔴 **IP:** blacklisted (203.0.113.50)
    - 🚩 **Return-Path:** не совпадает с From
    - 🚩 **Reply-To:** подозрительный адрес
    - ⚠️ **Тема:** suspicious keywords, много "!!!"

    Используется для демонстрации полной проверки неизвестного отправителя.
    """,
    responses={
        200: {
            "description": "⚠️ Тест выполнен, обнаружены угрозы",
            "content": {
                "application/json": {
                    "example": {
                        "action": "quarantine",
                        "status": "warning",
                        "risk_score": 59.2,
                        "in_registry": False,
                        "check_type": "full"
                    }
                }
            }
        }
    }
)
async def test_untrusted_sender(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    **Тест с недоверенным отправителем**

    Проверяет подозрительное письмо с множеством красных флагов.

    Ожидается: ⚠️ quarantine, 🟠 warning, 🔬 full check
    """
    checker = AnalysisService(db)

    result = await checker.check_incoming_email(
        from_address="ceo@mega-bank.com",
        to_address="admin@ministry.gov.ru",
        subject="URGENT: Verify your account NOW!!!",
        ip_address="203.0.113.50",
        headers={
            "From": "CEO <ceo@mega-bank.com>",
            "To": "Admin <admin@ministry.gov.ru>",
            "Date": "Mon, 13 Oct 2025 03:00:00 +0300",
            "Message-ID": "<suspicious123@mega-bank.com>",
            "Return-Path": "<different@other-domain.ru>",
            "Reply-To": "scam@phishing-site.ru"
        },
        body_preview="URGENT! Your account will be suspended. Click here to verify NOW!",
        spf_result="softfail",
        dkim_result="none",
        use_cache=False
    )

    return result


@router.get(
    "/test/suspicious",
    response_model=EmailCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="🚨 Тест: фишинговое письмо",
    description="""
    **Тестовый endpoint** с примером высоко подозрительного фишингового письма.

    ## 🧪 Параметры теста

    - **Отправитель:** security@goverment-portal.ru (опечатка!)
    - **Тема:** "СРОЧНО! ПОДТВЕРДИТЕ ПАРОЛЬ! IMPORTANT!!!"
    - **Ожидаемый результат:** 🚨 quarantine/block, 🔴 danger

    ## 🚩 Критические угрозы

    - 🔴 **SPF FAIL** - сервер не авторизован
    - 🔴 **DKIM NONE** - нет подписи
    - 🔴 **IP Blacklisted** - в черном списке
    - 🚩 **Domain typo:** "goverment" вместо "government"
    - 🚩 **Return-Path mismatch** - не совпадает с From
    - 🚩 **Reply-To suspicious** - phishing@evil.com
    - ⚠️ **Много Received** - подозрительная цепочка релеев
    - 🚩 **Suspicious keywords:** СРОЧНО, пароль, подтвердите
    - ⚠️ **5 восклицательных знаков** в теме
    - ⚠️ **80% заглавных букв** в теме

    ## 📊 Ожидаемые оценки

    - **Technical Score:** ~9/100 (critical)
    - **Context Score:** ~30/100 (suspicious)
    - **Behavioral Score:** ~75/100 (unknown sender)
    - **Final Risk:** ~65/100 (danger)

    Используется для демонстрации обнаружения сложных фишинговых атак.
    """,
    responses={
        200: {
            "description": "🚨 Тест выполнен, обнаружена критическая угроза",
            "content": {
                "application/json": {
                    "example": {
                        "action": "quarantine",
                        "status": "warning",
                        "risk_score": 64.9,
                        "checks": {
                            "technical": {
                                "spf": "fail",
                                "dkim": "none",
                                "ip": "blacklisted"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def test_suspicious_email(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    **Тест с фишинговым письмом**

    Проверяет высоко подозрительное письмо с множественными угрозами.

    Ожидается: 🚨 block/quarantine, 🔴 danger, 9 красных флагов
    """
    checker = AnalysisService(db)

    result = await checker.check_incoming_email(
        from_address="security@goverment-portal.ru",
        to_address="director@ministry.gov.ru",
        subject="СРОЧНО! ПОДТВЕРДИТЕ ПАРОЛЬ! IMPORTANT!!!",
        ip_address="198.51.100.100",
        headers={
            "From": "Security Service <security@goverment-portal.ru>",
            "To": "Director <director@ministry.gov.ru>",
            "Date": "Mon, 13 Oct 2025 02:00:00 +0300",
            "Message-ID": "<fake456@random.com>",
            "Return-Path": "<bounce@another-domain.com>",
            "Reply-To": "phishing@evil.com",
            "Received": "from unknown.server.com",
            "Received": "from another.relay.net",
            "Received": "from suspicious.host.org"
        },
        body_preview="СРОЧНО! Ваш аккаунт заблокирован! Нажмите здесь для подтверждения пароля!",
        spf_result="fail",
        dkim_result="none",
        use_cache=False
    )

    return result


@router.delete(
    "/cache/{email}/{ip}",
    status_code=status.HTTP_200_OK,
    summary="🗑️ Очистить кэш для отправителя",
    description="""
    **Удалить кэшированный результат** для конкретной комбинации email/IP.

    ## 💾 Формат ключа

    ```
    registry_check:{email}:{ip}
    ```

    ## 📝 Пример

    Для очистки кэша:
    - Email: `director@ministry.gov.ru`
    - IP: `10.0.1.15`

    Будет удален ключ:
    ```
    registry_check:director@ministry.gov.ru:10.0.1.15
    ```

    ## 💡 Когда использовать

    - После изменения записи в реестре
    - При обновлении trust level
    - Для принудительной повторной проверки
    - После обнаружения компрометации

    **Требуется:** Аутентифицированный пользователь
    """,
    responses={
        200: {
            "description": "✅ Кэш успешно очищен",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "deleted": True,
                        "message": "Cache cleared"
                    }
                }
            }
        },
        404: {
            "description": "ℹ️ Кэш не найден",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "deleted": False,
                        "message": "No cache entry found"
                    }
                }
            }
        }
    }
)
async def clear_cache(
    email: str,
    ip: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    **Очистить кэш для конкретного email/IP**

    Удаляет кэшированный результат проверки.

    Требуется: Любой аутентифицированный пользователь
    """
    from redis_client import redis_client

    cache_key = f"registry_check:{email}:{ip}"

    try:
        deleted = await redis_client.delete(cache_key)

        return {
            "status": "success",
            "cache_key": cache_key,
            "deleted": bool(deleted),
            "message": "Кэш очищен" if deleted else "Кэш не найден"
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки кэша: {str(e)}"
        )


@router.delete(
    "/cache/all",
    status_code=status.HTTP_200_OK,
    summary="🗑️ Очистить весь кэш проверок",
    description="""
    **Удалить ВСЕ кэшированные результаты проверок** из Redis.

    ## ⚠️ ВНИМАНИЕ!

    Эта операция удалит **все кэшированные результаты** проверок писем!

    ## 🔍 Что будет удалено

    Все ключи с паттерном:
    ```
    registry_check:*
    ```

    ## 💡 Когда использовать

    - 🔄 После обновления логики проверки
    - 📝 После массовых изменений в реестре
    - 🛠️ При обслуживании системы
    - 🧪 После изменения конфигурации

    ## 📊 Результат

    Возвращает количество удаленных записей.

    **⚠️ Используйте осторожно!**
    После очистки все последующие проверки будут медленнее (до заполнения кэша).

    **Требуется:** Аутентифицированный пользователь
    """,
    responses={
        200: {
            "description": "✅ Весь кэш успешно очищен",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "deleted_count": 42,
                        "message": "Cleared 42 cache entries"
                    }
                }
            }
        },
        401: {"description": "🔒 Требуется аутентификация"}
    }
)
async def clear_all_caches(
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    **Очистить ВСЕ кэшированные результаты**

    ⚠️ Внимание: Удаляет весь кэш проверок!

    Требуется: Любой аутентифицированный пользователь
    """
    from redis_client import redis_client

    try:
        pattern = "registry_check:*"
        cursor = 0
        deleted_count = 0

        # Scan for keys (safer than KEYS command)
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted = await redis_client.delete(*keys)
                deleted_count += deleted

            if cursor == 0:
                break

        logger.info(f"Cleared {deleted_count} cache entries by user {current_user.id}")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Очищено {deleted_count} записей кэша"
        }

    except Exception as e:
        logger.error(f"Error clearing all caches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки кэша: {str(e)}"
        )
