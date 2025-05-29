from fastapi import APIRouter, HTTPException, Request
from app.services.whatsapp_service import WhatsAppService
from app.services.flexge_service import FlexgeService
from app.services.elevenlabs_service import text_to_speech
from app.core.config import settings
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
async def associate_whatsapp(request: WhatsAppAssociationRequest):
    """
    Associa um número de WhatsApp ao email de um aluno no Notion
    Requer código de verificação enviado por email
    """
    flexge_service = FlexgeService()
    whatsapp_service = WhatsAppService()
    
    try:
        # TODO: Implementar verificação do código enviado por email
        
        # Verificar se o aluno existe no Notion
        aluno = await flexge_service.buscar_aluno_por_email(request.email)
        if not aluno:
            raise HTTPException(
                status_code=400,
                detail="Email não encontrado no sistema."
            )
        
        # TODO: Atualizar o número de WhatsApp no Notion
        # Esta funcionalidade deve ser implementada no NotionService
        
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
        logger.info(f"Webhook recebido: {webhook_data}")

        # Ignorar mensagens de grupo
        if webhook_data.get("isGroup") or "group" in str(webhook_data.get("phone", "")):
            logger.info("Mensagem de grupo ignorada.")
            return {"status": "ignored", "message": "Mensagem de grupo não processada."}

        # Extrair texto da mensagem para ReceivedCallback
        if webhook_data.get("type") == "ReceivedCallback":
            logger.info("Processando ReceivedCallback")
            webhook_data["type"] = "message"
            if isinstance(webhook_data.get("text"), dict):
                webhook_data["text"] = webhook_data["text"].get("message", "")
            logger.info(f"Mensagem normalizada: {webhook_data}")
        
        # Verificar se é um tipo de mensagem suportado
        if webhook_data.get("type") not in ["message", "audio", "image", "document"]:
            logger.info(f"Tipo de mensagem não suportado: {webhook_data.get('type')}")
            return {"status": "ignored"}
        
        # Processar mensagem
        service = WhatsAppService()
        resultado = await service.processar_webhook(webhook_data)
        
        if resultado.get("error"):
            logger.error(f"Erro no processamento do webhook: {resultado['error']}")
            if resultado["error"] == "Aluno não encontrado":
                # Enviar mensagem educada informando que não foi encontrado
                await service.enviar_mensagem_texto(
                    webhook_data.get("phone"),
                    "Olá! Não consegui encontrar seu cadastro. Por favor, verifique se seu número está registrado corretamente no sistema."
                )
            raise HTTPException(status_code=400, detail=resultado["error"])
        
        # Processar a mensagem com a Zaia
        logger.info(f"Processando mensagem com Zaia: {resultado}")
        resposta, usar_audio = await service.process_with_zaia(
            resultado.get("message", ""),
            resultado.get("aluno"),
            resultado.get("contexto"),
            resultado.get("phone", webhook_data.get("phone"))
        )
        logger.info(f"Resposta da Zaia: {resposta}, usar_audio: {usar_audio}")
        
        # Enviar resposta
        if usar_audio and settings.ELEVENLABS_API_KEY and webhook_data.get("type") == "audio":
            try:
                # Converter texto em áudio
                audio_data = await text_to_speech(resposta)
                if audio_data:
                    # Enviar áudio diretamente sem tentar serializar para JSON
                    await service.enviar_audio(webhook_data.get("phone"), audio_data)
                else:
                    await service.enviar_mensagem_texto(webhook_data.get("phone"), resposta)
            except Exception as e:
                logger.error(f"Erro ao processar áudio: {str(e)}")
                # Fallback para mensagem de texto em caso de erro
                await service.enviar_mensagem_texto(webhook_data.get("phone"), resposta)
        else:
            logger.info(f"Enviando resposta como texto para {webhook_data.get('phone')}")
            await service.enviar_mensagem_texto(webhook_data.get("phone"), resposta)
        
        return {"status": "success", "message": "Mensagem processada com sucesso"}
        
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