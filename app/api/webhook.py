from fastapi import APIRouter
from app.models.webhook_models import WebhookPayload
from app.services.zaia_service import detectar_intencao
from app.services.flexge_service import processar_mastery_test
from app.services.gramatica_service import processar_duvida_gramatical
from app.services.financeiro_service import processar_boleto
from app.services.voice_service import processar_voz
from app.utils.zapi_utils import enviar_mensagem_zapi, enviar_audio_zapi

router = APIRouter()

@router.post("/zapi")
async def webhook_zapi(payload: WebhookPayload):
    numero = payload.from_
    tipo = payload.type
    texto = payload.body if payload.body else ""

    # 1. Detecta tipo de mensagem
    # (Se quiser, trate audio_url e image_url aqui)

    # 2. Chama Zaia para entender intenção
    intencao = detectar_intencao(texto, numero)

    # 3. Roteia para o serviço correto
    if intencao == "reenviar_boleto":
        resposta = processar_boleto(numero)
        enviar_mensagem_zapi(numero, resposta)
    elif intencao == "ajuda_prova_flexge":
        resposta = processar_mastery_test(numero)
        enviar_mensagem_zapi(numero, resposta)
    elif intencao == "duvida_gramatical":
        resposta = processar_duvida_gramatical(numero, texto)
        enviar_mensagem_zapi(numero, resposta)
    elif intencao == "resposta_audio":
        resposta = processar_voz(numero, texto)
        enviar_audio_zapi(numero, resposta)
    else:
        enviar_mensagem_zapi(numero, "Desculpe, não entendi sua solicitação.")
    return {"status": "ok"} 