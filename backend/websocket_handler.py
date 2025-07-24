"""
WebSocket handler for real-time communication
Implements comprehensive WebSocket support for the legal AI application
"""
import json
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from sqlalchemy.orm import Session
import jwt
from models import User, Organization, ChatSession, ChatMessage
from database import get_db
# Authentication disabled - no imports needed
from config import settings

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections with organization-level isolation"""
    
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, WebSocket] = {}
        # Store user metadata for connections
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        # Store organization memberships
        self.user_organizations: Dict[str, str] = {}
        # Store presence status
        self.user_presence: Dict[str, str] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, organization_id: str, user_data: dict):
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        
        # Store connection with metadata
        self.active_connections[user_id] = websocket
        self.connection_metadata[user_id] = {
            "user_id": user_id,
            "organization_id": organization_id,
            "connected_at": datetime.utcnow().isoformat(),
            "user_data": user_data
        }
        self.user_organizations[user_id] = organization_id
        self.user_presence[user_id] = "online"
        
        logger.info(f"WebSocket connected", extra={
            "user_id": user_id,
            "organization_id": organization_id,
            "total_connections": len(self.active_connections)
        })
        
        # Broadcast user presence to organization members
        await self.broadcast_to_organization(
            organization_id, 
            {
                "type": "user_presence", 
                "data": {
                    "user_id": user_id,
                    "status": "online",
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            exclude_user=user_id
        )
    
    async def disconnect(self, user_id: str):
        """Remove WebSocket connection and cleanup"""
        if user_id in self.active_connections:
            organization_id = self.user_organizations.get(user_id)
            
            # Remove from all tracking dictionaries
            self.active_connections.pop(user_id, None)
            self.connection_metadata.pop(user_id, None)
            self.user_organizations.pop(user_id, None)
            self.user_presence.pop(user_id, None)
            
            logger.info(f"WebSocket disconnected", extra={
                "user_id": user_id,
                "organization_id": organization_id,
                "remaining_connections": len(self.active_connections)
            })
            
            # Broadcast user offline status to organization
            if organization_id:
                await self.broadcast_to_organization(
                    organization_id,
                    {
                        "type": "user_presence",
                        "data": {
                            "user_id": user_id,
                            "status": "offline",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )
    
    async def send_personal_message(self, user_id: str, message: dict):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Failed to send personal message", extra={
                    "user_id": user_id,
                    "error": str(e)
                })
                # Remove broken connection
                await self.disconnect(user_id)
                return False
        return False
    
    async def broadcast_to_organization(self, organization_id: str, message: dict, exclude_user: Optional[str] = None):
        """Broadcast message to all users in organization"""
        sent_count = 0
        failed_users = []
        
        for user_id, user_org_id in self.user_organizations.items():
            if user_org_id == organization_id and user_id != exclude_user:
                success = await self.send_personal_message(user_id, message)
                if success:
                    sent_count += 1
                else:
                    failed_users.append(user_id)
        
        logger.info(f"Organization broadcast completed", extra={
            "organization_id": organization_id,
            "sent_count": sent_count,
            "failed_count": len(failed_users),
            "message_type": message.get("type", "unknown")
        })
        
        return {"sent": sent_count, "failed": len(failed_users)}
    
    async def update_presence(self, user_id: str, status: str):
        """Update user presence status"""
        if user_id in self.user_presence:
            old_status = self.user_presence[user_id]
            self.user_presence[user_id] = status
            
            organization_id = self.user_organizations.get(user_id)
            if organization_id and old_status != status:
                await self.broadcast_to_organization(
                    organization_id,
                    {
                        "type": "user_presence",
                        "data": {
                            "user_id": user_id,
                            "status": status,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    },
                    exclude_user=user_id
                )
    
    def get_organization_users(self, organization_id: str) -> List[dict]:
        """Get list of online users in organization"""
        org_users = []
        for user_id, user_org_id in self.user_organizations.items():
            if user_org_id == organization_id:
                metadata = self.connection_metadata.get(user_id, {})
                org_users.append({
                    "user_id": user_id,
                    "status": self.user_presence.get(user_id, "online"),
                    "connected_at": metadata.get("connected_at"),
                    "user_data": metadata.get("user_data", {})
                })
        return org_users
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        org_counts = {}
        for user_id, org_id in self.user_organizations.items():
            org_counts[org_id] = org_counts.get(org_id, 0) + 1
        
        return {
            "total_connections": len(self.active_connections),
            "organization_counts": org_counts,
            "presence_status": dict(self.user_presence)
        }

# Global connection manager instance
manager = ConnectionManager()

async def authenticate_websocket_token(token: str, db: Session) -> tuple[User, Organization]:
    """No authentication - return anonymous user/org objects"""
    try:
        # Create anonymous user object
        class AnonymousUser:
            def __init__(self):
                self.id = "anonymous-user"
                self.email = "[email@example.com]"
                self.organization_id = "anonymous-org"
        
        # Create anonymous organization object
        class AnonymousOrg:
            def __init__(self):
                self.id = "anonymous-org"
                self.name = "Demo Organization"
        
        return AnonymousUser(), AnonymousOrg()
    
    except Exception as e:
        logger.error(f"WebSocket setup failed: {str(e)}")
        raise HTTPException(status_code=500, detail="WebSocket setup failed")

class WebSocketHandler:
    """Main WebSocket message handler"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def handle_message(self, websocket: WebSocket, user: User, organization: Organization, message: dict):
        """Handle incoming WebSocket message"""
        message_type = message.get("type", "unknown")
        data = message.get("data", {})
        
        try:
            if message_type == "ping":
                await self.handle_ping(websocket, user)
            elif message_type == "chat_message":
                await self.handle_chat_message(websocket, user, organization, data)
            elif message_type == "presence_update":
                await self.handle_presence_update(websocket, user, organization, data)
            elif message_type == "subscribe":
                await self.handle_subscribe(websocket, user, organization, data)
            elif message_type == "unsubscribe":
                await self.handle_unsubscribe(websocket, user, organization, data)
            elif message_type == "document_update":
                await self.handle_document_update(websocket, user, organization, data)
            else:
                logger.warning(f"Unknown WebSocket message type", extra={
                    "type": message_type,
                    "user_id": user.id,
                    "organization_id": organization.id
                })
                await self.send_error(websocket, f"Unknown message type: {message_type}")
        
        except Exception as e:
            logger.error(f"Error handling WebSocket message", extra={
                "error": str(e),
                "message_type": message_type,
                "user_id": user.id,
                "organization_id": organization.id
            })
            await self.send_error(websocket, f"Message processing failed: {str(e)}")
    
    async def handle_ping(self, websocket: WebSocket, user: User):
        """Handle ping/keepalive message"""
        await websocket.send_text(json.dumps({
            "type": "pong",
            "data": {"timestamp": datetime.utcnow().isoformat()}
        }))
    
    async def handle_chat_message(self, websocket: WebSocket, user: User, organization: Organization, data: dict):
        """Handle real-time chat message"""
        session_id = data.get("sessionId")
        content = data.get("content", "")
        
        if not session_id or not content:
            await self.send_error(websocket, "Missing sessionId or content")
            return
        
        # Verify session belongs to organization
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.organization_id == organization.id
        ).first()
        
        if not session:
            await self.send_error(websocket, "Chat session not found")
            return
        
        # Save message to database
        message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=content,
            timestamp=datetime.utcnow()
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        # Broadcast to organization members (for collaborative features)
        await manager.broadcast_to_organization(
            organization.id,
            {
                "type": "chat_message",
                "data": {
                    "sessionId": session_id,
                    "messageId": message.id,
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "userId": user.id
                }
            },
            exclude_user=user.id
        )
        
        # Send confirmation to sender
        await websocket.send_text(json.dumps({
            "type": "chat_message_ack",
            "data": {
                "messageId": message.id,
                "status": "saved",
                "timestamp": message.timestamp.isoformat()
            }
        }))
    
    async def handle_presence_update(self, websocket: WebSocket, user: User, organization: Organization, data: dict):
        """Handle user presence status update"""
        status = data.get("status", "online")
        if status not in ["online", "away", "busy", "offline"]:
            await self.send_error(websocket, "Invalid presence status")
            return
        
        await manager.update_presence(user.id, status)
        
        # Confirm update to sender
        await websocket.send_text(json.dumps({
            "type": "presence_updated",
            "data": {
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        }))
    
    async def handle_subscribe(self, websocket: WebSocket, user: User, organization: Organization, data: dict):
        """Handle subscription to real-time updates"""
        subscription_type = data.get("type")
        resource_id = data.get("resourceId")
        
        if subscription_type == "document" and resource_id:
            # Subscribe to document updates
            await websocket.send_text(json.dumps({
                "type": "subscription_confirmed",
                "data": {
                    "type": subscription_type,
                    "resourceId": resource_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }))
        else:
            await self.send_error(websocket, "Invalid subscription request")
    
    async def handle_unsubscribe(self, websocket: WebSocket, user: User, organization: Organization, data: dict):
        """Handle unsubscription from real-time updates"""
        subscription_type = data.get("type")
        resource_id = data.get("resourceId")
        
        await websocket.send_text(json.dumps({
            "type": "unsubscription_confirmed",
            "data": {
                "type": subscription_type,
                "resourceId": resource_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }))
    
    async def handle_document_update(self, websocket: WebSocket, user: User, organization: Organization, data: dict):
        """Handle document update notifications"""
        document_id = data.get("documentId")
        update_type = data.get("updateType", "modified")
        
        if not document_id:
            await self.send_error(websocket, "Missing documentId")
            return
        
        # Broadcast document update to organization
        await manager.broadcast_to_organization(
            organization.id,
            {
                "type": "document_update",
                "data": {
                    "documentId": document_id,
                    "updateType": update_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "userId": user.id
                }
            },
            exclude_user=user.id
        )
    
    async def send_error(self, websocket: WebSocket, error_message: str):
        """Send error message to WebSocket client"""
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }))

# Helper functions for broadcasting to connected clients
async def broadcast_document_update(organization_id: str, document_id: str, update_type: str = "modified", user_id: str = None):
    """Broadcast document update to all organization members"""
    await manager.broadcast_to_organization(
        organization_id,
        {
            "type": "document_update",
            "data": {
                "documentId": document_id,
                "updateType": update_type,
                "timestamp": datetime.utcnow().isoformat(),
                "userId": user_id
            }
        },
        exclude_user=user_id
    )

async def broadcast_notification(organization_id: str, notification: dict, user_id: str = None):
    """Broadcast notification to organization members"""
    await manager.broadcast_to_organization(
        organization_id,
        {
            "type": "notification",
            "data": {
                **notification,
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        exclude_user=user_id
    )

async def send_user_notification(user_id: str, notification: dict):
    """Send notification to specific user"""
    await manager.send_personal_message(
        user_id,
        {
            "type": "notification",
            "data": {
                **notification,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
