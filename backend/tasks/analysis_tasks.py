"""
Celery task for analyzing emails.
Runs linguistic and technical analysis on synced emails.
"""
from celery.utils.log import get_task_logger
from sqlalchemy.future import select

from config.celery_config import celery_app
from database import AsyncSessionLocal, EmailAnalysis
from analyzers.linguistic_analyzer import LinguisticAnalyzer
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.behavioral_analyzer import BehavioralAnalyzer
from analyzers.contextual_analyzer import ContextualAnalyzer

# Import tasks base class to reuse async runner
from tasks.mail_sync import MailSyncTask

logger = get_task_logger(__name__)

# Initialize analyzers
linguistic = LinguisticAnalyzer()
technical = TechnicalAnalyzer()
contextual = ContextualAnalyzer()

@celery_app.task(
    bind=True,
    base=MailSyncTask,
    name="tasks.analysis_tasks.analyze_email_task",
    max_retries=3
)
def analyze_email_task(self, analysis_id: int):
    """
    Run analysis pipeline on a synced email.
    Updates risk_score and detailed scores in the database.
    """
    async def _analyze():
        async with AsyncSessionLocal() as db:
            from services.analysis_service import AnalysisService
            service = AnalysisService(db)
            
            # 1. Fetch analysis record
            result = await db.execute(
                select(EmailAnalysis).where(EmailAnalysis.id == analysis_id)
            )
            analysis = result.scalar_one_or_none()
            
            if not analysis:
                logger.error(f"Analysis record {analysis_id} not found")
                return
            
            logger.info(f"Analyzing email {analysis.id}: {analysis.subject}")
            
            try:
                # 2. Perform Analysis (No Persistence)
                headers = analysis.raw_headers or {}
                
                results = await service.perform_full_analysis(
                    from_address=analysis.from_address,
                    to_address=analysis.to_address,
                    subject=analysis.subject,
                    headers=headers,
                    body=analysis.body_text,
                    # We pass body as preview if body_preview is missing, 
                    # but perform_full_analysis handles that internally for contextual analyzer
                )
                
                # 3. Update Existing Record
                analysis.risk_score = results["risk_score"]
                
                # Determine status based on risk score (Simple Logic matching Service)
                # BUG-23 fix: use >= for consistent boundary handling
                if analysis.risk_score >= 90: analysis.status = "danger"
                elif analysis.risk_score >= 70: analysis.status = "warning"
                elif analysis.risk_score >= 40: analysis.status = "caution"
                else: analysis.status = "safe"
                
                # Update sub-scores
                analysis.technical_score = results["technical"].get("authentication", {}).get("score", 0)
                analysis.linguistic_score = results["linguistic"].get("risk_score", 0)
                analysis.behavioral_score = results["behavioral"].get("score", 0)
                analysis.contextual_score = results["contextual"].get("score", 0)
                analysis.analysis_details = results.get("analysis_details", {})
                
                await db.commit()
                
                logger.info(f"Email {analysis.id} analyzed. Score: {analysis.risk_score}, Status: {analysis.status}")
                
                return {
                    "id": analysis.id,
                    "score": analysis.risk_score,
                    "status": analysis.status
                }

            except Exception as e:
                logger.error(f"Analysis pipeline failed for {analysis.id}: {e}", exc_info=True)
                analysis.status = "error"
                await db.commit()
                return None

    return self.run_async(_analyze())
