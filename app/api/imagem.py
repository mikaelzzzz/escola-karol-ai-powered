from fastapi import APIRouter, UploadFile, File
from app.services.imagem_service import analisar_imagem

router = APIRouter()

@router.post("/analisar")
async def analisar(file: UploadFile = File(...)):
    return await analisar_imagem(file) 