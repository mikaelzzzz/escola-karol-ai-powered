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
                    return {"success": True}
                else:
                    error_text = await response.text()
                    logger.error(f"Erro ao enviar mensagem: {error_text}")
                    return {"error": error_text}
        except Exception as e:
            logger.error(f"Exceção ao enviar mensagem: {str(e)}")
            return {"error": str(e)}

async def enviar_audio_zapi(numero, audio_bytes):
    """
    Envia um áudio via Z-API.
    O áudio deve estar em formato OGG.
    """
    url = f"https://api.z-api.io/instances/{settings.ZAPI_INSTANCE_ID}/token/{settings.ZAPI_TOKEN}/send-audio/base64"
    
    try:
        # Codificar o áudio em base64
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        payload = {
            "phone": numero,
            "base64": audio_base64
        }
        
        headers = {
            "Content-Type": "application/json",
            "Client-Token": settings.ZAPI_SECURITY_TOKEN,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Áudio enviado para {numero}")
                    return {"success": True}
                else:
                    error_text = await response.text()
                    logger.error(f"Erro ao enviar áudio: {error_text}")
                    return {"error": error_text}
                    
    except Exception as e:
        logger.error(f"Exceção ao enviar áudio: {str(e)}")
        return {"error": str(e)}

