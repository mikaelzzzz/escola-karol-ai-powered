import requests
from app.core.config import settings

def processar_voz(numero, texto, voice_id="EXAVITQu4vr4xnSDxMaL", model_id="eleven_multilingual_v2"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": texto,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.content  # Áudio em bytes (mp3)
    else:
        raise Exception(f"Erro ElevenLabs: {response.status_code} - {response.text}") 