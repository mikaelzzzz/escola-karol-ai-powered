import aiohttp
from app.core.config import settings
import logging
import base64

logger = logging.getLogger(__name__)

async def enviar_mensagem_zapi(numero, mensagem):
    """
    Envia uma mensagem de texto via Z-API.
    """
    url = f"https://api.z-api.io/instances/{settings.ZAPI_INSTANCE_ID}/token/{settings.ZAPI_TOKEN}/send-text"
    payload = {
        "phone": numero,
        "message": mensagem
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": settings.ZAPI_SECURITY_TOKEN,
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Mensagem enviada para {numero}")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"Erro ao enviar mensagem para {numero}: {text}")
                    return False
        except Exception as e:
            logger.error(f"Exceção ao enviar mensagem para {numero}: {str(e)}")
            return False

async def enviar_audio_zapi(numero, audio_bytes):
    """
    Envia um áudio (mp3) via Z-API.
    """
    url = f"https://api.z-api.io/instances/{settings.ZAPI_INSTANCE_ID}/token/{settings.ZAPI_TOKEN}/send-audio"
    
    # Converte os bytes do áudio para base64
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    payload = {
        "phone": numero,
        "audio": f"data:audio/mpeg;base64,{audio_base64}",
        "waveform": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Client-Token": settings.ZAPI_SECURITY_TOKEN,
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Áudio enviado para {numero}")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"Erro ao enviar áudio para {numero}: {text}")
                    return False
        except Exception as e:
            logger.error(f"Exceção ao enviar áudio para {numero}: {str(e)}")
            return False

