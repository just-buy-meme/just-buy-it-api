from fastapi import APIRouter

from app.api.routes import utils
from app.api.routes import trading_monitor
from app.api.routes import chat
from app.api.routes import recommendation

api_router = APIRouter()
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(trading_monitor.router, tags=["trading_monitor"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(recommendation.router, tags=["recommendation"])