import os
import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from livekit.api import access_token
from livekit.api.access_token import VideoGrants
from api.deps import get_current_user
from core.models import User
import asyncio

router = APIRouter()

# WebRTC连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()


@router.get("/token")
async def get_livekit_token(user: User = Depends(get_current_user)):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    room_name = f"agent-room-{user.id}"
    
    token = access_token.AccessToken(api_key, api_secret)
    token = token.with_identity(f"user_{user.id}")
    token = token.with_grants(VideoGrants(room_join=True, room=room_name))
    
    return {"token": token.to_jwt(), "url": os.getenv("LIVEKIT_URL")}


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebRTC信令服务器
    处理offer/answer和ICE候选者交换
    """
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            # 处理不同类型的信令消息
            if data["type"] == "offer":
                # 处理offer，生成answer
                # 这里可以集成LLM处理逻辑
                await manager.send_personal_message(
                    {"type": "offer_received", "message": "Offer received"},
                    user_id
                )
            elif data["type"] == "answer":
                # 处理answer
                await manager.send_personal_message(
                    {"type": "answer_received", "message": "Answer received"},
                    user_id
                )
            elif data["type"] == "candidate":
                # 处理ICE候选者
                await manager.send_personal_message(
                    {"type": "candidate_received", "message": "Candidate received"},
                    user_id
                )
            elif data["type"] == "interrupt":
                # 处理打断请求
                await manager.send_personal_message(
                    {"type": "interrupt_ack", "message": "Interrupt acknowledged"},
                    user_id
                )
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)
