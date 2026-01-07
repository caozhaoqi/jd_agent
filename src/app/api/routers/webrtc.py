import os
from fastapi import APIRouter, Depends
from livekit.api import access_token
from livekit.api.access_token import VideoGrants
from api.deps import get_current_user
from core.models import User

router = APIRouter()


@router.get("/token")
async def get_livekit_token(user: User = Depends(get_current_user)):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    room_name = f"agent-room-{user.id}"
    
    token = access_token.AccessToken(api_key, api_secret)
    token = token.with_identity(f"user_{user.id}")
    token = token.with_grants(VideoGrants(room_join=True, room=room_name))
    
    return {"token": token.to_jwt(), "url": os.getenv("LIVEKIT_URL")}
