import requests
from app.core.config import settings
from app.models.whatsapp_mapping import WhatsAppMapping
from sqlalchemy.orm import Session
import time
from openai import OpenAI
import json
from app.services.notion_service import NotionService

class FlexgeService:
    def __init__(self, db: Session = None):
        self.base_url = settings.FLEXGE_API_BASE
        self.api_key = settings.FLEXGE_API_KEY
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.db = db
        self.notion_service = NotionService()
    
    def generate_headers(self):
        return {
            "x-api-key": self.api_key,
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-Request-ID": str(time.time())
        }
    
    async def get_students(self, page: int = 1):
        url = f"{self.base_url}/students?page={page}"
        resp = requests.get(url, headers=self.generate_headers(), timeout=10)
        return resp.json() if resp.status_code == 200 else None
    
    async def buscar_aluno_por_email(self, email: str):
        """
        Busca um aluno pelo email, primeiro no Notion e depois no Flexge
        """
        # Primeiro buscar no Notion para ter os dados completos
        aluno_notion = await self.notion_service.buscar_aluno_por_email(email)
        if not aluno_notion:
            # Se não encontrar no Notion, buscar no Flexge
            page = 1
            while True:
                data = await self.get_students(page)
                if not data or not data.get("docs"):
                    return None
                for aluno in data["docs"]:
                    if aluno["email"].lower() == email.lower():
                        return aluno
                if page >= data["pages"]:
                    break
                page += 1
            return None
            
        # Se encontrou no Notion, buscar dados complementares no Flexge
        page = 1
        while True:
            data = await self.get_students(page)
            if not data or not data.get("docs"):
                break
            for aluno in data["docs"]:
                if aluno["email"].lower() == email.lower():
                    # Mesclar dados do Notion com dados do Flexge
                    return {
                        **aluno,
                        "whatsapp": aluno_notion["whatsapp"],
                        "notion_id": aluno_notion["notion_id"],
                        "status_notion": aluno_notion["status"]
                    }
            if page >= data["pages"]:
                break
            page += 1
                
        # Se não encontrou no Flexge, retornar apenas dados do Notion
        return aluno_notion

    async def buscar_aluno_por_numero(self, phone: str):
        """
        Busca um aluno pelo número de WhatsApp usando o Notion
        """
        # Buscar diretamente no Notion
        aluno_notion = await self.notion_service.buscar_aluno_por_whatsapp(phone)
        if not aluno_notion:
            return None
            
        # Se encontrou no Notion, buscar dados complementares no Flexge
        if aluno_notion["email"]:
            page = 1
            while True:
                data = await self.get_students(page)
                if not data or not data.get("docs"):
                    break
                for aluno in data["docs"]:
                    if aluno["email"].lower() == aluno_notion["email"].lower():
                        # Mesclar dados do Notion com dados do Flexge
                        return {
                            **aluno,
                            "whatsapp": aluno_notion["whatsapp"],
                            "notion_id": aluno_notion["notion_id"],
                            "status_notion": aluno_notion["status"]
                        }
                if page >= data["pages"]:
                    break
                page += 1
                    
        # Se não encontrou no Flexge, retornar apenas dados do Notion
        return aluno_notion
        
    async def associar_whatsapp(self, phone: str, email: str):
        """
        Associa um número de WhatsApp a um email de aluno
        """
        if not self.db:
            return False
            
        try:
            # Verificar se o aluno existe no Flexge
            aluno = await self.buscar_aluno_por_email(email)
            if not aluno:
                return False
                
            # Formatar o número
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('55'):
                phone = '55' + phone
                
            # Criar ou atualizar o mapeamento
            mapping = WhatsAppMapping(phone=phone, email=email)
            self.db.merge(mapping)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao associar WhatsApp: {str(e)}")
            return False

    async def patch_student_action(self, student_id: str, action: str):
        url = f"{self.base_url}/students/{action}"
        payload = {"students": [student_id]}
        return requests.patch(url, headers=self.generate_headers(), json=payload, timeout=10)
    
    async def buscar_erros_gramatica(self, aluno_id: str):
        url = f"{self.base_url}/students/{aluno_id}/studied-grammars?page=1"
        resp = requests.get(url, headers=self.generate_headers(), timeout=10)
        return resp.json() if resp.status_code == 200 else None
    
    async def buscar_resultados_mastery(self, aluno_id: str):
        url = f"{self.base_url}/students/{aluno_id}/mastery-tests?page=1"
        resp = requests.get(url, headers=self.generate_headers(), timeout=10)
        return resp.json() if resp.status_code == 200 else None
    
    async def gerar_resposta_gpt(self, topico: str):
        prompt = f"""
        Crie uma explicação completa sobre '{topico}' com:
        - 1 definição simples
        - 3 exemplos bilíngues (EN → PT)
        - 2 dicas práticas
        Formato: Texto simples com no máximo 5 linhas"""
        
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um professor de inglês direto e prático, que ensina alunos com TDAH"},
                    {"role": "user", "content": prompt}
                ],
                timeout=10
            )
            return resp.choices[0].message.content
        except Exception:
            return f"Explicação sobre {topico} não disponível no momento. Por favor tente mais tarde."

    async def buscar_detalhes_prova(self, aluno_id: str):
        """
        Busca detalhes das provas recentes do aluno
        """
        try:
            # Buscar mastery tests
            url_tests = f"{self.base_url}/students/{aluno_id}/mastery-tests"
            resp_tests = requests.get(url_tests, headers=self.generate_headers(), timeout=10)
            if resp_tests.status_code != 200:
                return None
                
            mastery_tests = resp_tests.json()
            resultados = []
            
            # Pegar os 3 testes mais recentes
            for test in mastery_tests[:3]:
                mastery_test_id = test["_id"]
                
                # Buscar execuções desse mastery test
                url_exec = f"{self.base_url}/students/{aluno_id}/mastery-tests/{mastery_test_id}/executions"
                resp_exec = requests.get(url_exec, headers=self.generate_headers(), timeout=10)
                if resp_exec.status_code != 200:
                    continue
                    
                execucoes = resp_exec.json()
                for execucao in execucoes:
                    execution_id = execucao["_id"]
                    
                    # Buscar respostas do aluno nessa execução
                    url_items = f"{self.base_url}/students/{aluno_id}/mastery-tests/{mastery_test_id}/executions/{execution_id}/items"
                    resp_items = requests.get(url_items, headers=self.generate_headers(), timeout=10)
                    if resp_items.status_code != 200:
                        continue
                        
                    respostas = resp_items.json()
                    resultados.append({
                        "test_name": test.get("name", ""),
                        "test_date": execucao.get("startedAt", ""),
                        "score": execucao.get("score", 0),
                        "total_questions": len(respostas),
                        "correct_answers": sum(1 for r in respostas if r.get("isCorrect", False)),
                        "questions": [{
                            "question": r.get("question", ""),
                            "correct_answer": r.get("correctAnswer", ""),
                            "student_answer": r.get("studentAnswer", ""),
                            "is_correct": r.get("isCorrect", False)
                        } for r in respostas]
                    })
            
            return resultados
            
        except Exception as e:
            print(f"Erro ao buscar detalhes da prova: {str(e)}")
            return None

def generate_headers():
    return {
        "x-api-key": settings.FLEXGE_API_KEY,
        "accept": "application/json",
        "Content-Type": "application/json"
    }

def buscar_aluno_por_numero(numero):
    # Aqui você pode adaptar para buscar por telefone, email, etc.
    url = f"{settings.FLEXGE_API_BASE}/students?page=1"
    resp = requests.get(url, headers=generate_headers(), timeout=10)
    if resp.status_code != 200:
        return None
    alunos = resp.json().get("docs", [])
    for aluno in alunos:
        if aluno.get("phone") == numero or aluno.get("numero") == numero:
            return aluno
    return None

def processar_mastery_test(numero):
    aluno = buscar_aluno_por_numero(numero)
    if not aluno:
        return {"erro": "Aluno não encontrado"}
    student_id = aluno["_id"]
    # 1. Buscar todos os mastery tests do aluno
    url_tests = f"{settings.FLEXGE_API_BASE}/students/{student_id}/mastery-tests"
    resp_tests = requests.get(url_tests, headers=generate_headers(), timeout=10)
    if resp_tests.status_code != 200:
        return {"erro": "Não foi possível buscar mastery tests"}
    mastery_tests = resp_tests.json()
    resultados = []
    for test in mastery_tests:
        mastery_test_id = test["_id"]
        # 2. Buscar execuções desse mastery test
        url_exec = f"{settings.FLEXGE_API_BASE}/students/{student_id}/mastery-tests/{mastery_test_id}/executions"
        resp_exec = requests.get(url_exec, headers=generate_headers(), timeout=10)
        if resp_exec.status_code != 200:
            continue
        execucoes = resp_exec.json()
        for execucao in execucoes:
            execution_id = execucao["_id"]
            # 3. Buscar respostas do aluno nessa execução
            url_items = f"{settings.FLEXGE_API_BASE}/students/{student_id}/mastery-tests/{mastery_test_id}/executions/{execution_id}/items"
            resp_items = requests.get(url_items, headers=generate_headers(), timeout=10)
            if resp_items.status_code != 200:
                continue
            respostas = resp_items.json()
            resultados.append({
                "mastery_test": test,
                "execucao": execucao,
                "respostas": respostas
            })
    return {"aluno": aluno, "resultados": resultados} 