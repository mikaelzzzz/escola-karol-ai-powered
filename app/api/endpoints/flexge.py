from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services.flexge_service import FlexgeService
from app.services.whatsapp_service import WhatsAppService
from app.services.email_service import EmailService
from app.core.config import settings
import datetime

router = APIRouter()
flexge_service = FlexgeService()
whatsapp_service = WhatsAppService()
email_service = EmailService()

class EmailRequest(BaseModel):
    email: str

@router.post("/explicacao-gramatica")
async def explicacao_gramatica(request_data: EmailRequest):
    try:
        aluno = await flexge_service.buscar_aluno_por_email(request_data.email)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        erros = await flexge_service.buscar_erros_gramatica(aluno["id"])
        if not erros:
            return {"resposta": "🌟 Nenhum erro recente!", "status": "sucesso"}

        resposta = "📊 *Análise Flexge* 📊\n\n"
        for erro in sorted(erros, key=lambda x: x["errorPercentage"], reverse=True)[:3]:
            explicacao = await flexge_service.gerar_resposta_gpt(erro["name"])
            resposta += f"📌 **{erro['name']} ({erro['errorPercentage']}%)**\n{explicacao}\n-------------------------\n"

        return {"resposta": resposta.strip(), "status": "sucesso"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mastery-test")
async def mastery_test(request_data: EmailRequest):
    try:
        aluno = await flexge_service.buscar_aluno_por_email(request_data.email)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        # Buscar resultados dos testes do aluno
        resultados = await flexge_service.buscar_resultados_mastery(aluno["id"])
        if not resultados:
            return {"resposta": "🌟 Nenhum teste recente encontrado!", "status": "sucesso"}

        resposta = "📝 *Análise dos Mastery Tests* 📝\n\n"
        for teste in resultados[:3]:  # Últimos 3 testes
            explicacao = await flexge_service.gerar_resposta_gpt(f"Mastery Test {teste['level']}")
            resposta += f"📌 **Nível {teste['level']} - {teste['score']}%**\n"
            resposta += f"Tópicos: {teste['topics']}\n"
            resposta += f"Dicas: {explicacao}\n-------------------------\n"

        return {"resposta": resposta.strip(), "status": "sucesso"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/habilitar-aluno")
async def habilitar_aluno(request_data: EmailRequest):
    try:
        aluno = await flexge_service.buscar_aluno_por_email(request_data.email)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        
        resp = await flexge_service.patch_student_action(aluno["id"], "enable")
        if resp.status_code == 200:
            return {"status": "Aluno habilitado com sucesso"}
        
        raise HTTPException(status_code=400, detail=resp.text)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/desabilitar-aluno")
async def desabilitar_aluno(request_data: EmailRequest):
    try:
        aluno = await flexge_service.buscar_aluno_por_email(request_data.email)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        
        resp = await flexge_service.patch_student_action(aluno["id"], "disable")
        if resp.status_code == 200:
            return {"status": "Aluno desabilitado com sucesso"}
        
        raise HTTPException(status_code=400, detail=resp.text)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-inatividade")
async def check_inatividade(background_tasks: BackgroundTasks):
    try:
        page = 1
        bloqueados = 0
        avisados = 0
        hoje = datetime.datetime.utcnow()
        
        while True:
            dados = await flexge_service.get_students(page)
            if not dados or not dados.get("docs"):
                break
            
            for aluno in dados["docs"]:
                last_access = aluno.get("lastAccess")
                if not last_access:
                    continue
                
                dias_inativo = (hoje - datetime.datetime.fromisoformat(last_access.replace("Z", "+00:00"))).days
                
                if dias_inativo >= 10:
                    # Desabilitar aluno
                    await flexge_service.patch_student_action(aluno["id"], "disable")
                    bloqueados += 1
                elif dias_inativo >= 8:
                    # Enviar email de aviso
                    background_tasks.add_task(
                        email_service.send_inactivity_email,
                        aluno["email"],
                        aluno["name"].split()[0]
                    )
                    avisados += 1
            
            page += 1
        
        return {"bloqueados": bloqueados, "avisados": avisados}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 