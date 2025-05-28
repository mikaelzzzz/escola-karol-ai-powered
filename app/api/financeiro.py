from fastapi import APIRouter
from app.models.financeiro_models import EmailRequest
from app.services.financeiro_service import processar_boleto

router = APIRouter()

@router.post("/reenviar-boleto")
async def reenviar_boleto(request: EmailRequest):
    return processar_boleto(request.email) 