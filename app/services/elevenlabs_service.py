from app.core.config import settings
import requests
import json
import os
from datetime import datetime

async def text_to_speech(text: str, voice_id: str = None):
    """
    Converte texto em áudio usando a API do ElevenLabs
    """
    try:
        # Se não for especificado um voice_id, usar o padrão das configurações
        voice_id = voice_id or settings.ELEVENLABS_VOICE_ID
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": settings.ELEVENLABS_API_KEY
        }

        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Erro na API do ElevenLabs: {response.text}")
            
    except Exception as e:
        raise Exception(f"Erro na síntese de voz: {str(e)}") 