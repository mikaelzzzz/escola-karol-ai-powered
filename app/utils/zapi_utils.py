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
            logger.info(f"Enviando mensagem para {numero}. URL: {url}")
            logger.info(f"Payload: {payload}")
            async with session.post(url, headers=headers, json=payload) as response:
                response_text = await response.text()
                logger.info(f"Resposta do Z-API: Status={response.status}, Body={response_text}")
                if response.status == 200:
                    logger.info(f"Mensagem enviada para {numero}")
                    return {"success": True}
                else:
                    error_text = f"Status: {response.status}, Response: {response_text}"
                    logger.error(f"Erro ao enviar mensagem: {error_text}")
                    return {"error": error_text}
        except Exception as e:
            logger.error(f"Exceção ao enviar mensagem: {str(e)}")
            return {"error": str(e)}

async def enviar_audio_zapi(numero: str, audio_bytes: bytes):
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
            "Client-Token": settings.ZAPI_SECURITY_TOKEN
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response_data = await response.json()
                if response.status == 200 and response_data.get("sent", False):
                    logger.info(f"Áudio enviado para {numero}")
                    return {"success": True}
                else:
                    error_text = f"Status: {response.status}, Response: {response_data}"
                    logger.error(f"Erro ao enviar áudio: {error_text}")
                    return {"error": error_text}
                    
    except Exception as e:
        logger.error(f"Exceção ao enviar áudio: {str(e)}")
        return {"error": str(e)}

