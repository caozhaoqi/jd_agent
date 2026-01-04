import os
from fastapi import APIRouter, Depends
from livekit import api
from api.deps import get_current_user
from core.models import User

router = APIRouter()


@router.get("/token")
async def get_livekit_token(user: User = Depends(get_current_user)):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    grant = api.VideoGrant(room_join=True, agent=True)
    token = api.AccessToken(api_key, api_secret, identity=f"user_{user.id}")
    token.add_grant(grant)
    return {"token": token.to_jwt(), "url": os.getenv("LIVEKIT_URL")}
