"""
API endpoints for attachment and URL analysis

Provides endpoints for:
- Single attachment scanning
- Multiple attachment scanning
- Single URL analysis
- Bulk URL analysis
- Email URL extraction and analysis

Author: SPEAR-GUARD Team
Date: 2025-11-05
"""

import base64
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime

from schemas.attachments import (
    AttachmentScanRequest,
    AttachmentScanResponse,
    URLAnalysisRequest,
    URLAnalysisResponse,
    BulkURLAnalysisRequest,
    BulkURLAnalysisResponse,
    EmailURLExtractionRequest
)
from analyzers.attachment_scanner import attachment_scanner
from analyzers.url_inspector import url_inspector
from utils.url_extractor import url_extractor
from auth.permissions import get_current_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/analyze",
    tags=["🔬 Анализ вложений и URL"],
)


# ============================================================================
# ATTACHMENT ENDPOINTS
# ============================================================================

@router.post(
    "/attachments",
    response_model=AttachmentScanResponse,
    summary="📎 Анализ вложения (base64)",
    description="""
    **Комплексный анализ email вложения**

    ## 🔍 Что проверяется:

    ### 1️⃣ Статический анализ (мгновенно)
    - ❌ Опасные расширения (.exe, .scr, .bat, .js, .vbs)
    - 🎭 Двойные расширения (.pdf.exe, .docx.scr)
    - 📏 Размер файла (слишком маленький = подозрительно)
    - 🏷️ MIME type и magic bytes
    - 🎯 Подозрительные имена файлов

    ### 2️⃣ Обнаружение макросов (для Office)
    - 📊 Поиск VBA макросов в .doc, .xls, .ppt
    - 🔍 Детекция AutoOpen, Auto_Open
    - ⚠️ Scoring: 0-100 (риск макросов)

    ### 3️⃣ VirusTotal (опционально, ~1-2 сек)
    - 🔐 SHA256 hash lookup
    - 🌐 70+ антивирусных движков
    - 📊 Статистика обнаружений

    ### 4️⃣ Sandbox анализ (опционально, ~30-60 сек)
    - 🧪 Cuckoo Sandbox execution
    - 🌐 Network activity monitoring
    - 📁 File system modifications
    - ⚙️ Registry changes
    - 🚨 Behavioral signatures

    ## 📊 Risk Levels

    | Level | Score | Action |
    |-------|-------|--------|
    | 🟢 Low | 0-29 | SAFE - Appears clean |
    | 🟡 Medium | 30-49 | CAUTION - Scan with AV |
    | 🟠 High | 50-69 | QUARANTINE - Review |
    | 🔴 Critical | 70-100 | BLOCK - Do not open |

    ## ⚡ Performance

    - **Fast mode** (no sandbox): ~100-200ms
    - **Full scan** (with sandbox): ~30-60 seconds

    ## 🔐 Security

    - Max file size: 25 MB
    - Files are NOT stored
    - Analysis in isolated environment
    """,
    responses={
        200: {"description": "✅ Анализ успешно завершен"},
        400: {"description": "❌ Невалидный base64 или формат"},
        401: {"description": "🔒 Требуется аутентификация"},
        413: {"description": "📦 Файл слишком большой (>25 MB)"},
        500: {"description": "⚠️ Ошибка сервера"}
    }
)
async def scan_attachment_base64(
    request: AttachmentScanRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Scan email attachment from base64 encoded data
    """
    try:
        # Decode base64
        try:
            file_content = base64.b64decode(request.file_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 encoding: {str(e)}"
            )

        # Check file size
        max_size = 25 * 1024 * 1024  # 25 MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(file_content)} bytes (max: {max_size})"
            )

        # Scan attachment
        result = await attachment_scanner.scan_attachment(
            filename=request.filename,
            file_content=file_content,
            enable_sandbox=request.enable_sandbox,
            enable_virustotal=request.enable_virustotal
        )

        logger.info(
            f"Attachment scanned: {request.filename} - "
            f"Risk: {result['overall_risk']['level']}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Attachment scan error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Scan error: {str(e)}"
        )


@router.post(
    "/attachments/upload",
    response_model=AttachmentScanResponse,
    summary="📤 Анализ вложения (загрузка файла)",
    description="""
    **Загрузка и анализ файла**

    Альтернативный способ анализа - прямая загрузка файла.

    ## 📋 Параметры

    - **file**: Файл для анализа (multipart/form-data)
    - **enable_sandbox**: Включить sandbox (bool, опционально)
    - **enable_virustotal**: Включить VirusTotal (bool, опционально)

    ## 📝 Пример curl

    ```bash
    curl -X POST http://localhost:8000/api/v1/analyze/attachments/upload \\
      -H "Authorization: Bearer test-token" \\
      -F "file=@suspicious.exe" \\
      -F "enable_sandbox=false" \\
      -F "enable_virustotal=true"
    ```
    """,
    responses={
        200: {"description": "✅ Анализ успешно завершен"},
        400: {"description": "❌ Файл не предоставлен"},
        401: {"description": "🔒 Требуется аутентификация"},
        413: {"description": "📦 Файл слишком большой"},
        500: {"description": "⚠️ Ошибка сервера"}
    }
)
async def scan_attachment_upload(
    file: UploadFile = File(...),
    enable_sandbox: bool = Form(False),
    enable_virustotal: bool = Form(True),
    current_user: dict = Depends(get_current_user)
):
    """
    Scan uploaded file
    """
    try:
        # Read file content
        file_content = await file.read()

        # Check file size
        max_size = 25 * 1024 * 1024  # 25 MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(file_content)} bytes (max: {max_size})"
            )

        # Scan attachment
        result = await attachment_scanner.scan_attachment(
            filename=file.filename,
            file_content=file_content,
            enable_sandbox=enable_sandbox,
            enable_virustotal=enable_virustotal
        )

        logger.info(
            f"Uploaded file scanned: {file.filename} - "
            f"Risk: {result['overall_risk']['level']}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload scan error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Scan error: {str(e)}"
        )


# ============================================================================
# URL ENDPOINTS
# ============================================================================

@router.post(
    "/urls",
    response_model=URLAnalysisResponse,
    summary="🔗 Анализ URL",
    description="""
    **Комплексный анализ URL на фишинг и вредоносность**

    ## 🔍 Что проверяется:

    ### 1️⃣ Структурный анализ
    - 🌐 IP адрес вместо домена
    - 👤 Credentials в URL (user:pass@domain)
    - 🔢 Необычные порты
    - 📊 Избыточные поддомены (>3)
    - 🔗 URL shorteners (bit.ly, tinyurl, и др.)
    - 🎭 Display text mismatch (<a href="evil.com">bank.com</a>)

    ### 2️⃣ Фишинг-паттерны
    - 🔑 Suspicious keywords: login, verify, account, secure
    - 🏦 Brand impersonation (paypal.evil.com)
    - 🎯 Path-based phishing (/secure-login)

    ### 3️⃣ Homograph атаки
    - 🌍 IDN/Punycode домены (xn--)
    - 🔤 Mixing character sets (Latin + Cyrillic)
    - 👁️ Look-alike domains (g00gle.com)

    ### 4️⃣ VirusTotal репутация
    - 🌐 URL scan (70+ движков)
    - 🏠 Domain reputation check
    - 📊 Malicious/Suspicious counts

    ### 5️⃣ Возраст домена (опционально)
    - 📅 WHOIS lookup
    - ⚠️ Новые домены (<30 дней) = риск

    ## 📊 Risk Levels

    | Level | Score | Action |
    |-------|-------|--------|
    | 🟢 Low | 0-29 | SAFE - Appears legitimate |
    | 🟡 Medium | 30-49 | SUSPICIOUS - Proceed with caution |
    | 🟠 High | 50-69 | DANGEROUS - Likely phishing |
    | 🔴 Critical | 70-100 | BLOCK - Do not visit |

    ## ⚡ Performance

    - **Fast mode** (no VT): ~50-100ms
    - **Full scan** (with VT): ~1-2 seconds

    ## 🔐 URLs не посещаются

    Анализ выполняется БЕЗ фактического посещения URL.
    """,
    responses={
        200: {"description": "✅ Анализ успешно завершен"},
        400: {"description": "❌ Невалидный URL"},
        401: {"description": "🔒 Требуется аутентификация"},
        500: {"description": "⚠️ Ошибка сервера"}
    }
)
async def analyze_url(
    request: URLAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze single URL for phishing and malware
    """
    try:
        result = await url_inspector.analyze_url(
            url=request.url,
            display_text=request.display_text,
            enable_virustotal=request.enable_virustotal
        )

        logger.info(
            f"URL analyzed: {request.url} - "
            f"Risk: {result['overall_risk']['level']}"
        )

        return result

    except Exception as e:
        logger.error(f"URL analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis error: {str(e)}"
        )


@router.post(
    "/urls/bulk",
    response_model=BulkURLAnalysisResponse,
    summary="🔗 Массовый анализ URL",
    description="""
    **Анализ нескольких URL одновременно**

    ## 📋 Параметры

    - **urls**: Список URL (максимум 50)
    - **enable_virustotal**: Включить VirusTotal (bool)

    ## ⚡ Параллельная обработка

    Все URL анализируются параллельно для максимальной скорости.

    ## 📊 Результат

    Возвращает:
    - Полные результаты для каждого URL
    - Общее количество высокорисковых URL
    - Время анализа

    ## 🔒 Лимиты

    - Максимум 50 URL за запрос
    - Rate limiting применяется для VirusTotal
    """,
    responses={
        200: {"description": "✅ Анализ успешно завершен"},
        400: {"description": "❌ Невалидные URL или слишком много"},
        401: {"description": "🔒 Требуется аутентификация"},
        500: {"description": "⚠️ Ошибка сервера"}
    }
)
async def analyze_bulk_urls(
    request: BulkURLAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze multiple URLs in parallel
    """
    try:
        start_time = datetime.utcnow()

        # Analyze all URLs in parallel
        results = await url_inspector.analyze_multiple_urls(
            urls=request.urls,
            enable_virustotal=request.enable_virustotal
        )

        # Count high-risk URLs
        high_risk_count = sum(
            1 for r in results
            if r.get('overall_risk', {}).get('level') in ['high', 'critical']
        )

        scan_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"Bulk URL analysis: {len(request.urls)} URLs, "
            f"{high_risk_count} high-risk"
        )

        return {
            'total_urls': len(request.urls),
            'results': results,
            'high_risk_count': high_risk_count,
            'scan_time': scan_time,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Bulk URL analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis error: {str(e)}"
        )


@router.post(
    "/urls/extract-from-email",
    response_model=BulkURLAnalysisResponse,
    summary="📧 Извлечь и проанализировать URL из письма",
    description="""
    **Извлечение всех URL из email и их анализ**

    ## 🔍 Откуда извлекаются URL:

    ### 1️⃣ Plain text body
    - Regex поиск http(s):// паттернов

    ### 2️⃣ HTML body
    - Парсинг <a href="..."> ссылок
    - Extraction display text для mismatch detection

    ### 3️⃣ Email headers
    - List-Unsubscribe
    - List-Subscribe
    - X-* custom headers

    ## 📊 Результат

    Для каждого найденного URL:
    - Полный анализ безопасности
    - Display text mismatch detection
    - Все проверки как в `/urls`

    ## ⚡ Use case

    ```python
    # Analyze all URLs in phishing email
    POST /api/v1/analyze/urls/extract-from-email
    {
      "body_html": "<a href='http://evil.com'>Click here</a>",
      "body_text": "Visit: http://another-bad-site.com",
      "enable_virustotal": true
    }
    ```

    ## 📝 Automatic deduplication

    Duplicate URLs are automatically removed.
    """,
    responses={
        200: {"description": "✅ URL извлечены и проанализированы"},
        400: {"description": "❌ Невалидные данные"},
        401: {"description": "🔒 Требуется аутентификация"},
        500: {"description": "⚠️ Ошибка сервера"}
    }
)
async def extract_and_analyze_urls_from_email(
    request: EmailURLExtractionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Extract all URLs from email and analyze them
    """
    try:
        start_time = datetime.utcnow()

        # Extract URLs
        extracted_urls = url_extractor.extract_all_urls(
            body_text=request.body_text,
            body_html=request.body_html,
            headers=request.headers
        )

        if not extracted_urls:
            return {
                'total_urls': 0,
                'results': [],
                'high_risk_count': 0,
                'scan_time': 0.0,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Analyze each URL
        analysis_tasks = []
        for url_info in extracted_urls:
            task = url_inspector.analyze_url(
                url=url_info['url'],
                display_text=url_info.get('display_text'),
                enable_virustotal=request.enable_virustotal
            )
            analysis_tasks.append(task)

        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    'url': extracted_urls[i]['url'],
                    'error': str(result),
                    'overall_risk': {'level': 'unknown'}
                })
            else:
                final_results.append(result)

        # Count high-risk
        high_risk_count = sum(
            1 for r in final_results
            if r.get('overall_risk', {}).get('level') in ['high', 'critical']
        )

        scan_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"Email URL extraction: {len(extracted_urls)} URLs found, "
            f"{high_risk_count} high-risk"
        )

        return {
            'total_urls': len(extracted_urls),
            'results': final_results,
            'high_risk_count': high_risk_count,
            'scan_time': scan_time,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Email URL extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Extraction error: {str(e)}"
        )


# Missing import
import asyncio
