from fastapi import APIRouter
from app.models.voice_models import VoiceRequest
from app.services.voice_service import processar_voz

router = APIRouter()

@router.post("/clonar")
async def clonar_voz(request: VoiceRequest):
    return processar_voz(request.numero, request.texto) 