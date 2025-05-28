from fastapi import APIRouter
from app.services.flexge_service import processar_mastery_test

router = APIRouter()

@router.get("/mastery-test/{numero}")
async def mastery_test(numero: str):
    return processar_mastery_test(numero) 