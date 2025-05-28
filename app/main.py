from fastapi import FastAPI
from app.api import webhook, financeiro, flexge, gramatica, imagem, voice
from app.api.endpoints import whatsapp

app = FastAPI()

app.include_router(webhook.router, prefix="/api/webhook", tags=["Webhook"])
app.include_router(financeiro.router, prefix="/api/financeiro", tags=["Financeiro"])
app.include_router(flexge.router, prefix="/api/flexge", tags=["Flexge"])
app.include_router(gramatica.router, prefix="/api/gramatica", tags=["Gramatica"])
app.include_router(imagem.router, prefix="/api/imagem", tags=["Imagem"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["WhatsApp"]) 