"""
WebSocket Connection Manager

Manages WebSocket connections for real-time notifications:
- Connection lifecycle (connect/disconnect)
- Broadcasting messages to all clients
- Sending targeted messages to specific users
- Heartbeat/ping-pong for connection health

Author: SPEAR-GUARD Team
Date: 2026-01-27
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications
    
    Features:
    - Multiple connections per user (browser + extension)
    - Broadcasting to all connected clients
    - Targeted messages to specific users
    - Connection health monitoring
    """
    
    def __init__(self):
        # Active connections: {user_id: {websocket1, websocket2, ...}}
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        
        # Connection metadata: {websocket: {"user_id": int, "connected_at": datetime, ...}}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Statistics
        self.total_connections = 0
        self.total_messages_sent = 0
        
        logger.info("WebSocket ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, user_id: int, client_type: str = "unknown"):
        """
        Accept and register a new WebSocket connection
        
        Args:
            websocket: WebSocket instance
            user_id: User ID
            client_type: Type of client (dashboard, extension, mobile)
        """
        await websocket.accept()
        
        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "client_type": client_type,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        self.total_connections += 1
        
        logger.info(
            f"WebSocket connected: user_id={user_id}, client_type={client_type}, "
            f"total_connections={len(self.connection_metadata)}"
        )
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection_established",
                "message": "Connected to SPEAR-GUARD real-time notifications",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection
        
        Args:
            websocket: WebSocket instance to remove
        """
        metadata = self.connection_metadata.get(websocket)
        
        if metadata:
            user_id = metadata["user_id"]
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Remove user entry if no more connections
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(
                f"WebSocket disconnected: user_id={user_id}, "
                f"remaining_connections={len(self.connection_metadata)}"
            )
        else:
            logger.warning("Attempted to disconnect unknown WebSocket")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection
        
        Args:
            message: Message dict to send
            websocket: Target WebSocket
        """
        try:
            await websocket.send_json(message)
            self.total_messages_sent += 1
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def send_to_user(self, message: dict, user_id: int):
        """
        Send a message to all connections of a specific user
        
        Args:
            message: Message dict to send
            user_id: Target user ID
        """
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user_id={user_id}")
            return
        
        # Send to all user's connections
        disconnected = []
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
                self.total_messages_sent += 1
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)
    
    async def broadcast(self, message: dict, exclude_user_id: Optional[int] = None):
        """
        Broadcast a message to all connected clients
        
        Args:
            message: Message dict to broadcast
            exclude_user_id: Optional user ID to exclude from broadcast
        """
        disconnected = []
        sent_count = 0
        
        for websocket, metadata in self.connection_metadata.items():
            user_id = metadata["user_id"]
            
            # Skip excluded user
            if exclude_user_id and user_id == exclude_user_id:
                continue
            
            try:
                await websocket.send_json(message)
                self.total_messages_sent += 1
                sent_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)
        
        logger.debug(f"Broadcast sent to {sent_count} clients")
    
    async def send_alert(self, alert_data: dict, user_id: Optional[int] = None):
        """
        Send an alert notification
        
        Args:
            alert_data: Alert data dict
            user_id: If specified, send only to this user; otherwise broadcast
        """
        message = {
            "type": "alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            await self.send_to_user(message, user_id)
        else:
            await self.broadcast(message)
    
    async def send_email_analysis_result(self, analysis_data: dict, user_id: int):
        """
        Send email analysis result to user
        
        Args:
            analysis_data: Analysis result data
            user_id: Target user ID
        """
        message = {
            "type": "email_analysis",
            "data": analysis_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_user(message, user_id)
    
    async def send_registry_update(self, registry_data: dict):
        """
        Broadcast registry update to all clients
        
        Args:
            registry_data: Registry update data
        """
        message = {
            "type": "registry_update",
            "data": registry_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message)
    
    async def ping_all(self):
        """
        Send ping to all connections to check health
        """
        message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected = []
        
        for websocket, metadata in self.connection_metadata.items():
            try:
                await websocket.send_json(message)
                metadata["last_ping"] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Ping failed for user {metadata['user_id']}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)
    
    def get_stats(self) -> dict:
        """
        Get connection statistics
        
        Returns:
            Dict with statistics
        """
        return {
            "active_connections": len(self.connection_metadata),
            "active_users": len(self.active_connections),
            "total_connections_ever": self.total_connections,
            "total_messages_sent": self.total_messages_sent,
            "connections_by_type": self._get_connections_by_type()
        }
    
    def _get_connections_by_type(self) -> dict:
        """Get count of connections by client type"""
        counts = {}
        for metadata in self.connection_metadata.values():
            client_type = metadata.get("client_type", "unknown")
            counts[client_type] = counts.get(client_type, 0) + 1
        return counts


# Global singleton instance
connection_manager = ConnectionManager()


async def heartbeat_task():
    """
    Background task to send periodic pings to all connections
    """
    while True:
        await asyncio.sleep(30)  # Ping every 30 seconds
        try:
            await connection_manager.ping_all()
            logger.debug("Heartbeat ping sent to all connections")
        except Exception as e:
            logger.error(f"Heartbeat task error: {e}")
