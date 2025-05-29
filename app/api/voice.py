from fastapi import APIRouter, HTTPException
from app.services.voice_service import text_to_speech
from app.schemas.voice import VoiceRequest, VoiceResponse

router = APIRouter()

@router.post("/generate", response_model=VoiceResponse)
async def generate_voice(request: VoiceRequest):
    """
    Gera áudio a partir de texto usando ElevenLabs
    """
    try:
        audio_data = await text_to_speech(request.text)
        return VoiceResponse(audio=audio_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 