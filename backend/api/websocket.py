"""
WebSocket API Endpoints

Provides WebSocket endpoints for real-time notifications:
- /ws/{user_id} - Main WebSocket endpoint
- WebSocket authentication via token
- Real-time alerts and updates

Author: SPEAR-GUARD Team
Date: 2026-01-27
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.exceptions import HTTPException

from websocket_manager import connection_manager
from auth.permissions import get_current_user_from_token, CurrentUser

router = APIRouter(
    prefix="/ws",
    tags=["🔌 WebSocket"]
)

logger = logging.getLogger(__name__)


async def get_user_from_ws_token(token: str) -> CurrentUser:
    """
    Authenticate WebSocket connection via token
    
    Args:
        token: JWT token
        
    Returns:
        CurrentUser object
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        user = await get_current_user_from_token(token)
        return user
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(..., description="JWT authentication token"),
    client_type: str = Query("unknown", description="Client type: dashboard, extension, mobile")
):
    """
    Main WebSocket endpoint for real-time notifications
    
    **Authentication:** Requires valid JWT token in query parameter
    
    **Message Types:**
    - `connection_established` - Sent on successful connection
    - `alert` - Security alert notification
    - `email_analysis` - Email analysis result
    - `registry_update` - Registry update notification
    - `ping` - Heartbeat ping (expect pong response)
    
    **Example:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/123?token=YOUR_JWT_TOKEN&client_type=dashboard');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data.type, data);
    };
    ```
    """
    
    # Authenticate user
    try:
        current_user = await get_user_from_ws_token(token)
        
        # Verify user_id matches token
        if current_user.id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning(f"User ID mismatch: token={current_user.id}, path={user_id}")
            return
            
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Connect to manager
    await connection_manager.connect(websocket, user_id, client_type)
    
    try:
        # Listen for messages from client
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "pong":
                # Heartbeat response
                logger.debug(f"Received pong from user {user_id}")
                
            elif message_type == "subscribe":
                # Client wants to subscribe to specific events
                logger.info(f"User {user_id} subscribed to: {data.get('events', [])}")
                
            elif message_type == "unsubscribe":
                # Client wants to unsubscribe from events
                logger.info(f"User {user_id} unsubscribed from: {data.get('events', [])}")
                
            else:
                logger.warning(f"Unknown message type from user {user_id}: {message_type}")
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected: user_id={user_id}")
        
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        connection_manager.disconnect(websocket)


@router.get("/stats", summary="Get WebSocket statistics")
async def get_websocket_stats(
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """
    Get WebSocket connection statistics
    
    **Requires:** Authentication
    
    **Returns:**
    - Active connections count
    - Active users count
    - Total connections ever
    - Total messages sent
    - Connections by client type
    """
    return connection_manager.get_stats()
