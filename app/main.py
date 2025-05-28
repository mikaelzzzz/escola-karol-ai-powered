from fastapi import FastAPI
from app.api import webhook, financeiro, flexge, gramatica, imagem, voice

app = FastAPI()

app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
app.include_router(financeiro.router, prefix="/financeiro", tags=["Financeiro"])
app.include_router(flexge.router, prefix="/flexge", tags=["Flexge"])
app.include_router(gramatica.router, prefix="/gramatica", tags=["Gramatica"])
app.include_router(imagem.router, prefix="/imagem", tags=["Imagem"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"]) 