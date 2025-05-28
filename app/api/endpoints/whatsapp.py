from fastapi import APIRouter, HTTPException, Request, Depends
from app.services.whatsapp_service import WhatsAppService
from app.services.flexge_service import FlexgeService
from app.services.elevenlabs_service import text_to_speech
from app.db.session import get_db
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import json
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class WhatsAppAssociationRequest(BaseModel):
    phone: str
    email: str
    verification_code: str  # Código enviado por email para verificação

@router.post("/associate")
async def associate_whatsapp(
    request: WhatsAppAssociationRequest,
    db: Session = Depends(get_db)
):
    """
    Associa um número de WhatsApp ao email de um aluno
    Requer código de verificação enviado por email
    """
    flexge_service = FlexgeService(db)
    whatsapp_service = WhatsAppService()
    
    try:
        # TODO: Implementar verificação do código enviado por email
        
        # Associar o número ao email
        success = await flexge_service.associar_whatsapp(request.phone, request.email)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível associar o número. Verifique se o email está cadastrado no Flexge."
            )
        
        # Enviar mensagem de confirmação
        await whatsapp_service.enviar_mensagem_texto(
            request.phone,
            "Seu número foi associado com sucesso! Agora você pode conversar com a Karol."
        )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Erro na associação de WhatsApp: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def zapi_webhook(request: Request):
    """
    Endpoint para receber webhooks do Z-API
    """
    try:
        webhook_data = await request.json()
        
        # Verificar se é um tipo de mensagem suportado
        if webhook_data.get("type") not in ["message", "audio", "image", "document"]:
            return {"status": "ignored"}
        
        # Processar a mensagem
        whatsapp_service = WhatsAppService()
        result = await whatsapp_service.processar_webhook(webhook_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        phone = result["phone"]
        message = result["message"]
        message_type = result["type"]
        
        # Identificar aluno pelo número do WhatsApp
        flexge_service = FlexgeService()
        aluno = await flexge_service.buscar_aluno_por_numero(phone)
        if not aluno:
            # Registrar tentativa de contato para follow-up
            logger.info(f"Tentativa de contato de número não cadastrado - {datetime.now().isoformat()}")
            logger.info(f"Número: {phone}")
            logger.info(f"Mensagem: {message}")
            return {"status": "número não cadastrado"}
        
        # Processar a mensagem com a Zaia
        zaia_response, usar_audio = await whatsapp_service.process_with_zaia(message, aluno)
        
        # Enviar resposta de acordo com o tipo de mensagem original
        await whatsapp_service.enviar_resposta(phone, zaia_response, message_type)
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def check_status():
    """
    Endpoint para verificar status da conexão com WhatsApp
    """
    try:
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 