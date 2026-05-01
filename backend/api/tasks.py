from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from pydantic import BaseModel

from auth.permissions import get_current_user, CurrentUser, require_security_officer
from tasks.registry_tasks import (
    auto_populate_registry_task,
    update_trust_scores_task,
    import_from_ad_task,
    import_from_egrul_task,
    trigger_manual_import
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class TaskTriggerRequest(BaseModel):
    """Request to trigger a task"""
    dry_run: bool = True
    months_back: Optional[int] = 6
    min_emails: Optional[int] = 10
    min_reply_rate: Optional[float] = 30.0


class ManualImportRequest(BaseModel):
    """Request to trigger manual import"""
    source: str = "all"  # 'all', 'history', 'ad', or 'egrul'
    dry_run: bool = True


@router.post("/auto-populate", summary="Trigger auto-populate from email history")
async def trigger_auto_populate(
    request: TaskTriggerRequest,
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Manually trigger automatic registry population from email history

    Requires: Security Officer role

    This task normally runs daily at 02:00 Moscow time
    """
    try:
        # Trigger task asynchronously
        task = auto_populate_registry_task.apply_async(
            kwargs={
                "months_back": request.months_back,
                "min_emails": request.min_emails,
                "min_reply_rate": request.min_reply_rate,
                "dry_run": request.dry_run
            }
        )

        return {
            "status": "triggered",
            "task_id": task.id,
            "message": "Auto-populate task has been queued",
            "dry_run": request.dry_run
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )


@router.post("/update-trust-scores", summary="Trigger trust score update")
async def trigger_trust_score_update(
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Manually trigger trust score recalculation for existing entries

    Requires: Security Officer role

    This task normally runs daily at 03:00 Moscow time
    """
    try:
        task = update_trust_scores_task.apply_async()

        return {
            "status": "triggered",
            "task_id": task.id,
            "message": "Trust score update task has been queued"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )


@router.post("/import-ad", summary="Trigger Active Directory import")
async def trigger_ad_import(
    dry_run: bool = True,
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Manually trigger import from Active Directory

    Requires: Security Officer role

    This task normally runs weekly on Monday at 01:00 Moscow time
    """
    try:
        task = import_from_ad_task.apply_async(
            kwargs={"dry_run": dry_run}
        )

        return {
            "status": "triggered",
            "task_id": task.id,
            "message": "AD import task has been queued",
            "dry_run": dry_run
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )


@router.post("/import-egrul", summary="Trigger EGRUL import")
async def trigger_egrul_import(
    min_contract_count: int = 5,
    dry_run: bool = True,
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Manually trigger import from EGRUL (Russian business registry)

    Requires: Security Officer role

    This task normally runs monthly on the 1st at 01:00 Moscow time
    """
    try:
        task = import_from_egrul_task.apply_async(
            kwargs={
                "min_contract_count": min_contract_count,
                "dry_run": dry_run
            }
        )

        return {
            "status": "triggered",
            "task_id": task.id,
            "message": "EGRUL import task has been queued",
            "dry_run": dry_run
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )


@router.post("/import-all", summary="Trigger all import tasks")
async def trigger_all_imports(
    request: ManualImportRequest,
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Manually trigger all import tasks at once

    Requires: Security Officer role

    Sources:
    - 'all': Run all import tasks
    - 'history': Only email history analysis
    - 'ad': Only Active Directory
    - 'egrul': Only EGRUL
    """
    try:
        task = trigger_manual_import.apply_async(
            kwargs={
                "source": request.source,
                "dry_run": request.dry_run
            }
        )

        return {
            "status": "triggered",
            "task_id": task.id,
            "message": f"Manual import task has been queued (source: {request.source})",
            "dry_run": request.dry_run
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )


@router.get("/status/{task_id}", summary="Get task status")
async def get_task_status(
    task_id: str,
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Get the status of a Celery task

    Requires: Security Officer role
    """
    try:
        from celery.result import AsyncResult
        from config.celery_config import celery_app

        task_result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "status": task_result.status,
            "ready": task_result.ready()
        }

        if task_result.ready():
            if task_result.successful():
                response["result"] = task_result.result
            else:
                response["error"] = str(task_result.info)

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )
