from fastapi import APIRouter
from app.models.gramatica_models import GramaticaRequest
from app.services.gramatica_service import processar_duvida_gramatical

router = APIRouter()

@router.post("/duvida")
async def duvida_gramatical(request: GramaticaRequest):
    return processar_duvida_gramatical(request.numero, request.texto) 