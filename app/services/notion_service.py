from app.core.config import settings
import requests
import json
from typing import Optional, Dict

class NotionService:
    def __init__(self):
        self.api_key = settings.NOTION_API_KEY
        self.database_id = settings.NOTION_DATABASE_ID
        self.base_url = "https://api.notion.com/v1"
        
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
    async def buscar_aluno_por_whatsapp(self, phone: str) -> Optional[Dict]:
        """
        Busca dados do aluno pelo número do WhatsApp no banco do Notion
        """
        try:
            # Formatar número para garantir consistência (remover caracteres especiais)
            phone_formatted = ''.join(filter(str.isdigit, phone))
            print(f"Buscando aluno no Notion com telefone: {phone} -> formatado: {phone_formatted}")
            
            # Construir a query para o Notion
            url = f"{self.base_url}/databases/{self.database_id}/query"
            payload = {
                "filter": {
                    "property": "Telefone",
                    "rich_text": {
                        "contains": phone_formatted
                    }
                }
            }
            
            print(f"URL da consulta: {url}")
            print(f"Payload da consulta: {json.dumps(payload, indent=2)}")
            print(f"Headers: {self._get_headers()}")
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload
            )
            
            print(f"Status da resposta: {response.status_code}")
            print(f"Resposta completa: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            if not data.get("results"):
                print("Nenhum resultado encontrado no Notion")
                return None
                
            # Pegar o primeiro resultado
            student = data["results"][0]
            properties = student["properties"]
            
            print(f"Propriedades encontradas: {list(properties.keys())}")
            
            # Mapear os dados do aluno com os campos corretos
            return {
                "id": student["id"],
                "nome": properties.get("Student Name", {}).get("title", [{}])[0].get("text", {}).get("content", ""),
                "email": properties.get("Email", {}).get("email", ""),
                "telefone": properties.get("Telefone", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "cpf": properties.get("CPF", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "plano": properties.get("Plano", {}).get("select", {}).get("name", ""),
                "endereco": properties.get("Endereço Completo", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            }
            
        except Exception as e:
            print(f"Erro ao buscar aluno no Notion: {str(e)}")
            return None
            
    async def buscar_aluno_por_email(self, email: str) -> Optional[Dict]:
        """
        Busca um aluno no banco de dados do Notion pelo email
        """
        try:
            url = f"{self.base_url}/databases/{self.database_id}/query"
            payload = {
                "filter": {
                    "property": "Email",
                    "email": {
                        "equals": email.lower()
                    }
                }
            }
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            if not data["results"]:
                return None
                
            # Pegar o primeiro resultado
            student = data["results"][0]
            properties = student["properties"]
            
            # Mapear os dados do aluno com os campos corretos
            return {
                "id": student["id"],
                "nome": properties.get("Student Name", {}).get("title", [{}])[0].get("text", {}).get("content", ""),
                "email": properties.get("Email", {}).get("email", ""),
                "telefone": properties.get("Telefone", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "cpf": properties.get("CPF", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "plano": properties.get("Plano", {}).get("select", {}).get("name", ""),
                "endereco": properties.get("Endereço Completo", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            }
            
        except Exception as e:
            print(f"Erro ao buscar aluno no Notion: {str(e)}")
            return None 