from fastapi import APIRouter
from app.models.webhook_models import WebhookPayload
from app.services.zaia_service import detectar_intencao
from app.services.flexge_service import processar_mastery_test
from app.services.gramatica_service import processar_duvida_gramatical
from app.services.financeiro_service import processar_boleto
from app.services.voice_service import processar_voz
from app.utils.zapi_utils import enviar_mensagem_zapi, enviar_audio_zapi
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/zapi")
async def webhook_zapi(payload: WebhookPayload):
    try:
        logger.info(f"Recebido webhook do Z-API: {payload.dict()}")
        
        numero = payload.phone
        tipo = payload.type
        texto = payload.text if payload.text else ""
        
        if tipo not in ["message", "audio", "image", "document"]:
            logger.info(f"Tipo de mensagem não suportado: {tipo}")
            return {"status": "ignored"}
            
        # Se for áudio, pegar a URL
        if tipo == "audio" and payload.audio:
            audio_url = payload.audio.get("url")
            if audio_url:
                texto = await processar_voz(audio_url)
        
        # Se for imagem, pegar a URL
        elif tipo == "image" and payload.image:
            image_url = payload.image.get("url")
            if image_url:
                texto = f"[Imagem recebida: {image_url}]"
        
        # Se for documento, pegar a URL
        elif tipo == "document" and payload.document:
            document_url = payload.document.get("url")
            if document_url:
                texto = f"[Documento recebido: {document_url}]"

        # Detectar intenção
        intencao = detectar_intencao(texto, numero)
        logger.info(f"Intenção detectada: {intencao}")

        # Rotear para o serviço correto
        if intencao == "reenviar_boleto":
            resposta = processar_boleto(numero)
            await enviar_mensagem_zapi(numero, resposta)
        elif intencao == "ajuda_prova_flexge":
            resposta = processar_mastery_test(numero)
            await enviar_mensagem_zapi(numero, resposta)
        elif intencao == "duvida_gramatical":
            resposta = processar_duvida_gramatical(numero, texto)
            await enviar_mensagem_zapi(numero, resposta)
        elif intencao == "resposta_audio":
            resposta = processar_voz(numero, texto)
            await enviar_audio_zapi(numero, resposta)
        else:
            await enviar_mensagem_zapi(numero, "Desculpe, não entendi sua solicitação.")

        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return {"status": "error", "message": str(e)} 