"""
WebSocket Integration Utilities

Helper functions to integrate WebSocket notifications with existing services:
- Alert notifications
- Email analysis results
- Registry updates

Author: SPEAR-GUARD Team
Date: 2026-01-27
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from websocket_manager import connection_manager

logger = logging.getLogger(__name__)


async def notify_alert_created(alert_data: Dict[str, Any], recipient_user_id: Optional[int] = None):
    """
    Send WebSocket notification when a new alert is created
    
    Args:
        alert_data: Alert data dict (from Alert model)
        recipient_user_id: User ID to notify (if None, broadcast to all)
    """
    try:
        notification = {
            "id": alert_data.get("id"),
            "type": alert_data.get("alert_type"),
            "severity": alert_data.get("severity"),
            "title": alert_data.get("title"),
            "message": alert_data.get("message"),
            "sender_email": alert_data.get("sender_email"),
            "recipient_email": alert_data.get("recipient_email"),
            "created_at": alert_data.get("created_at")
        }
        
        if recipient_user_id:
            await connection_manager.send_alert(notification, user_id=recipient_user_id)
            logger.info(f"Alert notification sent to user {recipient_user_id}")
        else:
            await connection_manager.send_alert(notification)
            logger.info("Alert notification broadcast to all users")
            
    except Exception as e:
        logger.error(f"Error sending alert notification: {e}")


async def notify_email_analysis_complete(
    analysis_data: Dict[str, Any],
    user_id: int
):
    """
    Send WebSocket notification when email analysis is complete
    
    Args:
        analysis_data: Analysis result data
        user_id: User ID who requested the analysis
    """
    try:
        notification = {
            "message_id": analysis_data.get("message_id"),
            "from_address": analysis_data.get("from_address"),
            "to_address": analysis_data.get("to_address"),
            "subject": analysis_data.get("subject"),
            "risk_score": analysis_data.get("risk_score"),
            "status": analysis_data.get("status"),
            "in_registry": analysis_data.get("in_registry"),
            "analyzed_at": analysis_data.get("analyzed_at")
        }
        
        await connection_manager.send_email_analysis_result(notification, user_id)
        logger.info(f"Email analysis notification sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending email analysis notification: {e}")


async def notify_registry_updated(
    action: str,
    email_address: str,
    trust_level: Optional[int] = None,
    status: Optional[str] = None
):
    """
    Send WebSocket notification when registry is updated
    
    Args:
        action: Action performed (added, updated, removed, approved)
        email_address: Email address affected
        trust_level: New trust level (if applicable)
        status: New status (if applicable)
    """
    try:
        notification = {
            "action": action,
            "email_address": email_address,
            "trust_level": trust_level,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection_manager.send_registry_update(notification)
        logger.info(f"Registry update notification broadcast: {action} {email_address}")
        
    except Exception as e:
        logger.error(f"Error sending registry update notification: {e}")


async def notify_threat_detected(
    threat_data: Dict[str, Any],
    affected_user_ids: Optional[list] = None
):
    """
    Send WebSocket notification when a threat is detected
    
    Args:
        threat_data: Threat data dict
        affected_user_ids: List of user IDs to notify (if None, broadcast)
    """
    try:
        notification = {
            "threat_type": threat_data.get("threat_type"),
            "severity": threat_data.get("severity"),
            "description": threat_data.get("description"),
            "source": threat_data.get("source"),
            "indicators": threat_data.get("indicators"),
            "detected_at": datetime.utcnow().isoformat()
        }
        
        message = {
            "type": "threat_alert",
            "data": notification,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if affected_user_ids:
            for user_id in affected_user_ids:
                await connection_manager.send_to_user(message, user_id)
            logger.info(f"Threat notification sent to {len(affected_user_ids)} users")
        else:
            await connection_manager.broadcast(message)
            logger.info("Threat notification broadcast to all users")
            
    except Exception as e:
        logger.error(f"Error sending threat notification: {e}")


async def notify_system_status(
    status: str,
    message: str,
    severity: str = "info"
):
    """
    Send system status notification to all connected clients
    
    Args:
        status: Status type (maintenance, degraded, operational)
        message: Status message
        severity: Severity level (info, warning, critical)
    """
    try:
        notification = {
            "type": "system_status",
            "data": {
                "status": status,
                "message": message,
                "severity": severity
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection_manager.broadcast(notification)
        logger.info(f"System status notification broadcast: {status}")
        
    except Exception as e:
        logger.error(f"Error sending system status notification: {e}")
